from flask import Flask, request, jsonify, render_template_string
from datetime import datetime
import json
import os

app = Flask(__name__)

DATA_FILE = "signals.json"
TIMEFRAMES = ["1h", "4h", "1d", "1w"]
WATCHLIST = [
    "THYAO", "ASELS", "TUPRS", "EREGL", "KCHOL", "SISE", "AKBNK", "YKBNK", "GARAN", "ISCTR",
    "SAHOL", "BIMAS", "PGSUS", "FROTO", "TOASO", "KOZAL", "KOZAA", "HEKTS", "SASA", "PETKM",
    "ALARK", "ENJSA", "ENKAI", "MAVI", "ARCLK", "VESTL", "CCOLA", "DOHOL", "GUBRF", "ODAS",
    "SMRTG", "ASTOR", "EUPWR", "CWENE", "KONTR", "GESAN", "QUAGR", "OYAKC", "CIMSA", "BRISA",
    "MPARK", "MEDTR", "AEFES", "ULKER", "BRSAN", "OTKAR", "TTRAK", "AGHOL", "TSKB", "HALKB",
    "VAKBN", "EKGYO", "KRDMD", "ISMEN", "DOAS", "MACKO", "ANSGR", "AKSA", "ZOREN", "TKFEN"
]

HTML = """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>BIST Sinyal Paneli</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; background: #f5f7fb; color: #1f2937; }
    h1 { margin-bottom: 8px; }
    .meta { color: #6b7280; margin-bottom: 16px; }
    .toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
    input, select, button {
      padding: 10px 12px; border: 1px solid #d1d5db; border-radius: 10px; background: white;
    }
    table { border-collapse: collapse; width: 100%; background: white; border-radius: 16px; overflow: hidden; }
    th, td { padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: center; }
    th:first-child, td:first-child { text-align: left; font-weight: 600; }
    tr:hover { background: #f9fafb; }
    .sig-AL { background: #dcfce7; color: #166534; font-weight: 700; border-radius: 8px; }
    .sig-SAT { background: #fee2e2; color: #991b1b; font-weight: 700; border-radius: 8px; }
    .sig-NOTR { background: #e5e7eb; color: #374151; font-weight: 700; border-radius: 8px; }
    .sig-YOK { background: #fef3c7; color: #92400e; font-weight: 700; border-radius: 8px; }
    .badge { display: inline-block; min-width: 56px; padding: 6px 10px; }
    .small { color: #6b7280; font-size: 12px; }
  </style>
</head>
<body>
  <h1>BIST Sinyal Paneli</h1>
  <div class="meta">1s / 4s / 1g / 1hf sinyallerini tek tabloda gösterir.</div>

  <div class="toolbar">
    <input id="search" placeholder="Hisse ara..." oninput="renderTable()">
    <select id="filter" onchange="renderTable()">
      <option value="ALL">Tümü</option>
      <option value="AL">En az 1 AL</option>
      <option value="SAT">En az 1 SAT</option>
      <option value="FULL_AL">Tüm timeframe AL</option>
      <option value="FULL_SAT">Tüm timeframe SAT</option>
    </select>
    <button onclick="loadData()">Yenile</button>
  </div>

  <table>
    <thead>
      <tr>
        <th>Hisse</th>
        <th>1 Saat</th>
        <th>4 Saat</th>
        <th>1 Gün</th>
        <th>1 Hafta</th>
        <th>Son Güncelleme</th>
      </tr>
    </thead>
    <tbody id="tbody"></tbody>
  </table>

<script>
let rows = [];

function badgeClass(value) {
  if (value === 'AL') return 'sig-AL';
  if (value === 'SAT') return 'sig-SAT';
  if (value === 'NOTR') return 'sig-NOTR';
  return 'sig-YOK';
}

function matchesFilter(row, filter) {
  const vals = [row['1h'], row['4h'], row['1d'], row['1w']];
  if (filter === 'ALL') return true;
  if (filter === 'AL') return vals.includes('AL');
  if (filter === 'SAT') return vals.includes('SAT');
  if (filter === 'FULL_AL') return vals.every(v => v === 'AL');
  if (filter === 'FULL_SAT') return vals.every(v => v === 'SAT');
  return true;
}

function renderTable() {
  const tbody = document.getElementById('tbody');
  const q = document.getElementById('search').value.trim().toUpperCase();
  const filter = document.getElementById('filter').value;

  const filtered = rows.filter(r => r.symbol.includes(q) && matchesFilter(r, filter));

  tbody.innerHTML = filtered.map(r => `
    <tr>
      <td>${r.symbol}</td>
      <td><span class="badge ${badgeClass(r['1h'])}">${r['1h']}</span></td>
      <td><span class="badge ${badgeClass(r['4h'])}">${r['4h']}</span></td>
      <td><span class="badge ${badgeClass(r['1d'])}">${r['1d']}</span></td>
      <td><span class="badge ${badgeClass(r['1w'])}">${r['1w']}</span></td>
      <td><div>${r.updated_at || '-'}</div><div class="small">${r.last_tf || ''}</div></td>
    </tr>
  `).join('');
}

async function loadData() {
  const res = await fetch('/api/table');
  rows = await res.json();
  renderTable();
}

loadData();
setInterval(loadData, 15000);
</script>
</body>
</html>
"""


def load_signals():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_signals(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def ensure_watchlist(data):
    for symbol in WATCHLIST:
        data.setdefault(symbol, {
            "1h": "YOK",
            "4h": "YOK",
            "1d": "YOK",
            "1w": "YOK",
            "updated_at": "",
            "last_tf": ""
        })
    return data


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/table")
def api_table():
    data = ensure_watchlist(load_signals())
    rows = []
    for symbol in WATCHLIST:
        row = data.get(symbol, {})
        rows.append({
            "symbol": symbol,
            "1h": row.get("1h", "YOK"),
            "4h": row.get("4h", "YOK"),
            "1d": row.get("1d", "YOK"),
            "1w": row.get("1w", "YOK"),
            "updated_at": row.get("updated_at", ""),
            "last_tf": row.get("last_tf", "")
        })
    return jsonify(rows)


@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.get_json(force=True, silent=True) or {}

    symbol = str(payload.get("symbol", "")).upper().strip()
    signals = payload.get("signals", {})

    if not symbol or not isinstance(signals, dict):
        return jsonify({
            "ok": False,
            "error": "Geçersiz veri. Beklenen: symbol ve signals objesi"
        }), 400

    data = ensure_watchlist(load_signals())

    data.setdefault(symbol, {
        "1h": "YOK",
        "4h": "YOK",
        "1d": "YOK",
        "1w": "YOK",
        "updated_at": "",
        "last_tf": ""
    })

    for tf in ["1h", "4h", "1d", "1w"]:
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
    data = ensure_watchlist({})
    save_signals(data)
    return jsonify({"ok": True, "message": "Boş sinyal verisi oluşturuldu."})


if __name__ == "__main__":
    app.run(debug=True, port=5000)

