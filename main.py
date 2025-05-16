import os, json, socket, requests
from datetime import datetime, timedelta, timezone

"""
Forex‑Factory JSON Notifier – v5.1 (syntax fix)
---------------------------------------------
* 通貨コードで 7 通貨を判定
* impact ≧ 2 を抽出
* rows==0 なら raw 件数を表示
* Cloudflare CDN → 2 URL ローテーション
"""

SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")
if not SLACK_WEBHOOK:
    raise RuntimeError("⚠ SLACK_WEBHOOK secret が設定されていません")

JSON_SOURCES = [
    "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json",
    "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
]
UA = {"User-Agent": "macro-notifier/1.2"}

# ---------- JSON 取得 ----------
resp = None
for url in JSON_SOURCES:
    try:
        host = url.split("//")[1].split("/")[0]
        socket.getaddrinfo(host, 443)  # DNS 解決チェック
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

# ---------- デバッグ: 最初の3件をSlackに送信 ----------
sample = json.dumps(events[:3], ensure_ascii=False, indent=2)
requests.post(SLACK_WEBHOOK, json={"text": f"```{sample}```"})

# ---------- 抽出条件 ----------
TARGET_CCY   = {"USD", "EUR", "GBP", "JPY", "CNY", "AUD", "NZD"}
TARGET_LEVEL = 2  # ★2 以上

jst    = timezone(timedelta(hours=9))
today  = datetime.now(jst).date()
tomorrow = today + timedelta(days=1)
check_dates = {today, tomorrow}

rows = []
for ev in events:
    # --- 日付組み立て ---
    ev_date = ev.get("date") or (
        lambda y, m, d: f"{y:04d}-{m:02d}-{d:02d}" if (y and m and d) else None
    )(ev.get("year") or ev.get("y"), ev.get("month") or ev.get("m"), ev.get("day") or ev.get("d"))
    if not ev_date:
        continue
    try:
        d_obj = datetime.strptime(ev_date, "%Y-%m-%d").date()
    except ValueError:
        continue

    # 00‑05 時台は前日扱い→当日に補正
    time_str = ev.get("time", "00:00")
    try:
        hour = int(time_str.split(":")[0])
    except ValueError:
        hour = 0
    if d_obj == today - timedelta(days=1) and hour < 6:
        d_obj = today

    if d_obj not in check_dates:
        continue

    if (ccy := ev.get("currency")) not in TARGET_CCY:
        continue

    impact_val = int(str(ev.get("impact", "0")))
    if impact_val < TARGET_LEVEL:
        continue

    title = ev.get("title") or ev.get("event") or "不明"
    star  = "★" * impact_val
    rows.append(f"【{ccy}】{time_str} （{title}）（{star}）")

# ---------- Slack 送信 ----------
header = ":chart_with_upwards_trend: *本日の重要経済指標（7通貨・★2以上）*\n\n"
if rows:
    body = "\n".join(rows)
else:
    body = f"本日は対象通貨の重要指標がありません。（raw 件数: {len(events)}）"

requests.post(SLACK_WEBHOOK, json={"text": header + body})

