import os
import requests
import json

webhook = os.environ.get("SLACK_WEBHOOK")
payload = {
    "text": ":bug: Slack通知テスト（本番コード）"
}

if webhook:
    response = requests.post(webhook, json=payload)
    print("Slack通知成功:", response.status_code)
else:
    print("Slack通知失敗: SLACK_WEBHOOK が設定されていません")
