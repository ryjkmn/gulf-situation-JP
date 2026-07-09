import json, datetime, urllib.request, xml.etree.ElementTree as ET, os
# 無料版の土台：RSS取得先を SOURCES に追加できます。
# AI APIなしでは完全な日本語要約はできないため、現在は見出し収集用の安全な最小構成です。
SOURCES = []
path="news.json"
try:
    with open(path,encoding="utf-8") as f: data=json.load(f)
except:
    data={"risk":{"level":"yellow","summary":"最新情報を確認中です。"},"items":[]}
data["updated_at"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
# SOURCES追加後にRSS項目を収集し、既存データへ統合する拡張ポイント
with open(path,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2)
