import os, json, socket, requests
from datetime import datetime, date, timedelta, timezone

"""
Forex‑Factory JSON Notifier – v4 (時間ずれ補正)
---------------------------------------------
■ 改良点
1. *「本日 + 翌日」の 2 日分* をチェック
   - JST では早朝 00‑05 時台の指標が前日扱いになるため重複除外済み
2. Slack へ **ヒット件数** を出力 （デバッグしやすい）
3. rows==0 のときは  ⚠ 表示行 + raw 件数 を送信して原因を追いやすく

依存： requests のみ
Secrets： SLACK_WEBHOOK
"""

SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")
if not SLACK_WEBHOOK:
    raise RuntimeError("SLACK_WEBHOOK secret が設定されていません")

JSON_SOURCES = [
    "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json",
    "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
]

UA = {"User-Agent": "macro-notifier/1.1"}

resp = None
for url in JSON_SOURCES:
    try:
        host = url.split("//")[1].split("/")[0]
        socket.getaddrinfo(host, 443)
        r = requests.get(url, headers=UA, timeout=30)
        if r.status_code == 200:
            resp = r
            break
    except Exception as e:
        print("[WARN]", url, e)

if resp is None:
    requests.post(SLACK_WEBHOOK, json={"text": "⚠️ ForexFactory JSON 取得失敗"})
    raise SystemExit

try:
    events = resp.json()
except Exception as e:
    requests.post(SLACK_WEBHOOK, json={"text": f"⚠️ JSON パースエラー: {e}"})
    raise

TARGET_COUNTRIES = {
    "United States", "Euro Area", "United Kingdom",
    "Japan", "China", "Australia", "New Zealand",
}
TARGET_IMPACT = {"2", "3"}

# 今日+明日 (ローカル日付) セット
jst = timezone(timedelta(hours=9))
today = datetime.now(jst).date()
check_dates = {today, today + timedelta(days=1)}

rows = []
for ev in events:
    # --- 日付取り出し ---
    ev_date = ev.get("date")
    if not ev_date:
        y = ev.get("y") or ev.get("year")
        m = ev.get("m") or ev.get("month")
        d = ev.get("d") or ev.get("day")
        if y and m and d:
            ev_date = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    if not ev_date:
        continue
    try:
        d_obj = datetime.strptime(ev_date, "%Y-%m-%d").date()
    except ValueError:
        continue

    # 00‑05 時台は前日表示のまま→ 翌日扱いに補正
    t_str = ev.get("time", "00:00")
    try:
        h = int(t_str.split(":")[0])
    except ValueError:
        h = 0
    if d_obj == today - timedelta(days=1) and h < 6:
        d_obj = today

    if d_obj not in check_dates:
        continue

    if ev.get("country") not in TARGET_COUNTRIES:
        continue
    impact = str(ev.get("impact", "0"))
    if impact not in TARGET_IMPACT:
        continue

    title = ev.get("title") or ev.get("event") or "不明"
    star = "★" * int(impact)
    rows.append(f"【{ev['country']}】{t_str} （{title}）（{star}）")

header = ":chart_with_upwards_trend: *本日の重要経済指標（7カ国・★2以上）*\n\n"
if rows:
    body = "\n".join(rows)
else:
    body = "本日は対象国の重要指標がありません。（raw 件数: %d）" % len(events)

requests.post(SLACK_WEBHOOK, json={"text": header + body})
