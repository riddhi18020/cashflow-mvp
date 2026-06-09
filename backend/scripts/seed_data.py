

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import uuid
import random
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.db.database import SessionLocal, engine
from app.db.models import Base, Business, Transaction, FlowType

random.seed(42)
np.random.seed(42)


def generate_transactions(business_id: str, city: str, profile: dict, start_date: datetime, days: int = 180):
    transactions = []
    HOLIDAYS = {
        "2024-01-26", "2024-03-25", "2024-04-14", "2024-08-15",
        "2024-10-02", "2024-10-13", "2024-12-25",
        "2025-01-26", "2025-03-14", "2025-08-15", "2025-12-25",
    }

    for day_offset in range(days):
        date = start_date + timedelta(days=day_offset)
        date_str = date.strftime("%Y-%m-%d")

        if random.random() < profile.get("miss_day_prob", 0):
            continue

        is_weekend = date.weekday() >= 5
        is_holiday_day = date_str in HOLIDAYS

        revenue_multiplier = 1.0
        if is_weekend:
            revenue_multiplier *= profile.get("weekend_multiplier", 1.3)
        if is_holiday_day:
            revenue_multiplier *= profile.get("holiday_multiplier", 0.5)

        daily_revenue = max(0, np.random.normal(
            profile["avg_daily_revenue"] * revenue_multiplier,
            profile["revenue_std"]
        ))

        if daily_revenue > 0:
            transactions.append(Transaction(
                id=str(uuid.uuid4()),
                business_id=business_id,   # already a str
                timestamp=date.replace(hour=random.randint(8, 20), minute=random.randint(0, 59)),
                amount=round(daily_revenue, 2),
                flow_type=FlowType.INFLOW,
                category="Revenue",
                description="Daily sales",
                source="seed",
                raw_input="",
            ))

        for (day_of_month, amount, category, desc) in profile.get("fixed_monthly", []):
            if date.day == day_of_month:
                transactions.append(Transaction(
                    id=str(uuid.uuid4()),
                    business_id=business_id,
                    timestamp=date.replace(hour=9, minute=0),
                    amount=round(amount * random.uniform(0.98, 1.02), 2),
                    flow_type=FlowType.OUTFLOW,
                    category=category,
                    description=desc,
                    source="seed",
                    raw_input="",
                ))

        for (prob, min_amt, max_amt, category, desc) in profile.get("random_expenses", []):
            if random.random() < prob:
                transactions.append(Transaction(
                    id=str(uuid.uuid4()),
                    business_id=business_id,
                    timestamp=date.replace(hour=random.randint(7, 18), minute=random.randint(0, 59)),
                    amount=round(random.uniform(min_amt, max_amt), 2),
                    flow_type=FlowType.OUTFLOW,
                    category=category,
                    description=desc,
                    source="seed",
                    raw_input="",
                ))

    return transactions


BUSINESS_PROFILES = [
    {
        "name": "Ramesh Golgappa Stall",
        "owner_phone": "+919876543210",
        "business_type": "micro_vendor",
        "city": "Surat",
        "profile": {
            "avg_daily_revenue": 2500, "revenue_std": 3500,
            "weekend_multiplier": 2.5, "holiday_multiplier": 4.0,
            "miss_day_prob": 0.20,
            "fixed_monthly": [
                 (1, 7000, "Rent", "Monthly stall rent"),
                 (7, 2500, "Utility", "Commercial gas cylinder refill"),
                 (14, 2500, "Utility", "Commercial gas cylinder refill"),
                 (21, 2500, "Utility", "Commercial gas cylinder refill"),
                 (15, 1200, "Inventory", "Supplier settlement payment"),
            ],
            "random_expenses": [
                (0.90, 300, 1500, "Inventory", "Vegetables and spices purchase"),
                (0.40, 100, 800, "Transport", "Auto fare to market"),
                (0.08, 2000, 8000, "Maintenance", "Cart repair"),
                (0.05, 5000, 20000, "Emergency", "Family medical expense"),
                (0.08, 500, 2500, "Utility", "Unexpected operating expense"),
            ],
        },
    },
    {
        "name": "Priya Fashion Boutique",
        "owner_phone": "+919988776655",
        "business_type": "boutique",
        "city": "Mumbai",
        "profile": {
            "avg_daily_revenue": 8500, "revenue_std": 3000,
            "weekend_multiplier": 1.8, "holiday_multiplier": 2.0,
            "miss_day_prob": 0.05,
            "fixed_monthly": [
                (1, 25000, "Rent", "Shop rent"),
                (5, 40000, "Staff_Wages", "Staff salaries"),
                (1, 3000, "Utility", "Electricity bill"),
                (1, 1500, "Utility", "Internet and phone"),
            ],
            "random_expenses": [
                (0.3, 5000, 20000, "Inventory", "New clothing stock"),
                (0.1, 500, 2000, "Marketing", "Instagram ads"),
                (0.1, 200, 800, "Utility", "Packing materials"),
            ],
        },
    },
    {
        "name": "City Fresh Superstore",
        "owner_phone": "+917766554433",
        "business_type": "superstore",
        "city": "Ahmedabad",
        "profile": {
            "avg_daily_revenue": 45000, "revenue_std": 12000,
            "weekend_multiplier": 1.4, "holiday_multiplier": 1.8,
            "miss_day_prob": 0.0,
            "fixed_monthly": [
                (1, 80000, "Rent", "Store rent"),
                (5, 200000, "Staff_Wages", "Staff salaries"),
                (1, 15000, "Utility", "Electricity"),
                (1, 5000, "Utility", "Internet and POS systems"),
            ],
            "random_expenses": [
                (0.9, 20000, 80000, "Inventory", "Wholesale grocery stock"),
                (0.3, 2000, 8000, "Transport", "Delivery and logistics"),
                (0.2, 1000, 5000, "Utility", "Maintenance and repairs"),
            ],
        },
    },
]


def seed(db: Session):
    print("🌱 Seeding database with sample businesses and transactions...")

    db.query(Transaction).filter(Transaction.source == "seed").delete()
    db.query(Business).delete()
    db.commit()

    start_date = datetime.now() - timedelta(days=180)

    for bp in BUSINESS_PROFILES:
        biz_id = str(uuid.uuid4())
        biz = Business(
            id=biz_id,
            name=bp["name"],
            owner_phone=bp["owner_phone"],
            business_type=bp["business_type"],
            city=bp["city"],
        )
        db.add(biz)
        db.commit()

        txs = generate_transactions(
            business_id=biz_id,
            city=bp["city"],
            profile=bp["profile"],
            start_date=start_date,
            days=180,
        )

        db.bulk_save_objects(txs)
        db.commit()
        print(f"  ✅ {biz.name}: {len(txs)} transactions")

    print("\n✅ Seed complete!")
    print("   Visit http://localhost:8000/businesses to see the data.")
    print("   Then POST to /businesses/{id}/forecast to generate your first forecast.")


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
