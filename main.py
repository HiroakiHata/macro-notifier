import requests
from datetime import datetime, timedelta
import os
import pytz

# 対象国（7カ国）
TARGET_COUNTRIES = ["United States", "Japan", "China", "Euro Area", "United Kingdom", "Australia", "New Zealand"]
# 重要度フィルタ
MIN_IMPORTANCE = 2  # 1: Low, 2: Medium, 3: High

# Slack Webhook（GitHub Secrets）
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")

# JSTタイムゾーン
JST = pytz.timezone("Asia/Tokyo")
TODAY = datetime.now(JST).date()

def fetch_events():
    url = "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json"
    res = requests.get(url)
    res.raise_for_status()
    data = res.json()
    rows = []

    for event in data["events"]:
        # 重要度・国フィルタ
        if event["country"] not in TARGET_COUNTRIES:
            continue
        if event["impact"] not in ["Medium", "High"]:
            continue

        # 日時（UTC→JST）
        dt_utc = datetime.strptime(event["date"] + " " + event["time"], "%Y-%m-%d %H:%M")
        dt_jst = pytz.utc.localize(dt_utc).astimezone(JST)
        if dt_jst.date() != TODAY:
            continue

        # メッセージ整形
        time_str = dt_jst.strftime("%H:%M")
        country = event["country"]
        title = event["title"]
        impact = "★2" if event["impact"] == "Medium" else "★3"

        rows.append(f"【{country}】{time_str}　（{title}）（{impact}）")

    return rows

def send_to_slack(events):
    message = "📊 *本日の重要経済指標（7カ国・★2以上）*\n\n"
    if events:
        message += "\n".join(events)
    else:
        message += "本日は対象国の重要指標がありません。"

    res = requests.post(SLACK_WEBHOOK, json={ "text": message })
    res.raise_for_status()

if __name__ == "__main__":
    events = fetch_events()
    print("取得件数:", len(events))
    for e in events:
        print(e)
    send_to_slack(events)

