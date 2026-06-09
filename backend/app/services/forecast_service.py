"""Forecast service — persists and retrieves forecast results."""

import uuid
import json
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.db.models import Forecast


def save_forecast(db: Session, business_id: str, forecast_result: dict) -> Forecast:
    fc = Forecast(
        id=str(uuid.uuid4()),
        business_id=str(business_id),
        generated_at=datetime.utcnow(),
        horizon_days=forecast_result.get("horizon_days", 90),
        predictions_json=json.dumps(forecast_result.get("predictions", [])),
        runway_days=forecast_result.get("runway_days"),
        first_risk_date=(
            datetime.fromisoformat(forecast_result["first_risk_date"])
            if forecast_result.get("first_risk_date")
            else None
        ),
        alert_message=forecast_result.get("alert_message", ""),
    )
    db.add(fc)
    db.commit()
    db.refresh(fc)
    return fc


def get_latest_forecast(db: Session, business_id: str) -> Optional[Forecast]:
    return (
        db.query(Forecast)
        .filter(Forecast.business_id == str(business_id))
        .order_by(Forecast.generated_at.desc())
        .first()
    )


def forecast_to_dict(fc: Forecast, business_id: str, current_balance: float) -> dict:
    return {
        "business_id":     str(business_id),
        "generated_at":    fc.generated_at.isoformat(),
        "current_balance": current_balance,
        "horizon_days":    fc.horizon_days,
        "predictions":     json.loads(fc.predictions_json),
        "runway_days":     fc.runway_days,
        "first_risk_date": fc.first_risk_date.strftime("%Y-%m-%d") if fc.first_risk_date else None,
        "alert_message":   fc.alert_message,
        "metrics":         {},
    }