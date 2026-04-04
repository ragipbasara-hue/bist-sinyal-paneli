from flask import Flask, request, jsonify, render_template_string
from datetime import datetime
from supabase import create_client
import requests
import os

app = Flask(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL ve SUPABASE_KEY environment variable olarak tanımlı olmalı.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

HTML = """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>BIST Sinyal Paneli</title>
  <style>
    :root {
      --bg: #f5f7fb;
      --card: #ffffff;
      --text: #1f2937;
      --muted: #6b7280;
      --border: #e5e7eb;
      --input-bg: #ffffff;
      --header-bg: #f3f4f6;

      --long-bg: rgba(34, 197, 94, 0.14);
      --short-bg: rgba(239, 68, 68, 0.14);

      --badge-long-bg: #dcfce7;
      --badge-long-text: #166534;

      --badge-short-bg: #fee2e2;
      --badge-short-text: #991b1b;

      --badge-neutral-bg: #e5e7eb;
      --badge-neutral-text: #374151;

      --badge-missing-bg: #fef3c7;
      --badge-missing-text: #92400e;

      --toolbar-btn-bg: #ffffff;
      --toolbar-btn-text: #111827;
    }

    body.dark {
      --bg: #0f172a;
      --card: #111827;
      --text: #e5e7eb;
      --muted: #9ca3af;
      --border: #253046;
      --input-bg: #0b1220;
      --header-bg: #172033;

      --long-bg: rgba(34, 197, 94, 0.18);
      --short-bg: rgba(239, 68, 68, 0.18);

      --badge-long-bg: #14532d;
      --badge-long-text: #dcfce7;

      --badge-short-bg: #7f1d1d;
      --badge-short-text: #fee2e2;

      --badge-neutral-bg: #374151;
      --badge-neutral-text: #e5e7eb;

      --badge-missing-bg: #78350f;
      --badge-missing-text: #fde68a;

      --toolbar-btn-bg: #172033;
      --toolbar-btn-text: #e5e7eb;
    }

    * { box-sizing: border-box; }

    body {
      font-family: Arial, sans-serif;
      margin: 24px;
      background: var(--bg);
      color: var(--text);
      transition: background 0.2s ease, color 0.2s ease;
    }

    h1 {
      margin-bottom: 8px;
      font-size: 28px;
    }

    .meta {
      color: var(--muted);
      margin-bottom: 16px;
      font-size: 15px;
    }

    .toolbar {
      display: flex;
      gap: 12px;
      margin-bottom: 16px;
      flex-wrap: wrap;
      align-items: center;
    }

    input, select, button {
      padding: 10px 12px;
      border: 1px solid var(--border);
      border-radius: 10px;
      background: var(--input-bg);
      color: var(--text);
      font-size: 15px;
    }

    button {
      cursor: pointer;
      background: var(--toolbar-btn-bg);
      color: var(--toolbar-btn-text);
    }

    .table-wrap {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 18px;
      overflow: hidden;
    }

    table {
      border-collapse: collapse;
      width: 100%;
      background: var(--card);
    }

    th, td {
      padding: 14px 12px;
      border-bottom: 1px solid var(--border);
      text-align: center;
      transition: background 0.2s ease;
    }

    th {
      background: var(--header-bg);
      font-size: 15px;
    }

    th:first-child,
    td:first-child {
      text-align: left;
      font-weight: 700;
    }

    tr:hover {
      filter: brightness(0.98);
    }

    .row-long td {
      background: var(--long-bg);
    }

    .row-short td {
      background: var(--short-bg);
    }

    .badge {
      display: inline-block;
      min-width: 72px;
      padding: 8px 12px;
      border-radius: 10px;
      font-weight: 700;
      letter-spacing: 0.2px;
    }

    .sig-LONG, .sig-AL {
      background: var(--badge-long-bg);
      color: var(--badge-long-text);
    }

    .sig-SHORT, .sig-SAT {
      background: var(--badge-short-bg);
      color: var(--badge-short-text);
    }

    .sig-NOTR {
      background: var(--badge-neutral-bg);
      color: var(--badge-neutral-text);
    }

    .sig-YOK {
      background: var(--badge-missing-bg);
      color: var(--badge-missing-text);
    }

    .small {
      color: var(--muted);
      font-size: 12px;
      margin-top: 4px;
    }

    .score {
      font-weight: 700;
      white-space: nowrap;
    }

    .footer-note {
      margin-top: 12px;
      color: var(--muted);
      font-size: 13px;
    }

    .symbol-cell {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }

    .remove-btn {
      border: 1px solid var(--border);
      background: transparent;
      border-radius: 8px;
      padding: 6px 10px;
      font-size: 13px;
    }

    .summary {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }

    .summary-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 14px;
    }

    .summary-title {
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 6px;
    }

    .summary-value {
      font-size: 24px;
      font-weight: 700;
    }
  </style>
</head>
<body>
  <h1>BIST Sinyal Paneli</h1>
  <div class="meta">1s / 4s / 1g / 1hf sinyallerini tek tabloda gösterir.</div>

  <div class="summary">
    <div class="summary-card">
      <div class="summary-title">İzlenen Varlık</div>
      <div class="summary-value" id="sumTotal">0</div>
    </div>
    <div class="summary-card">
      <div class="summary-title">4/4 LONG</div>
      <div class="summary-value" id="sumFullLong">0</div>
    </div>
    <div class="summary-card">
      <div class="summary-title">4/4 SHORT</div>
      <div class="summary-value" id="sumFullShort">0</div>
    </div>
    <div class="summary-card">
      <div class="summary-title">3+ LONG</div>
      <div class="summary-value" id="sumStrongLong">0</div>
    </div>
    <div class="summary-card">
      <div class="summary-title">3+ SHORT</div>
      <div class="summary-value" id="sumStrongShort">0</div>
    </div>
  </div>

  <div class="toolbar">
    <input id="search" placeholder="Hisse/Coin ara..." oninput="renderTable()">
    <select id="filter" onchange="renderTable()">
      <option value="ALL">Tümü</option>
      <option value="LONG">En az 1 LONG</option>
      <option value="SHORT">En az 1 SHORT</option>
      <option value="FULL_LONG">4/4 LONG</option>
      <option value="FULL_SHORT">4/4 SHORT</option>
      <option value="STRONG_LONG">3+ LONG</option>
      <option value="STRONG_SHORT">3+ SHORT</option>
    </select>
    <input id="newSymbol" placeholder="Varlık ekle (THYAO/BTCUSDT)" onkeydown="if(event.key==='Enter') addSymbol()">
    <button onclick="addSymbol()">Ekle</button>
    <button onclick="loadData()">Yenile</button>
    <button onclick="toggleTheme()">🌗 Tema</button>
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Varlık</th>
          <th>Skor</th>
          <th>1 Saat</th>
          <th>4 Saat</th>
          <th>1 Gün</th>
          <th>1 Hafta</th>
          <th>Son Güncelleme</th>
        </tr>
      </thead>
      <tbody id="tbody"></tbody>
    </table>
  </div>

  <div class="footer-note">
    Not: LONG/AL yeşil, SHORT/SAT kırmızı gösterilir. Watchlist panel üzerinden yönetilir.
  </div>

<script>
let rows = [];

function signalClass(value) {
  if (value === 'LONG' || value === 'AL') return 'sig-LONG';
  if (value === 'SHORT' || value === 'SAT') return 'sig-SHORT';
  if (value === 'NOTR') return 'sig-NOTR';
  return 'sig-YOK';
}

function countLong(row) {
  const vals = [row['1h'], row['4h'], row['1d'], row['1w']];
  return vals.filter(v => v === 'LONG' || v === 'AL').length;
}

function countShort(row) {
  const vals = [row['1h'], row['4h'], row['1d'], row['1w']];
  return vals.filter(v => v === 'SHORT' || v === 'SAT').length;
}

function matchesFilter(row, filter) {
  const longCount = countLong(row);
  const shortCount = countShort(row);

  if (filter === 'ALL') return true;
  if (filter === 'LONG') return longCount >= 1;
  if (filter === 'SHORT') return shortCount >= 1;
  if (filter === 'FULL_LONG') return longCount === 4;
  if (filter === 'FULL_SHORT') return shortCount === 4;
  if (filter === 'STRONG_LONG') return longCount >= 3;
  if (filter === 'STRONG_SHORT') return shortCount >= 3;
  return true;
}

function updateSummary(data) {
  const total = data.length;
  const fullLong = data.filter(r => countLong(r) === 4).length;
  const fullShort = data.filter(r => countShort(r) === 4).length;
  const strongLong = data.filter(r => countLong(r) >= 3).length;
  const strongShort = data.filter(r => countShort(r) >= 3).length;

  document.getElementById('sumTotal').textContent = total;
  document.getElementById('sumFullLong').textContent = fullLong;
  document.getElementById('sumFullShort').textContent = fullShort;
  document.getElementById('sumStrongLong').textContent = strongLong;
  document.getElementById('sumStrongShort').textContent = strongShort;
}

function renderTable() {
  const tbody = document.getElementById('tbody');
  const q = document.getElementById('search').value.trim().toUpperCase();
  const filter = document.getElementById('filter').value;

  const filtered = rows.filter(r =>
    r.symbol.includes(q) && matchesFilter(r, filter)
  );

  tbody.innerHTML = filtered.map(r => `
    <tr class="${r.row_class || ''}">
      <td>
        <div class="symbol-cell">
          <span>${r.symbol}</span>
          <button class="remove-btn" onclick="removeSymbol('${r.symbol}')">Sil</button>
        </div>
      </td>
      <td><span class="score">${r.score_text || '-'}</span></td>
      <td><span class="badge ${signalClass(r['1h'])}">${r['1h']}</span></td>
      <td><span class="badge ${signalClass(r['4h'])}">${r['4h']}</span></td>
      <td><span class="badge ${signalClass(r['1d'])}">${r['1d']}</span></td>
      <td><span class="badge ${signalClass(r['1w'])}">${r['1w']}</span></td>
      <td>
        <div>${r.updated_at || '-'}</div>
        <div class="small">${r.last_tf || ''}</div>
      </td>
    </tr>
  `).join('');

  updateSummary(filtered);
}

async function loadData() {
  const res = await fetch('/api/table');
  rows = await res.json();
  renderTable();
}

async function addSymbol() {
  const el = document.getElementById('newSymbol');
  const symbol = el.value.trim().toUpperCase();
  if (!symbol) return;

  await fetch('/api/add', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({symbol})
  });

  el.value = '';
  await loadData();
}

async function removeSymbol(symbol) {
  await fetch('/api/remove', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({symbol})
  });

  await loadData();
}

function toggleTheme() {
  document.body.classList.toggle('dark');
  localStorage.setItem(
    'theme',
    document.body.classList.contains('dark') ? 'dark' : 'light'
  );
}

(function initTheme() {
  const theme = localStorage.getItem('theme');
  if (theme === 'dark') {
    document.body.classList.add('dark');
  }
})();

loadData();
setInterval(loadData, 15000);
</script>
</body>
</html>
"""

def ensure_defaults():
    existing = supabase.table("watchlist").select("symbol").execute()
    if existing.data:
        return

    defaults = ["THYAO", "ASELS", "TUPRS", "EREGL", "KCHOL"]
    watch_rows = [{"symbol": s} for s in defaults]
    signal_rows = [{"symbol": s, "alert_level": ""} for s in defaults]

    supabase.table("watchlist").upsert(watch_rows, on_conflict="symbol").execute()
    supabase.table("signals").upsert(signal_rows, on_conflict="symbol").execute()

def is_long(val):
    return val in ["LONG", "AL"]

def is_short(val):
    return val in ["SHORT", "SAT"]

def calc_counts(row):
    vals = [row["1h"], row["4h"], row["1d"], row["1w"]]
    long_count = sum(1 for v in vals if is_long(v))
    short_count = sum(1 for v in vals if is_short(v))
    return long_count, short_count

def get_row_class(row):
    long_count, short_count = calc_counts(row)
    if long_count >= 3:
        return "row-long"
    if short_count >= 3:
        return "row-short"
    return ""

def get_score_text(row):
    long_count, short_count = calc_counts(row)
    if long_count > short_count:
        return f"{long_count}/4 LONG"
    if short_count > long_count:
        return f"{short_count}/4 SHORT"
    if long_count == 0 and short_count == 0:
        return "0/4"
    return f"{long_count}-{short_count}"

def sort_key(row):
    long_count, short_count = calc_counts(row)
    strength = max(long_count, short_count)
    direction_priority = 1 if long_count > short_count else 0
    return (-strength, -direction_priority, row["symbol"])

def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return {"ok": False, "error": "Telegram env eksik"}

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    }

    try:
        r = requests.post(url, json=payload, timeout=15)
        return {
            "ok": r.ok,
            "status_code": r.status_code,
            "response": r.text
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

def detect_signal_level(tf_1h, tf_4h, tf_1d, tf_1w):
    long_1h = tf_1h in ["LONG", "AL"]
    long_4h = tf_4h in ["LONG", "AL"]
    long_1d = tf_1d in ["LONG", "AL"]
    long_1w = tf_1w in ["LONG", "AL"]

    short_1h = tf_1h in ["SHORT", "SAT"]
    short_4h = tf_4h in ["SHORT", "SAT"]
    short_1d = tf_1d in ["SHORT", "SAT"]

    # EXIT mantığı
    if short_1d:
        return "TREND_BITTI"

    if short_4h:
        return "CIK"

    if short_1h:
        return "KAR_AL"

    # LONG mantığı
    if long_1h and long_4h and long_1d and long_1w:
        return "COK_GUCLU_AL"

    if long_1h and long_4h and long_1d:
        return "GUCLU_AL"

    if long_1h and long_4h:
        return "ERKEN_AL"

    return None

def format_signal_message(symbol, level, price):
    titles = {
        "ERKEN_AL": "🟢 ERKEN AL",
        "GUCLU_AL": "✅ GÜÇLÜ AL",
        "COK_GUCLU_AL": "🚀 ÇOK GÜÇLÜ AL",
        "KAR_AL": "⚠️ KÂR AL",
        "CIK": "🔻 SAT",
        "TREND_BITTI": "⛔ DÜŞÜŞ TRENDİ"
    }

    title = titles.get(level, level or "")

    return f"{title}\n{symbol}\nFiyat: {price}"

@app.route("/")
def index():
    ensure_defaults()
    return render_template_string(HTML)

@app.route("/api/table")
def api_table():
    ensure_defaults()

    watch_res = supabase.table("watchlist").select("symbol").execute()
    sig_res = supabase.table("signals").select("*").execute()

    watchlist = [r["symbol"] for r in (watch_res.data or [])]
    signals_map = {r["symbol"]: r for r in (sig_res.data or [])}

    rows = []
    for symbol in watchlist:
        s = signals_map.get(symbol, {})
        item = {
            "symbol": symbol,
            "1h": s.get("tf_1h", "YOK"),
            "4h": s.get("tf_4h", "YOK"),
            "1d": s.get("tf_1d", "YOK"),
            "1w": s.get("tf_1w", "YOK"),
            "updated_at": s.get("updated_at") or "",
            "last_tf": s.get("last_tf") or ""
        }
        item["row_class"] = get_row_class(item)
        item["score_text"] = get_score_text(item)
        rows.append(item)

    rows.sort(key=sort_key)
    return jsonify(rows)

@app.route("/api/add", methods=["POST"])
def add_symbol():
    payload = request.get_json(force=True, silent=True) or {}
    symbol = str(payload.get("symbol", "")).upper().strip()

    if not symbol:
        return jsonify({"ok": False, "error": "Geçersiz varlık"}), 400

    supabase.table("watchlist").upsert(
        {"symbol": symbol},
        on_conflict="symbol"
    ).execute()

    supabase.table("signals").upsert(
        {"symbol": symbol, "alert_level": ""},
        on_conflict="symbol"
    ).execute()

    return jsonify({"ok": True, "symbol": symbol})

@app.route("/api/remove", methods=["POST"])
def remove_symbol():
    payload = request.get_json(force=True, silent=True) or {}
    symbol = str(payload.get("symbol", "")).upper().strip()

    supabase.table("watchlist").delete().eq("symbol", symbol).execute()
    return jsonify({"ok": True, "symbol": symbol})

@app.route("/test-telegram")
def test_telegram():
    result = send_telegram_message("✅ Telegram bağlantı testi başarılı.")
    return jsonify(result)

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

    supabase.table("watchlist").upsert(
        {"symbol": symbol},
        on_conflict="symbol"
    ).execute()

    existing = supabase.table("signals").select("alert_level").eq("symbol", symbol).execute()
    last_level = ""
    if existing.data:
        last_level = existing.data[0].get("alert_level") or ""

    level = detect_signal_level(tf_1h, tf_4h, tf_1d, tf_1w)

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

@app.route("/seed")
def seed():
    ensure_defaults()
    sig_res = supabase.table("signals").select("symbol").execute()
    symbols = [r["symbol"] for r in (sig_res.data or [])]

    if symbols:
        rows = [{
            "symbol": s,
            "tf_1h": "YOK",
            "tf_4h": "YOK",
            "tf_1d": "YOK",
            "tf_1w": "YOK",
            "updated_at": None,
            "last_tf": "",
            "alert_level": ""
        } for s in symbols]

        supabase.table("signals").upsert(rows, on_conflict="symbol").execute()

    return jsonify({"ok": True, "message": "Sinyaller sıfırlandı."})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
