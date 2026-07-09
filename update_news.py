import json
import datetime
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import hashlib
import email.utils

# 検索するニューステーマ
SEARCHES = [
    ("US", "Trump Iran US military Middle East"),
    ("Iran", "Iran missile retaliation nuclear"),
    ("Gulf", "UAE Saudi Qatar Bahrain Kuwait Oman Iran attack"),
    ("Flight", "UAE Dubai airspace closure flights Iran Middle East"),
    ("Hormuz", "Strait of Hormuz tanker shipping Iran"),
]

MAX_ITEMS_PER_SEARCH = 5


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

    with urllib.request.urlopen(request, timeout=20) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)
    results = []

    for item in root.findall(".//item")[:MAX_ITEMS_PER_SEARCH]:
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        pub_date = item.findtext("pubDate", "").strip()

        try:
            parsed_date = email.utils.parsedate_to_datetime(pub_date)
            published_at = parsed_date.isoformat()
        except Exception:
            published_at = datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat()

        item_id = hashlib.md5(
            (title + link).encode("utf-8")
        ).hexdigest()

        results.append({
            "id": item_id,
            "category": category,
            "published_at": published_at,
            "title_ja": title,
            "summary_ja": "最新ニュースとして自動取得されました。",
            "dubai_impact": assess_dubai_impact(title),
            "url": link,
            "location": None
        })

    return results


def assess_dubai_impact(text):
    text = text.lower()

    high_keywords = [
        "uae",
        "dubai",
        "abu dhabi",
        "missile attack",
        "drone attack",
        "airspace closure",
    ]

    medium_keywords = [
        "bahrain",
        "qatar",
        "kuwait",
        "saudi",
        "hormuz",
        "tanker",
        "us military",
    ]

    if any(word in text for word in high_keywords):
        return (
            "UAEまたはドバイに直接関係する可能性があります。"
            "公式情報とフライト状況を確認してください。"
        )

    if any(word in text for word in medium_keywords):
        return (
            "湾岸地域に関連する動きです。現時点でドバイへの"
            "直接的影響が確認されていない場合でも、情勢の変化に注意が必要です。"
        )

    return (
        "現時点では、ドバイへの直接的な影響は確認されていません。"
    )


def calculate_risk(items):
    titles = " ".join(
        item["title_ja"].lower() for item in items
    )

    red_terms = [
        "attack on uae",
        "missile hits dubai",
        "attack on dubai",
        "uae under attack",
    ]

    orange_terms = [
        "uae airspace closure",
        "missile attack",
        "drone attack",
        "strait of hormuz closed",
    ]

    yellow_terms = [
        "iran retaliation",
        "us military",
        "tanker attack",
        "airspace",
        "flight cancelled",
    ]

    if any(term in titles for term in red_terms):
        return {
            "level": "red",
            "summary": (
                "UAEまたはドバイに直接関係する重大な安全保障上の"
                "情報が検出されました。公式情報を優先して確認してください。"
            )
        }

    if any(term in titles for term in orange_terms):
        return {
            "level": "orange",
            "summary": (
                "地域情勢に重大な動きがあります。現時点でドバイへの"
                "直接的影響が確認されていない場合でも、注意が必要です。"
            )
        }

    if any(term in titles for term in yellow_terms):
        return {
            "level": "yellow",
            "summary": (
                "湾岸・イラン情勢に注意すべき動きがあります。"
                "ドバイへの直接的影響を継続して確認します。"
            )
        }

    return {
        "level": "green",
        "summary": (
            "現時点で、取得したニュースからドバイへの重大な"
            "直接的影響は検出されていません。"
        )
    }


def main():
    all_items = []

    for category, query in SEARCHES:
        try:
            print(f"Fetching: {category} / {query}")
            items = fetch_google_news(category, query)
            all_items.extend(items)
        except Exception as error:
            print(f"Error fetching {category}: {error}")

    # 重複を削除
    unique_items = {}
    for item in all_items:
        unique_items[item["id"]] = item

    items = list(unique_items.values())

    # 新しい順
    items.sort(
        key=lambda x: x["published_at"],
        reverse=True
    )

    # 最大30件
    items = items[:30]

    data = {
        "updated_at": datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),
        "risk": calculate_risk(items),
        "items": items
    }

    with open(
        "news.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(f"Updated news.json with {len(items)} items.")


if __name__ == "__main__":
    main()
