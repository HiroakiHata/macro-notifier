import os
import requests
from datetime import datetime, timedelta, timezone

# 環境変数取得
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")
TRADING_API_KEY = os.getenv("TRADING_ECONOMICS_API_KEY")
if not SLACK_WEBHOOK:
    raise ValueError("❌ Slack Webhook URL が環境変数から取得できません。Secrets を確認してください。")
if not TRADING_API_KEY:
    raise ValueError("❌ Trading Economics API キーが環境変数から取得できません。Secrets を確認してください。")

# 翻訳用（Optional: googletrans==3.1.0a0 を requirements.txt に追加）
try:
    from googletrans import Translator
    translator = Translator()
    def to_ja(text):
        return translator.translate(text, dest='ja').text
except Exception:
    def to_ja(text):
        return text  # 翻訳不可時は原文を返す

# フィルタ設定
IMPACT_MAP = {'Low': 1, 'Medium': 2, 'High': 3}
MIN_IMPACT = 1  # ★1以上

# JST 6:01-翌6:00 範囲
JST = timezone(timedelta(hours=9))
now = datetime.now(JST)
start = now.replace(hour=6, minute=1, second=0, microsecond=0)
if now.hour < 6:
    start -= timedelta(days=1)
end = start + timedelta(days=1)

def fetch_events():
    url = (
        f"https://api.tradingeconomics.com/calendar"
        f"?d1={start.date()}&d2={end.date()}"
        f"&c=USD,EUR,GBP,JPY,CNY,AUD,NZD"
        f"&f=json&apikey={TRADING_API_KEY}"
    )
    r = requests.get(url)
    if r.status_code != 200:
        msg = f"⚠️ API Error {r.status_code}\n{r.text}"
        requests.post(SLACK_WEBHOOK, json={"text": msg})
        exit(1)
    return r.json()

# メイン
events = fetch_events()
filtered = []
for ev in events:
    if IMPACT_MAP.get(ev.get('impact','Low'),0) < MIN_IMPACT:
        continue
    t = datetime.fromisoformat(ev['date']).astimezone(JST)
    if not (start <= t < end):
        continue
    filtered.append((ev, t))

# Slack メッセージ作成
lines = []
for ev, t in filtered:
    time_str = t.strftime('%H:%M')
    title_ja = to_ja(ev['title'])
    stars = '★' * IMPACT_MAP.get(ev['impact'],1)
    caution = ' ⚠️ 大きく動く可能性あり' if IMPACT_MAP.get(ev['impact'],1) >= 2 else ''
    lines.append(f"【{ev['country']}】{time_str} （{title_ja}）（{stars}）{caution}")

header = ":chart_with_upwards_trend: 本日の重要経済指標（☆1以上）\n"
body = "\n".join(lines) if lines else "本日は対象通貨の重要指標がありません。"

# 簡易要約レポート（例：直接埋め込むか別APIで生成）
summary_en = (
    "Prelim GDP Price Index y/y and Inflation Expectations q/q are highlighted. "
    "Italian Trade Balance, EU Economic Forecasts and Housing Starts may influence markets."
)
report = to_ja(summary_en)

payload = {
    "text": header + body + f"\n\n:page_facing_up: 要約レポート\n{report}"
}
requests.post(SLACK_WEBHOOK, json=payload)

