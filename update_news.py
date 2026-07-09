import os
import json
import datetime
import urllib.request
import urllib.parse
import urllib.error
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
MAX_OTHER_NEWS = 6


# ==========================================
# Google News RSS
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
# 前回データ
# ==========================================

def load_previous_data():
    try:
        with open("news.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"items": []}


# ==========================================
# Gemini API
# 503時は自動リトライ
# ==========================================

def call_gemini(prompt, max_attempts=3):
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY が設定されていません。")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{GEMINI_MODEL}:generateContent"
        f"?key={urllib.parse.quote(GEMINI_API_KEY)}"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.15,
            "responseMimeType": "application/json"
        }
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    for attempt in range(1, max_attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                result = json.loads(
                    response.read().decode("utf-8")
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
                raise RuntimeError("Geminiの回答本文が空です。")

            return json.loads(text)

        except urllib.error.HTTPError as error:
            error_body = error.read().decode(
                "utf-8",
                errors="replace"
            )

            if error.code in (429, 500, 502, 503, 504):
                if attempt < max_attempts:
                    wait_seconds = 30 * attempt
                    print(
                        f"Gemini API HTTP {error.code}. "
                        f"{wait_seconds}秒後に再試行します..."
                    )
                    time.sleep(wait_seconds)
                    continue

            raise RuntimeError(
                f"Gemini API HTTP {error.code}: {error_body}"
            )

    raise RuntimeError("Gemini APIへの接続に失敗しました。")


# ==========================================
# AIプロンプト
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
あなたは「GULF WATCH JP」のAIニュース編集長です。
読者は主にドバイ・UAE在住の日本人です。

以下のニュース見出しを分析し、
ドバイ在住者が30秒から2分程度で、
「今何が起きているか」「ドバイにどう影響するか」を理解できるように編集してください。


【最重要ルール】

1. 必ず自然で読みやすい日本語で回答する。
2. ニュース見出しから確認できない事実を推測しない。
3. 同じ出来事を扱う類似ニュースは重複として扱い、原則1件だけ選ぶ。
4. 同じ出来事について複数メディアの記事がある場合、最も具体的で重要な1件を代表記事として選ぶ。
5. ドバイへの直接的影響と、湾岸地域全体への間接的影響を明確に区別する。
6. センセーショナルな表現を避ける。
7. 単に Iran、Trump、missile などの単語が含まれるだけで危険度を上げない。
8. 「今日読むべきニュース」と「その他の重要ニュース」は絶対に重複させない。
9. 「昨日から何が変わった？」と「今日読むべきニュース」も、可能な限り重複を避ける。
10. フライトへの影響には、UAE、Dubai、DXB、DWC、Abu Dhabi、AUH、Emirates、flydubai、Etihadに実際に関連する記事だけを選ぶ。
11. 同じ事実や結論を、タイトル・要約・読むべきポイントで繰り返さない。
12. 各文章にはそれぞれ明確に異なる役割を持たせる。


【サイトの表示構成】

1. 今、ドバイは安全？
2. 現在の状況まとめ：約3文
3. 昨日から何が変わった？：最大3件
4. 今日読むべきニュース：最大3件
5. フライトへの影響：関連する重要記事のみ、最大3件
6. その他の重要ニュース：最大6件。ただし十分な重要ニュースがなければ少なくてよい。


【1. 今、ドバイは安全？】

risk.summary は、
「現在のドバイまたはUAEの安全状況の結論」だけを書いてください。

必ず1〜2文、できるだけ短くしてください。

ここでは国際情勢全体を詳しく説明しないでください。
米国・イラン間で何が起きたかなどの詳細は、
current_situation_summary に書いてください。

risk.summary と current_situation_summary で
同じ文章、同じ事実、同じ表現を繰り返してはいけません。

良い例：
「現時点でドバイ市内への直接的な脅威は確認されていません。ただし、湾岸地域の緊張とフライトへの影響には注意が必要です。」

悪い例：
米国とイランの攻撃内容やホルムズ海峡の詳細を長く説明する。


【安全レベル】

green = 通常
yellow = 注意
orange = 警戒
red = 重大

安全レベルは、
ドバイまたはUAEへの実際の直接的影響を最も重視してください。

湾岸地域で緊張が高まっているだけで、
ドバイへの直接的な脅威が確認されていない場合、
過度に高い安全レベルを設定しないでください。


【2. 現在の状況まとめ】

current_situation_summary は、
日本語で約3文にしてください。

内容は可能な限り次の順番にしてください。

- 現在、国際情勢または湾岸地域で何が起きているか
- ドバイまたはUAEへの直接的・間接的影響
- フライト、空域、物流など今後注意すべきこと

risk.summary ですでに書いた結論を繰り返さず、
より具体的な背景と現在の状況を説明してください。


【3. 各ニュースの文章の役割】

各ニュースについて、以下の4つを作成してください。

■ title_ja
何が起きたかを一目で理解できる、
自然で簡潔な日本語タイトル。

■ summary_ja
ニュース本文の要約。
「何が起きたか」に加えて、
タイトルだけでは分からない具体的な情報や背景を書く。
1〜2文。

タイトルを単純に言い換えただけの文章は禁止。

■ key_point_ja
ニュース内容を再び要約してはいけません。

必ず以下のどれかを説明してください。

- なぜこのニュースが重要なのか
- ドバイ・UAE在住者にどんな影響があり得るのか
- フライト、空域、物流、安全、生活にどう関係するのか
- 今後何に注目すべきなのか

1文で簡潔に書いてください。

■ importance_score
0〜100の整数。


【重複禁止の具体例】

悪い例：

タイトル：
「米軍がイランを攻撃」

要約：
「米軍がイランへの攻撃を実施しました。」

読むべきポイント：
「米軍によるイラン攻撃は重要な動きです。」

これは3回ほぼ同じことを言っているので禁止です。


良い例：

タイトル：
「米軍、イラン国内の複数目標を攻撃」

要約：
「米軍は過去2夜で複数の目標を攻撃し、米イラン間の軍事的緊張が再び高まっています。」

読むべきポイント：
「緊張の拡大により、UAE周辺の空域変更やフライト運航への影響に注意が必要です。」


【重要フレーズのハイライト】

各文章について、
読者が一目で最重要ポイントを理解できるよう、
重要な短いフレーズを1つだけ選んでください。

以下のフィールドを追加してください。

- risk_highlight
- situation_highlight
- summary_highlight
- key_point_highlight

ルール：

1. 必ず元の文章の中に完全一致する文字列を選ぶ。
2. 1つのハイライトは原則5〜20文字程度。
3. 文章全体をハイライトしない。
4. 1文章につき最大1か所だけ。
5. 重要な結論、数字、直接的影響を優先する。
6. 適切なフレーズがない場合は空文字 "" にする。


【返却するJSON形式】

{{
  "risk": {{
    "level": "green または yellow または orange または red",
    "label": "通常 または 注意 または 警戒 または 重大",
    "summary": "ドバイの安全状況についての短い説明",
    "risk_highlight": "summary内に完全一致する重要フレーズ"
  }},

  "current_situation_summary": "現在の状況を約3文でまとめた日本語",

  "situation_highlight": "current_situation_summary内に完全一致する重要フレーズ",

  "items": [
    {{
      "id": "元のニュースID",
      "title_ja": "日本語タイトル",
      "summary_ja": "日本語要約",
      "summary_highlight": "summary_ja内に完全一致する重要フレーズ",
      "key_point_ja": "ドバイ・UAE在住者への意味や影響",
      "key_point_highlight": "key_point_ja内に完全一致する重要フレーズ",
      "importance_score": 0
    }}
  ],

  "changes_ids": [
    "ニュースID"
  ],

  "must_read_ids": [
    "ニュースID"
  ],

  "flight_impact_ids": [
    "ニュースID"
  ],

  "other_news_ids": [
    "ニュースID"
  ]
}}


【最終確認】

JSONを返す前に必ず確認してください。

- risk.summary と current_situation_summary が同じ内容になっていないか
- title_ja と summary_ja が同じ内容になっていないか
- summary_ja と key_point_ja が同じ内容になっていないか
- 「今日読むべきニュース」と「その他の重要ニュース」が重複していないか
- ハイライト文字列が元の文章内に完全一致しているか
- 日本語として自然か

重複があれば、返答前に必ず書き直してください。


【ニュース一覧】

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
# IDから記事を選択
# ==========================================

def select_items_by_ids(items, ids, limit=None, excluded_ids=None):
    item_map = {
        item["id"]: item
        for item in items
    }

    excluded_ids = set(excluded_ids or [])
    selected = []
    seen_ids = set()

    for item_id in ids:
        if item_id in seen_ids:
            continue

        if item_id in excluded_ids:
            continue

        if item_id not in item_map:
            continue

        selected.append(item_map[item_id])
        seen_ids.add(item_id)

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
            fetched = fetch_google_news(category, query)
            all_items.extend(fetched)

        except Exception as error:
            print(f"Fetch error for {category}: {error}")

    # 完全一致の重複削除
    unique_items = {}

    for item in all_items:
        if item["id"] not in unique_items:
            unique_items[item["id"]] = item

    items = list(unique_items.values())

    items.sort(
        key=lambda item: item.get("published_at", ""),
        reverse=True
    )

    items = items[:MAX_TOTAL_ITEMS]

    if not items:
        raise RuntimeError("ニュースを1件も取得できませんでした。")

    print(f"Fetched {len(items)} unique news items.")

    prompt = build_prompt(items, previous_ids)

    print("Sending news to Gemini AI...")

    ai_result = call_gemini(prompt)

    print("Gemini AI analysis completed.")

    items = merge_ai_results(items, ai_result)

    items.sort(
        key=lambda item: item.get("importance_score", 0),
        reverse=True
    )

    # 昨日から何が変わった？
    changes = select_items_by_ids(
        items,
        ai_result.get("changes_ids", []),
        limit=3
    )

    change_ids = {
        item["id"] for item in changes
    }

    # 今日読むべきニュース
    # changesとの重複も可能な限り除外
    must_read = select_items_by_ids(
        items,
        ai_result.get("must_read_ids", []),
        limit=3,
        excluded_ids=change_ids
    )

    # AIが3件選ばなかった場合は、
    # changesと重複しない重要記事から補完
    if len(must_read) < 3:
        existing_ids = change_ids | {
            item["id"] for item in must_read
        }

        for item in items:
            if item["id"] not in existing_ids:
                must_read.append(item)
                existing_ids.add(item["id"])

            if len(must_read) >= 3:
                break

    must_read_ids = {
        item["id"] for item in must_read
    }

    # フライトへの影響
    flight_impacts = select_items_by_ids(
        items,
        ai_result.get("flight_impact_ids", []),
        limit=3
    )

    # その他の重要ニュース
    # 今日読むべきニュースは絶対に除外
    # changesも除外して重複を減らす
    excluded_from_other = (
        must_read_ids |
        change_ids
    )

    other_news = select_items_by_ids(
        items,
        ai_result.get("other_news_ids", []),
        limit=MAX_OTHER_NEWS,
        excluded_ids=excluded_from_other
    )

    # AI選択が6件未満なら、重要度順から補完
    if len(other_news) < MAX_OTHER_NEWS:
        existing_ids = (
            excluded_from_other |
            {item["id"] for item in other_news}
        )

        for item in items:
            if item["id"] not in existing_ids:
                other_news.append(item)
                existing_ids.add(item["id"])

            if len(other_news) >= MAX_OTHER_NEWS:
                break

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

    current_situation_summary = ai_result.get(
        "current_situation_summary",
        risk.get("summary", "")
    )

    output = {
        "updated_at": datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),

        "risk": risk,

        "current_situation_summary": current_situation_summary,

        "changes": changes,

        "must_read": must_read,

        "flight_impacts": flight_impacts,

        "other_news": other_news,

        # 元データも保持
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

    print("================================")
    print("GULF WATCH JP AI update complete")
    print(f"Total source news: {len(items)}")
    print(f"Changes: {len(changes)}")
    print(f"Must read: {len(must_read)}")
    print(f"Flight impacts: {len(flight_impacts)}")
    print(f"Other news: {len(other_news)}")
    print(f"Risk: {risk.get('label', '不明')}")
    print("================================")


if __name__ == "__main__":
    main()
