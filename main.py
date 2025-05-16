import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import os

def fetch_events():
    url = "https://jp.investing.com/economic-calendar/"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")

    today_jst = datetime.now(pytz.timezone("Asia/Tokyo")).strftime("%m/%d")
    target_countries = ["アメリカ", "ユーロ圏", "イギリス", "日本", "中国", "オーストラリア", "ニュージーランド"]

    results = []
    rows = soup.select("tr.js-event-item")

    for row in rows:
        date_attr = row.get("data-event-datetime", "")
        if today_jst not in date_attr:
            continue

        country_tag = row.select_one("td.left.flagCur span")
        country = country_tag["title"] if country_tag and country_tag.has_attr("title") else ""
        if country not in target_countries:
            continue

        importance = len(row.select("td.sentiment i.grayFullBullishIcon"))
        if importance < 2:
            continue

        time = row.select_one("td.js-time")
        event = row.select_one("td.event a, td.event span")
        results.append(f"【{country}】{time.text.strip()}　{event.text.strip()}（★{importance}）")

    return results

def notify_slack(events):
    webhook_url = os.environ.get("SLACK_WEBHOOK")
    if not webhook_url:
        print("No Slack webhook set.")
        return

    message = "📊 *本日の重要経済指標（7カ国・★2以上）*

"
    message += "\n".join(events) if events else "本日は対象国の重要指標がありません。"

    res = requests.post(webhook_url, json={"text": message})
    print("Slack status:", res.status_code)

if __name__ == "__main__":
    events = fetch_events()
    notify_slack(events)
