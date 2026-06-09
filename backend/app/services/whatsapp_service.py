"""
WhatsApp Business Cloud API integration.
Handles incoming messages and sends text/audio replies.
"""

import requests
from app.core.config import get_settings

settings = get_settings()

WHATSAPP_API_URL = "https://graph.facebook.com/v19.0"


def verify_webhook(mode: str, token: str, challenge: str) -> str | None:
    """Verify the webhook URL with Meta's verification challenge."""
    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        return challenge
    return None


def parse_incoming_message(payload: dict) -> dict | None:
    """
    Extract message text and sender phone from WhatsApp Cloud API webhook payload.

    Returns: {"from_number": str, "message_text": str, "timestamp": str} or None
    """
    try:
        entry = payload["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        messages = value.get("messages", [])
        if not messages:
            return None

        msg = messages[0]
        if msg.get("type") != "text":
            return None

        return {
            "from_number":   msg["from"],
            "message_text":  msg["text"]["body"],
            "timestamp":     msg.get("timestamp", ""),
            "message_id":    msg.get("id", ""),
        }
    except (KeyError, IndexError):
        return None


def send_text_message(to_number: str, text: str) -> bool:
    """Send a plain text reply via WhatsApp Cloud API."""
    if not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_ID:
        print(f"[WhatsApp] Would send to {to_number}: {text}")
        return True  # Dev mode — just log

    url = f"{WHATSAPP_API_URL}/{settings.WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text},
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"[WhatsApp] Send error: {e}")
        return False


def send_forecast_summary(to_number: str, forecast: dict) -> bool:
    """Send a formatted forecast summary as a WhatsApp message."""
    balance = forecast.get("current_balance", 0)
    runway = forecast.get("runway_days")
    alert = forecast.get("alert_message", "")

    lines = [
        f"📊 *Cash Flow Update*",
        f"Current Balance: ₹{balance:,.0f}",
    ]

    if runway:
        lines.append(f"Cash runway: ~{runway} days")

    lines.append(f"\n{alert}")
    lines.append("\nReply with your expenses anytime, e.g. 'spent 500 on stock'")

    return send_text_message(to_number, "\n".join(lines))