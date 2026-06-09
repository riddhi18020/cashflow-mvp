"""
LightGBM Forecast Model
========================
Trains a gradient-boosted tree model on historical daily cashflow data.
Predicts daily_net_cashflow for the next N days.

Why LightGBM over ARIMA or LSTM:
- Handles missing/sparse days natively (no interpolation needed)
- Works well with small datasets (< 1 year of history)
- Supports exogenous features (weather, holidays) out of the box
- Fast training — re-trains per business on every forecast request
"""

import os
import json
import pickle
import numpy as np
import pandas as pd
import lightgbm as lgb
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error

from app.ml.features import (
    get_training_data,
    get_inference_data,
    FEATURE_COLUMNS,
    aggregate_daily,
)
from app.core.config import get_settings

settings = get_settings()

MODEL_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
os.makedirs(MODEL_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# LightGBM hyperparameters
# ---------------------------------------------------------------------------

LGBM_PARAMS = {
    "objective":        "regression",
    "metric":           "mae",
    "boosting_type":    "gbdt",
    "num_leaves":       31,
    "learning_rate":    0.05,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq":     5,
    "min_child_samples": 5,       # low — important for small datasets
    "n_estimators":     300,
    "verbose":          -1,
}


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train_model(
    transactions: List[dict],
    business_id: str,
    city: str = "Mumbai",
) -> Tuple[lgb.LGBMRegressor, dict]:
    """
    Train a LightGBM model for a single business.
    Uses TimeSeriesSplit cross-validation.

    Returns: (trained model, metrics dict)
    """
    X, y, dates = get_training_data(transactions, city=city)

    if len(X) < settings.MIN_HISTORY_DAYS:
        raise ValueError(
            f"Not enough history to train. Need {settings.MIN_HISTORY_DAYS} days, "
            f"got {len(X)}. Keep logging transactions!"
        )

    model = lgb.LGBMRegressor(**LGBM_PARAMS)

    # Rolling time-series cross validation (NEVER use random split for time series)
    metrics = {"mae_scores": [], "rmse_scores": []}

    if len(X) >= 30:
        tscv = TimeSeriesSplit(n_splits=3)
        for train_idx, val_idx in tscv.split(X):
            X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]
            model.fit(X_tr, y_tr)
            preds = model.predict(X_val)
            metrics["mae_scores"].append(float(mean_absolute_error(y_val, preds)))
            metrics["rmse_scores"].append(float(np.sqrt(mean_squared_error(y_val, preds))))

    # Final fit on all data
    model.fit(X, y)

    metrics["avg_mae"]  = float(np.mean(metrics["mae_scores"])) if metrics["mae_scores"] else None
    metrics["avg_rmse"] = float(np.mean(metrics["rmse_scores"])) if metrics["rmse_scores"] else None
    metrics["training_days"] = len(X)
    metrics["feature_importance"] = dict(zip(FEATURE_COLUMNS, model.feature_importances_.tolist()))

    # Save model to disk
    model_path = os.path.join(MODEL_DIR, f"{business_id}.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    return model, metrics


def load_model(business_id: str) -> Optional[lgb.LGBMRegressor]:
    """Load a saved model for a business. Returns None if not trained yet."""
    model_path = os.path.join(MODEL_DIR, f"{business_id}.pkl")
    if not os.path.exists(model_path):
        return None
    with open(model_path, "rb") as f:
        return pickle.load(f)


# ---------------------------------------------------------------------------
# Prediction & Forecast Generation
# ---------------------------------------------------------------------------

def generate_forecast(
    transactions: List[dict],
    business_id: str,
    city: str = "Mumbai",
    horizon_days: int = 90,
    retrain: bool = False,
) -> dict:
    """
    Main entry point: generate a cash flow forecast for a business.

    Steps:
    1. Load or train model
    2. Build inference feature matrix
    3. Predict day-by-day (autoregressive — each prediction feeds next lag)
    4. Compute cumulative balance and runway
    5. Generate plain-language alert

    Returns a dict with:
    - predictions: list of {date, predicted_net, cumulative_balance}
    - runway_days: days until balance hits 0
    - first_risk_date: first date below safety buffer
    - alert_message: plain-language warning
    - metrics: training metrics
    """
    # Get current balance from history
    daily_history = aggregate_daily(transactions)
    current_balance = float(daily_history["daily_net"].sum()) if len(daily_history) > 0 else 0.0

    # Train or load model
    model = None if retrain else load_model(business_id)
    metrics = {}

    if model is None:
        if len(transactions) < settings.MIN_HISTORY_DAYS:
            # Not enough data — use simple moving average fallback
            return _fallback_forecast(transactions, current_balance, horizon_days)
        model, metrics = train_model(transactions, business_id, city)

    # Build inference features
    X_future, future_dates = get_inference_data(transactions, city=city, horizon_days=horizon_days)

    if len(X_future) == 0:
        return _fallback_forecast(transactions, current_balance, horizon_days)

    # Autoregressive prediction:
    # Each day's prediction is used to update lag features for the next day.
    # This gives a realistic compounding forecast rather than flat extrapolation.
    X_arr = X_future.values.copy()
    predicted_nets = []

    lag_cols_idx = {col: i for i, col in enumerate(FEATURE_COLUMNS)}

    for i in range(len(X_arr)):
        row = X_arr[i].reshape(1, -1)
        pred = float(model.predict(row)[0])
        import random

        pred += random.choice([
        -25000,
        -15000,
        -8000,
        5000,
        12000,
        20000,
        30000
])
        predicted_nets.append(pred)

        # Update lag features for subsequent rows
        if i + 1 < len(X_arr):
            if "lag_1" in lag_cols_idx:
                X_arr[i + 1, lag_cols_idx["lag_1"]] = pred
            if i + 1 >= 3 and "lag_3" in lag_cols_idx:
                X_arr[i + 1, lag_cols_idx["lag_3"]] = np.mean(predicted_nets[-3:])
            if i + 1 >= 7 and "lag_7" in lag_cols_idx:
                X_arr[i + 1, lag_cols_idx["lag_7"]] = np.mean(predicted_nets[-7:])
            if "ma_3" in lag_cols_idx:
                X_arr[i + 1, lag_cols_idx["ma_3"]] = np.mean(predicted_nets[-min(3, len(predicted_nets)):])
            if "ma_7" in lag_cols_idx:
                X_arr[i + 1, lag_cols_idx["ma_7"]] = np.mean(predicted_nets[-min(7, len(predicted_nets)):])

    # Build output predictions list
    predictions = []
    running_balance = current_balance

    for date, net in zip(future_dates, predicted_nets):
        running_balance += net
        predictions.append({
            "date":               date.strftime("%Y-%m-%d"),
            "predicted_net":      round(net, 2),
            "cumulative_balance": round(running_balance, 2),
        })

    # Compute runway
    runway_days, first_risk_date = compute_runway(predictions, safety_days=settings.SAFETY_BUFFER_DAYS)

    # Generate alert
    alert = generate_alert(
        current_balance=current_balance,
        runway_days=runway_days,
        first_risk_date=first_risk_date,
        predictions=predictions,
        safety_buffer_days=settings.SAFETY_BUFFER_DAYS,
    )

    return {
        "business_id":      business_id,
        "generated_at":     datetime.utcnow().isoformat(),
        "current_balance":  round(current_balance, 2),
        "horizon_days":     horizon_days,
        "predictions":      predictions,
        "runway_days":      runway_days,
        "first_risk_date":  first_risk_date,
        "alert_message":    alert,
        "metrics":          metrics,
    }


def compute_runway(predictions: list, safety_days: int = 7) -> Tuple[Optional[int], Optional[str]]:
    """
    Find how many days until cumulative balance hits zero.
    Also finds the first date where balance drops within the safety buffer.
    """
    runway_days = None
    first_risk_date = None

    for i, p in enumerate(predictions):
        bal = p["cumulative_balance"]
        if bal <= 0 and runway_days is None:
            runway_days = i
        # Safety buffer: alert if we'll run out within safety_days from this point
        future_idx = i + safety_days
        if future_idx < len(predictions):
            future_bal = predictions[future_idx]["cumulative_balance"]
            if future_bal <= 0 and first_risk_date is None:
                first_risk_date = p["date"]

    return runway_days, first_risk_date


def generate_alert(
    current_balance: float,
    runway_days: Optional[int],
    first_risk_date: Optional[str],
    predictions: list,
    safety_buffer_days: int = 7,
) -> str:
    """
    Convert numerical forecast into a plain-language actionable alert.
    Small merchants need clear actions, not graphs.
    """
    if runway_days is not None and runway_days <= 7:
        return (
            f"⚠️ CRITICAL: Your cash will run out in {runway_days} days. "
            f"Stop non-essential purchases immediately and focus on collecting "
            f"any outstanding payments today."
        )

    if first_risk_date:
        return (
            f"⚠️ WARNING: Your balance may drop dangerously low around {first_risk_date}. "
            f"Reduce inventory purchases by 25% this week and consider delaying any "
            f"large expenses until after that date."
        )

    if runway_days is not None and runway_days <= 30:
        return (
            f"📉 ATTENTION: Cash flow looks tight in {runway_days} days. "
            f"Review your largest expense categories and see if any can be reduced or deferred."
        )

    # Positive outlook
    if len(predictions) > 0:
        end_balance = predictions[-1]["cumulative_balance"]
        if end_balance > current_balance * 1.2:
            return (
                f"✅ HEALTHY: Your cash flow looks positive for the next {len(predictions)} days. "
                f"Projected balance: ₹{end_balance:,.0f}. Good time to restock inventory or invest in growth."
            )

    return (
        f"📊 STABLE: Your cash flow appears stable. Current balance: ₹{current_balance:,.0f}. "
        f"Keep logging daily transactions for more accurate forecasts."
    )


def _fallback_forecast(
    transactions: List[dict],
    current_balance: float,
    horizon_days: int,
) -> dict:
    """
    Simple moving average fallback when there's not enough data for LightGBM.
    Uses last 7 days average daily net as the daily prediction.
    """
    daily = aggregate_daily(transactions)
    if len(daily) > 0:
        avg_daily = float(daily["daily_net"].tail(7).mean())
    else:
        avg_daily = 0.0

    predictions = []
    running_balance = current_balance
    today = datetime.utcnow().date()

    for i in range(horizon_days):
        date = today + timedelta(days=i + 1)
        running_balance += avg_daily
        predictions.append({
            "date":               date.strftime("%Y-%m-%d"),
            "predicted_net":      round(avg_daily, 2),
            "cumulative_balance": round(running_balance, 2),
        })

    runway_days, first_risk_date = compute_runway(predictions)
    alert = generate_alert(current_balance, runway_days, first_risk_date, predictions)

    return {
        "business_id":     None,
        "generated_at":    datetime.utcnow().isoformat(),
        "current_balance": round(current_balance, 2),
        "horizon_days":    horizon_days,
        "predictions":     predictions,
        "runway_days":     runway_days,
        "first_risk_date": first_risk_date,
        "alert_message":   alert,
        "metrics":         {"note": "Fallback moving average — not enough history for ML model"},
    }