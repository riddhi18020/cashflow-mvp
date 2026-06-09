"""
WhatsApp Cloud API Webhook
==========================
Two endpoints:
  GET  /webhook/whatsapp  — Meta verification challenge
  POST /webhook/whatsapp  — Incoming message handler

When a micro-vendor sends a WhatsApp message:
  1. We parse it with the normalizer
  2. Store it as a transaction
  3. Reply with a confirmation + balance summary
"""

from fastapi import APIRouter, Request, HTTPException, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.database import get_db
from app.services import business_service, transaction_service
from app.services.whatsapp_service import (
    verify_webhook,
    parse_incoming_message,
    send_text_message,
)
from app.ingestion.normalizer import parse_whatsapp
from app.ml.features import aggregate_daily

router = APIRouter(prefix="/webhook", tags=["WhatsApp Webhook"])


@router.get("/whatsapp", response_class=PlainTextResponse)
def whatsapp_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """Meta webhook verification — returns the challenge string if token matches."""
    result = verify_webhook(hub_mode, hub_verify_token, hub_challenge)
    if result:
        return result
    raise HTTPException(403, "Verification failed — check WHATSAPP_VERIFY_TOKEN in .env")


@router.post("/whatsapp")
async def whatsapp_incoming(request: Request, db: Session = Depends(get_db)):
    """
    Handle incoming WhatsApp messages from merchants.

    Flow:
    1. Parse the message payload
    2. Look up business by sender's phone number
    3. Parse transaction from message text
    4. Save to DB
    5. Reply with confirmation + current balance
    """
    payload = await request.json()

    msg = parse_incoming_message(payload)
    if not msg:
        return {"status": "ignored"}   # not a text message

    from_number  = msg["from_number"]
    message_text = msg["message_text"]

    # Look up business by phone number
    businesses = business_service.list_businesses(db, limit=1000)
    biz = next((b for b in businesses if b.owner_phone == from_number or
                b.owner_phone == f"+{from_number}"), None)

    if not biz:
        send_text_message(
            from_number,
            "👋 Hi! I don't recognize this number. "
            "Please register your business first at our portal, or ask your admin to link this number."
        )
        return {"status": "unregistered_number"}

    # Parse the transaction
    parsed = parse_whatsapp(message_text, str(biz.id), datetime.utcnow())

    if not parsed:
        send_text_message(
            from_number,
            "❓ I didn't understand that. Try:\n"
            "• 'spent 500 on vegetables'\n"
            "• 'received 2000 from sales'\n"
            "• 'paid 300 for gas'\n"
            "• 'mila 1500 aaj' (Hindi supported)"
        )
        return {"status": "parse_failed"}

    # Save transaction
    tx = transaction_service.create_transaction(db, str(biz.id), parsed)

    # Compute current balance for reply
    all_txs = transaction_service.get_all_transactions_as_dicts(db, str(biz.id))
    daily = aggregate_daily(all_txs)
    current_balance = float(daily["daily_net"].sum()) if len(daily) > 0 else 0.0

    # Format confirmation
    direction = "📈 Received" if tx.flow_type.value == "INFLOW" else "📉 Spent"
    reply = (
        f"✅ Logged!\n"
        f"{direction} ₹{float(tx.amount):,.0f} — {tx.category}\n"
        f"Balance: ₹{current_balance:,.0f}\n\n"
        f"Reply 'balance' for full report."
    )

    # Handle special commands
    if message_text.strip().lower() in ("balance", "report", "summary", "status"):
        reply = (
            f"📊 *{biz.name}*\n"
            f"Current Balance: ₹{current_balance:,.0f}\n"
            f"Transactions logged: {len(all_txs)}\n\n"
            f"For a full forecast, visit the dashboard."
        )

    send_text_message(from_number, reply)
    return {"status": "ok"}