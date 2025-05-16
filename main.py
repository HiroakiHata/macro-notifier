import os
import urllib.parse
import requests
from datetime import datetime, timezone

# 1. APIキーを環境変数から取得
api_key = os.getenv("TRADING_ECONOMICS_API_KEY")

# 2. 取得できていない場合はエラーで止める
if not api_key:
    raise ValueError("❌ APIキーが環境変数から取得できていません。GitHub Secretsに 'TRADING_ECONOMICS_API_KEY' を設定してください。")

# 3. APIキーをURLエンコード（必ず文字列型に変換）
encoded_key = urllib.parse.quote(str(api_key))

# 4. 今日の日付をUTCで取得
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# 5. APIエンドポイントURL
url = f"https://api.tradingeconomics.com/calendar?c={encoded_key}&d1={today}&d2={today}&f=json"

# 6. リクエスト送信
res = requests.get(url)

print(f"レスポンスステータス: {res.status_code}")
print(f"レスポンス内容: {res.text}")

# 7. 成功時のみJSONとして処理
if res.status_code == 200:
    try:
        data = res.json()
        print(f"取得されたイベント数: {len(data)}")
    except Exception as e:
        print(f"❌ JSONパース失敗: {e}")
else:
    print("❌ APIリクエストに失敗しました。")
