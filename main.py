import os, json, socket, requests
from datetime import datetime, timezone, date

"""
Forex‑Factory JSON 版 – Robust v3
---------------------------------
• 取得先 (free):
    https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json  (primary)
    https://nfs.faireconomy.media/ff_calendar_thisweek.json      (fallback)
• 403 / DNS 不達 → 自動で次へ。
• JSON 仕様変更に耐える汎用パーサ:
    - 日付フィールド : `date` (YYYY‑MM‑DD) があればそれを使用。
    - ない場合は `year`/`y`, `month`/`m`, `day`/`d` を組み立て。
• 重要度 impact が "2" または "3"。
• 国は 7 か国固定。
• Slack Webhook 必須 (Secrets: SLACK_WEBHOOK)
"""

SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")
if not SLACK_WEBHOOK:
    raise RuntimeError("SLACK_WEBHOOK secret が設定されていません")

JSON_SOURCES = [
    "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json",
    "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
]

session = requests.Session()
session.headers.update({"User-Agent": "macro-notifier/1.0"})

resp = None
for url in JSON_SOURCES:
    try:
        host = url.split("//")[1].split("/")[0]
        socket.getaddrinfo(host, 443)  # DNS resolve check
        r = session.get(url, timeout=30)
        if r.status_code == 200:
            resp = r
            break
    except Exception as e:
        print(f"[WARN] {url}: {e}")

if resp is None:
    requests.post(SLACK_WEBHOOK, json={"text": "⚠️ ForexFactory JSON 取得に全て失敗しました"})
    raise SystemExit

try:
    events = resp.json()
except Exception as e:
    requests.post(SLACK_WEBHOOK, json={"text": f"⚠️ JSON パースエラー: {e}"})
    raise

# ===== フィルタ条件 =====
TARGET_COUNTRIES = {
    "United States", "Euro Area", "United Kingdom",
    "Japan", "China", "Australia", "New Zealand",
}
TARGET_IMPACT = {"2", "3"}

# 今日 (JST 基準だと UTC+9) だと FF の date はサイトのタイムゾーン依存で
# ずれる場合があるため、UTC ではなくローカル日付で比較。
today = date.today().isoformat()  # "YYYY-MM-DD"
rows = []

for ev in events:
    # --- 日付判定 ---
    ev_date = ev.get("date")
    if not ev_date:
        # y/m/d → YYYY-MM-DD を組み立て
        y = ev.get("y") or ev.get("year")
        m = ev.get("m") or ev.get("month")
        d = ev.get("d") or ev.get("day")
        if y and m and d:
            ev_date = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    if ev_date != today:
        continue

    # --- 国・重要度 ---
    country = ev.get("country")
    if country not in TARGET_COUNTRIES:
        continue
    impact = str(ev.get("impact", "0"))
    if impact not in TARGET_IMPACT:
        continue

    # --- 表示行を生成 ---
    tm = ev.get("time", "")
    title = ev.get("title") or ev.get("event") or "不明"
    star = "★" * int(impact)
    rows.append(f"【{country}】{tm} （{title}）（{star}）")

# ===== Slack 通知 =====
header = ":chart_with_upwards_trend: *本日の重要経済指標（7カ国・★2以上）*\n\n"
body = "\n".join(rows) if rows else "本日は対象国の重要指標がありません。"
requests.post(SLACK_WEBHOOK, json={"text": header + body})
