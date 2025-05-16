import os
import json
import requests
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup

# --- 設定 ---
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK")
TARGET_COUNTRIES = ["アメリカ", "ユーロ圏", "日本", "中国", "イギリス", "オーストラリア", "ニュージーランド"]
impact_map = {"★": 1, "★★": 2, "★★★": 3}

# --- JST時間のフィルター枠 ---
jst = timezone(timedelta(hours=9))
now = datetime.now(jst)
start = now.replace(hour=6, minute=1, second=0, microsecond=0)
end = (now + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)

# --- HTML読み込み ---
with open("HTML.txt", "r", encoding="utf-8") as f:
    html = f.read()
soup = BeautifulSoup(html, "html.parser")

# --- データ抽出 ---
events = []
rows = soup.select("table.genTbl.closedTbl.ecEventsTable tr.js-event-item")
for row in rows:
    time_td = row.select_one("td.first.left.time")
    country_td = row.select_one("td.left.flagCur.noWrap")
    event_td = row.select_one("td.event")
    impact_td = row.select_one("td.sentiment")

    if not all([time_td, country_td, event_td, impact_td]):
        continue

    time_str = time_td.get_text(strip=True)
    country = country_td.get("title", "")
    title = event_td.get_text(strip=True)
    stars = impact_td.get_text(strip=True)

    # 国フィルタ（7カ国のみ）
    if not any(t in country for t in TARGET_COUNTRIES):
        continue

    # 日付変換（例: "21:30" → 今日の21:30）
    try:
        dt = datetime.strptime(time_str, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day, tzinfo=jst
        )
        if dt < now and now.hour < 6:
            dt += timedelta(days=1)  # 翌日扱い
    except:
        continue

    if not (start <= dt < end):
        continue

    impact = "★" * len(stars)
    events.append({
        "country": country,
        "time": dt.strftime("%H:%M"),
        "title": title,
        "impact": impact
    })

# --- 整形 ---
events.sort(key=lambda x: x['time'])
impact_rank = {"★": 1, "★★": 2, "★★★": 3}
lines = [f"【{e['country']}】{e['time']} （{e['title']}）（{e['impact']}）" for e in events]
event_text = "\n".join(lines) if lines else "本日は対象通貨の重要指標がありません。"

# --- 日本語ルールベース要約 ---
def generate_summary(events):
    if not events:
        return "本日は大きな材料が少ないものの、個別指標には注意が必要です。"
    keywords = ["GDP", "インフレ", "消費者", "貿易", "住宅"]
    matched = [e for e in events if any(k in e["title"] for k in keywords)]
    if matched:
        summary = "本日は以下の重要指標に注目です：\n"
        for e in matched:
            summary += f"- {e['title']}（{e['country']}）\n"
    else:
        summary = "本日は目立った注目指標はないものの、市場の変動には注意が必要です。"
    return summary + "\n特に発表時刻前後の値動きに注意してください。"

summary = generate_summary(events)

# --- Slack通知 ---
payload = {
    "text": f":chart_with_upwards_trend: 本日の重要経済指標（7通貨・★1以上）\n{event_text}\n\n:bookmark_tabs: 要約レポート\n{summary}"
}

if SLACK_WEBHOOK:
    try:
        res = requests.post(SLACK_WEBHOOK, json=payload)
        res.raise_for_status()
        print("Slack通知成功")
    except Exception as e:
        print("Slack通知失敗:", e)
else:
    print("Slack Webhookが未設定です")
