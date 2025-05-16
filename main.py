import requests
import os
from datetime import datetime

# 環境変数から取得
webhook_url = os.environ.get("SLACK_WEBHOOK")
api_key = os.environ.get("TE_API_KEY")

# 今日の日付を取得（UTC基準）
today = datetime.utcnow().strftime('%Y-%m-%d')

# APIから経済指標を取得
url = f"https://api.tradingeconomics.com/calendar/country/United States,Japan,China,Euro Area,United Kingdom,Australia,New Zealand?d1={today}&d2={today}&c={api_key}&f=json"
res = requests.get(url)
data = res.json()

# 重要度★2以上だけを抽出
important = [f"【{d['Country']}】{d['Date']} {d['Event']}（★{d['Importance']}）"
             for d in data if int(d.get("Importance", 0)) >= 2]

# Slackに送信
if important:
    text = ":bar_chart: 本日の重要経済指標（★2以上）\n" + "\n".join(important)
else:
    text = ":bar_chart: 本日の重要経済指標（★2以上）はありません"

requests.post(webhook_url, json={"text": text})
