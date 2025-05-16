import os
import json
import requests
from datetime import datetime, timedelta, timezone

# --- 環境変数からWebhookとHFトークン取得 ---
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK")
HF_TOKEN = os.environ.get("HF_TOKEN")

# --- JSTの日付取得（当日6:01〜翌6:00までを対象） ---
jst = timezone(timedelta(hours=9))
now = datetime.now(jst)
start = now.replace(hour=6, minute=1, second=0, microsecond=0)
end = (now + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)

# --- Trading Economics APIのモック（ここはAPI取得に差し替える） ---
events = [
  {"title": "Prelim GDP q/q", "country": "JPY", "date": "2025-05-16T08:50:00+09:00", "impact": "High"},
  {"title": "Housing Starts", "country": "USD", "date": "2025-05-16T21:30:00+09:00", "impact": "Medium"},
  {"title": "BusinessNZ Manufacturing Index", "country": "NZD", "date": "2025-05-16T07:30:00+09:00", "impact": "Low"},
  {"title": "Empire State Manufacturing Index", "country": "USD", "date": "2025-05-16T22:00:00+09:00", "impact": "Medium"},
  {"title": "Retail Sales m/m", "country": "USD", "date": "2025-05-16T21:30:00+09:00", "impact": "High"}
]

# --- 絞り込み（★1以上 & 6:01〜翌6:00） ---
impact_stars = {"Low": 1, "Medium": 2, "High": 3}
filtered = [e for e in events if start <= datetime.fromisoformat(e['date']) < end]
filtered.sort(key=lambda x: x['date'])

# --- 要約生成（HuggingFace API） ---
def generate_summary(text):
    if not HF_TOKEN:
        return "要約生成エラー: HF_TOKEN が未設定です"

    url = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {"inputs": text}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        res.raise_for_status()
        summary = res.json()[0].get("summary_text", "")
        return summary
    except Exception as e:
        return f"要約生成失敗: {e}"

# --- 指標一覧テキスト生成 ---
def format_events(events):
    lines = []
    for e in events:
        dt = datetime.fromisoformat(e['date']).astimezone(jst)
        time_str = dt.strftime("%H:%M")
        stars = "★" * impact_stars.get(e['impact'], 1)
        lines.append(f"【{e['country']}】{time_str} （{e['title']}）（{stars}）")
    return "\n".join(lines) if lines else "本日は対象通貨の重要指標がありません。"

# --- GPT要約の文章テンプレ（簡易） ---
events_text = ", ".join([f"{e['title']}（{e['country']}）" for e in filtered])
summary = generate_summary(events_text)
if not summary.strip():
    summary = "本日は大きな材料が少ないものの、個別指標には注意が必要です。"
else:
    summary += "\n特に発表時刻前後の値動きに注意してください。"

# --- Slackメッセージ生成 ---
header = ":chart_with_upwards_trend: 本日の重要経済指標（7通貨・★1以上）"
events_msg = format_events(filtered)
report = f":bookmark_tabs: 要約レポート\n{summary}"

payload = {
    "text": f"{header}\n{events_msg}\n\n{report}"
}

# --- Slackへ通知 ---
if SLACK_WEBHOOK:
    try:
        res = requests.post(SLACK_WEBHOOK, json=payload)
        res.raise_for_status()
        print("Slack通知成功")
    except Exception as e:
        print("Slack通知失敗:", e)
else:
    print("Slack Webhookが未設定です")
