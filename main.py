import os, socket, requests
from datetime import datetime, timedelta, timezone

"""
Forex-Factory JSON Notifier – v5.7
-------------------------------------------------------------
* 通貨コード: USD/EUR/GBP/JPY/CNY/AUD/NZD を判定
* impact: Low=1, Medium=2, High=3 → 1以上を抽出
* 表示時間帯: 当日 06:01 ～ 翌日 06:00
* JSON取得失敗 or パース失敗時はSlackにエラー通知
"""

# ---- 初期設定 ----
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")
if not SLACK_WEBHOOK:
    raise RuntimeError("⚠️ SLACK_WEBHOOK secret が設定されていません。")

JSON_URLS = [
    "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json",
    "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
]
UA = {"User-Agent": "macro-notifier/1.7"}

# ---- JSON取得 ----
resp = None
for url in JSON_URLS:
    try:
        host = url.split("//")[1].split("/")[0]
        socket.getaddrinfo(host, 443)
        r = requests.get(url, headers=UA, timeout=30)
        if r.status_code == 200:
            resp = r
            break
    except:
        continue
if resp is None:
    requests.post(SLACK_WEBHOOK, json={"text": "⚠️ ForexFactory JSON取得失敗"})
    raise SystemExit

# ---- JSONパース ----
try:
    events = resp.json()
except Exception as e:
    requests.post(SLACK_WEBHOOK, json={"text": f"⚠️ JSONパースエラー: {e}"})
    raise

# ---- フィルタ条件 ----
TARGET_CCY = {"USD", "EUR", "GBP", "JPY", "CNY", "AUD", "NZD"}
IMPACT_MAP = {"Low":1, "Medium":2, "High":3}
MIN_IMPACT = 1  # ★1以上

jst = timezone(timedelta(hours=9))
now = datetime.now(jst)
today = now.date()

# 翌日の開始境界
start_today = datetime.combine(today, datetime.min.time(), jst) + timedelta(hours=6, minutes=1)
end_next = start_today + timedelta(days=1) - timedelta(minutes=1)  # 翌6:00まで

# ---- イベント抽出 ----
rows = []
for ev in events:
    dt_raw = ev.get("date")
    if not dt_raw:
        continue
    try:
        dt = datetime.fromisoformat(dt_raw).astimezone(jst)
    except:
        continue
    # フィルタ時間帯
    if not (start_today <= dt <= end_next):
        continue
    # 通貨
    ccy = (ev.get("currency") or ev.get("country") or "").upper()
    if ccy not in TARGET_CCY:
        continue
    # インパクト
    impact_val = IMPACT_MAP.get(str(ev.get("impact","Low")).title(), 0)
    if impact_val < MIN_IMPACT:
        continue
    # 表示行
    time_str = dt.strftime("%H:%M")
    title = ev.get("title") or ev.get("event") or "不明"
    stars = "★" * impact_val
    rows.append(f"【{ccy}】{time_str} （{title}）（{stars}）")

# ---- Slack通知 ----
header = ":chart_with_upwards_trend: *本日の重要経済指標（7通貨・★1以上 / JST 06:01～翌06:00）*\n\n"
body = "\n".join(rows) if rows else "本日は対象通貨の重要指標がありません。"
requests.post(SLACK_WEBHOOK, json={"text": header + body})

