import os, json, socket, requests
from datetime import datetime, timedelta, timezone

"""
Forex‑Factory JSON Notifier – v5.4 (include ★1以上)
-------------------------------------------------------------
* 通貨コード: USD/EUR/GBP/JPY/CNY/AUD/NZD を判定
* impact: Low=1, Medium=2, High=3 → 1 以上を抽出
* 00‑05 時台の深夜指標は当日扱い
* 今日＆明日の2日分を対象
* JSON 取得失敗 or パース失敗時は Slack にエラー通知
"""

# ---- 初期設定 ----
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")
if not SLACK_WEBHOOK:
    raise RuntimeError("⚠ SLACK_WEBHOOK secret が設定されていません。")

JSON_SOURCES = [
    "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json",
    "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
]
UA = {"User-Agent": "macro-notifier/1.4"}

# ---- JSON 取得 ----
resp = None
for url in JSON_SOURCES:
    try:
        host = url.split("//")[1].split("/")[0]
        socket.getaddrinfo(host, 443)
        r = requests.get(url, headers=UA, timeout=30)
        if r.status_code == 200:
            resp = r
            break
    except Exception:
        continue

if resp is None:
    requests.post(SLACK_WEBHOOK, json={"text": "⚠️ ForexFactory JSON 取得失敗"})
    raise SystemExit

# ---- JSON パース ----
try:
    events = resp.json()
except Exception as e:
    requests.post(SLACK_WEBHOOK, json={"text": f"⚠️ JSON パースエラー: {e}"})
    raise

# ---- フィルタ条件 ----
TARGET_CCY   = {"USD", "EUR", "GBP", "JPY", "CNY", "AUD", "NZD"}
IMPACT_MAP   = {"Low": 1, "Medium": 2, "High": 3}
TARGET_LEVEL = 1  # ★1 以上

jst         = timezone(timedelta(hours=9))
now         = datetime.now(jst)
check_dates = { now.date(), (now + timedelta(days=1)).date() }

# ---- 抽出処理 ----nrows = []
rows = []
for ev in events:
    # ISO datetime 解析
    raw_dt = ev.get("date")
    dt_obj = None
    if raw_dt:
        try:
            obj = datetime.fromisoformat(raw_dt)
            dt_obj = obj.astimezone(jst)
        except Exception:
            dt_obj = None
    # 年月日分割対応
    if not dt_obj:
        y, m, d = ev.get("year"), ev.get("month"), ev.get("day")
        if y and m and d:
            try:
                dt_obj = datetime(int(y), int(m), int(d), tzinfo=jst)
            except Exception:
                dt_obj = None
    if not dt_obj:
        continue

    # 日付チェック
    d_obj = dt_obj.date()
    if d_obj not in check_dates:
        if d_obj == (now.date() - timedelta(days=1)) and dt_obj.hour < 6:
            d_obj = now.date()
        else:
            continue

    # 通貨判定
    ccy = (ev.get("currency") or ev.get("country") or "").upper()
    if ccy not in TARGET_CCY:
        continue

    # 重要度判定
    impact_val = IMPACT_MAP.get(str(ev.get("impact", "Low")).title(), 0)
    if impact_val < TARGET_LEVEL:
        continue

    # 時刻とタイトル
    time_str = dt_obj.strftime("%H:%M")
    title    = ev.get("title") or ev.get("event") or "不明"
    star     = "★" * impact_val
    rows.append(f"【{ccy}】{time_str} （{title}）（{star}）")

# ---- Slack 通知 ----
header = ":chart_with_upwards_trend: *本日の重要経済指標（7通貨・★1以上）*\n\n"
if rows:
    body = "\n".join(rows)
else:
    body = f"本日は対象通貨の重要指標がありません。（raw 件数: {len(events)}）"

requests.post(SLACK_WEBHOOK, json={"text": header + body})

