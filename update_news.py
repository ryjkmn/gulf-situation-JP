import os
import json
import datetime
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import hashlib
import email.utils
import time


# ==========================================
# 設定
# ==========================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

GEMINI_MODEL = "gemini-2.5-flash"

SEARCHES = [
    ("US", "Trump Iran US military Middle East"),
    ("Iran", "Iran missile retaliation nuclear attack"),
    ("Gulf", "UAE Saudi Qatar Bahrain Kuwait Oman Iran attack"),
    ("Flight", "UAE Dubai airspace closure flights Iran Middle East"),
    ("Hormuz", "Strait of Hormuz tanker shipping Iran"),
]

MAX_ITEMS_PER_SEARCH = 5
MAX_TOTAL_ITEMS = 25


# ==========================================
# Google News RSSからニュース取得
# ==========================================

def fetch_google_news(category, query):

    encoded = urllib.parse.quote(query)

    url = (
        "https://news.google.com/rss/search?"
        f"q={encoded}&hl=en-US&gl=US&ceid=US:en"
    )

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)

    items = []

    for item in root.findall(".//item")[:MAX_ITEMS_PER_SEARCH]:

        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        pub_date = item.findtext("pubDate", "").strip()

        try:
            parsed_date = email.utils.parsedate_to_datetime(pub_date)
            published_at = parsed_date.isoformat()
        except Exception:
            published_at = pub_date

        unique_id = hashlib.md5(
            (title + link).encode("utf-8")
        ).hexdigest()

        items.append({
            "id": unique_id,
            "category": category,
            "title": title,
            "url": link,
            "published_at": published_at,
        })

    return items


# ==========================================
# 前回のnews.jsonを読み込む
# ==========================================

def load_previous_data():

    try:
        with open("news.json", "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception:
        return {"items": []}


# ==========================================
# Gemini API
# ==========================================

def call_gemini(prompt):

    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY が設定されていません。"
        )

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{GEMINI_MODEL}:generateContent"
        f"?key={urllib.parse.quote(GEMINI_API_KEY)}"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json"
        }
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as error:

        error_body = error.read().decode(
            "utf-8",
            errors="replace"
        )

        raise RuntimeError(
            f"Gemini API HTTP {error.code}: {error_body}"
        )

    candidates = result.get("candidates", [])

    if not candidates:
        raise RuntimeError(
            f"Geminiから回答がありません: {result}"
        )

    text = (
        candidates[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "")
    )

    if not text:
        raise RuntimeError(
            "Geminiの回答本文が空です。"
        )

    return json.loads(text)


# ==========================================
# AI分析用プロンプト
# ==========================================

def build_prompt(items, previous_ids):

    simplified_items = []

    for item in items:
        simplified_items.append({
            "id": item["id"],
            "category": item["category"],
            "title": item["title"],
            "published_at": item["published_at"],
            "is_new": item["id"] not in previous_ids
        })

    return f"""
あなたは、ドバイ在住の日本人向けに、
イラン、米国、湾岸諸国、ホルムズ海峡、
中東の空域・航空便を分析するニュース編集者です。

以下のニュース見出しを分析してください。

重要なルール:
- 必ず日本語で回答する。
- 事実を推測しない。
- ニュース見出しから確認できない内容は断定しない。
- ドバイへの直接的影響と、湾岸地域全体への影響を区別する。
- 単に「Iran」という単語があるだけで危険度を上げない。
- 同じ出来事の重複記事は重要ニュースとして複数選ばない。
- センセーショナルな表現を避ける。
- 安全判定は取得したニュースだけを根拠にする。
- 「今日読むべきニュース」はドバイ在住者にとって重要な3件を選ぶ。
- 「昨日から何が変わった？」は is_new=true の中から最大3件を選ぶ。
- フライト情報はUAE、Dubai、DXB、DWC、Abu Dhabi、AUH、
  Emirates、flydubai、Etihadへの影響があるものだけを選ぶ。

安全レベル:
- green = 通常
- yellow = 注意
- orange = 警戒
- red = 重大

各ニュースについて以下を作成してください:
- title_ja: 自然で短い日本語タイトル
- summary_ja: 日本語で1〜2文の要約
- key_point_ja: ドバイ在住者が最も読むべきポイントを1文
- importance_score: 0〜100

以下のJSON形式だけを返してください:

{{
  "risk": {{
    "level": "green または yellow または orange または red",
    "label": "通常 または 注意 または 警戒 または 重大",
    "summary": "日本語の短い説明"
  }},
  "items": [
    {{
      "id": "元のニュースID",
      "title_ja": "日本語タイトル",
      "summary_ja": "日本語要約",
      "key_point_ja": "最重要ポイント",
      "importance_score": 0
    }}
  ],
  "changes_ids": [
    "ニュースID"
  ],
  "must_read_ids": [
    "ニュースID",
    "ニュースID",
    "ニュースID"
  ],
  "flight_impact_ids": [
    "ニュースID"
  ]
}}

ニュース一覧:
{json.dumps(simplified_items, ensure_ascii=False, indent=2)}
"""


# ==========================================
# AI結果を元データに統合
# ==========================================

def merge_ai_results(items, ai_result):

    ai_items = {
        item.get("id"): item
        for item in ai_result.get("items", [])
        if item.get("id")
    }

    merged = []

    for original in items:

        item = original.copy()

        ai_data = ai_items.get(item["id"], {})

        item["title_ja"] = ai_data.get(
            "title_ja",
            item["title"]
        )

        item["summary_ja"] = ai_data.get(
            "summary_ja",
            ""
        )

        item["key_point_ja"] = ai_data.get(
            "key_point_ja",
            ""
        )

        try:
            item["importance_score"] = int(
                ai_data.get("importance_score", 0)
            )
        except Exception:
            item["importance_score"] = 0

        merged.append(item)

    return merged


# ==========================================
# IDから記事を取得
# ==========================================

def select_items_by_ids(items, ids, limit=None):

    item_map = {
        item["id"]: item
        for item in items
    }

    selected = []

    for item_id in ids:

        if item_id in item_map:
            selected.append(item_map[item_id])

        if limit and len(selected) >= limit:
            break

    return selected


# ==========================================
# メイン
# ==========================================

def main():

    print("Starting GULF WATCH JP AI update...")

    previous_data = load_previous_data()

    previous_ids = {
        item.get("id")
        for item in previous_data.get("items", [])
        if item.get("id")
    }

    all_items = []

    for category, query in SEARCHES:

        print(f"Fetching {category}...")

        try:
            fetched = fetch_google_news(
                category,
                query
            )

            all_items.extend(fetched)

        except Exception as error:
            print(
                f"Fetch error for {category}: {error}"
            )

    # 重複削除
    unique_items = {}

    for item in all_items:

        if item["id"] not in unique_items:
            unique_items[item["id"]] = item

    items = list(unique_items.values())

    # 新しい順
    items.sort(
        key=lambda item: item.get(
            "published_at",
            ""
        ),
        reverse=True
    )

    items = items[:MAX_TOTAL_ITEMS]

    if not items:
        raise RuntimeError(
            "ニュースを1件も取得できませんでした。"
        )

    print(
        f"Fetched {len(items)} unique news items."
    )

    prompt = build_prompt(
        items,
        previous_ids
    )

    print("Sending news to Gemini AI...")

    ai_result = call_gemini(prompt)

    print("Gemini AI analysis completed.")

    items = merge_ai_results(
        items,
        ai_result
    )

    # 重要度順
    items.sort(
        key=lambda item: item.get(
            "importance_score",
            0
        ),
        reverse=True
    )

    changes = select_items_by_ids(
        items,
        ai_result.get("changes_ids", []),
        limit=3
    )

    must_read = select_items_by_ids(
        items,
        ai_result.get("must_read_ids", []),
        limit=3
    )

    flight_impacts = select_items_by_ids(
        items,
        ai_result.get(
            "flight_impact_ids",
            []
        ),
        limit=5
    )

    risk = ai_result.get(
        "risk",
        {
            "level": "green",
            "label": "通常",
            "summary": (
                "現在取得できたニュースからは、"
                "ドバイへの重大な直接的影響は確認されていません。"
            )
        }
    )

    output = {
        "updated_at": datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),

        "risk": risk,

        "changes": changes,

        "must_read": must_read,

        "flight_impacts": flight_impacts,

        "items": items
    }

    with open(
        "news.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("==============================")
    print("GULF WATCH JP AI update complete")
    print(f"Total news: {len(items)}")
    print(f"Changes: {len(changes)}")
    print(f"Must read: {len(must_read)}")
    print(f"Flight impacts: {len(flight_impacts)}")
    print(f"Risk: {risk.get('label', '不明')}")
    print("==============================")


if __name__ == "__main__":
    main()
