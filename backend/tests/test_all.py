"""
Test suite for the Cash Flow MVP backend.
Run: pytest tests/ -v
"""

import pytest
from datetime import datetime
from app.ingestion.normalizer import (
    parse_sms, parse_whatsapp, parse_csv_row, parse_erp_webhook, infer_category
)
from app.ml.features import aggregate_daily, add_lag_features, FEATURE_COLUMNS
from app.ml.model import generate_forecast, compute_runway


# ===========================================================================
# Normalizer tests
# ===========================================================================

class TestSMSParser:
    BIZ_ID = "00000000-0000-0000-0000-000000000001"

    def test_hdfc_debit(self):
        sms = "Rs.1200.00 debited from A/c XX1234 on 15-Mar-24"
        result = parse_sms(sms, self.BIZ_ID)
        assert result is not None
        assert result["amount"] == 1200.0
        assert result["flow_type"] == "OUTFLOW"
        assert result["source"] == "sms"

    def test_sbi_credit(self):
        sms = "INR 5000 credited to your SBI account"
        result = parse_sms(sms, self.BIZ_ID)
        assert result is not None
        assert result["amount"] == 5000.0
        assert result["flow_type"] == "INFLOW"

    def test_upi_cr(self):
        sms = "UPI/CR/123456789/2500.00 PaymentFrom:RameshKumar"
        result = parse_sms(sms, self.BIZ_ID)
        assert result is not None
        assert result["amount"] == 2500.0
        assert result["flow_type"] == "INFLOW"

    def test_upi_dr(self):
        sms = "UPI/DR/987654321/800.00 Vegetables"
        result = parse_sms(sms, self.BIZ_ID)
        assert result is not None
        assert result["flow_type"] == "OUTFLOW"

    def test_unparseable_returns_none(self):
        result = parse_sms("Your OTP is 123456", self.BIZ_ID)
        assert result is None

    def test_comma_in_amount(self):
        sms = "Rs.12,500.00 debited from your account"
        result = parse_sms(sms, self.BIZ_ID)
        assert result is not None
        assert result["amount"] == 12500.0


class TestWhatsAppParser:
    BIZ_ID = "00000000-0000-0000-0000-000000000001"

    def test_spent_english(self):
        result = parse_whatsapp("spent 800 on vegetables", self.BIZ_ID)
        assert result is not None
        assert result["amount"] == 800.0
        assert result["flow_type"] == "OUTFLOW"
        assert result["category"] == "Inventory"

    def test_received_english(self):
        result = parse_whatsapp("received 3000 from customer", self.BIZ_ID)
        assert result is not None
        assert result["amount"] == 3000.0
        assert result["flow_type"] == "INFLOW"

    def test_sale(self):
        result = parse_whatsapp("sale 4500", self.BIZ_ID)
        assert result is not None
        assert result["amount"] == 4500.0
        assert result["flow_type"] == "INFLOW"

    def test_hindi_mila(self):
        result = parse_whatsapp("mila 2000 aaj", self.BIZ_ID)
        assert result is not None
        assert result["amount"] == 2000.0
        assert result["flow_type"] == "INFLOW"

    def test_rent_category(self):
        result = parse_whatsapp("paid 5000 rent", self.BIZ_ID)
        assert result is not None
        assert result["category"] == "Rent"

    def test_gas_transport(self):
        result = parse_whatsapp("spent 1200 on petrol", self.BIZ_ID)
        assert result is not None
        assert result["category"] == "Transport"


class TestCSVParser:
    BIZ_ID = "00000000-0000-0000-0000-000000000001"

    def test_standard_row(self):
        row = {
            "date": "2024-03-15",
            "amount": "1200",
            "type": "OUTFLOW",
            "description": "Vegetable purchase",
        }
        result = parse_csv_row(row, self.BIZ_ID)
        assert result is not None
        assert result["amount"] == 1200.0
        assert result["flow_type"] == "OUTFLOW"

    def test_negative_amount_infers_outflow(self):
        row = {"Date": "2024-03-15", "Amount": "-500"}
        result = parse_csv_row(row, self.BIZ_ID)
        assert result is not None
        assert result["flow_type"] == "OUTFLOW"

    def test_positive_amount_infers_inflow(self):
        row = {"Date": "2024-03-15", "Amount": "3000"}
        result = parse_csv_row(row, self.BIZ_ID)
        assert result is not None
        assert result["flow_type"] == "INFLOW"

    def test_missing_date_returns_none(self):
        row = {"amount": "500", "type": "INFLOW"}
        result = parse_csv_row(row, self.BIZ_ID)
        assert result is None

    def test_custom_column_map(self):
        row = {"txn_date": "2024-03-15", "value": "750", "narration": "Gas refill"}
        col_map = {"timestamp": "txn_date", "amount": "value", "description": "narration"}
        result = parse_csv_row(row, self.BIZ_ID, col_map)
        assert result is not None
        assert result["amount"] == 750.0


class TestERPParser:
    BIZ_ID = "00000000-0000-0000-0000-000000000001"

    def test_quickbooks_payment(self):
        payload = {
            "TxnDate": "2024-03-15",
            "TotalAmt": 5000.0,
            "TxnType": "Payment",
            "PrivateNote": "Sale to customer",
        }
        result = parse_erp_webhook(payload, self.BIZ_ID)
        assert result is not None
        assert result["amount"] == 5000.0
        assert result["flow_type"] == "INFLOW"

    def test_quickbooks_purchase(self):
        payload = {
            "TxnDate": "2024-03-15",
            "TotalAmt": 1200.0,
            "TxnType": "Purchase",
            "PrivateNote": "Inventory",
        }
        result = parse_erp_webhook(payload, self.BIZ_ID)
        assert result is not None
        assert result["flow_type"] == "OUTFLOW"

    def test_tally_receipt(self):
        payload = {
            "VoucherDate": "20240315",
            "Amount": 8000.0,
            "VoucherType": "Receipt",
            "Narration": "Customer payment",
        }
        result = parse_erp_webhook(payload, self.BIZ_ID)
        assert result is not None
        assert result["flow_type"] == "INFLOW"


class TestCategoryInference:
    def test_inventory(self):
        assert infer_category("bought vegetables from market") == "Inventory"

    def test_rent(self):
        assert infer_category("monthly rent payment") == "Rent"

    def test_staff(self):
        assert infer_category("paid salary to workers") == "Staff_Wages"

    def test_utility(self):
        assert infer_category("electricity bill paid") == "Utility"

    def test_unknown(self):
        assert infer_category("random thing xyz") == "Uncategorized"


# ===========================================================================
# Feature engineering tests
# ===========================================================================

class TestFeatureEngineering:
    def _make_transactions(self, n=30):
        import uuid, random
        txs = []
        base = datetime(2024, 1, 1)
        for i in range(n):
            txs.append({
                "id": str(uuid.uuid4()),
                "timestamp": base.replace(day=min(i + 1, 28)),
                "amount": random.uniform(500, 5000),
                "flow_type": "INFLOW" if random.random() > 0.3 else "OUTFLOW",
                "category": "Revenue",
            })
        return txs

    def test_aggregate_daily_shape(self):
        txs = self._make_transactions(30)
        daily = aggregate_daily(txs)
        assert "date" in daily.columns
        assert "daily_net" in daily.columns
        assert len(daily) > 0

    def test_no_missing_dates(self):
        txs = self._make_transactions(20)
        daily = aggregate_daily(txs)
        # All dates between min and max should be present
        expected_days = (daily["date"].max() - daily["date"].min()).days + 1
        assert len(daily) == expected_days

    def test_lag_features_present(self):
        txs = self._make_transactions(30)
        daily = aggregate_daily(txs)
        daily = add_lag_features(daily)
        for col in ["lag_1", "lag_7", "ma_7", "days_since_last_log", "day_of_week"]:
            assert col in daily.columns, f"Missing feature: {col}"

    def test_feature_columns_count(self):
        assert len(FEATURE_COLUMNS) >= 20


# ===========================================================================
# Forecast model tests
# ===========================================================================

class TestForecastModel:
    def _make_transactions(self, n=60):
        import uuid, random
        txs = []
        base = datetime(2024, 1, 1)
        for i in range(n):
            date = base + timedelta(days=i)
            if random.random() > 0.1:  # 90% of days have transactions
                txs.append({
                    "id": str(uuid.uuid4()),
                    "timestamp": date,
                    "amount": random.uniform(1000, 8000),
                    "flow_type": "INFLOW",
                    "category": "Revenue",
                })
                txs.append({
                    "id": str(uuid.uuid4()),
                    "timestamp": date,
                    "amount": random.uniform(200, 2000),
                    "flow_type": "OUTFLOW",
                    "category": "Inventory",
                })
        return txs

    def test_forecast_returns_predictions(self):
        from datetime import timedelta
        txs = self._make_transactions(60)
        result = generate_forecast(txs, "test-biz-001", horizon_days=30)
        assert "predictions" in result
        assert len(result["predictions"]) == 30

    def test_forecast_prediction_structure(self):
        from datetime import timedelta
        txs = self._make_transactions(60)
        result = generate_forecast(txs, "test-biz-002", horizon_days=30)
        first = result["predictions"][0]
        assert "date" in first
        assert "predicted_net" in first
        assert "cumulative_balance" in first

    def test_fallback_with_sparse_data(self):
        import uuid
        txs = [
            {"id": str(uuid.uuid4()), "timestamp": datetime(2024, 1, 1),
             "amount": 1000, "flow_type": "INFLOW", "category": "Revenue"},
        ]
        result = generate_forecast(txs, "test-biz-003", horizon_days=30)
        assert "predictions" in result
        assert result["metrics"].get("note") is not None   # fallback note

    def test_compute_runway_positive(self):
        preds = [
            {"date": "2024-01-01", "predicted_net": 100, "cumulative_balance": 1000 + i * 100}
            for i in range(30)
        ]
        runway, risk_date = compute_runway(preds)
        assert runway is None   # never hits 0

    def test_compute_runway_deficit(self):
        preds = [
            {"date": f"2024-01-{i+1:02d}", "predicted_net": -200, "cumulative_balance": 1000 - i * 200}
            for i in range(10)
        ]
        runway, _ = compute_runway(preds)
        assert runway is not None
        assert runway <= 5