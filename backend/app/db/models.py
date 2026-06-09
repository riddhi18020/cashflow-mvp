import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Numeric, Enum, Text,
    ForeignKey, Boolean, Float, Integer
)
from sqlalchemy.orm import relationship
from app.db.database import Base
import enum


class FlowType(str, enum.Enum):
    INFLOW = "INFLOW"
    OUTFLOW = "OUTFLOW"


class Business(Base):
    __tablename__ = "businesses"

    id            = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name          = Column(String(255), nullable=False)
    owner_phone   = Column(String(20), nullable=True)
    business_type = Column(String(50), nullable=True)
    city          = Column(String(100), nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

    transactions = relationship("Transaction", back_populates="business")
    forecasts    = relationship("Forecast", back_populates="business")


class Transaction(Base):
    __tablename__ = "transactions"

    id          = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(String(36), ForeignKey("businesses.id"), nullable=False)
    timestamp   = Column(DateTime, nullable=False, index=True)
    amount      = Column(Numeric(12, 2), nullable=False)
    flow_type   = Column(Enum(FlowType), nullable=False)
    category    = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    source      = Column(String(50), nullable=True)
    raw_input   = Column(Text, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="transactions")


class Forecast(Base):
    __tablename__ = "forecasts"

    id               = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id      = Column(String(36), ForeignKey("businesses.id"), nullable=False)
    generated_at     = Column(DateTime, default=datetime.utcnow)
    horizon_days     = Column(Integer, default=90)
    predictions_json = Column(Text, nullable=False)
    runway_days      = Column(Integer, nullable=True)
    first_risk_date  = Column(DateTime, nullable=True)
    alert_message    = Column(Text, nullable=True)

    business = relationship("Business", back_populates="forecasts")


class ExternalFeature(Base):
    __tablename__ = "external_features"

    id           = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    city         = Column(String(100), nullable=False)
    date         = Column(DateTime, nullable=False)
    is_holiday   = Column(Boolean, default=False)
    rain_mm      = Column(Float, default=0.0)
    temp_celsius = Column(Float, nullable=True)