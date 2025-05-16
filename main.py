import os
import requests
from datetime import datetime, timedelta, timezone
from googletrans import Translator  # 日本語訳用

# 環境変数取得
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK")
HF_TOKEN = os.environ.get("HF_TOKEN")
if not SLACK_WEBHOOK:
    raise ValueError("❌ Slack Webhook URL が環境変数から取得できません。Secrets 設定を確認してください。")

# 翻訳オブジェクト生成
translator = Translator()

# 対象通貨・重要度フィルタ
TARGET_IMPACT = {"Low": 1, "Medium": 2, "High": 3}
MIN_IMPACT = 1  # ☆1以上を表示

# 日本時間午前6:01〜翌6:00
JST = timezone(timedelta(hours=9))
now_jst = datetime.now(JST)
start = now_jst.replace(hour=6, minute=1, second=0, microsecond=0)
if now_jst.hour < 6:
    start -= timedelta(days=1)
end = start + timedelta(hours=24)

# データ取得
url = f"https://api.tradingeconomics.com/calendar?d1={start.strftime('%Y-%m-%d')}&d2={end.strftime('%Y-%m-%d')}&c=USD,EUR,GBP,JPY,CNY,AUD,NZD&f=json&apikey={os.environ.get('TRADING_ECONOMICS_API_KEY', '')}"
resp = requests.get(url)
if resp.status_code != 200:
    requests.post(SLACK_WEBHOOK, json={"text": f"⚠️ API取得失敗: {resp.status_code}\n{resp.text}"})
    exit(1)

events = resp.json()
# フィルタリング
filtered = []
for ev in events:
    if TARGET_IMPACT.get(ev.get('impact','Low'),0) >= MIN_IMPACT:
        evt_time = datetime.fromisoformat(ev['date'])
        if start <= evt_time.astimezone(JST) < end:
            filtered.append(ev)

# Slack送信メッセージ組立
header = ":chart_with_upwards_trend: 本日の重要経済指標（☆1以上）\n"
lines = []
for ev in filtered:
    jtime = datetime.fromisoformat(ev['date']).astimezone(JST).strftime('%H:%M')
    title_ja = translator.translate(ev['title'], dest='ja').text
    impact_star = '★' * TARGET_IMPACT.get(ev['impact'],1)
    caution = " ⚠️ 大きく動く可能性あり" if TARGET_IMACT.get(ev['impact'],1)>=2 else ''
    lines.append(f"【{ev['country']}】{jtime} （{title_ja}）（{impact_star}）{caution}")
msg_body = "\n".join(lines) if lines else "本日は対象通貨の重要指標がありません。"
report_en = "Prelim GDP Price Index q/q and Inflation Expectations q/q are key items. Italian trade balance and EU forecasts might move markets. Watch closely at their release times."
# 日本語レポート生成
report_ja = translator.translate(report_en, dest='ja').text

payload = {
    "text": header + msg_body + "\n\n:page_facing_up: 要約レポート\n" + report_ja
}
requests.post(SLACK_WEBHOOK, json=payload)
