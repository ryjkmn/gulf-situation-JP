const DATA_URL = "news.json";

let allItems = [];

// 日本語カテゴリー名
const categoryNames = {
  US: "米国・トランプ",
  Iran: "イラン",
  Gulf: "湾岸諸国",
  Flight: "空域・フライト",
  Hormuz: "ホルムズ海峡"
};

async function loadNews() {
  try {
    const response = await fetch(`${DATA_URL}?t=${Date.now()}`);

    if (!response.ok) {
      throw new Error("ニュースデータを取得できませんでした");
    }

    const data = await response.json();

    allItems = Array.isArray(data.items) ? data.items : [];

    updatePage(data);
    renderNews(allItems);
    renderFilters();

  } catch (error) {
    console.error(error);

    const newsList = document.getElementById("newsList");

    if (newsList) {
      newsList.innerHTML = `
        <p class="empty">
          現在、ニュース情報を取得できません。
        </p>
      `;
    }
  }
}


function updatePage(data) {

  // 更新時間
  const updatedAt = document.getElementById("updatedAt");

  if (updatedAt && data.updated_at) {
    const date = new Date(data.updated_at);

    updatedAt.textContent = date.toLocaleString("ja-JP", {
      timeZone: "Asia/Dubai",
      year: "numeric",
      month: "numeric",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });
  }


  // 現在の警戒レベル
  const risk = data.risk || {};
  const riskLevel = document.getElementById("riskLevel");

  if (riskLevel) {
    riskLevel.textContent = risk.level || "確認中";
  }


  // AIが選んだ最重要ポイント
  const heroHighlight = document.getElementById("heroHighlight");

  if (heroHighlight) {

    if (risk.summary) {
      heroHighlight.textContent = risk.summary;

    } else if (allItems.length > 0) {
      heroHighlight.textContent =
        allItems[0].summary ||
        allItems[0].title ||
        "最新情報を確認しています。";

    } else {
      heroHighlight.textContent =
        "現在、重要な変化がないか確認しています。";
    }
  }


  // 前回からの変化
  renderChanges(data.changes || []);
}


function renderChanges(changes) {

  const container = document.getElementById("changesList");

  if (!container) return;

  if (!Array.isArray(changes) || changes.length === 0) {

    container.innerHTML = `
      <p class="empty">
        前回の確認以降、重要な変化はありません。
      </p>
    `;

    return;
  }

  container.innerHTML = changes.map(change => `
    <article>
      <h3>${escapeHTML(change.title || "重要な変化")}</h3>

      ${
        change.summary
          ? `<p>${escapeHTML(change.summary)}</p>`
          : ""
      }
    </article>
  `).join("");
}


function renderFilters() {

  const filters = document.getElementById("filters");

  if (!filters) return;

  const existingCategories = [
    ...new Set(
      allItems
        .map(item => item.category)
        .filter(Boolean)
    )
  ];

  const buttons = [
    `<button class="active" data-category="all">すべて</button>`,

    ...existingCategories.map(category => `
      <button data-category="${escapeHTML(category)}">
        ${escapeHTML(categoryNames[category] || category)}
      </button>
    `)
  ];

  filters.innerHTML = buttons.join("");

  filters.querySelectorAll("button").forEach(button => {

    button.addEventListener("click", () => {

      filters.querySelectorAll("button").forEach(btn => {
        btn.classList.remove("active");
      });

      button.classList.add("active");

      const category = button.dataset.category;

      if (category === "all") {
        renderNews(allItems);
      } else {
        renderNews(
          allItems.filter(item => item.category === category)
        );
      }
    });
  });
}


function renderNews(items) {

  const newsList = document.getElementById("newsList");

  if (!newsList) return;

  if (!Array.isArray(items) || items.length === 0) {

    newsList.innerHTML = `
      <p class="empty">
        現在、表示できる重要ニュースはありません。
      </p>
    `;

    return;
  }

  newsList.innerHTML = items.map((item, index) => {

    const category =
      categoryNames[item.category] ||
      item.category ||
      "最新情報";

    const date = formatDate(item.published_at);

    const title =
      item.title_ja ||
      item.title ||
      "タイトルなし";

    const summary =
      item.summary_ja ||
      item.summary ||
      "";

    const impact =
      item.impact_ja ||
      item.impact ||
      "ドバイへの直接的な影響は現在確認中です。";

    return `
      <article class="card ${index === 0 ? "top-story" : ""}">

        <div class="meta">
          ${escapeHTML(category)}
          ${date ? `・${escapeHTML(date)}` : ""}
        </div>

        <h3>
          ${escapeHTML(title)}
        </h3>

        ${
          summary
            ? `<p>${escapeHTML(summary)}</p>`
            : ""
        }

        <div>
          <span class="impact">
            ドバイへの影響：${escapeHTML(impact)}
          </span>
        </div>

        ${
          item.url
            ? `
              <a
                href="${escapeHTML(item.url)}"
                target="_blank"
                rel="noopener noreferrer"
              >
                情報源を開く →
              </a>
            `
            : ""
        }

      </article>
    `;
  }).join("");
}


function formatDate(dateString) {

  if (!dateString) return "";

  const date = new Date(dateString);

  if (Number.isNaN(date.getTime())) {
    return dateString;
  }

  return date.toLocaleString("ja-JP", {
    timeZone: "Asia/Dubai",
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}


function escapeHTML(value) {

  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}


loadNews();
