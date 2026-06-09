from datetime import datetime
import re


def parse_whatsapp(message, business_id=None, timestamp=None):
    """
    Examples:
    spent 500 on vegetables
    received 2000 from sale
    mila 1500 aaj
    """

    text = message.lower()

    amount_match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not amount_match:
        return None

    amount = float(amount_match.group(1))

    if any(word in text for word in ["received", "sale", "income", "mila"]):
        flow_type = "INFLOW"
    else:
        flow_type = "OUTFLOW"

    return {
        "timestamp": timestamp or datetime.utcnow(),
        "amount": amount,
        "flow_type": flow_type,
        "category": "Uncategorized",
        "description": message,
        "source": "whatsapp",
        "raw_input": message,
    }


def parse_sms(raw_sms, business_id=None, timestamp=None):
    text = raw_sms.lower()

    amount_match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not amount_match:
        return None

    amount = float(amount_match.group(1))

    flow_type = (
        "INFLOW"
        if ("credited" in text or "cr" in text)
        else "OUTFLOW"
    )

    return {
        "timestamp": timestamp or datetime.utcnow(),
        "amount": amount,
        "flow_type": flow_type,
        "category": "Bank",
        "description": raw_sms,
        "source": "sms",
        "raw_input": raw_sms,
    }


def parse_csv_row(row, business_id=None, col_map=None):
    try:
        date_col = "Date" if "Date" in row else list(row.keys())[0]
        amount_col = "Amount" if "Amount" in row else list(row.keys())[1]

        amount = float(row[amount_col])

        flow_type = "INFLOW" if amount >= 0 else "OUTFLOW"

        return {
            "timestamp": datetime.fromisoformat(row[date_col]),
            "amount": abs(amount),
            "flow_type": flow_type,
            "category": row.get("Category", "Uncategorized"),
            "description": row.get("Description", ""),
            "source": "csv",
        }

    except Exception:
        return None


def parse_erp_webhook(payload, business_id=None):
    try:
        return {
            "timestamp": datetime.utcnow(),
            "amount": float(payload.get("amount", 0)),
            "flow_type": payload.get("flow_type", "INFLOW"),
            "category": payload.get("category", "ERP"),
            "description": payload.get("description", ""),
            "source": "erp",
        }
    except Exception:
        return None

