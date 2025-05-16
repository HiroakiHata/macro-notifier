import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz

# 対象国（7カ国）
TARGET_COUNTRIES = [
    "アメリカ", "日本", "中国", "ユーロ圏", "イギリス", "オーストラリア", "ニュージーランド"
]

# Slack Webhook（GitHub Secrets 経由）
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")

# スクレイピング対象のURL（Investing.comの経済指標カレンダー）
URL = "https://jp.investing.com/economic-calendar/"

# タイムゾーン（JST）
JST = pytz.timezone("Asia/Tokyo")
TODAY = datetime.now(JST).strftime("%m/%d/%Y")

# リクエストヘッダー（Bot対策用）
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def scrape_events():
    response = requests.get(URL, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")
    rows = []

    for row in soup.select("tr.js-event-item"):
        # 日付と国情報を取得
        date_raw = row.get("data-event-datetime")
        country = row.select_one("td.left.flagCur span.flagCur")  # 国名
        importance = row.select_one(".sentiment")  # ★の数
        title = row.select_one(".event")  # 指標名

        if not (date_raw and country and importance and title):
            continue

        # 日本時間に変換
        dt = datetime.utcfromtimestamp(int(date_raw)).astimezone(JST)
        time_str = dt.strftime("%H:%M")
        country_name = country.text.strip()
        star_count = len(importance.select("i.grayFullBullishIcon"))
        title_text = title.text.strip()

        # フィルタ：今日・対象国・★2以上
        if dt.strftime("%m/%d/%Y") != TODAY:
            continue
        if country_name not in TARGET_COUNTRIES:
            continue
        if star_count < 2:
            continue

        rows.append(f"【{country_name}】{time_str}　（{title_text}）（★{star_count}）")

    return rows

def send_to_slack(rows):
    if not SLACK_WEBHOOK:
        raise ValueError("SLACK_WEBHOOK が環境変数に設定されていません。")

    message = "📊 *本日の重要経済指標（7カ国・★2以上）*\n\n"
    if rows:
        message += "\n".join(rows)
    else:
        message += "本日は対象国の重要指標がありません。"

    payload = { "text": message }

    res = requests.post(SLACK_WEBHOOK, json=payload)
    res.raise_for_status()

if __name__ == "__main__":
    events = scrape_events()
    send_to_slack(events)

if __name__ == "__main__":
    events = scrape_events()
    print("取得されたイベント数:", len(events))
    for e in events:
        print(e)  # ← 取得できてる内容を確認
    send_to_slack(events)

