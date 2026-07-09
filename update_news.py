import json
import datetime
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import hashlib
import email.utils
import re


# ==========================================
# 検索するニューステーマ
# ==========================================

SEARCHES = [
    ("US", "Trump Iran US military Middle East"),
    ("Iran", "Iran missile retaliation nuclear attack"),
    ("Gulf", "UAE Saudi Qatar Bahrain Kuwait Oman Iran attack"),
    ("Flight", "UAE Dubai airspace closure flights Iran Middle East"),
    ("Hormuz", "Strait of Hormuz tanker shipping Iran"),
]

MAX_ITEMS_PER_SEARCH = 5


# ==========================================
# 日本語カテゴリー名
# ==========================================

CATEGORY_NAMES = {
    "US": "米国・トランプ",
    "Iran": "イラン",
    "Gulf": "湾岸諸国",
    "Flight": "空域・フライト",
    "Hormuz": "ホルムズ海峡",
}


# ==========================================
# Google News RSS取得
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

    with urllib.request.urlopen(request, timeout=20) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)

    items = []

    for item in root.findall(".//item")[:MAX_ITEMS_PER_SEARCH]:

        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        pub_date = item.findtext("pubDate", "").strip()

        try:
            dt = email.utils.parsedate_to_datetime(pub_date)
            published_at = dt.isoformat()
        except Exception:
            published_at = pub_date

        news_id = hashlib.md5(
            (title + link).encode("utf-8")
        ).hexdigest()

        items.append({
            "id": news_id,
            "category": category,
            "title": title,
            "url": link,
            "published_at": published_at,
        })

    return items


# ==========================================
# ニュースの重要度を自動判定
# ==========================================

def calculate_importance(title, category):

    text = title.lower()

    score = 0

    high_keywords = [
        "attack",
        "strike",
        "missile",
        "war",
        "airspace closed",
        "airspace closure",
        "airport closed",
        "evacuation",
        "explosion",
        "nuclear",
        "retaliation",
        "military action",
    ]

    medium_keywords = [
        "trump",
        "iran",
        "pentagon",
        "ceasefire",
        "sanctions",
        "negotiations",
        "deal",
        "threat",
        "tanker",
        "shipping",
    ]

    dubai_keywords = [
        "dubai",
        "uae",
        "emirates",
        "abu dhabi",
        "gulf",
    ]

    for word in high_keywords:
        if word in text:
            score += 5

    for word in medium_keywords:
        if word in text:
            score += 2

    for word in dubai_keywords:
        if word in text:
            score += 4

    if category == "Flight":
        score += 3

    if category == "Gulf":
        score += 2

    return score


# ==========================================
# 日本語の読むべきポイントを自動生成
# ==========================================

def create_japanese_summary(title, category):

    text = title.lower()

    if any(word in text for word in [
        "missile", "attack", "strike", "explosion"
    ]):

        return (
            "軍事攻撃やミサイルに関する新たな動きです。"
            "攻撃場所、被害状況、報復の可能性を確認する必要があります。"
        )

    if "trump" in text:

        return (
            "トランプ大統領の最新発言または米国政府の動きです。"
            "イランへの軍事対応や外交方針に影響する可能性があります。"
        )

    if any(word in text for word in [
        "airspace", "flight", "airport", "emirates"
    ]):

        return (
            "中東地域の空域またはフライトに関する最新情報です。"
            "UAE発着便への影響や迂回ルートに注意が必要です。"
        )

    if any(word in text for word in [
        "hormuz", "tanker", "shipping"
    ]):

        return (
            "ホルムズ海峡と船舶輸送に関する重要な動きです。"
            "原油価格や湾岸地域の物流への影響に注意が必要です。"
        )

    if category == "Iran":

        return (
            "イラン情勢に関する最新の動きです。"
            "軍事的緊張や米国・湾岸諸国への影響を確認しています。"
        )

    if category == "Gulf":

        return (
            "湾岸諸国に関連する最新情報です。"
            "UAEとドバイへの直接的・間接的影響に注意が必要です。"
        )

    return (
        "中東情勢に関する最新ニュースです。"
        "今後の動きとドバイへの影響を継続して確認します。"
    )


# ==========================================
# ドバイへの影響を自動判定
# ==========================================

def create_dubai_impact(title, category):

    text = title.lower()

    if any(word in text for word in [
        "dubai airport closed",
        "dubai airspace closed",
        "uae attack",
        "uae missile",
        "dubai attack",
    ]):

        return (
            "ドバイまたはUAEへの直接的な影響が報じられています。"
            "航空便、安全情報、政府発表を優先して確認してください。"
        )

    if any(word in text for word in [
        "airspace",
        "flight",
        "airport",
        "emirates",
    ]):

        return (
            "ドバイ発着便に遅延、欠航、迂回が発生する可能性があります。"
        )

    if any(word in text for word in [
        "bahrain",
        "kuwait",
        "qatar",
        "saudi",
        "oman",
    ]):

        return (
            "現時点でドバイへの直接的な影響は確認されていませんが、"
            "湾岸地域全体の緊張拡大に注意が必要です。"
        )

    if any(word in text for word in [
        "hormuz",
        "tanker",
        "shipping",
    ]):

        return (
            "ドバイへの直接的な軍事影響は確認されていませんが、"
            "物流、燃料価格、海上輸送への影響が考えられます。"
        )

    if any(word in text for word in [
        "missile",
        "attack",
        "strike",
        "retaliation",
    ]):

        return (
            "現時点でドバイへの直接的な影響は確認されていません。"
            "ただし、報復の連鎖による湾岸地域への波及に注意が必要です。"
        )

    return (
        "現時点では、ドバイへの直接的な影響は確認されていません。"
    )


# ==========================================
# 警戒レベルを判定
# ==========================================

def calculate_risk(items):

    if not items:
        return {
            "level": "情報確認中",
            "summary": "現在、最新情報を確認しています。"
        }

    max_score = max(
        item.get("importance", 0)
        for item in items
    )

    direct_uae = any(
        any(keyword in item["title"].lower() for keyword in [
            "uae attack",
            "uae missile",
            "dubai attack",
            "dubai airport closed",
            "dubai airspace closed",
        ])
        for item in items
    )

    if direct_uae:
        return {
            "level": "警戒",
            "summary": (
                "UAEまたはドバイへの直接的な影響を示す報道があります。"
                "航空、安全、政府発表を優先して確認してください。"
            )
        }

    if max_score >= 12:
        return {
            "level": "注意",
            "summary": (
                "湾岸・イラン情勢に注意すべき重要な動きがあります。"
                "ドバイへの直接的な影響を継続して確認します。"
            )
        }

    return {
        "level": "通常",
        "summary": (
            "現時点でドバイへの重大な直接的影響は確認されていません。"
        )
    }


# ==========================================
# 前回データを読み込む
# ==========================================

def load_previous_data():

    try:
        with open("news.json", encoding="utf-8") as f:
            return json.load(f)

    except Exception:
        return {
            "items": []
        }


# ==========================================
# メイン処理
# ==========================================

def main():

    previous_data = load_previous_data()

    previous_ids = {
        item.get("id")
        for item in previous_data.get("items", [])
    }

    all_items = []

    for category, query in SEARCHES:

        try:
            news_items = fetch_google_news(category, query)

            for item in news_items:

                item["importance"] = calculate_importance(
                    item["title"],
                    category
                )

                item["summary_ja"] = create_japanese_summary(
                    item["title"],
                    category
                )

                item["impact_ja"] = create_dubai_impact(
                    item["title"],
                    category
                )

                all_items.append(item)

        except Exception as error:
            print(
                f"Error fetching {category}: {error}"
            )


    # 重複削除
    unique_items = {}

    for item in all_items:
        unique_items[item["id"]] = item

    all_items = list(unique_items.values())


    # 重要度順に並べる
    all_items.sort(
        key=lambda item: (
            item.get("importance", 0),
            item.get("published_at", "")
        ),
        reverse=True
    )


    # 最大30件
    all_items = all_items[:30]


    # 前回から新しく追加された重要ニュース
    changes = []

    for item in all_items:

        if (
            item["id"] not in previous_ids
            and item.get("importance", 0) >= 7
        ):

            changes.append({
                "title": item["title"],
                "summary": item["summary_ja"],
            })


    # 最大5件
    changes = changes[:5]


    risk = calculate_risk(all_items)


    output = {
        "updated_at": datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),

        "risk": risk,

        "changes": changes,

        "items": all_items,
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


    print(
        f"Updated news.json with "
        f"{len(all_items)} items."
    )


if __name__ == "__main__":
    main()
