"""
Cash Flow Forecasting MVP — FastAPI Application
================================================
Entry point. Mounts all routers and sets up startup events.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.db.database import engine, init_timescaledb, SessionLocal
from app.db import models
from app.api import businesses, transactions, forecast, webhooks
from app.core.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create all tables + init TimescaleDB hypertable
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        init_timescaledb(db)
    except Exception as e:
        print(f"[Startup] TimescaleDB hypertable init skipped: {e}")
    finally:
        db.close()
    print("✅ Database ready")
    yield
    # Shutdown (nothing needed for local dev)


app = FastAPI(
    title="Cash Flow Forecasting MVP",
    description="""
## Small Business Cash Flow Forecasting

Predict your 30–90 day cash runway using transaction history + weather + holidays.

### Ingestion channels supported:
- **Manual** — direct API entry
- **SMS/UPI** — paste banking notification text
- **WhatsApp** — natural language messages
- **CSV** — drag-and-drop spreadsheet upload
- **ERP Webhook** — QuickBooks, Xero, Tally

### How it works:
1. Register your business
2. Log transactions via any channel
3. Hit `/forecast` to get a 90-day runway prediction
4. View the dashboard for charts and alerts
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# Allow React dev server to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routers
app.include_router(businesses.router)
app.include_router(transactions.router)
app.include_router(forecast.router)
app.include_router(webhooks.router)


@app.get("/", tags=["Health"])
def root():
    return {
        "status": "ok",
        "app":    "Cash Flow Forecasting MVP",
        "docs":   "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}