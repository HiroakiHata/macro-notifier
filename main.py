import os
import requests
from datetime import datetime, timedelta, timezone
import urllib.parse

"""
Macro Notifier – Trading Economics → Slack
-------------------------------------------
1.  GitHub Actions の `env:` で渡される 2 つの環境変数を取得する
      - SLACK_WEBHOOK
      - TRADING_ECONOMICS_API_KEY
2.  当日‑翌日分の経済カレンダーを取得（★2 以上 / 7 カ国）
3.  注目ワードに一致する指標だけを抽出
4.  結果を Slack にポスト（無ければ「ありません」）

※ 500 エラーやキー未設定時は詳細を Slack に送って調査しやすくする。
"""

# ===== 1. 環境変数取得 =====
slack_webhook = os.getenv("SLACK_WEBHOOK")
api_key       = os.getenv("TRADING_ECONOMICS_API_KEY")  # ← Secrets 名と必ず一致させる

if not slack_webhook:
    raise ValueError("❌ 環境変数 SLACK_WEBHOOK が取得できません。Secrets 設定を確認してください。")
if not api_key:
    raise ValueError("❌ 環境変数 TRADING_ECONOMICS_API_KEY が取得できません。Secrets 設定を確認してください。")

encoded_key = urllib.parse.quote(str(api_key))

# ===== 2. 日付範囲 =====
now_utc = datetime.now(timezone.utc)
d1 = now_utc.strftime("%Y-%m-%d")
d2 = (now_utc + timedelta(days=1)).strftime("%Y-%m-%d")

# ===== 3. API リクエスト =====
base = (
    "https://api.tradingeconomics.com/calendar/country/"
    "United%20States,Euro%20Area,United%20Kingdom,Japan,China,Australia,New%20Zealand"
)
url = f"{base}?c={encoded_key}&d1={d1}&d2={d2}&importance=2&f=json"
print("Request URL:", url)

try:
    response = requests.get(url, timeout=30)
except Exception as e:
    requests.post(slack_webhook, json={"text": f"❌ API接続エラー: {e}"})
    raise

print("Status:", response.status_code)

if response.status_code != 200:
    # 失敗時のレスポンスをそのまま Slack 通知
    requests.post(slack_webhook, json={"text": f"❌ API Error {response.status_code}: {response.text}"})
    raise SystemExit("API Error")

try:
    events = response.json()
except ValueError as e:
    requests.post(slack_webhook, json={"text": f"❌ JSON パースエラー: {e}\nBody: {response.text[:400]}"})
    raise

if not isinstance(events, list):
    requests.post(slack_webhook, json={"text": f"❌ 予期しないレスポンス形式: {events}"})
    raise SystemExit("Unexpected response format")

# ===== 4. フィルター処理 =====
TARGET_WORDS = [
    "CPI", "雇用", "FOMC", "政策金利", "失業率", "PMI", "GDP", "小売", "消費者信頼感", "景況感"
]
results = []

for ev in events:
    if not isinstance(ev, dict):
        continue
    country = ev.get("Country", "")
    importance = ev.get("Importance", 0)
    title = ev.get("Event", "不明")
    time_iso = ev.get("Date", ev.get("DateTime", ""))
    time_str = time_iso[11:16] if len(time_iso) >= 16 else time_iso

    if any(word in title for word in TARGET_WORDS):
        results.append(f"【{country}】{time_str} （{title}）（★{importance}）")

# ===== 5. Slack へ通知 =====
header = ":chart_with_upwards_trend: *本日の重要経済指標（7カ国・★2以上 + 注目ワード一致）*\n\n"
body   = "\n".join(results) if results else "本日は対象国の重要指標がありません。"

requests.post(slack_webhook, json={"text": header + body})
