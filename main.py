import os
import json
from datetime import datetime, timezone
import cloudscraper  # Cloudflare 回避用
import requests

"""
Free‑tier でも取れる **Forex Factory JSON** を使う版
------------------------------------------------------
  • API キー不要（スクレイピング）
  • Cloudflare 403 を避けるため cloudscraper を利用
  • 重要度★2 以上のみ／7カ国（US‑EU‑UK‑JP‑CN‑AU‑NZ）
"""

# ===== Secrets =====
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")
if not SLACK_WEBHOOK:
    raise ValueError("❌ SLACK_WEBHOOK が設定されていません。GitHub Secrets を確認してください。")

# ===== 取得元 URL =====
FF_URL = "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json"

# ===== Cloudflare 回避リクエスト =====
scraper = cloudscraper.create_scraper()
resp = scraper.get(FF_URL, timeout=30)
print("Status:", resp.status_code)

if resp.status_code != 200:
    requests.post(SLACK_WEBHOOK, json={"text": f"❌ ForexFactory 取得失敗 {resp.status_code}: {resp.text[:200]}"})
    raise SystemExit("Fetch failed")

# ===== JSON パース =====
try:
    events = resp.json()
except json.JSONDecodeError as e:
    requests.post(SLACK_WEBHOOK, json={"text": f"❌ JSON パースエラー: {e}"})
    raise

if not isinstance(events, list):
    requests.post(SLACK_WEBHOOK, json={"text": f"❌ 想定外の形式: {events}"})
    raise SystemExit("Unexpected format")

# ===== 今日の日付 (UTC→ローカル JP) =====
now_jst = datetime.now(timezone.utc).astimezone()
today_str = now_jst.strftime("%Y-%m-%d")

TARGET_COUNTRIES = {
    "United States", "Euro Area", "United Kingdom", "Japan",
    "China", "Australia", "New Zealand"
}

results = []
for ev in events:
    if ev.get("date") != today_str:
        continue
    if ev.get("country") not in TARGET_COUNTRIES:
        continue
    if int(ev.get("impact", 0)) < 2:
        continue
    time = ev.get("time", "")
    title = ev.get("title", "不明")
    star  = "★" * int(ev.get("impact", 0))
    country = ev.get("country")
    results.append(f"【{country}】{time} （{title}）（{star}）")

# ===== Slack へ通知 =====
header = ":bar_chart: *本日の重要経済指標（7カ国・★2以上）*\n\n"
body = "\n".join(results) if results else "本日は対象国の重要指標がありません。"
requests.post(SLACK_WEBHOOK, json={"text": header + body})

