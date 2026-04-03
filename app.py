from flask import Flask, request, jsonify, render_template_string
from datetime import datetime
import json
import os

app = Flask(__name__)

DATA_FILE = "signals.json"
WATCHLIST_FILE = "watchlist.json"
TIMEFRAMES = ["1h", "4h", "1d", "1w"]

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
      <div class="summary-title">İzlenen Hisse</div>
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
    <input id="search" placeholder="Hisse ara..." oninput="renderTable()">
    <select id="filter" onchange="renderTable()">
      <option value="ALL">Tümü</option>
      <option value="LONG">En az 1 LONG</option>
      <option value="SHORT">En az 1 SHORT</option>
      <option value="FULL_LONG">4/4 LONG</option>
      <option value="FULL_SHORT">4/4 SHORT</option>
      <option value="STRONG_LONG">3+ LONG</option>
      <option value="STRONG_SHORT">3+ SHORT</option>
    </select>
    <input id="newSymbol" placeholder="Hisse ekle (THYAO)" onkeydown="if(event.key==='Enter') addSymbol()">
    <button onclick="addSymbol()">Ekle</button>
    <button onclick="loadData()">Yenile</button>
    <button onclick="toggleTheme()">🌗 Tema</button>
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Hisse</th>
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
    Not: Watchlist artık panel üzerinden yönetilir. LONG/AL yeşil, SHORT/SAT kırmızı gösterilir.
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


def load_json_file(path, default_value):
    if not os.path.exists(path):
        return default_value
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_value


def save_json_file(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_signals():
    return load_json_file(DATA_FILE, {})


def save_signals(data):
    save_json_file(DATA_FILE, data)


def load_watchlist():
    watchlist = load_json_file(WATCHLIST_FILE, [])
    cleaned = []
    for symbol in watchlist:
        s = str(symbol).upper().strip()
        if s and s not in cleaned:
            cleaned.append(s)
    return cleaned


def save_watchlist(watchlist):
    cleaned = []
    for symbol in watchlist:
        s = str(symbol).upper().strip()
        if s and s not in cleaned:
            cleaned.append(s)
    save_json_file(WATCHLIST_FILE, cleaned)


def ensure_watchlist_file():
    if not os.path.exists(WATCHLIST_FILE):
        save_watchlist(["THYAO", "ASELS", "TUPRS", "EREGL", "KCHOL"])


def ensure_signals_for_watchlist(data, watchlist):
    for symbol in watchlist:
        data.setdefault(symbol, {
            "1h": "YOK",
            "4h": "YOK",
            "1d": "YOK",
            "1w": "YOK",
            "updated_at": "",
            "last_tf": ""
        })
    return data


def is_long(val):
    return val in ["LONG", "AL"]


def is_short(val):
    return val in ["SHORT", "SAT"]


def calc_counts(row):
    vals = [
        row.get("1h", "YOK"),
        row.get("4h", "YOK"),
        row.get("1d", "YOK"),
        row.get("1w", "YOK")
    ]
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


@app.route("/")
def index():
    ensure_watchlist_file()
    return render_template_string(HTML)


@app.route("/api/table")
def api_table():
    ensure_watchlist_file()
    watchlist = load_watchlist()
    data = ensure_signals_for_watchlist(load_signals(), watchlist)
    save_signals(data)

    rows = []
    for symbol in watchlist:
        row = data.get(symbol, {})
        item = {
            "symbol": symbol,
            "1h": row.get("1h", "YOK"),
            "4h": row.get("4h", "YOK"),
            "1d": row.get("1d", "YOK"),
            "1w": row.get("1w", "YOK"),
            "updated_at": row.get("updated_at", ""),
            "last_tf": row.get("last_tf", "")
        }
        item["row_class"] = get_row_class(item)
        item["score_text"] = get_score_text(item)
        rows.append(item)

    rows.sort(key=sort_key)
    return jsonify(rows)


@app.route("/api/add", methods=["POST"])
def add_symbol():
    ensure_watchlist_file()
    payload = request.get_json(force=True, silent=True) or {}
    symbol = str(payload.get("symbol", "")).upper().strip()

    if not symbol:
        return jsonify({"ok": False, "error": "Geçersiz hisse"}), 400

    watchlist = load_watchlist()
    if symbol not in watchlist:
        watchlist.append(symbol)
        save_watchlist(watchlist)

    data = load_signals()
    data = ensure_signals_for_watchlist(data, watchlist)
    save_signals(data)

    return jsonify({"ok": True, "symbol": symbol})


@app.route("/api/remove", methods=["POST"])
def remove_symbol():
    ensure_watchlist_file()
    payload = request.get_json(force=True, silent=True) or {}
    symbol = str(payload.get("symbol", "")).upper().strip()

    watchlist = load_watchlist()
    if symbol in watchlist:
        watchlist.remove(symbol)
        save_watchlist(watchlist)

    return jsonify({"ok": True, "symbol": symbol})


@app.route("/webhook", methods=["POST"])
def webhook():
    ensure_watchlist_file()
    payload = request.get_json(force=True, silent=True) or {}

    symbol = str(payload.get("symbol", "")).upper().strip()
    signals = payload.get("signals", {})

    if not symbol or not isinstance(signals, dict):
        return jsonify({
            "ok": False,
            "error": "Geçersiz veri. Beklenen: symbol ve signals objesi"
        }), 400

    watchlist = load_watchlist()
    if symbol not in watchlist:
        watchlist.append(symbol)
        save_watchlist(watchlist)

    data = ensure_signals_for_watchlist(load_signals(), watchlist)

    data.setdefault(symbol, {
        "1h": "YOK",
        "4h": "YOK",
        "1d": "YOK",
        "1w": "YOK",
        "updated_at": "",
        "last_tf": ""
    })

    for tf in TIMEFRAMES:
        val = str(signals.get(tf, "")).upper().strip()
        if val in ["LONG", "SHORT", "NOTR", "AL", "SAT"]:
            data[symbol][tf] = val

    data[symbol]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data[symbol]["last_tf"] = "multi"

    save_signals(data)

    return jsonify({
        "ok": True,
        "symbol": symbol,
        "signals": signals
    })


@app.route("/seed")
def seed():
    ensure_watchlist_file()
    watchlist = load_watchlist()
    data = ensure_signals_for_watchlist({}, watchlist)
    save_signals(data)
    return jsonify({"ok": True, "message": "Boş sinyal verisi oluşturuldu."})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
