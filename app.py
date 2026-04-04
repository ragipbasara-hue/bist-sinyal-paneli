
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import requests
from flask import Flask, jsonify, request
from supabase import Client, create_client


app = Flask(__name__)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


# ========= ENV =========
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
SUPABASE_STATE_TABLE = os.getenv("SUPABASE_STATE_TABLE", "signal_state").strip()
SUPABASE_HISTORY_TABLE = os.getenv("SUPABASE_HISTORY_TABLE", "signal_history").strip()

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()
REQUIRE_SECRET = os.getenv("REQUIRE_SECRET", "false").strip().lower() == "true"

REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "12"))


# ========= SUPABASE =========
supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client initialized.")
    except Exception as e:
        logger.exception("Supabase client init failed: %s", e)
        supabase = None
else:
    logger.warning("Supabase env eksik. DB kayıtları pas geçilecek.")


# ========= HELPERS =========
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_signal(value: Any) -> Optional[str]:
    if value is None:
        return None

    text = str(value).strip().lower()

    long_values = {"long", "buy", "bull", "up", "1", "true", "yes", "al"}
    short_values = {"short", "sell", "bear", "down", "-1", "false", "no", "sat"}

    if text in long_values:
        return "long"
    if text in short_values:
        return "short"
    return None


def get_payload_value(data: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return None


def get_symbol(data: Dict[str, Any]) -> str:
    symbol = get_payload_value(data, "symbol", "ticker", "coin", "pair")
    return str(symbol).strip().upper() if symbol else "COIN"


def get_price(data: Dict[str, Any]) -> Optional[float]:
    raw_price = get_payload_value(
        data,
        "price",
        "close",
        "signal_price",
        "entry_price",
        "market_price",
        "last_price",
    )
    if raw_price in (None, ""):
        return None

    try:
        return float(raw_price)
    except Exception:
        try:
            return float(str(raw_price).replace(",", ""))
        except Exception:
            return None


def format_price(price: Optional[float]) -> str:
    if price is None:
        return "Bilinmiyor"
    if price >= 1000:
        return f"{price:,.2f}"
    if price >= 1:
        return f"{price:.4f}"
    return f"{price:.8f}"


def classify_signal(
    tf_1h: Optional[str],
    tf_4h: Optional[str],
    tf_1d: Optional[str],
    tf_1w: Optional[str],
) -> Tuple[Optional[int], Optional[str]]:
    """
    Long tarafı giriş:
    1  -> ERKEN AL
    2  -> GÜÇLÜ AL
    3  -> ÇOK GÜÇLÜ AL

    Short tarafı sadece çıkış yönetimi:
    -1 -> KÂR AL
    -2 -> ÇIK
    -3 -> TREND BİTTİ
    """

    # Öncelik: çıkış yönetimi
    if tf_1d == "short":
        return -3, "TREND BİTTİ"

    if tf_4h == "short":
        return -2, "ÇIK"

    if tf_1h == "short":
        return -1, "KÂR AL"

    # Giriş sinyalleri
    if tf_1h == "long" and tf_4h == "long" and tf_1d == "long" and tf_1w == "long":
        return 3, "ÇOK GÜÇLÜ AL"

    if tf_1h == "long" and tf_4h == "long" and tf_1d == "long":
        return 2, "GÜÇLÜ AL"

    if tf_1h == "long" and tf_4h == "long":
        return 1, "ERKEN AL"

    return None, None


def build_message(symbol: str, action: str, price: Optional[float]) -> str:
    return f"{symbol} — {action}\nFiyat: {format_price(price)}"


def validate_secret(req) -> Tuple[bool, Optional[str]]:
    if not REQUIRE_SECRET:
        return True, None

    header_secret = (req.headers.get("X-Webhook-Secret") or "").strip()
    query_secret = (req.args.get("secret") or "").strip()

    candidate = header_secret or query_secret
    if not WEBHOOK_SECRET:
        return False, "REQUIRE_SECRET=true ama WEBHOOK_SECRET tanımlı değil."

    if candidate != WEBHOOK_SECRET:
        return False, "Geçersiz webhook secret."

    return True, None


def send_telegram_message(text: str) -> Tuple[bool, str]:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        msg = "Telegram env eksik."
        logger.warning(msg)
        return False, msg

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
    }

    try:
        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        logger.info("Telegram mesajı gönderildi.")
        return True, "ok"
    except Exception as e:
        logger.exception("Telegram gönderim hatası: %s", e)
        return False, str(e)


def fetch_last_state(symbol: str) -> Optional[Dict[str, Any]]:
    if not supabase:
        return None

    try:
        response = (
            supabase
            .table(SUPABASE_STATE_TABLE)
            .select("*")
            .eq("symbol", symbol)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None
    except Exception as e:
        logger.exception("State fetch hatası: %s", e)
        return None


def should_send_alert(new_level: Optional[int], last_level: Optional[int]) -> bool:
    if new_level is None:
        return False

    if last_level is None:
        return True

    if new_level == last_level:
        return False

    # Çıkış sinyalleri her değişimde gönderilsin
    if new_level < 0:
        return True

    # Long sinyalde zayıflama mesajı atma; sadece yeni / daha güçlü olunca gönder
    if new_level > 0:
        if last_level <= 0:
            return True
        return new_level > last_level

    return False


def upsert_state(
    symbol: str,
    action: str,
    alert_level: int,
    signal_price: Optional[float],
    tf_1h: Optional[str],
    tf_4h: Optional[str],
    tf_1d: Optional[str],
    tf_1w: Optional[str],
    raw_payload: Dict[str, Any],
) -> None:
    if not supabase:
        return

    row = {
        "symbol": symbol,
        "action": action,
        "alert_level": alert_level,
        "signal_price": signal_price,
        "tf_1h": tf_1h,
        "tf_4h": tf_4h,
        "tf_1d": tf_1d,
        "tf_1w": tf_1w,
        "raw_payload": raw_payload,
        "updated_at": utc_now_iso(),
    }

    try:
        (
            supabase
            .table(SUPABASE_STATE_TABLE)
            .upsert(row, on_conflict="symbol")
            .execute()
        )
        logger.info("State upsert tamamlandı: %s", symbol)
    except Exception as e:
        logger.exception("State upsert hatası: %s", e)


def insert_history(
    symbol: str,
    action: str,
    alert_level: int,
    signal_price: Optional[float],
    tf_1h: Optional[str],
    tf_4h: Optional[str],
    tf_1d: Optional[str],
    tf_1w: Optional[str],
    raw_payload: Dict[str, Any],
    telegram_sent: bool,
    telegram_message: str,
) -> None:
    if not supabase:
        return

    row = {
        "symbol": symbol,
        "action": action,
        "alert_level": alert_level,
        "signal_price": signal_price,
        "tf_1h": tf_1h,
        "tf_4h": tf_4h,
        "tf_1d": tf_1d,
        "tf_1w": tf_1w,
        "telegram_sent": telegram_sent,
        "telegram_message": telegram_message,
        "raw_payload": raw_payload,
        "created_at": utc_now_iso(),
    }

    try:
        supabase.table(SUPABASE_HISTORY_TABLE).insert(row).execute()
        logger.info("History insert tamamlandı: %s", symbol)
    except Exception as e:
        logger.exception("History insert hatası: %s", e)


# ========= ROUTES =========
@app.route("/", methods=["GET"])
def home():
    return jsonify(
        {
            "ok": True,
            "service": "tradingview-telegram-webhook",
            "time": utc_now_iso(),
        }
    ), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "ok": True,
            "supabase": bool(supabase),
            "telegram_configured": bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID),
            "time": utc_now_iso(),
        }
    ), 200


@app.route("/webhook", methods=["POST"])
def webhook():
    is_valid, error = validate_secret(request)
    if not is_valid:
        return jsonify({"ok": False, "error": error}), 401

    try:
        data = request.get_json(silent=True) or {}
        logger.info("Webhook geldi: %s", json.dumps(data, ensure_ascii=False))

        symbol = get_symbol(data)
        price = get_price(data)

        tf_1h = normalize_signal(get_payload_value(data, "tf_1h", "1h", "signal_1h"))
        tf_4h = normalize_signal(get_payload_value(data, "tf_4h", "4h", "signal_4h"))
        tf_1d = normalize_signal(get_payload_value(data, "tf_1d", "1d", "signal_1d"))
        tf_1w = normalize_signal(get_payload_value(data, "tf_1w", "1w", "signal_1w"))

        alert_level, action = classify_signal(tf_1h, tf_4h, tf_1d, tf_1w)

        if alert_level is None or action is None:
            logger.info("Sinyal oluşmadı: %s", symbol)
            return jsonify(
                {
                    "ok": True,
                    "message_sent": False,
                    "reason": "Uygun sinyal oluşmadı",
                }
            ), 200

        last_state = fetch_last_state(symbol) or {}
        last_level = last_state.get("alert_level")

        if last_level is not None:
            try:
                last_level = int(last_level)
            except Exception:
                last_level = None

        if not should_send_alert(alert_level, last_level):
            logger.info(
                "Tekrar eden / zayıflayan sinyal pas geçildi | %s | last=%s new=%s",
                symbol, last_level, alert_level
            )

            upsert_state(
                symbol=symbol,
                action=action,
                alert_level=alert_level,
                signal_price=price,
                tf_1h=tf_1h,
                tf_4h=tf_4h,
                tf_1d=tf_1d,
                tf_1w=tf_1w,
                raw_payload=data,
            )

            return jsonify(
                {
                    "ok": True,
                    "message_sent": False,
                    "reason": "Aynı veya daha zayıf sinyal, Telegram gönderilmedi",
                    "symbol": symbol,
                    "alert_level": alert_level,
                    "last_level": last_level,
                }
            ), 200

        message = build_message(symbol, action, price)
        sent, send_info = send_telegram_message(message)

        upsert_state(
            symbol=symbol,
            action=action,
            alert_level=alert_level,
            signal_price=price,
            tf_1h=tf_1h,
            tf_4h=tf_4h,
            tf_1d=tf_1d,
            tf_1w=tf_1w,
            raw_payload=data,
        )

        insert_history(
            symbol=symbol,
            action=action,
            alert_level=alert_level,
            signal_price=price,
            tf_1h=tf_1h,
            tf_4h=tf_4h,
            tf_1d=tf_1d,
            tf_1w=tf_1w,
            raw_payload=data,
            telegram_sent=sent,
            telegram_message=message,
        )

        return jsonify(
            {
                "ok": True,
                "message_sent": sent,
                "send_info": send_info,
                "symbol": symbol,
                "action": action,
                "alert_level": alert_level,
                "price": price,
            }
        ), 200

    except Exception as e:
        logger.exception("Webhook genel hata: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
