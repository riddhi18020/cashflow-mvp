import uuid
from sqlalchemy.orm import Session
from app.db.models import Business
from app.api.schemas import BusinessCreate


def create_business(db: Session, data: BusinessCreate) -> Business:
    biz = Business(
        id=str(uuid.uuid4()),
        name=data.name,
        owner_phone=data.owner_phone,
        business_type=data.business_type,
        city=data.city or "Mumbai",
    )
    db.add(biz)
    db.commit()
    db.refresh(biz)
    return biz


def get_business(db: Session, business_id: str):
    return db.query(Business).filter(Business.id == str(business_id)).first()


def list_businesses(db: Session, skip: int = 0, limit: int = 50):
    return db.query(Business).offset(skip).limit(limit).all()


def delete_business(db: Session, business_id: str) -> bool:
    biz = get_business(db, business_id)
    if not biz:
        return False
    db.delete(biz)
    db.commit()
    return True