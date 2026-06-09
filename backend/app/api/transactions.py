"""
Transaction Routes
==================
Handles all ingestion channels:
- POST /transactions/           Manual entry
- POST /transactions/sms        SMS / UPI parse
- POST /transactions/whatsapp   WhatsApp natural language
- POST /transactions/csv        CSV file upload
- POST /transactions/erp        ERP webhook payload
- GET  /transactions/           List transactions
- DELETE /transactions/{id}     Delete one
"""

import io
import csv
import json
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.schemas import (
    TransactionCreate, TransactionOut, TransactionListOut,
    SMSIngestRequest, WhatsAppMessage, IngestResponse,
    CSVUploadResponse, CSVColumnMap, ERPWebhookRequest,
)
from app.services import transaction_service, business_service
from app.ingestion.normalizer import (
    parse_sms, parse_whatsapp, parse_csv_row, parse_erp_webhook
)

router = APIRouter(prefix="/businesses/{business_id}/transactions", tags=["Transactions"])


def _check_business(business_id: str, db: Session):
    biz = business_service.get_business(db, business_id)
    if not biz:
        raise HTTPException(404, "Business not found")
    return biz


# ---------------------------------------------------------------------------
# Manual entry
# ---------------------------------------------------------------------------

@router.post("/", response_model=TransactionOut, status_code=201)
def add_transaction(
    business_id: str,
    data: TransactionCreate,
    db: Session = Depends(get_db),
):
    """Manually add a single transaction."""
    _check_business(business_id, db)
    return transaction_service.create_transaction_from_schema(db, business_id, data)


# ---------------------------------------------------------------------------
# SMS ingestion
# ---------------------------------------------------------------------------

@router.post("/sms", response_model=IngestResponse)
def ingest_sms(
    business_id: str,
    req: SMSIngestRequest,
    db: Session = Depends(get_db),
):
    """
    Parse a banking SMS notification and log it as a transaction.

    Example: "Rs.1200.00 debited from A/c XX1234 on 15-Mar-24"
    """
    _check_business(business_id, db)
    parsed = parse_sms(req.raw_sms, business_id, req.timestamp)

    if not parsed:
        return IngestResponse(
            success=False,
            error="Could not parse SMS. Supported formats: HDFC/SBI/ICICI debit/credit alerts, UPI notifications.",
            raw_input=req.raw_sms,
        )

    tx = transaction_service.create_transaction(db, business_id, parsed)
    return IngestResponse(
        success=True,
        transaction=TransactionOut.model_validate(tx),
        raw_input=req.raw_sms,
    )


# ---------------------------------------------------------------------------
# WhatsApp ingestion
# ---------------------------------------------------------------------------

@router.post("/whatsapp", response_model=IngestResponse)
def ingest_whatsapp(
    business_id: str,
    req: WhatsAppMessage,
    db: Session = Depends(get_db),
):
    """
    Parse a casual WhatsApp message and log it as a transaction.

    Examples:
    - "spent 1200 on gas today"
    - "received 5000 from customer"
    - "mila 2000 aaj"
    """
    _check_business(business_id, db)
    parsed = parse_whatsapp(req.message, business_id, req.timestamp)

    if not parsed:
        return IngestResponse(
            success=False,
            error="Could not parse message. Try: 'spent 500 on stock' or 'received 2000 from sale'",
            raw_input=req.message,
        )

    tx = transaction_service.create_transaction(db, business_id, parsed)
    return IngestResponse(
        success=True,
        transaction=TransactionOut.model_validate(tx),
        raw_input=req.message,
    )


# ---------------------------------------------------------------------------
# CSV upload
# ---------------------------------------------------------------------------

@router.post("/csv", response_model=CSVUploadResponse)
async def upload_csv(
    business_id: str,
    file: UploadFile = File(...),
    column_map_json: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Upload a CSV file of historical transactions.

    The CSV should have columns for date, amount, and optionally
    type/category/description. Column names are auto-detected or
    can be specified via column_map_json.

    Example CSV:
    ```
    Date,Amount,Type,Description
    2024-03-01,5000,INFLOW,Morning sales
    2024-03-01,-1200,OUTFLOW,Bought vegetables
    ```
    """
    _check_business(business_id, db)

    # Parse optional column map
    col_map = None
    if column_map_json:
        try:
            col_map = json.loads(column_map_json)
        except json.JSONDecodeError:
            raise HTTPException(400, "column_map_json must be valid JSON")

    # Read CSV
    contents = await file.read()
    try:
        text = contents.decode("utf-8-sig")   # handle BOM
    except UnicodeDecodeError:
        text = contents.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    if not rows:
        raise HTTPException(400, "CSV file is empty")

    imported = 0
    failed = 0
    errors = []
    parsed_batch = []

    for i, row in enumerate(rows):
        parsed = parse_csv_row(row, business_id, col_map)
        if parsed:
            parsed_batch.append(parsed)
            imported += 1
        else:
            failed += 1
            if len(errors) < 10:   # cap error list
                errors.append(f"Row {i + 2}: Could not parse — {dict(row)}")

    if parsed_batch:
        transaction_service.bulk_create_transactions(db, business_id, parsed_batch)

    return CSVUploadResponse(
        total_rows=len(rows),
        imported=imported,
        failed=failed,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# ERP webhook
# ---------------------------------------------------------------------------

@router.post("/erp", response_model=IngestResponse)
def ingest_erp_webhook(
    business_id: str,
    req: ERPWebhookRequest,
    db: Session = Depends(get_db),
):
    """
    Accept an ERP webhook payload (QuickBooks, Xero, or Tally).
    Normalizes into the standard transaction schema automatically.
    """
    _check_business(business_id, db)
    parsed = parse_erp_webhook(req.payload, business_id)

    if not parsed:
        return IngestResponse(
            success=False,
            error=f"Could not parse {req.provider} payload. Check the payload format.",
            raw_input=str(req.payload),
        )

    parsed["source"] = f"erp_{req.provider}"
    tx = transaction_service.create_transaction(db, business_id, parsed)
    return IngestResponse(
        success=True,
        transaction=TransactionOut.model_validate(tx),
        raw_input=str(req.payload),
    )


# ---------------------------------------------------------------------------
# List & delete
# ---------------------------------------------------------------------------

@router.get("/", response_model=TransactionListOut)
def list_transactions(
    business_id: str,
    days: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List transactions for a business. Filter by last N days optionally."""
    _check_business(business_id, db)
    txs = transaction_service.get_transactions(db, business_id, days=days, skip=skip, limit=limit)
    total = transaction_service.count_transactions(db, business_id)
    return TransactionListOut(
        total=total,
        transactions=[TransactionOut.model_validate(t) for t in txs],
    )


@router.delete("/{tx_id}", status_code=204)
def delete_transaction(business_id: str, tx_id: str, db: Session = Depends(get_db)):
    _check_business(business_id, db)
    if not transaction_service.delete_transaction(db, tx_id, business_id):
        raise HTTPException(404, "Transaction not found")