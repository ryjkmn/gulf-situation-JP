let allNews = [];
let map = null;


// ==========================================
// データ取得
// ==========================================

async function loadNews() {
  try {
    const response = await fetch("news.json?t=" + Date.now());

    if (!response.ok) {
      throw new Error("news.json の取得に失敗しました");
    }

    const data = await response.json();

    // その他の重要ニュースだけを保持
    allNews = data.other_news || [];

    renderUpdatedAt(data.updated_at);
    renderRisk(data.risk);
    renderCurrentSituation(data.current_situation_summary);
    renderChanges(data.changes || []);
    renderMustRead(data.must_read || []);
    renderFlights(data.flight_impacts || []);
    renderAllNews(allNews);

    initFilters();

    // 地図には全ニュースを渡す
    initMap(data.items || []);

  } catch (error) {
    console.error(error);

    const newsList = document.getElementById("newsList");

    if (newsList) {
      newsList.innerHTML = `
        <div class="empty-message">
          最新ニュースを読み込めませんでした。
        </div>
      `;
    }
  }
}


// ==========================================
// 更新時間
// ==========================================

function renderUpdatedAt(dateString) {
  const element = document.getElementById("updatedAt");

  if (!element) return;

  if (!dateString) {
    element.textContent = "不明";
    return;
  }

  const date = new Date(dateString);

  element.textContent = date.toLocaleString("ja-JP", {
    timeZone: "Asia/Dubai",
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}


// ==========================================
// 今、ドバイは安全？
// ==========================================

function renderRisk(risk) {
  const label = document.getElementById("riskLabel");
  const summary = document.getElementById("riskSummary");
  const dot = document.getElementById("riskDot");

  if (!label || !summary || !dot) return;

  if (!risk) {
    label.textContent = "確認中";
    summary.textContent = "最新情報を確認しています。";
    return;
  }

  label.textContent = risk.label || "確認中";
  summary.textContent = risk.summary || "";

  dot.className = "risk-dot";

  if (risk.level) {
    dot.classList.add("risk-" + risk.level);
  }
}


// ==========================================
// 現在の状況 3行まとめ
// ==========================================

function renderCurrentSituation(summary) {
  const element = document.getElementById(
    "currentSituationSummary"
  );

  if (!element) return;

  if (!summary) {
    element.textContent =
      "現在の情勢を分析しています。";
    return;
  }

  element.textContent = summary;
}


// ==========================================
// 昨日から何が変わった？
// ==========================================

function renderChanges(items) {
  const container = document.getElementById("changesList");

  if (!container) return;

  if (!items.length) {
    container.innerHTML = `
      <div class="empty-message">
        前回の更新以降、重要な変化は確認されていません。
      </div>
    `;
    return;
  }

  container.innerHTML = items
    .slice(0, 3)
    .map((item, index) =>
      createEditorialCard(item, index + 1, true)
    )
    .join("");
}


// ==========================================
// 今日読むべきニュース
// ==========================================

function renderMustRead(items) {
  const container = document.getElementById("mustReadList");

  if (!container) return;

  if (!items.length) {
    container.innerHTML = `
      <div class="empty-message">
        現在、重要ニュースを選定中です。
      </div>
    `;
    return;
  }

  container.innerHTML = items
    .slice(0, 3)
    .map((item, index) =>
      createEditorialCard(item, index + 1, true)
    )
    .join("");
}


// ==========================================
// フライトへの影響
// ==========================================

function renderFlights(items) {
  const container = document.getElementById("flightList");

  if (!container) return;

  if (!items.length) {
    container.innerHTML = `
      <div class="empty-message">
        現時点で、UAE発着便に関する重要な影響は確認されていません。
      </div>
    `;
    return;
  }

  container.innerHTML = items
    .slice(0, 3)
    .map((item, index) =>
      createEditorialCard(item, index + 1, false)
    )
    .join("");
}


// ==========================================
// ニュースカード
// ==========================================

function createEditorialCard(item, number, highlight) {

  const title = escapeHtml(
    item.title_ja ||
    item.title ||
    "タイトルなし"
  );

  const summary = escapeHtml(
    item.summary_ja || ""
  );

  const keyPoint = escapeHtml(
    item.key_point_ja || ""
  );

  const category = getCategoryLabel(item.category);
  const date = formatDate(item.published_at);

  const highlightClass = highlight
    ? " highlight-card"
    : "";

  return `
    <article class="editorial-card${highlightClass}">

      <div class="card-meta">

        <span class="card-number">
          ${String(number).padStart(2, "0")}
        </span>

        <span class="card-category">
          ${escapeHtml(category)}
        </span>

      </div>

      <h3 class="card-title">
        <span class="title-highlight">
          ${title}
        </span>
      </h3>

      ${
        summary
          ? `
            <p class="card-summary">
              ${summary}
            </p>
          `
          : ""
      }

      ${
        keyPoint
          ? `
            <div class="key-point">
              <strong>読むべきポイント</strong>
              <p>${keyPoint}</p>
            </div>
          `
          : ""
      }

      <div class="card-bottom">

        <span class="card-date">
          ${date}
        </span>

        <a
          class="source-link"
          href="${escapeAttribute(item.url || "#")}"
          target="_blank"
          rel="noopener noreferrer"
        >
          情報源を読む →
        </a>

      </div>

    </article>
  `;
}


// ==========================================
// その他の重要ニュース
// ==========================================

function renderAllNews(items) {
  const container = document.getElementById("newsList");

  if (!container) return;

  if (!items.length) {
    container.innerHTML = `
      <div class="empty-message">
        現在、その他の重要ニュースはありません。
      </div>
    `;
    return;
  }

  container.innerHTML = items
    .slice(0, 6)
    .map(item => {

      const title = escapeHtml(
        item.title_ja ||
        item.title ||
        "タイトルなし"
      );

      const summary = escapeHtml(
        item.summary_ja || ""
      );

      const keyPoint = escapeHtml(
        item.key_point_ja || ""
      );

      const category = getCategoryLabel(item.category);
      const date = formatDate(item.published_at);

      return `
        <article class="news-item">

          <div class="news-meta">
            ${escapeHtml(category)} ・ ${date}
          </div>

          <h3 class="news-title">
            ${title}
          </h3>

          ${
            summary
              ? `
                <p class="news-summary">
                  ${summary}
                </p>
              `
              : ""
          }

          ${
            keyPoint
              ? `
                <div class="news-key-point">
                  <strong>重要ポイント：</strong>
                  ${keyPoint}
                </div>
              `
              : ""
          }

          <a
            class="source-link"
            href="${escapeAttribute(item.url || "#")}"
            target="_blank"
            rel="noopener noreferrer"
          >
            情報源を読む →
          </a>

        </article>
      `;
    })
    .join("");
}


// ==========================================
// フィルター
// ==========================================

function initFilters() {
  const buttons = document.querySelectorAll(".filter");

  buttons.forEach(button => {

    button.addEventListener("click", () => {

      buttons.forEach(btn =>
        btn.classList.remove("active")
      );

      button.classList.add("active");

      const category = button.dataset.category;

      if (category === "all") {
        renderAllNews(allNews);
        return;
      }

      const filtered = allNews.filter(
        item => item.category === category
      );

      renderAllNews(filtered);
    });
  });
}


// ==========================================
// 地図
// ==========================================

function initMap(items) {
  const mapElement = document.getElementById("map");

  if (!mapElement || typeof L === "undefined") {
    return;
  }

  if (map) {
    map.remove();
    map = null;
  }

  map = L.map("map").setView(
    [25.2048, 55.2708],
    5
  );

  L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
      attribution: "© OpenStreetMap contributors"
    }
  ).addTo(map);

  L.marker([25.2048, 55.2708])
    .addTo(map)
    .bindPopup("Dubai");

  items.forEach(item => {

    if (
      typeof item.lat === "number" &&
      typeof item.lng === "number"
    ) {

      const popupTitle =
        item.title_ja ||
        item.title ||
        "";

      L.marker([item.lat, item.lng])
        .addTo(map)
        .bindPopup(
          escapeHtml(popupTitle)
        );
    }
  });
}


// ==========================================
// カテゴリー日本語化
// ==========================================

function getCategoryLabel(category) {
  const labels = {
    US: "米国・トランプ",
    Iran: "イラン",
    Gulf: "湾岸諸国",
    Flight: "空域・フライト",
    Hormuz: "ホルムズ海峡"
  };

  return labels[category] || category || "ニュース";
}


// ==========================================
// 日付
// ==========================================

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


// ==========================================
// セキュリティ
// ==========================================

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}


function escapeAttribute(value) {
  return escapeHtml(value);
}


// ==========================================
// START
// ==========================================

loadNews();
