import os, json, time
from datetime import datetime, timezone
import requests, socket

"""
Macro Notifier – 100% 無料スクレイピング版 v2
================================================
• データ元 1:  https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json
• データ元 2:  https://nfs.faireconomy.media/ff_calendar_thisweek.json  (fallback)
  └ GitHub Actions ランナーで稀に `host not known` が出るため 2 段 fallback を実装
• Cloudflare による JS チャレンジは JSON エンドポイントでは発生しないため
  依存パッケージは **requests のみ** に戻した
"""

SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")
if not SLACK_WEBHOOK:
    raise ValueError("❌ SLACK_WEBHOOK が設定されていません。Secrets を確認してください。")

JSON_SOURCES = [
    "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json",
    "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
]

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 macro-notifier"})

resp = None
for url in JSON_SOURCES:
    try:
        # DNS テスト: getaddrinfo で名前解決できなければスキップ
        host = url.split("//")[1].split("/")[0]
        socket.getaddrinfo(host, 443)
        resp = session.get(url, timeout=30)
        if resp.status_code == 200:
            break
    except Exception as e:
        print(f"[WARN] {url} failed → {e}")
        resp = None
        continue

if resp is None or resp.status_code != 200:
    requests.post(SLACK_WEBHOOK, json={"text": f"⚠️ ForexFactory JSON が取得できませんでした。最後の status: {getattr(resp,'status_code',None)}"})
    raise SystemExit("fetch failed")

try:
    events = resp.json()
except json.JSONDecodeError as e:
    requests.post(SLACK_WEBHOOK, json={"text": f"⚠️ JSON パースエラー: {e}"})
    raise

now_jst = datetime.now(timezone.utc).astimezone()
today = now_jst.strftime("%Y-%m-%d")

TARGET_COUNTRIES = {"United States", "Euro Area", "United Kingdom", "Japan", "China", "Australia", "New Zealand"}
TARGET_IMPACT = {"2", "3"}  # FF JSON の impact は文字列 "0"〜"3"

rows = []
for ev in events:
    if ev.get("date") != today:
        continue
    if ev.get("country") not in TARGET_COUNTRIES:
        continue
    if ev.get("impact") not in TARGET_IMPACT:
        continue
    tm = ev.get("time", "")
    title = ev.get("title", "不明")
    star = "★" * int(ev.get("impact"))
    rows.append(f"【{ev['country']}】{tm} （{title}）（{star}）")

header = ":chart_with_upwards_trend: *本日の重要経済指標（7カ国・★2以上）*\n\n"
body = "\n".join(rows) if rows else "本日は対象国の重要指標がありません。"
requests.post(SLACK_WEBHOOK, json={"text": header + body})

