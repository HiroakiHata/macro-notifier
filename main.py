import os
import requests
from datetime import datetime, timezone

# ===== 設定 =====
slack_webhook = os.getenv("SLACK_WEBHOOK")
api_key = os.getenv("TRADING_ECONOMICS_API_KEY")

today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
url = f"https://api.tradingeconomics.com/calendar?c={api_key}&d1={today}&f=json"

# ===== データ取得 =====
res = requests.get(url)
print("レスポンスステータス:", res.status_code)
print("レスポンス内容:", res.text[:300])  # 長すぎるときのために先頭だけ

try:
    data = res.json()
    if not isinstance(data, list):
        raise ValueError("JSONデータがリスト形式ではありません。内容: " + str(data))
except Exception as e:
    print("JSONパース失敗 or 異常形式:", e)
    message = f":warning: API取得失敗または形式異常\n```\n{e}\n```"
    requests.post(slack_webhook, json={"text": message})
    exit(1)

# ===== 指標フィルター処理 =====
TARGET_COUNTRIES = ['United States', 'Euro Area', 'United Kingdom', 'Japan', 'China', 'Australia', 'New Zealand']
MIN_IMPORTANCE = 2

filtered = []
for event in data:
    try:
        country = event.get("Country", "")
        importance = event.get("Importance", 0)
        time = event.get("Date", "")
        event_name = event.get("Event", "不明")
        if country in TARGET_COUNTRIES and importance >= MIN_IMPORTANCE:
            line = f"【{country}】{time}　（{event_name}）（★{importance}）"
            filtered.append(line)
    except Exception as e:
        print("1件パース失敗:", e)
        continue

# ===== Slack 通知 =====
message = ":chart_with_upwards_trend: *本日の重要経済指標（7カ国・★2以上）*\n\n"
message += "\n".join(filtered) if filtered else "本日は対象国の重要指標がありません。"

slack_res = requests.post(slack_webhook, json={"text": message})
print("Slack通知ステータス:", slack_res.status_code)

