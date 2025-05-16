import os
import json
import requests

# 通知用Webhookの取得
webhook = os.environ.get("SLACK_WEBHOOK")

# 送信するSlackメッセージ（テスト）
payload = {
    "text": ":bug: Slack通知テスト - デバッグ用"
}

# --- デバッグ出力 ---
print(">>> SLACK_WEBHOOK:", webhook)

# SlackへPOSTリクエスト
try:
    response = requests.post(webhook, json=payload)
    print(">>> Slack HTTP status:", response.status_code)
    print(">>> Slack response body:", response.text)
except Exception as e:
    print(">>> Slack POST Error:", e)

