import os
import requests
import datetime

# ================== 環境変数取得 ==================
api_key = os.environ.get("TRADING_ECONOMICS_API_KEY")
webhook = os.environ.get("SLACK_WEBHOOK")

if not api_key:
    raise ValueError("❌ APIキーが環境変数から取得できていません。GitHub Secretsに 'TRADING_ECONOMICS_API_KEY' を設定してください。")
if not webhook:
    raise ValueError("❌ Slack Webhookが環境変数から取得できていません。GitHub Secretsに 'SLACK_WEBHOOK' を設定してください。")

# ================== 日付取得 ==================
today = datetime.datetime.utcnow().strftime("%Y-%m-%d")

# ================== データ取得 ==================
url = f"https://api.tradingeconomics.com/calendar/country/United States,Euro Area,United Kingdom,Japan,China,Australia,New Zealand?c={api_key}&d1={today}&importance=2&f=json"
res = requests.get(url)

print(f"レスポンスステータス: {res.status_code}")
print(f"レスポンス内容: {res.text}")

if res.status_code != 200:
    raise Exception(f"⚠️ APIエラーが発生しました: {res.text}")

try:
    data = res.json()
except Exception:
    raise ValueError(f"JSONパース失敗 or 異常形式: JSONデータがリスト形式ではありません。内容: {res.text}")

if not isinstance(data, list):
    raise ValueError(f"JSONデータがリスト形式ではありません。内容: {data}")

# ================== メッセージ整形 ==================
message = ":chart_with_upwards_trend: *本日の重要経済指標（7カ国・★2以上）*\n"

if not data:
    message += "本日は対象国の重要指標がありません。"
else:
    for event in data:
        country = event.get("Country", "不明")
        date_time = event.get("Date", "")
        importance = event.get("Importance", "")
        star = "★" * int(importance) if importance.isdigit() else ""
        message += f"【{country}】{date_time}　（{star}）\n"

# ================== Slack通知 ==================
requests.post(webhook, json={"text": message})
