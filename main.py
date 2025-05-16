import os
import json
import requests
from datetime import datetime, timedelta, timezone

# --- 環境変数からWebhookとTE APIキーを取得 ---
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK")
TE_API_KEY = os.environ.get("TRADING_ECONOMICS_API_KEY")

# --- JSTの日付取得（当日6:01〜翌6:00までを対象） ---
jst = timezone(timedelta(hours=9))
now = datetime.now(jst)
start = now.replace(hour=6, minute=1, second=0, microsecond=0)
end = (now + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)

# --- Trading Economics APIから取得 ---
try:
    url = f"https://api.tradingeconomics.com/calendar/country/United%20States,Japan,China,Euro%20Area,United%20Kingdom,Australia,New%20Zealand?c={TE_API_KEY}"
    res = requests.get(url)
    res.raise_for_status()
    raw_events = res.json()
except Exception as e:
    raw_events = []
    print("TE API取得失敗:", e)

# --- フィルター処理 ---
impact_stars = {"low": 1, "medium": 2, "high": 3}
filtered = []
for e in raw_events:
    if not e.get("date") or not e.get("country") or not e.get("event"):
        continue
    dt = datetime.fromisoformat(e['date'].replace("Z", "+00:00")).astimezone(jst)
    if start <= dt < end:
        impact = e.get("importance", "low").lower()
        filtered.append({
            "title": e['event'],
            "country": e['country'],
            "date": dt.isoformat(),
            "impact": impact.capitalize()
        })

filtered.sort(key=lambda x: x['date'])

# --- 日本語ルールベース要約 ---
def generate_summary(text):
    if not text.strip():
        return "本日は大きな材料が少ないものの、個別指標には注意が必要です。"

    keywords = ["GDP", "インフレ", "消費者", "貿易", "住宅"]
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
        stars = "★" * impact_stars.get(e['impact'].lower(), 1)
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

