import os, socket, requests
from datetime import datetime, timedelta, timezone

"""
Forex-Factory JSON Notifier + Hugging Face 要約 – v6.1
-------------------------------------------------------------
• 通貨コード: USD/EUR/GBP/JPY/CNY/AUD/NZD を判定
• impact: Low=1, Medium=2, High=3 → ★1以上を抽出
• 表示時間帯: 当日 06:01 ～ 翌日 06:00 JST
• 平日 08:00 JST に自動実行 (cron: '0 23 * * 1-5')
• Hugging Face BART で要約レポート生成
"""

# ---- 環境変数 ----
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")
HF_TOKEN      = os.getenv("HF_TOKEN")
if not SLACK_WEBHOOK:
    raise RuntimeError("⚠️ SLACK_WEBHOOK が設定されていません。")
if not HF_TOKEN:
    raise RuntimeError("⚠️ HF_TOKEN が設定されていません。")

# ---- JSON取得 ----
JSON_URLS = [
    "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json",
    "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
]
UA = {"User-Agent": "macro-notifier/1.9"}
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
    requests.post(SLACK_WEBHOOK, json={"text":"⚠️ 経済カレンダー取得失敗"})
    raise SystemExit

# ---- JSONパース ----
try:
    events = resp.json()
except Exception as e:
    requests.post(SLACK_WEBHOOK, json={"text":f"⚠️ JSONパースエラー: {e}"})
    raise

# ---- フィルタ条件 ----
TARGET_CCY  = {"USD","EUR","GBP","JPY","CNY","AUD","NZD"}
IMPACT_MAP  = {"Low":1,"Medium":2,"High":3}
MIN_IMPACT  = 1
jst = timezone(timedelta(hours=9))
now = datetime.now(jst)
today = now.date()
# 開始: 当日 6:01 JST
start_dt = datetime.combine(today, datetime.min.time(), jst) + timedelta(hours=6, minutes=1)
# 終了: 翌日 6:00 JST
end_dt = start_dt + timedelta(days=1) - timedelta(minutes=1)

# ---- イベント抽出 ----
rows = []
event_lines = []
for ev in events:
    dt_raw = ev.get("date")
    if not dt_raw:
        continue
    try:
        dt = datetime.fromisoformat(dt_raw).astimezone(jst)
    except:
        continue
    if not (start_dt <= dt <= end_dt):
        continue
    ccy = (ev.get("currency") or ev.get("country") or "").upper()
    if ccy not in TARGET_CCY:
        continue
    imp_val = IMPACT_MAP.get(str(ev.get("impact","Low")).title(),0)
    if imp_val < MIN_IMPACT:
        continue
    time_str = dt.strftime("%H:%M")
    title    = ev.get("title") or ev.get("event") or "不明"
    stars    = "★" * imp_val
    line = f"【{ccy}】{time_str} （{title}）（{stars}）"
    rows.append(line)
    event_lines.append(line)

# ---- 要約生成 (Hugging Face BART API) ----
hf_payload = {
    "inputs": "\n".join(event_lines),
    "parameters": {"max_length":200, "min_length":50}
}
hf_headers = {"Authorization": f"Bearer {HF_TOKEN}"}
try:
    hf_resp = requests.post(
        "https://api-inference.huggingface.co/models/facebook/bart-large-cnn",
        headers=hf_headers,
        json=hf_payload,
        timeout=30
    )
    hf_resp.raise_for_status()
    summary = hf_resp.json()[0]["summary_text"]
except Exception as e:
    summary = f"⚠️ 要約生成エラー: {e}"

# ---- Slack通知 ----
header = ":chart_with_upwards_trend: *本日の重要経済指標（7通貨・★1以上）*\n`JST 06:01〜翌06:00`\n\n"
body   = "\n".join(rows) if rows else "本日は対象通貨の重要指標がありません。"
text   = header + body + "\n\n:page_facing_up: *要約レポート*\n" + summary
requests.post(SLACK_WEBHOOK, json={"text": text})
