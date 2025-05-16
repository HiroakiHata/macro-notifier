import os
import requests
from datetime import datetime

# ===== 設定 =====
slack_webhook = os.getenv("SLACK_WEBHOOK")
api_key = os.getenv("TRADING_ECONOMICS_API_KEY")

# 今日の日付（UTCで調整）を取得
today = datetime.utcnow().strftime("%Y-%m-%d")

# Trading Economics 経済指標取得URL
url = f"https://api.tradingeconomics.com/calendar?c={api_key}&d1={today}&f=json"

# ===== データ取得とログ出力 =====
res = requests.get(url)
print("レスポンスステータス:", res.status_code)
print("レスポンス内容:", res.text)

try:
    data = res.json()
except Exception as e:
    print("JSON読み込みエラー:", e)
    exit(1)

# ===== 指標のフィルタリング条件 =====
TARGET_COUNTRIES = ['United States', 'Euro Area', 'United Kingdom', 'Japan', 'China', 'Australia', 'New Zealand']
MIN_IMPORTANCE = 2

# ===== フィルタ処理 =====
filtered = []
for event in data:
    country = event.get("Country", "")
    importance = event.get("Importance", 0)
    time = event.get("Date", "")
    event_name = event.get("Event", "不明")

    if country in TARGET_COUNTRIES and importance >= MIN_IMPORTANCE:
        formatted = f"【{country}】{time}　（{event_name}）（★{importance}）"
        filtered.append(formatted)

# ===== Slackメッセージ生成 =====
message = ":chart_with_upwards_trend: *本日の重要経済指標（7カ国・★2以上）*\n\n"
message += "\n".join(filtered) if filtered else "本日は対象国の重要指標がありません。"

# ===== Slackへ通知 =====
res_slack = requests.post(
    slack_webhook,
    json={"text": message},
    headers={"Content-Type": "application/json"}
)
print("Slack通知ステータス:", res_slack.status_code)
