"""Transaction service — database operations for transactions."""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.models import Transaction, FlowType
from app.api.schemas import TransactionCreate


def create_transaction(db: Session, business_id: str, data: dict) -> Transaction:
    tx = Transaction(
        id=str(data.get("id", str(uuid.uuid4()))),
        business_id=str(business_id),
        timestamp=data["timestamp"],
        amount=data["amount"],
        flow_type=FlowType(data["flow_type"]),
        category=data.get("category", "Uncategorized"),
        description=data.get("description", ""),
        source=data.get("source", "manual"),
        raw_input=data.get("raw_input", ""),
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def create_transaction_from_schema(
    db: Session, business_id: str, schema: TransactionCreate
) -> Transaction:
    data = {
        "id": str(uuid.uuid4()),
        "timestamp": schema.timestamp,
        "amount": schema.amount,
        "flow_type": schema.flow_type,
        "category": schema.category,
        "description": schema.description,
        "source": schema.source,
        "raw_input": "",
    }
    return create_transaction(db, business_id, data)


def bulk_create_transactions(db: Session, business_id: str, data_list: List[dict]) -> int:
    objs = []
    for data in data_list:
        tx = Transaction(
            id=str(data.get("id", str(uuid.uuid4()))),
            business_id=str(business_id),
            timestamp=data["timestamp"],
            amount=data["amount"],
            flow_type=FlowType(data["flow_type"]),
            category=data.get("category", "Uncategorized"),
            description=data.get("description", ""),
            source=data.get("source", "manual"),
            raw_input=data.get("raw_input", ""),
        )
        objs.append(tx)
    db.bulk_save_objects(objs)
    db.commit()
    return len(objs)


def get_transactions(
    db: Session,
    business_id: str,
    days: Optional[int] = None,
    skip: int = 0,
    limit: int = 500,
) -> List[Transaction]:
    query = db.query(Transaction).filter(
        Transaction.business_id == str(business_id)
    )
    if days:
        since = datetime.utcnow() - timedelta(days=days)
        query = query.filter(Transaction.timestamp >= since)
    return query.order_by(Transaction.timestamp.desc()).offset(skip).limit(limit).all()


def get_all_transactions_as_dicts(db: Session, business_id: str) -> List[dict]:
    txs = (
        db.query(Transaction)
        .filter(Transaction.business_id == str(business_id))
        .order_by(Transaction.timestamp.asc())
        .all()
    )
    return [
        {
            "id":        str(tx.id),
            "timestamp": tx.timestamp,
            "amount":    float(tx.amount),
            "flow_type": tx.flow_type.value,
            "category":  tx.category,
        }
        for tx in txs
    ]


def count_transactions(db: Session, business_id: str) -> int:
    return db.query(Transaction).filter(
        Transaction.business_id == str(business_id)
    ).count()


def delete_transaction(db: Session, tx_id: str, business_id: str) -> bool:
    tx = (
        db.query(Transaction)
        .filter(and_(
            Transaction.id == str(tx_id),
            Transaction.business_id == str(business_id)
        ))
        .first()
    )
    if not tx:
        return False
    db.delete(tx)
    db.commit()
    return True