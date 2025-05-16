import os
import requests
from datetime import datetime, timedelta, timezone
import urllib.parse

slack_webhook = os.getenv("SLACK_WEBHOOK")
api_key = os.getenv("TRADING_ECONOMICS_API_KEY")
encoded_key = urllib.parse.quote(api_key)

# 日付範囲指定
today = datetime.now(timezone.utc)
d1 = today.strftime("%Y-%m-%d")
d2 = (today + timedelta(days=1)).strftime("%Y-%m-%d")
url = f"https://api.tradingeconomics.com/calendar?c={encoded_key}&d1={d1}&d2={d2}&f=json"

res = requests.get(url)
print("レスポンスステータス:", res.status_code)
print("レスポンス内容:", res.text[:300])

try:
    data = res.json()
    if not isinstance(data, list):
        raise ValueError("JSONデータがリスト形式ではありません。内容: " + str(data))
except Exception as e:
    print("JSONパース失敗 or 異常形式:", e)
    message = f":warning: API取得失敗または形式異常\n```\n{e}\n```"
    requests.post(slack_webhook, json={"text": message})
    exit(1)

