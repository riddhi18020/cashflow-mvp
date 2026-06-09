"""
Forecast Routes
===============
- POST /forecast        Generate a new 30/60/90-day forecast
- GET  /forecast        Get latest saved forecast
- GET  /dashboard       Full dashboard summary
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.schemas import ForecastRequest, ForecastOut, DashboardSummary, BusinessOut, DailySummary
from app.services import business_service, transaction_service, forecast_service
from app.ml.model import generate_forecast
from app.ml.features import aggregate_daily

router = APIRouter(prefix="/businesses/{business_id}", tags=["Forecast"])


def _check_business(business_id: str, db: Session):
    biz = business_service.get_business(db, business_id)
    if not biz:
        raise HTTPException(404, "Business not found")
    return biz


@router.post("/forecast", response_model=ForecastOut)
def run_forecast(
    business_id: str,
    req: ForecastRequest = ForecastRequest(),
    db: Session = Depends(get_db),
):
    """
    Generate a cash flow forecast for a business.

    - Trains (or reloads) a LightGBM model on all historical transactions
    - Predicts daily net cashflow for the next `horizon_days` days
    - Returns runway (days until balance hits 0) and a plain-language alert
    """
    biz = _check_business(business_id, db)

    transactions = transaction_service.get_all_transactions_as_dicts(db, business_id)

    city = req.city or biz.city or "Mumbai"

    result = generate_forecast(
        transactions=transactions,
        business_id=str(business_id),
        city=city,
        horizon_days=req.horizon_days,
        retrain=req.retrain,
    )

    # Persist forecast to DB
    forecast_service.save_forecast(db, business_id, result)

    return ForecastOut(**result)


@router.get("/forecast", response_model=ForecastOut)
def get_latest_forecast(business_id: str, db: Session = Depends(get_db)):
    """Get the most recently generated forecast for a business."""
    _check_business(business_id, db)

    fc = forecast_service.get_latest_forecast(db, business_id)
    if not fc:
        raise HTTPException(404, "No forecast generated yet. POST to /forecast first.")

    transactions = transaction_service.get_all_transactions_as_dicts(db, business_id)
    daily = aggregate_daily(transactions)
    current_balance = float(daily["daily_net"].sum()) if len(daily) > 0 else 0.0

    return ForecastOut(**forecast_service.forecast_to_dict(fc, business_id, current_balance))


@router.get("/dashboard", response_model=DashboardSummary)
def get_dashboard(business_id: str, db: Session = Depends(get_db)):
    """
    Full dashboard summary for the React frontend.
    Returns business info, 30-day history, balance, and latest forecast.
    """
    biz = _check_business(business_id, db)

    transactions = transaction_service.get_all_transactions_as_dicts(db, business_id)
    daily = aggregate_daily(transactions)

    total_balance    = float(daily["daily_net"].sum())           if len(daily) > 0 else 0.0
    last30            = daily.tail(30)
    last30_net        = float(last30["daily_net"].sum())         if len(last30) > 0 else 0.0
    last30_inflow     = float(last30["daily_inflow"].sum())      if len(last30) > 0 else 0.0
    last30_outflow    = float(last30["daily_outflow"].sum())     if len(last30) > 0 else 0.0

    daily_history = [
        DailySummary(
            date=str(row["date"])[:10],
            daily_net=float(row["daily_net"]),
            daily_inflow=float(row["daily_inflow"]),
            daily_outflow=float(row["daily_outflow"]),
            tx_count=int(row["tx_count"]),
        )
        for _, row in daily.tail(90).iterrows()
    ]

    # Latest forecast (optional)
    fc = forecast_service.get_latest_forecast(db, business_id)
    latest_forecast = None
    if fc:
        latest_forecast = ForecastOut(**forecast_service.forecast_to_dict(fc, business_id, total_balance))

    tx_count = transaction_service.count_transactions(db, business_id)

    return DashboardSummary(
        business=BusinessOut.model_validate(biz),
        total_balance=round(total_balance, 2),
        last_30_days_net=round(last30_net, 2),
        last_30_days_inflow=round(last30_inflow, 2),
        last_30_days_outflow=round(last30_outflow, 2),
        daily_history=daily_history,
        latest_forecast=latest_forecast,
        transaction_count=tx_count,
    )