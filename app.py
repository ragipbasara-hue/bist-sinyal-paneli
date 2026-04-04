@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.get_json(force=True, silent=True) or {}

    symbol = str(payload.get("symbol", "")).upper().strip()
    price = str(payload.get("price", "")).strip()
    signals = payload.get("signals", {})

    if not symbol or not isinstance(signals, dict):
        return jsonify({
            "ok": False,
            "error": "Geçersiz veri. Beklenen: symbol, price ve signals objesi"
        }), 400

    valid = {"LONG", "SHORT", "NOTR", "AL", "SAT", "YOK"}

    tf_1h = str(signals.get("1h", "YOK")).upper().strip()
    tf_4h = str(signals.get("4h", "YOK")).upper().strip()
    tf_1d = str(signals.get("1d", "YOK")).upper().strip()
    tf_1w = str(signals.get("1w", "YOK")).upper().strip()

    tf_1h = tf_1h if tf_1h in valid else "YOK"
    tf_4h = tf_4h if tf_4h in valid else "YOK"
    tf_1d = tf_1d if tf_1d in valid else "YOK"
    tf_1w = tf_1w if tf_1w in valid else "YOK"

    now = datetime.now().isoformat()

    # Watchlist'te yoksa ekle
    supabase.table("watchlist").upsert(
        {"symbol": symbol},
        on_conflict="symbol"
    ).execute()

    # Eski alarm seviyesini çek
    existing = supabase.table("signals").select("alert_level").eq("symbol", symbol).execute()
    last_level = ""
    if existing.data:
        last_level = existing.data[0].get("alert_level") or ""

    # Yeni seviye hesapla
    level = detect_signal_level(tf_1h, tf_4h, tf_1d, tf_1w)

    # DB'ye yaz
    supabase.table("signals").upsert(
        {
            "symbol": symbol,
            "tf_1h": tf_1h,
            "tf_4h": tf_4h,
            "tf_1d": tf_1d,
            "tf_1w": tf_1w,
            "updated_at": now,
            "last_tf": "multi",
            "alert_level": level or ""
        },
        on_conflict="symbol"
    ).execute()

    telegram_result = None
    error_message = ""

    try:
        if level and level != last_level:
            telegram_text = format_signal_message(symbol, level, price)
            telegram_result = send_telegram_message(telegram_text)
    except Exception as e:
        error_message = str(e)

    return jsonify({
        "ok": True,
        "symbol": symbol,
        "price": price,
        "signals": {
            "1h": tf_1h,
            "4h": tf_4h,
            "1d": tf_1d,
            "1w": tf_1w
        },
        "level": level or "",
        "last_level": last_level,
        "telegram_result": telegram_result,
        "error": error_message
    })
