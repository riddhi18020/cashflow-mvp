from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.api.schemas import BusinessCreate, BusinessOut
from app.services import business_service

router = APIRouter(prefix="/businesses", tags=["Businesses"])


@router.post("/", response_model=BusinessOut, status_code=201)
def create_business(data: BusinessCreate, db: Session = Depends(get_db)):
    """Register a new business / merchant."""
    return business_service.create_business(db, data)


@router.get("/", response_model=List[BusinessOut])
def list_businesses(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """List all registered businesses."""
    return business_service.list_businesses(db, skip=skip, limit=limit)


@router.get("/{business_id}", response_model=BusinessOut)
def get_business(business_id: str, db: Session = Depends(get_db)):
    biz = business_service.get_business(db, business_id)
    if not biz:
        raise HTTPException(404, "Business not found")
    return biz


@router.delete("/{business_id}", status_code=204)
def delete_business(business_id: str, db: Session = Depends(get_db)):
    if not business_service.delete_business(db, business_id):
        raise HTTPException(404, "Business not found")