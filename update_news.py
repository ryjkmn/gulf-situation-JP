import json
import datetime
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import hashlib
import email.utils

# ==========================================
# GULF WATCH JP
# ニュース検索設定
# ==========================================

SEARCHES = [
    ("US", "Trump Iran US military Middle East"),
    ("Iran", "Iran missile retaliation nuclear"),
    ("Gulf", "UAE Saudi Qatar Bahrain Kuwait Oman Iran attack"),
    ("Flight", "UAE Dubai airspace closure flights Iran Middle East"),
    ("Hormuz", "Strait of Hormuz tanker shipping Iran"),
]

MAX_ITEMS_PER_SEARCH = 5


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

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
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

    except Exception as e:
        print(f"ERROR: {category}: {e}")
        return []


# ==========================================
# 重要度スコア
# ==========================================

def calculate_importance(item):

    text = item.get("title", "").lower()
    score = 0

    # ドバイ・UAEへの直接関連
    direct_uae = [
        "dubai", "uae", "united arab emirates",
        "abu dhabi", "dxb", "auh"
    ]

    # 高リスク軍事情勢
    critical = [
        "missile", "attack", "strike", "bomb",
        "explosion", "war", "retaliation",
        "airspace closed", "airspace closure"
    ]

    # 米国・イラン関連
    geopolitical = [
        "trump", "iran", "tehran",
        "pentagon", "us military",
        "revolutionary guard", "irgc"
    ]

    # フライト関連
    flight = [
        "flight cancelled", "flight canceled",
        "airspace", "airport closed",
        "emirates", "flydubai", "etihad",
        "dxb", "auh", "diverted"
    ]

    # ホルムズ海峡・物流
    shipping = [
        "hormuz", "tanker", "shipping",
        "oil", "vessel"
    ]

    for keyword in direct_uae:
        if keyword in text:
            score += 5

    for keyword in critical:
        if keyword in text:
            score += 4

    for keyword in geopolitical:
        if keyword in text:
            score += 2

    for keyword in flight:
        if keyword in text:
            score += 4

    for keyword in shipping:
        if keyword in text:
            score += 2

    return score


# ==========================================
# ドバイへの危険度判定
# ==========================================

def calculate_dubai_risk(items):

    titles = " ".join(
        item.get("title", "").lower()
        for item in items
    )

    red_signals = [
        "attack on dubai",
        "attack on uae",
        "missile hits uae",
        "missile attack uae",
        "explosion in dubai",
        "dubai airport closed",
        "uae airspace closed"
    ]

    orange_signals = [
        "missile intercepted uae",
        "uae intercepts missile",
        "attack abu dhabi",
        "strike abu dhabi",
        "dxb closed",
        "auh closed"
    ]

    yellow_signals = [
        "iran attack",
        "iran retaliation",
        "us strikes iran",
        "us attacks iran",
        "gulf tensions",
        "hormuz closed",
        "hormuz closure",
        "bahrain attack",
        "qatar attack",
        "kuwait attack"
    ]

    if any(signal in titles for signal in red_signals):
        return {
            "level": "red",
            "label": "重大",
            "emoji": "🔴",
            "summary": "UAEまたはドバイへの直接的な安全上の影響を示す情報が確認されています。公式情報を優先して確認してください。"
        }

    if any(signal in titles for signal in orange_signals):
        return {
            "level": "orange",
            "label": "警戒",
            "emoji": "🟠",
            "summary": "UAEへの直接的な影響につながる可能性のある重要な動きがあります。最新情報に注意してください。"
        }

    if any(signal in titles for signal in yellow_signals):
        return {
            "level": "yellow",
            "label": "注意",
            "emoji": "🟡",
            "summary": "湾岸・イラン情勢に注意すべき動きがあります。現時点でのドバイへの直接的影響を継続して確認します。"
        }

    return {
        "level": "green",
        "label": "通常",
        "emoji": "🟢",
        "summary": "現時点で、取得したニュースからドバイへの重大な直接的影響は確認されていません。"
    }


# ==========================================
# フライト関連ニュース抽出
# ==========================================

def get_flight_impacts(items):

    keywords = [
        "flight", "airspace", "airport",
        "emirates", "flydubai", "etihad",
        "dxb", "dwc", "auh",
        "cancelled", "canceled",
        "diverted", "suspended"
    ]

    uae_keywords = [
        "uae", "dubai", "abu dhabi",
        "dxb", "dwc", "auh",
        "emirates", "flydubai", "etihad"
    ]

    results = []

    for item in items:

        text = item.get("title", "").lower()

        has_flight_keyword = any(
            keyword in text for keyword in keywords
        )

        has_uae_keyword = any(
            keyword in text for keyword in uae_keywords
        )

        if has_flight_keyword and has_uae_keyword:
            results.append(item)

    results.sort(
        key=lambda x: x.get("importance_score", 0),
        reverse=True
    )

    return results[:5]


# ==========================================
# メイン処理
# ==========================================

def main():

    path = "news.json"

    # 前回データを読み込む
    try:
        with open(path, encoding="utf-8") as f:
            old_data = json.load(f)
    except Exception:
        old_data = {
            "items": []
        }

    old_items = old_data.get("items", [])

    old_ids = {
        item.get("id")
        for item in old_items
        if item.get("id")
    }

    # 最新ニュース取得
    all_items = []

    for category, query in SEARCHES:
        print(f"Fetching: {category}")

        fetched = fetch_google_news(category, query)
        all_items.extend(fetched)

    # 重複削除
    unique_items = {}

    for item in all_items:
        item_id = item.get("id")

        if item_id and item_id not in unique_items:
            unique_items[item_id] = item

    items = list(unique_items.values())

    # 重要度スコア追加
    for item in items:
        item["importance_score"] = calculate_importance(item)

    # 公開日時順
    items.sort(
        key=lambda x: x.get("published_at", ""),
        reverse=True
    )

    # 昨日からの変化
    new_items = [
        item for item in items
        if item.get("id") not in old_ids
    ]

    new_items.sort(
        key=lambda x: x.get("importance_score", 0),
        reverse=True
    )

    changes = new_items[:3]

    # 今日読むべきニュース
    must_read = sorted(
        items,
        key=lambda x: x.get("importance_score", 0),
        reverse=True
    )[:3]

    # フライトへの影響
    flight_impacts = get_flight_impacts(items)

    # ドバイ安全度
    risk = calculate_dubai_risk(items)

    now = datetime.datetime.now(
        datetime.timezone.utc
    ).isoformat()

    output = {
        "updated_at": now,
        "risk": risk,
        "changes": changes,
        "must_read": must_read,
        "flight_impacts": flight_impacts,
        "items": items
    }

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("===================================")
    print("GULF WATCH JP update complete")
    print(f"Total news: {len(items)}")
    print(f"Changes: {len(changes)}")
    print(f"Must read: {len(must_read)}")
    print(f"Flight impacts: {len(flight_impacts)}")
    print(f"Dubai risk: {risk['label']}")
    print("===================================")


if __name__ == "__main__":
    main()
