import os
import json
import requests
from datetime import datetime, timedelta, timezone

# 環境変数取得 (TRADING_ECONOMICS_API_KEY または TE_API_KEY のどちらかを参照)
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")
TRADING_API_KEY = os.getenv("TRADING_ECONOMICS_API_KEY") or os.getenv("TE_API_KEY")
if not SLACK_WEBHOOK:
    raise ValueError("❌ Slack Webhook URL が環境変数から取得できません。Secrets を確認してください。")
if not TRADING_API_KEY:
    raise ValueError("❌ Trading Economics API キーが環境変数から取得できません。Secrets を確認してください。(TRADING_ECONOMICS_API_KEY or TE_API_KEY)")

# 翻訳用（Optional: googletrans==3.1.0a0 を requirements.txt に追加）
try:
    from googletrans import Translator
    translator = Translator()
    def to_ja(text):
        return translator.translate(text, dest='ja').text
except Exception:
    def to_ja(text):
        return text  # 翻訳不可時は原文を返す

# フィルタ設定
IMPACT_MAP = {'Low': 1, 'Medium': 2, 'High': 3}
MIN_IMPACT = 1  # ☆1以上

# JST 06:01-翌06:00 範囲
JST = timezone(timedelta(hours=9))
now = datetime.now(JST)
start = now.replace(hour=6, minute=1, second=0, microsecond=0)
if now.hour < 6:
    start -= timedelta(days=1)
end = start + timedelta(days=1)

def fetch_events():
    url = (
        f"https://api.tradingeconomics.com/calendar"
        f"?d1={start.date()}&d2={end.date()}"
        f"&c=USD,EUR,GBP,JPY,CNY,AUD,NZD"
        f"&f=json&apikey={TRADING_API_KEY}"
    )
    r = requests.get(url)
    if r.status_code != 200:
        msg = f"⚠️ API Error {r.status_code}\nRequest URL: {url}\nStatus: {r.status_code}"
        requests.post(SLACK_WEBHOOK, json={"text": msg})
        exit(1)
    return r.json()

# --- メイン処理 ---
events = fetch_events()

# --- デバッグ: 最初の3件をSlackに出力 ---
sample = json.dumps(events[:3], ensure_ascii=False, indent=2)
requests.post(SLACK_WEBHOOK, json={"text": f"```{sample}```"})

filtered = []
for ev in events:
    if IMPACT_MAP.get(ev.get('impact', 'Low'), 0) < MIN_IMPACT:
        continue
    t = datetime.fromisoformat(ev['date']).astimezone(JST)
    if not (start <= t < end):
        continue
    filtered.append((ev, t))

# Slack メッセージ作成
lines = []
for ev, t in filtered:
    time_str = t.strftime('%H:%M')
    title_ja = to_ja(ev['title'])
    stars = '★' * IMPACT_MAP.get(ev['impact'], 1)
    caution = ' ⚠️ 大きく動く可能性あり' if IMPACT_MAP.get(ev['impact'], 1) >= 2 else ''
    lines.append(f"【{ev['country']}】{time_str} （{title_ja}）（{stars}）{caution}")

header = ":chart_with_upwards_trend: 本日の重要経済指標（☆1以上）\n"
body = "\n".join(lines) if lines else "本日は対象通貨の重要指標がありません。"

# 簡易要約レポート（例: 将来的に別API差し替え可能）
summary_en = (
    "<ここに要約文を生成 or 外部API呼び出しで置換>"
)
report = to_ja(summary_en)

payload = {
    "text": header + body + f"\n\n:page_facing_up: 要約レポート\n{report}"
}
requests.post(SLACK_WEBHOOK, json=payload)

