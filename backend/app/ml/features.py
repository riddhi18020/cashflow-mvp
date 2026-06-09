"""
Feature Engineering Pipeline
=============================
Takes raw transaction history and produces the feature matrix
used by LightGBM for training and inference.

Key design decisions (from the plan):
- Use explicit lag features instead of ARIMA (handles missing days)
- Add days_since_last_log as an explicit sparsity feature
- Inject external signals: is_holiday, rain_mm
- Target: daily_net_cashflow = sum(inflows) - sum(outflows)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional
import requests
from app.core.config import get_settings

settings = get_settings()


# ---------------------------------------------------------------------------
# Step 1: Aggregate raw transactions to daily net cashflow
# ---------------------------------------------------------------------------

def aggregate_daily(transactions: List[dict]) -> pd.DataFrame:
    """
    Convert a list of transaction dicts to a daily aggregated DataFrame.

    Input:  list of transaction dicts (from DB or normalizer)
    Output: DataFrame with columns [date, daily_inflow, daily_outflow, daily_net, tx_count]

    Missing days are filled with 0 (not dropped) — critical for tree-based models.
    """
    if not transactions:
        return pd.DataFrame(columns=["date", "daily_net", "daily_inflow", "daily_outflow", "tx_count"])

    df = pd.DataFrame(transactions)
    df["date"] = pd.to_datetime(df["timestamp"]).dt.normalize()
    df["signed_amount"] = df.apply(
        lambda r: float(r["amount"]) if r["flow_type"] == "INFLOW" else -float(r["amount"]),
        axis=1
    )

    daily = df.groupby("date").agg(
        daily_net=("signed_amount", "sum"),
        daily_inflow=("signed_amount", lambda x: x[x > 0].sum()),
        daily_outflow=("signed_amount", lambda x: abs(x[x < 0].sum())),
        tx_count=("id", "count"),
    ).reset_index()

    # Fill missing dates with zeros
    if len(daily) > 1:
        full_range = pd.date_range(daily["date"].min(), daily["date"].max(), freq="D")
        daily = daily.set_index("date").reindex(full_range, fill_value=0).reset_index()
        daily.rename(columns={"index": "date"}, inplace=True)

    daily = daily.sort_values("date").reset_index(drop=True)
    return daily


# ---------------------------------------------------------------------------
# Step 2: Compute lag features
# ---------------------------------------------------------------------------

def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add rolling window and lag features for LightGBM.

    Features added:
    - lag_1, lag_3, lag_7: net cashflow N days ago
    - ma_3, ma_7, ma_30: moving average net cashflow
    - std_7, std_30: rolling std dev (volatility)
    - inflow_ma_7, outflow_ma_7: directional moving averages
    - tx_count_ma_7: transaction frequency trend
    - days_since_last_log: explicit sparsity signal
    - day_of_week, day_of_month, month: calendar features
    - is_month_start, is_month_end: wage/rent effect flags
    """
    df = df.copy()

    # Lag values
    for lag in [1, 3, 7, 14, 30]:
        df[f"lag_{lag}"] = df["daily_net"].shift(lag)

    # Moving averages — net cashflow
    for window in [3, 7, 30]:
        df[f"ma_{window}"] = df["daily_net"].rolling(window, min_periods=1).mean()
        df[f"std_{window}"] = df["daily_net"].rolling(window, min_periods=1).std().fillna(0)

    # Directional moving averages
    df["inflow_ma_7"]  = df["daily_inflow"].rolling(7, min_periods=1).mean()
    df["outflow_ma_7"] = df["daily_outflow"].rolling(7, min_periods=1).mean()

    # Transaction frequency trend
    df["tx_count_ma_7"] = df["tx_count"].rolling(7, min_periods=1).mean()

    # Sparsity signal — days since last non-zero transaction log
    df["has_tx"] = (df["tx_count"] > 0).astype(int)
    df["days_since_last_log"] = (
        df["has_tx"]
        .groupby((df["has_tx"] != df["has_tx"].shift()).cumsum())
        .cumcount()
    )

    # Calendar features
    df["day_of_week"]   = df["date"].dt.dayofweek          # 0=Monday
    df["day_of_month"]  = df["date"].dt.day
    df["month"]         = df["date"].dt.month
    df["is_month_start"] = (df["date"].dt.day <= 3).astype(int)
    df["is_month_end"]   = (df["date"].dt.day >= 28).astype(int)
    df["is_weekend"]     = (df["date"].dt.dayofweek >= 5).astype(int)

    # Cumulative balance (running total from day 1)
    df["cumulative_balance"] = df["daily_net"].cumsum()

    # Fill NaN lags with 0 (first few rows)
    lag_cols = [c for c in df.columns if c.startswith("lag_") or c.startswith("ma_") or c.startswith("std_")]
    df[lag_cols] = df[lag_cols].fillna(0)

    return df


# ---------------------------------------------------------------------------
# Step 3: Inject external features (weather + holidays)
# ---------------------------------------------------------------------------

def fetch_weather(city: str, date: datetime) -> dict:
    """
    Fetch historical weather for a city/date from OpenWeatherMap.
    Falls back to zeros if API key is not set or call fails.
    """
    if not settings.OPENWEATHER_API_KEY:
        return {"rain_mm": 0.0, "temp_celsius": None}

    try:
        # OpenWeatherMap historical data (requires paid plan for >5 days back)
        # For recent data, use the current forecast endpoint
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"q": city, "appid": settings.OPENWEATHER_API_KEY, "units": "metric"}
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()
        rain_mm = data.get("rain", {}).get("1h", 0.0) or 0.0
        temp    = data.get("main", {}).get("temp", None)
        return {"rain_mm": float(rain_mm), "temp_celsius": float(temp) if temp else None}
    except Exception:
        return {"rain_mm": 0.0, "temp_celsius": None}


INDIAN_HOLIDAYS_2024_2025 = {
    # National holidays (approximate — replace with a proper calendar API)
    "2024-01-26", "2024-03-25", "2024-04-14", "2024-04-17",
    "2024-05-23", "2024-08-15", "2024-10-02", "2024-10-12",
    "2024-10-13", "2024-11-01", "2024-11-15", "2024-12-25",
    "2025-01-26", "2025-03-14", "2025-04-14", "2025-08-15",
    "2025-10-02", "2025-10-20", "2025-10-21", "2025-10-22",
    "2025-12-25",
}


def is_holiday(date: datetime) -> bool:
    return date.strftime("%Y-%m-%d") in INDIAN_HOLIDAYS_2024_2025


def add_external_features(df: pd.DataFrame, city: str = "Mumbai") -> pd.DataFrame:
    """
    Add is_holiday and rain_mm columns to the daily DataFrame.
    Weather is fetched for future dates (forecast range); historical rows get 0.
    """
    df = df.copy()
    today = datetime.utcnow().date()

    df["is_holiday"] = df["date"].apply(lambda d: int(is_holiday(d)))
    df["rain_mm"] = 0.0

    # For future forecast dates, try to fetch weather forecast
    future_mask = df["date"].dt.date > today
    if future_mask.any() and settings.OPENWEATHER_API_KEY:
        weather = fetch_weather(city, datetime.utcnow())
        df.loc[future_mask, "rain_mm"] = weather["rain_mm"]

    return df


# ---------------------------------------------------------------------------
# Step 4: Full pipeline — transactions → feature matrix
# ---------------------------------------------------------------------------

FEATURE_COLUMNS = [
    "lag_1", "lag_3", "lag_7", "lag_14", "lag_30",
    "ma_3", "ma_7", "ma_30",
    "std_7", "std_30",
    "inflow_ma_7", "outflow_ma_7",
    "tx_count_ma_7",
    "days_since_last_log",
    "day_of_week", "day_of_month", "month",
    "is_month_start", "is_month_end", "is_weekend",
    "is_holiday", "rain_mm",
]


def build_feature_matrix(
    transactions: List[dict],
    city: str = "Mumbai",
    horizon_days: int = 90,
) -> pd.DataFrame:
    """
    Full pipeline: transactions → feature matrix for training or inference.

    For training:  returns historical rows with target column 'daily_net'
    For inference: appends future dates with lag features projected forward
    """
    # Aggregate to daily
    daily = aggregate_daily(transactions)

    # Extend with future dates for forecasting
    if len(daily) > 0:
        last_date = daily["date"].max()
        future_dates = pd.date_range(
            start=last_date + timedelta(days=1),
            periods=horizon_days,
            freq="D",
        )
        future_df = pd.DataFrame({
            "date": future_dates,
            "daily_net": np.nan,
            "daily_inflow": 0.0,
            "daily_outflow": 0.0,
            "tx_count": 0,
        })
        daily = pd.concat([daily, future_df], ignore_index=True)

    # Add features
    daily = add_lag_features(daily)
    daily = add_external_features(daily, city=city)

    return daily


def get_training_data(transactions: List[dict], city: str = "Mumbai"):
    """
    Returns X (features) and y (target) for LightGBM training.
    Only includes rows where the target (daily_net) is known.
    """
    df = build_feature_matrix(transactions, city=city, horizon_days=0)
    train_df = df[df["daily_net"].notna()].copy()

    X = train_df[FEATURE_COLUMNS].fillna(0)
    y = train_df["daily_net"]
    dates = train_df["date"]

    return X, y, dates


def get_inference_data(transactions: List[dict], city: str = "Mumbai", horizon_days: int = 90):
    """
    Returns feature matrix for future dates only (for prediction).
    """
    df = build_feature_matrix(transactions, city=city, horizon_days=horizon_days)
    future_df = df[df["daily_net"].isna()].copy()

    X = future_df[FEATURE_COLUMNS].fillna(0)
    dates = future_df["date"]

    return X, dates