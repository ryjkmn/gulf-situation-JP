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
# 429 / 5xx は自動リトライ
# ==========================================

def call_gemini(prompt, max_attempts=3):
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
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.15,
            "responseMimeType": "application/json"
        }
    }

    for attempt in range(1, max_attempts + 1):
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=180
            ) as response:
                result = json.loads(
                    response.read().decode("utf-8")
                )

            candidates = result.get("candidates", [])

            if not candidates:
                raise RuntimeError(
                    f"Geminiから回答がありません: {result}"
                )

            parts = (
                candidates[0]
                .get("content", {})
                .get("parts", [])
            )

            if not parts:
                raise RuntimeError(
                    "Geminiの回答本文が空です。"
                )

            text = parts[0].get("text", "")

            if not text:
                raise RuntimeError(
                    "Geminiの回答本文が空です。"
                )

            return json.loads(text)

        except urllib.error.HTTPError as error:
            error_body = error.read().decode(
                "utf-8",
                errors="replace"
            )

            if error.code in (
                429,
                500,
                502,
                503,
                504
            ):
                if attempt < max_attempts:
                    wait_seconds = 30 * attempt

                    print(
                        f"Gemini API HTTP {error.code}. "
                        f"{wait_seconds}秒後に再試行します..."
                    )

                    time.sleep(wait_seconds)
                    continue

            raise RuntimeError(
                f"Gemini API HTTP {error.code}: "
                f"{error_body}"
            )

        except urllib.error.URLError as error:
            if attempt < max_attempts:
                wait_seconds = 30 * attempt

                print(
                    "Gemini API接続エラー。"
                    f"{wait_seconds}秒後に再試行します..."
                )

                time.sleep(wait_seconds)
                continue

            raise RuntimeError(
                f"Gemini APIへの接続に失敗しました: {error}"
            )

        except json.JSONDecodeError as error:
            raise RuntimeError(
                f"GeminiのJSON解析に失敗しました: {error}"
            )

    raise RuntimeError(
        "Gemini APIへの接続に失敗しました。"
    )


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
「今何が起きているか」
「ドバイにどう影響するか」
を理解できるように編集してください。


【絶対ルール】

1. 必ず自然な日本語で回答する。
2. 返却する items には、入力された全ニュースを必ず含める。
3. 全ニュースについて必ず title_ja を日本語で作成する。
4. 全ニュースについて必ず summary_ja を日本語で作成する。
5. 全ニュースについて必ず key_point_ja を日本語で作成する。
6. 英語タイトルを title_ja にそのままコピーしてはいけない。
7. ニュース見出しから確認できない事実を推測しない。
8. センセーショナルな表現を避ける。
9. ドバイへの直接的影響と、湾岸地域全体への間接的影響を区別する。
10. 単に Iran、Trump、missile などの単語が含まれるだけで危険度を上げない。


【ニュースの重複について】

同じ出来事を扱う類似ニュースは、
表示対象として原則1件だけ選んでください。

同じ出来事について複数メディアの記事がある場合は、
最も具体的で重要な1件を代表記事として選んでください。

以下のセクション間では、
同じニュースIDを重複させないでください。

- 昨日から何が変わった？
- 今日読むべきニュース
- フライトへの影響
- その他の重要ニュース


【サイトの表示構成】

1. 今、ドバイは安全？
2. 現在の状況まとめ：約3文
3. 昨日から何が変わった？：最大3件
4. 今日読むべきニュース：最大3件
5. フライトへの影響：最大3件
6. その他の重要ニュース：最大6件


【今、ドバイは安全？】

risk.summary は、
現在のドバイまたはUAEの安全状況について、
結論だけを書いてください。

1〜2文で簡潔にしてください。

ここでは、
米国とイランの攻撃内容や、
ホルムズ海峡などの国際情勢を
詳しく説明しないでください。

それらは current_situation_summary に書いてください。

risk.summary と current_situation_summary で、
同じ事実や同じ表現を繰り返してはいけません。


【安全レベル】

green = 通常
yellow = 注意
orange = 警戒
red = 重大

安全レベルは、
ドバイまたはUAEへの実際の直接的影響を
最も重視してください。

湾岸地域で緊張が高まっているだけで、
ドバイへの直接的な脅威が確認されていない場合は、
過度に高い安全レベルを設定しないでください。


【現在の状況まとめ】

current_situation_summary は、
日本語で約3文にしてください。

内容は可能な限り、
次の順番にしてください。

1. 現在、国際情勢または湾岸地域で何が起きているか。
2. ドバイまたはUAEへの直接的・間接的影響。
3. フライト、空域、物流など今後注意すべきこと。

risk.summary ですでに書いた結論を
そのまま繰り返してはいけません。


【各ニュースの文章の役割】

各ニュースについて、
以下を必ず作成してください。


■ title_ja

何が起きたかを一目で理解できる、
自然で簡潔な日本語タイトル。


■ summary_ja

タイトルだけでは分からない、
具体的な情報や背景を書いてください。

1〜2文にしてください。

タイトルを単純に言い換えただけの文章は禁止です。


■ key_point_ja

ニュース内容を再び要約してはいけません。

以下のいずれかを説明してください。

- なぜこのニュースが重要なのか
- ドバイ・UAE在住者にどんな影響があり得るのか
- フライト、空域、物流、安全、生活にどう関係するのか
- 今後何に注目すべきなのか

1文で簡潔にしてください。


■ importance_score

0〜100の整数。


【タイトル・要約・ポイントの重複禁止】

悪い例：

タイトル：
「米軍がイランを攻撃」

要約：
「米軍がイランへの攻撃を実施しました。」

読むべきポイント：
「米軍によるイラン攻撃は重要な動きです。」

これは同じ内容を3回繰り返しているので禁止です。


良い例：

タイトル：
「米軍、イラン国内の複数目標を攻撃」

要約：
「米軍は過去2夜で複数の目標を攻撃し、
米イラン間の軍事的緊張が再び高まっています。」

読むべきポイント：
「緊張の拡大により、
UAE周辺の空域変更やフライト運航への影響に
注意が必要です。」


【重要フレーズのハイライト】

各文章について、
最重要の短いフレーズを1つだけ選んでください。

以下を返してください。

- risk_highlight
- situation_highlight
- summary_highlight
- key_point_highlight

ルール：

1. 必ず元の文章の中に完全一致する文字列を選ぶ。
2. 原則5〜20文字程度。
3. 文章全体をハイライトしない。
4. 1文章につき最大1か所。
5. 重要な結論、数字、直接的影響を優先する。
6. 適切なフレーズがなければ空文字 "" にする。


【昨日から何が変わった？】

changes_ids には、
is_new=true のニュースの中から、
前回更新以降の重要な変化を最大3件選んでください。

同じ出来事の類似記事を複数選ばないでください。


【今日読むべきニュース】

must_read_ids には、
ドバイ・UAE在住者が今日読む価値が最も高いニュースを
最大3件選んでください。

changes_ids と重複させないでください。


【フライトへの影響】

flight_impact_ids には、
以下に実際に関係するニュースだけを
最大3件選んでください。

- UAE
- Dubai
- DXB
- DWC
- Abu Dhabi
- AUH
- Emirates
- flydubai
- Etihad
- UAE周辺空域

単に中東の航空ニュースというだけでは選ばないでください。

changes_ids と must_read_ids に
すでに含まれる記事は選ばないでください。


【その他の重要ニュース】

other_news_ids には、
上記3セクションに含まれていないニュースから、
重要なものを最大6件選んでください。

同じ出来事の類似記事を複数選ばないでください。


【返却するJSON形式】

{{
  "risk": {{
    "level": "green または yellow または orange または red",
    "label": "通常 または 注意 または 警戒 または 重大",
    "summary": "ドバイの安全状況についての短い説明",
    "risk_highlight": "summary内に完全一致する重要フレーズ"
  }},

  "current_situation_summary":
    "現在の状況を約3文でまとめた日本語",

  "situation_highlight":
    "current_situation_summary内に完全一致する重要フレーズ",

  "items": [
    {{
      "id": "元のニュースID",
      "title_ja": "必ず日本語タイトル",
      "summary_ja": "必ず日本語要約",
      "summary_highlight":
        "summary_ja内に完全一致する重要フレーズ",
      "key_point_ja":
        "必ず日本語でドバイ・UAE在住者への意味や影響",
      "key_point_highlight":
        "key_point_ja内に完全一致する重要フレーズ",
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

- 入力された全ニュースが items に含まれているか。
- 全記事に日本語の title_ja があるか。
- 全記事に日本語の summary_ja があるか。
- 全記事に日本語の key_point_ja があるか。
- risk.summary と current_situation_summary が重複していないか。
- title_ja と summary_ja が同じ内容になっていないか。
- summary_ja と key_point_ja が同じ内容になっていないか。
- 各セクション間で同じIDが重複していないか。
- 類似ニュースを複数選んでいないか。
- ハイライト文字列が元文章内に完全一致しているか。
- 日本語として自然か。

問題があれば、
JSONを返す前に必ず修正してください。


【ニュース一覧】

{json.dumps(simplified_items, ensure_ascii=False, indent=2)}
"""


# ==========================================
# 日本語文字が含まれているか確認
# ==========================================

def contains_japanese(text):
    if not text:
        return False

    for char in text:
        code = ord(char)

        if (
            0x3040 <= code <= 0x309F or
            0x30A0 <= code <= 0x30FF or
            0x4E00 <= code <= 0x9FFF
        ):
            return True

    return False


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

        title_ja = str(
            ai_data.get("title_ja", "")
        ).strip()

        summary_ja = str(
            ai_data.get("summary_ja", "")
        ).strip()

        key_point_ja = str(
            ai_data.get("key_point_ja", "")
        ).strip()

        item["title_ja"] = title_ja
        item["summary_ja"] = summary_ja

        item["summary_highlight"] = str(
            ai_data.get(
                "summary_highlight",
                ""
            )
        ).strip()

        item["key_point_ja"] = key_point_ja

        item["key_point_highlight"] = str(
            ai_data.get(
                "key_point_highlight",
                ""
            )
        ).strip()

        try:
            item["importance_score"] = int(
                ai_data.get(
                    "importance_score",
                    0
                )
            )
        except Exception:
            item["importance_score"] = 0

        # 表示可能条件：
        # タイトル・要約・ポイントがすべて存在し、
        # すべてに日本語が含まれていること
        item["is_translated"] = (
            bool(title_ja) and
            bool(summary_ja) and
            bool(key_point_ja) and
            contains_japanese(title_ja) and
            contains_japanese(summary_ja) and
            contains_japanese(key_point_ja)
        )

        merged.append(item)

    return merged


# ==========================================
# IDから記事を選択
# ==========================================

def select_items_by_ids(
    items,
    ids,
    limit=None,
    excluded_ids=None
):
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
# 重要度順から不足分を補完
# ==========================================

def fill_from_ranked_items(
    selected,
    ranked_items,
    limit,
    excluded_ids=None
):
    excluded_ids = set(excluded_ids or [])

    existing_ids = {
        item["id"]
        for item in selected
    }

    for item in ranked_items:
        item_id = item["id"]

        if item_id in excluded_ids:
            continue

        if item_id in existing_ids:
            continue

        selected.append(item)
        existing_ids.add(item_id)

        if len(selected) >= limit:
            break

    return selected


# ==========================================
# メイン
# ==========================================

def main():
    print(
        "Starting GULF WATCH JP AI update..."
    )

    previous_data = load_previous_data()

    previous_ids = {
        item.get("id")
        for item in previous_data.get(
            "items",
            []
        )
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
                f"Fetch error for "
                f"{category}: {error}"
            )

    # 完全一致の重複を削除
    unique_items = {}

    for item in all_items:
        if item["id"] not in unique_items:
            unique_items[item["id"]] = item

    items = list(unique_items.values())

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
        f"Fetched {len(items)} "
        "unique news items."
    )

    prompt = build_prompt(
        items,
        previous_ids
    )

    print(
        "Sending news to Gemini AI..."
    )

    ai_result = call_gemini(prompt)

    print(
        "Gemini AI analysis completed."
    )

    items = merge_ai_results(
        items,
        ai_result
    )

    # 日本語化が完了した記事だけを
    # 実際の表示候補にする
    display_items = [
        item
        for item in items
        if item.get(
            "is_translated",
            False
        )
    ]

    display_items.sort(
        key=lambda item: item.get(
            "importance_score",
            0
        ),
        reverse=True
    )

    print(
        f"Translated display items: "
        f"{len(display_items)}"
    )

    if not display_items:
        raise RuntimeError(
            "日本語化されたニュースが"
            "1件もありませんでした。"
        )

    # ======================================
    # 昨日から何が変わった？
    # ======================================

    changes = select_items_by_ids(
        display_items,
        ai_result.get(
            "changes_ids",
            []
        ),
        limit=3
    )

    change_ids = {
        item["id"]
        for item in changes
    }

    # ======================================
    # 今日読むべきニュース
    # changesとの重複を禁止
    # ======================================

    must_read = select_items_by_ids(
        display_items,
        ai_result.get(
            "must_read_ids",
            []
        ),
        limit=3,
        excluded_ids=change_ids
    )

    must_read = fill_from_ranked_items(
        must_read,
        display_items,
        3,
        excluded_ids=change_ids
    )

    must_read_ids = {
        item["id"]
        for item in must_read
    }

    # ======================================
    # フライトへの影響
    # changes・must_readとの重複を禁止
    # ======================================

    excluded_from_flights = (
        change_ids |
        must_read_ids
    )

    flight_impacts = select_items_by_ids(
        display_items,
        ai_result.get(
            "flight_impact_ids",
            []
        ),
        limit=3,
        excluded_ids=excluded_from_flights
    )

    flight_ids = {
        item["id"]
        for item in flight_impacts
    }

    # ======================================
    # その他の重要ニュース
    # 上の全セクションとの重複を禁止
    # ======================================

    excluded_from_other = (
        change_ids |
        must_read_ids |
        flight_ids
    )

    other_news = select_items_by_ids(
        display_items,
        ai_result.get(
            "other_news_ids",
            []
        ),
        limit=MAX_OTHER_NEWS,
        excluded_ids=excluded_from_other
    )

    other_news = fill_from_ranked_items(
        other_news,
        display_items,
        MAX_OTHER_NEWS,
        excluded_ids=excluded_from_other
    )

    # ======================================
    # 安全状況
    # ======================================

    risk = ai_result.get(
        "risk",
        {
            "level": "green",
            "label": "通常",
            "summary": (
                "現在取得できたニュースからは、"
                "ドバイへの重大な直接的影響は"
                "確認されていません。"
            ),
            "risk_highlight": ""
        }
    )

    current_situation_summary = str(
        ai_result.get(
            "current_situation_summary",
            ""
        )
    ).strip()

    situation_highlight = str(
        ai_result.get(
            "situation_highlight",
            ""
        )
    ).strip()

    # ======================================
    # news.json 出力
    # ======================================

    output = {
        "updated_at": (
            datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat()
        ),

        "risk": risk,

        "current_situation_summary":
            current_situation_summary,

        "situation_highlight":
            situation_highlight,

        "changes": changes,

        "must_read": must_read,

        "flight_impacts":
            flight_impacts,

        "other_news": other_news,

        # 元データは保存しておく
        "items": items
    }

    with open(
        "news.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        "================================"
    )
    print(
        "GULF WATCH JP AI update complete"
    )
    print(
        f"Total source news: {len(items)}"
    )
    print(
        "Translated display items: "
        f"{len(display_items)}"
    )
    print(
        f"Changes: {len(changes)}"
    )
    print(
        f"Must read: {len(must_read)}"
    )
    print(
        "Flight impacts: "
        f"{len(flight_impacts)}"
    )
    print(
        f"Other news: {len(other_news)}"
    )
    print(
        f"Risk: {risk.get('label', '不明')}"
    )
    print(
        "================================"
    )


if __name__ == "__main__":
    main()
