"""
Pydantic Schemas
================
Request and response models for all API endpoints.
Pydantic v2 syntax throughout.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal
from datetime import datetime
from uuid import UUID
import enum


# ---------------------------------------------------------------------------
# Business
# ---------------------------------------------------------------------------

class BusinessCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, examples=["Ramesh Golgappa Stall"])
    owner_phone: Optional[str] = Field(None, examples=["+919876543210"])
    business_type: Optional[Literal["micro_vendor", "boutique", "superstore"]] = "micro_vendor"
    city: Optional[str] = Field("Mumbai", examples=["Surat"])


class BusinessOut(BaseModel):
    id: UUID
    name: str
    owner_phone: Optional[str]
    business_type: Optional[str]
    city: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------

class TransactionCreate(BaseModel):
    timestamp: datetime = Field(..., examples=["2024-03-15T10:30:00"])
    amount: float = Field(..., gt=0, examples=[1200.0])
    flow_type: Literal["INFLOW", "OUTFLOW"]
    category: Optional[str] = Field("Uncategorized", examples=["Inventory"])
    description: Optional[str] = Field("", examples=["Bought vegetables from market"])
    source: Optional[str] = Field("manual", examples=["manual"])

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("amount must be positive. Use flow_type to indicate direction.")
        return v


class TransactionOut(BaseModel):
    id: UUID
    business_id: UUID
    timestamp: datetime
    amount: float
    flow_type: str
    category: Optional[str]
    description: Optional[str]
    source: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionListOut(BaseModel):
    total: int
    transactions: List[TransactionOut]


# ---------------------------------------------------------------------------
# SMS / WhatsApp ingestion
# ---------------------------------------------------------------------------

class SMSIngestRequest(BaseModel):
    raw_sms: str = Field(
        ...,
        examples=["Rs.1200.00 debited from A/c XX1234 on 15-Mar-24"],
        description="Raw SMS text from banking notification"
    )
    timestamp: Optional[datetime] = None


class WhatsAppMessage(BaseModel):
    message: str = Field(
        ...,
        examples=["spent 800 on vegetable stock today"],
        description="Natural language message from WhatsApp"
    )
    timestamp: Optional[datetime] = None


class IngestResponse(BaseModel):
    success: bool
    transaction: Optional[TransactionOut] = None
    error: Optional[str] = None
    raw_input: str


# ---------------------------------------------------------------------------
# CSV Upload
# ---------------------------------------------------------------------------

class CSVColumnMap(BaseModel):
    """Optional column mapping for CSV uploads."""
    timestamp: Optional[str] = None
    amount: Optional[str] = None
    flow_type: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None


class CSVUploadResponse(BaseModel):
    total_rows: int
    imported: int
    failed: int
    errors: List[str] = []


# ---------------------------------------------------------------------------
# ERP Webhook
# ---------------------------------------------------------------------------

class ERPWebhookRequest(BaseModel):
    provider: Literal["quickbooks", "xero", "tally"] = Field(..., examples=["quickbooks"])
    payload: dict = Field(..., description="Raw ERP event payload")


# ---------------------------------------------------------------------------
# Forecast
# ---------------------------------------------------------------------------

class ForecastRequest(BaseModel):
    horizon_days: int = Field(90, ge=7, le=365, examples=[90])
    retrain: bool = Field(False, description="Force model retraining")
    city: Optional[str] = Field(None, description="City for weather/holiday features")


class ForecastPoint(BaseModel):
    date: str
    predicted_net: float
    cumulative_balance: float


class ForecastOut(BaseModel):
    business_id: str
    generated_at: str
    current_balance: float
    horizon_days: int
    predictions: List[ForecastPoint]
    runway_days: Optional[int]
    first_risk_date: Optional[str]
    alert_message: str
    metrics: dict


# ---------------------------------------------------------------------------
# Dashboard summary
# ---------------------------------------------------------------------------

class DailySummary(BaseModel):
    date: str
    daily_net: float
    daily_inflow: float
    daily_outflow: float
    tx_count: int


class DashboardSummary(BaseModel):
    business: BusinessOut
    total_balance: float
    last_30_days_net: float
    last_30_days_inflow: float
    last_30_days_outflow: float
    daily_history: List[DailySummary]
    latest_forecast: Optional[ForecastOut] = None
    transaction_count: int