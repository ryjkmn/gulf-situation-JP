let allNews = [];
let map = null;


// ==========================================
// データ取得
// ==========================================

async function loadNews() {
  try {
    const response = await fetch(
      "news.json?t=" + Date.now()
    );

    if (!response.ok) {
      throw new Error("news.json の取得に失敗しました");
    }

    const data = await response.json();

    allNews = data.items || [];

    renderUpdatedAt(data.updated_at);
    renderRisk(data.risk);
    renderChanges(data.changes || []);
    renderMustRead(data.must_read || []);
    renderFlights(data.flight_impacts || []);
    renderAllNews(allNews);

    initFilters();
    initMap(allNews);

  } catch (error) {
    console.error(error);

    document.getElementById("newsList").innerHTML = `
      <div class="empty-message">
        最新ニュースを読み込めませんでした。
      </div>
    `;
  }
}


// ==========================================
// 更新時間
// ==========================================

function renderUpdatedAt(dateString) {
  const element = document.getElementById("updatedAt");

  if (!dateString) {
    element.textContent = "不明";
    return;
  }

  const date = new Date(dateString);

  element.textContent = date.toLocaleString(
    "ja-JP",
    {
      timeZone: "Asia/Dubai",
      year: "numeric",
      month: "numeric",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    }
  );
}


// ==========================================
// 今、ドバイは安全？
// ==========================================

function renderRisk(risk) {
  const label = document.getElementById("riskLabel");
  const summary = document.getElementById("riskSummary");
  const dot = document.getElementById("riskDot");

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
// 昨日から何が変わった？
// ==========================================

function renderChanges(items) {
  const container = document.getElementById("changesList");

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

  if (!items.length) {
    container.innerHTML = `
      <div class="empty-message">
        現時点で、UAE発着便に関する重要な影響は確認されていません。
      </div>
    `;
    return;
  }

  container.innerHTML = items
    .slice(0, 5)
    .map((item, index) =>
      createEditorialCard(item, index + 1, false)
    )
    .join("");
}


// ==========================================
// 編集デザインカード
// ==========================================

function createEditorialCard(item, number, highlight) {
  const title = escapeHtml(item.title || "タイトルなし");

  const category = getCategoryLabel(item.category);

  const date = formatDate(item.published_at);

  const highlightClass = highlight
    ? " highlight-card"
    : "";

  return `
    <article class="editorial-card${highlightClass}">

      <div class="card-top">

        <span class="card-number">
          ${String(number).padStart(2, "0")}
        </span>

        <span class="card-category">
          ${category}
        </span>

      </div>

      <h3>
        <span class="title-highlight">
          ${title}
        </span>
      </h3>

      <div class="card-meta">
        ${date}
      </div>

      <a
        href="${escapeAttribute(item.url || "#")}"
        target="_blank"
        rel="noopener noreferrer"
        class="read-link"
      >
        情報源を読む →
      </a>

    </article>
  `;
}


// ==========================================
// 最新ニュース一覧
// ==========================================

function renderAllNews(items) {
  const container = document.getElementById("newsList");

  if (!items.length) {
    container.innerHTML = `
      <div class="empty-message">
        現在、表示できるニュースはありません。
      </div>
    `;
    return;
  }

  container.innerHTML = items
    .map(item => {

      const title = escapeHtml(
        item.title || "タイトルなし"
      );

      const category = getCategoryLabel(
        item.category
      );

      const date = formatDate(
        item.published_at
      );

      return `
        <article class="news-card">

          <div class="news-meta">
            ${category} ・ ${date}
          </div>

          <h3>
            ${title}
          </h3>

          <a
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

  map = L.map("map").setView(
    [25.2048, 55.2708],
    5
  );

  L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
      attribution:
        '&copy; OpenStreetMap contributors'
    }
  ).addTo(map);

  // ドバイ
  L.marker([25.2048, 55.2708])
    .addTo(map)
    .bindPopup("Dubai");

  // 将来的にニュースデータに緯度・経度がある場合のみ表示
  items.forEach(item => {

    if (
      typeof item.lat === "number" &&
      typeof item.lng === "number"
    ) {
      L.marker([item.lat, item.lng])
        .addTo(map)
        .bindPopup(
          escapeHtml(item.title || "")
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
  if (!dateString) {
    return "";
  }

  const date = new Date(dateString);

  if (Number.isNaN(date.getTime())) {
    return dateString;
  }

  return date.toLocaleString(
    "ja-JP",
    {
      timeZone: "Asia/Dubai",
      month: "numeric",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    }
  );
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
