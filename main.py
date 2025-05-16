import requests

# 経済指標の整形（例）
header = ":chart_with_upwards_trend: 本日の重要経済指標（7通貨・★1以上）"
content = "【USD】21:30（PPI m/m）（★★★）\n【JPY】08:50（GDP q/q）（★★）\n..."

# 要約レポート（日本語）
summary = ":bookmark_tabs: 要約レポート\n本日は米国のPPIが市場の注目材料です。08:50の日本GDPにも注意。"

# Slack送信用
payload = {
    "text": f"{header}\n{content}\n\n{summary}"
}
requests.post(webhook, json=payload)
