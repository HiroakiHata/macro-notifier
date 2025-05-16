import os
import requests
import datetime

# ===== 設定 =====
api_key = os.environ.get("TRADING_ECONOMICS_API_KEY")
webhook = os.environ.get("SLACK_WEBHOOK")

if not api_key:
    raise ValueError("❌ APIキーが環境変数から取得できていません。GitHub Secretsに 'TRADING_ECONOMICS_API_KEY' を設定してください。")

if not webhook:
    raise ValueError("❌ Slack Webhookが環境変数から取得できていません。GitHub Secretsに 'SLACK_WEBHOOK' を設定してください。")

# ===== 日付 =====
today = datetime.datetime.utcnow().strftime("%Y-%m-%d")

# ===== APIリクエスト =====
url = f"https://api.tradingeconomics.com/calendar/country/United%20States,Euro%20Area,United%20Kingdom,Japan,China,Australia,New%20Zealand?c={api_key}&d1={today}&importance=2"
response = requests.get(url)
print("レスポンスステータス:", response.status_code)

if response.status_code != 200:
    print("レスポンス内容:", response.text)
    raise Exception("❌ APIリクエストに失敗しました。")

try:
    events = response.json()
except Exception as e:
    print("JSONパース失敗 or 異常形式: JSONデータがリスト形式ではありません。内容:", response.text)
    raise e

# ===== フィルター処理 =====
target_words = ["CPI", "雇用", "FOMC", "政策金利", "失業率", "PMI", "GDP", "小売", "消費者信頼感", "景況感"]
results = []

for event in events:
    if isinstance(event, dict):
        country = event.get("Country", "")
        time = event.get("DateTime", "")
        importance = event.get("Importance", 0)
        title = event.get("Event", "")
        if any(word in title for word in target_words):
            results.append(f"【{country}】{time}　（{title}）（★{importance}）")

# ===== Slack通知 =====
message = "📈 *本日の重要経済指標（7カ国・★2以上 + 注目ワード一致）*\n\n"
message += "\n".join(results) if results else "本日は対象国の重要指標がありません。"

requests.post(
    webhook,
    headers={"Content-Type": "application/json"},
    json={"text": message}
)

