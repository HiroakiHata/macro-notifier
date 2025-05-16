import os, socket, requests
from datetime import datetime, timedelta, timezone
from googletrans import Translator

"""
Forex‑Factory JSON Notifier – v5.6 (日本時間0時～NY市場クローズを当日扱い、タイトル自動日本語翻訳)
-------------------------------------------------------------
* 通貨コード: USD/EUR/GBP/JPY/CNY/AUD/NZD を判定
* impact: Low=1, Medium=2, High=3 → 1 以上を抽出
* 日本時間00:00～06:00 のイベントは当日扱い
* 今日の06:01以降のイベントは除外
* タイトルを googletrans で日本語に自動翻訳
* JSON 取得失敗 or パース失敗時は Slack にエラー通知
"""

# ---- 初期設定 ----
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")
if not SLACK_WEBHOOK:
    raise RuntimeError("⚠ SLACK_WEBHOOK secret が設定されていません。")

translator = Translator()

JSON_SOURCES = [
    "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json",
    "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
]
UA = {"User-Agent": "macro-notifier/1.6"}

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

jst     = timezone(timedelta(hours=9))
now     = datetime.now(jst)
today   = now.date()

# ---- 抽出処理 ----
rows = []
for ev in events:
    raw_dt = ev.get("date")
    if not raw_dt:
        continue
    try:
        dt = datetime.fromisoformat(raw_dt).astimezone(jst)
    except:
        continue
    ev_date = dt.date()
    ev_hour = dt.hour + dt.minute/60
    # 00:00～06:00 は当日扱い
    if ev_date == today:
        pass
    elif ev_date == today + timedelta(days=1) and ev_hour < 6:
        pass
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
    # 翻訳
    title_en = ev.get("title") or ev.get("event") or ""
    try:
        title_jp = translator.translate(title_en, src='en', dest='ja').text
    except:
        title_jp = title_en
    # 文字組立
    time_str = dt.strftime("%H:%M")
    star     = "★" * impact_val
    rows.append(f"【{ccy}】{time_str} （{title_jp}）（{star}）")

# ---- Slack 通知 ----
header = ":chart_with_upwards_trend: *本日の重要経済指標（7通貨・★1以上）*\n\n"
if rows:
    body = "\n".join(rows)
else:
    body = "本日は対象通貨の重要指標がありません。"

requests.post(SLACK_WEBHOOK, json={"text": header + body})
