import os
import json
import requests
from datetime import datetime, timedelta, timezone

# --- 環境変数からWebhookとHFトークン取得 ---
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK")

# --- JSTの日付取得（当日6:01〜翌6:00までを対象） ---
jst = timezone(timedelta(hours=9))
now = datetime.now(jst)
start = now.replace(hour=6, minute=1, second=0, microsecond=0)
end = (now + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)

# --- Trading Economics APIのモック（ここはAPI取得に差し替える） ---
events = [
  {"title": "BusinessNZ Manufacturing Index", "country": "NZD", "date": "2025-05-16T07:30:00+09:00", "impact": "Low"},
  {"title": "Prelim GDP Price Index y/y", "country": "JPY", "date": "2025-05-16T08:50:00+09:00", "impact": "Low"},
  {"title": "Prelim GDP q/q", "country": "JPY", "date": "2025-05-16T08:50:00+09:00", "impact": "Low"},
  {"title": "Inflation Expectations q/q", "country": "NZD", "date": "2025-05-16T12:00:00+09:00", "impact": "Medium"},
  {"title": "Revised Industrial Production m/m", "country": "JPY", "date": "2025-05-16T13:30:00+09:00", "impact": "Low"},
  {"title": "Italian Trade Balance", "country": "EUR", "date": "2025-05-16T18:00:00+09:00", "impact": "Low"},
  {"title": "Trade Balance", "country": "EUR", "date": "2025-05-16T18:00:00+09:00", "impact": "Low"},
  {"title": "EU Economic Forecasts", "country": "EUR", "date": "2025-05-16T18:03:00+09:00", "impact": "Low"},
  {"title": "Building Permits", "country": "USD", "date": "2025-05-16T21:30:00+09:00", "impact": "Low"},
  {"title": "Housing Starts", "country": "USD", "date": "2025-05-16T21:30:00+09:00", "impact": "Low"},
  {"title": "Import Prices m/m", "country": "USD", "date": "2025-05-16T21:30:00+09:00", "impact": "Low"},
  {"title": "FOMC Member Barkin Speaks", "country": "USD", "date": "2025-05-16T21:30:00+09:00", "impact": "Low"},
  {"title": "Prelim UoM Consumer Sentiment", "country": "USD", "date": "2025-05-16T23:00:00+09:00", "impact": "High"},
  {"title": "Prelim UoM Inflation Expectations", "country": "USD", "date": "2025-05-16T23:00:00+09:00", "impact": "High"},
  {"title": "MPC Member Lombardelli Speaks", "country": "GBP", "date": "2025-05-17T00:00:00+09:00", "impact": "Low"},
  {"title": "TIC Long-Term Purchases", "country": "USD", "date": "2025-05-17T05:00:00+09:00", "impact": "Low"}
]

# --- 絞り込み（★1以上 & 6:01〜翌6:00） ---
impact_stars = {"Low": 1, "Medium": 2, "High": 3}
filtered = [e for e in events if start <= datetime.fromisoformat(e['date']) < end]
filtered.sort(key=lambda x: x['date'])

# --- 日本語ルールベース要約 ---
def generate_summary(text):
    if not text.strip():
        return "本日は大きな材料が少ないものの、個別指標には注意が必要です。"

    keywords = ["GDP", "インフレ", "消費者信頼感", "貿易収支", "住宅"]
    highlights = [line for line in text.split(". ") if any(k in line for k in keywords)]

    if highlights:
        summary = "本日は以下の重要指標に注目です：\n"
        for item in highlights:
            summary += f"- {item.strip()}\n"
    else:
        summary = "本日は目立った注目指標はないものの、市場の変動には注意が必要です。"

    return summary + "\n特に発表時刻前後の値動きに注意してください。"

# --- 指標一覧テキスト生成 ---
def format_events(events):
    lines = []
    for e in events:
        dt = datetime.fromisoformat(e['date']).astimezone(jst)
        time_str = dt.strftime("%H:%M")
        stars = "★" * impact_stars.get(e['impact'], 1)
        lines.append(f"【{e['country']}】{time_str} （{e['title']}）（{stars}）")
    return "\n".join(lines) if lines else "本日は対象通貨の重要指標がありません。"

# --- 要約文生成用テキスト ---
events_text = ". ".join([f"{e['title']}（{e['country']}）" for e in filtered])
summary = generate_summary(events_text)

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
