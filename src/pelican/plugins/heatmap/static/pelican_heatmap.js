(async function () {
  // ── i18n ──────────────────────────────────────────────────
  // Option 1 – pick a built-in locale:
  //   <script>window.HM_LANG = "zh-TW";</script>
  // Option 2 – full custom override (merges on top of the chosen locale):
  //   <script>window.HM_LOCALE = { months: [...], days: [...], ... }</script>
  const LOCALES = {
    en: {
      months: [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
      ],
      days: ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"],
      less: "Less",
      more: "More",
      no_posts: "No posts",
      posts: "posts",
      alltime: "all\u2011time\nposts", // \u2011 = non-breaking hyphen
      streak: "day\nstreak",
      prev_year: "Previous year",
      next_year: "Next year",
    },
    "zh-TW": {
      months: [
        "1月",
        "2月",
        "3月",
        "4月",
        "5月",
        "6月",
        "7月",
        "8月",
        "9月",
        "10月",
        "11月",
        "12月",
      ],
      days: ["日", "一", "二", "三", "四", "五", "六"],
      less: "少",
      more: "多",
      no_posts: "沒有文章",
      posts: "篇文章",
      alltime: "所有\n文章",
      streak: "天\n連續發文",
      prev_year: "前一年",
      next_year: "後一年",
    },
  };
  const lang = window.HM_LANG || document.documentElement.lang || "en";
  const base = LOCALES[lang] || LOCALES[lang.split("-")[0]] || LOCALES.en;
  const L = Object.assign({}, base, window.HM_LOCALE || {});

  // ── Mount point ───────────────────────────────────────────
  const root = document.getElementById("writing-heatmap");
  if (!root) return;

  const dataUrl =
    root.getAttribute("data-src") || window.HM_DATA_URL || "/writing-heatmap.json";

  // ── Inject HTML ───────────────────────────────────────────
  root.setAttribute("aria-busy", "true");
  root.innerHTML = `
    <div class="hm-stats">
      <div class="hm-stat-card">
        <span class="hm-stat-num" id="hm-stat-window">—</span>
        <span class="hm-stat-label" id="hm-stat-window-label">${L.posts}</span>
      </div>
      <div class="hm-stat-card">
        <span class="hm-stat-num" id="hm-stat-alltime">—</span>
        <span class="hm-stat-label">${L.alltime.replace("\n", "<br>")}</span>
      </div>
      <div class="hm-stat-card">
        <span class="hm-stat-num" id="hm-stat-streak">—</span>
        <span class="hm-stat-label">${L.streak.replace("\n", "<br>")}</span>
      </div>
    </div>

    <div class="hm-nav">
      <div class="hm-nav-btn" id="hm-btn-prev" role="button" tabindex="0" title="${L.prev_year}" aria-label="${L.prev_year}">&#8249;</div>
      <div class="hm-nav-btn" id="hm-btn-next" role="button" tabindex="0" title="${L.next_year}" aria-label="${L.next_year}">&#8250;</div>
      <span class="hm-nav-range" id="hm-nav-range"></span>
    </div>

    <div class="hm-container" id="hm-container">
      <div class="hm-inner">
        <div class="hm-month-labels" id="hm-month-labels"></div>
        <div class="hm-grid-wrap">
          <div class="hm-day-labels">
            ${L.days.map((d) => `<span>${d}</span>`).join("")}
          </div>
          <div class="hm-grid" id="hm-grid"></div>
        </div>
      </div>
    </div>

    <div class="hm-legend">
      <span>${L.less}</span>
      ${[0, 1, 2, 3, 4].map((l) => `<span class="hm-legend-cell" data-level="${l}"></span>`).join("")}
      <span>${L.more}</span>
    </div>

    <div class="hm-tooltip" id="hm-tooltip"></div>
  `;

  // ── Load JSON ─────────────────────────────────────────────
  let heatmapData = {},
    allTotal = 0,
    streak = 0;
  try {
    const json = await fetch(dataUrl).then((r) => r.json());
    heatmapData = json.data ?? {};
    allTotal = json.total ?? 0;
    streak = json.streak ?? 0;
  } catch (e) {
    console.warn("[writing_heatmap] failed to load " + dataUrl, e);
  }

  // ── Static stats ──────────────────────────────────────────
  document.getElementById("hm-stat-alltime").textContent = allTotal;
  document.getElementById("hm-stat-streak").textContent = streak;

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const allKeys = Object.keys(heatmapData).sort();
  const earliestDate = allKeys.length
    ? new Date(allKeys[0] + "T00:00:00")
    : new Date(today);
  const globalMax = Math.max(
    ...Object.values(heatmapData).map((v) => v.count),
    1,
  );

  function getLevel(c) {
    if (!c) return 0;
    const r = c / globalMax;
    if (r < 0.25) return 1;
    if (r < 0.5) return 2;
    if (r < 0.75) return 3;
    return 4;
  }
  function maxOffset() {
    return Math.ceil((today - earliestDate) / (365 * 86400000));
  }
  function windowDates(offset) {
    const base = new Date(today);
    base.setDate(base.getDate() + (6 - today.getDay())); // 本週六
    const end = new Date(base);
    end.setFullYear(end.getFullYear() - offset);
    const start = new Date(end);
    start.setDate(start.getDate() - 364);
    const sd = start.getDay();
    if (sd !== 0) start.setDate(start.getDate() - sd);
    return { start, end };
  }
  function countInRange(start, end) {
    let n = 0;
    for (const [k, v] of Object.entries(heatmapData)) {
      const d = new Date(k + "T00:00:00");
      if (d >= start && d <= end) n += v.count;
    }
    return n;
  }

  // ── DOM refs ──────────────────────────────────────────────
  const container = document.getElementById("hm-container");
  const grid = document.getElementById("hm-grid");
  const mlabels = document.getElementById("hm-month-labels");
  const tooltip = document.getElementById("hm-tooltip");
  const btnPrev = document.getElementById("hm-btn-prev");
  const btnNext = document.getElementById("hm-btn-next");
  const navRange = document.getElementById("hm-nav-range");
  const statWin = document.getElementById("hm-stat-window");
  const statWinLabel = document.getElementById("hm-stat-window-label");

  let windowOffset = 0;

  // ── Render ────────────────────────────────────────────────
  function render() {
    grid.innerHTML = "";
    mlabels.innerHTML = "";
    tooltip.classList.remove("hm-visible", "hm-pinned");
    tooltip.dataset.pinnedKey = "";

    const { start, end } = windowDates(windowOffset);
    const fmt = (d) =>
      `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, "0")}/${String(d.getDate()).padStart(2, "0")}`;
    navRange.textContent = `${fmt(start)} – ${fmt(end)}`;

    const winCount = countInRange(start, end);
    statWin.classList.add("hm-updating");
    requestAnimationFrame(() => {
      statWin.textContent = winCount;
      const y1 = start.getFullYear(),
        y2 = end.getFullYear();
      statWinLabel.innerHTML =
        y1 === y2 ? `${y1}<br>${L.posts}` : `${y1}–${y2}<br>${L.posts}`;
      statWin.classList.remove("hm-updating");
    });

    btnNext.dataset.disabled = windowOffset === 0 ? "true" : "";
    btnPrev.dataset.disabled = windowOffset >= maxOffset() ? "true" : "";

    const cur = new Date(start);
    const colInfo = [];
    let colIndex = 0;

    while (cur <= end) {
      if (cur.getDay() === 0) {
        colInfo.push(cur.getMonth());
        colIndex++;
      }

      // Use local date to avoid UTC offset shifting the day
      const key = `${cur.getFullYear()}-${String(cur.getMonth() + 1).padStart(2, "0")}-${String(cur.getDate()).padStart(2, "0")}`;
      const entry = heatmapData[key];
      const count = entry ? entry.count : 0;
      const isFuture = cur > today;
      const isPast = cur < earliestDate;

      const cell = document.createElement("div");
      cell.className = "hm-cell";
      cell.dataset.level = isFuture || isPast ? "0" : getLevel(count);
      if (isFuture) cell.classList.add("hm-cell--future");
      if (isPast) cell.classList.add("hm-cell--past");

      const _key = key,
        _entry = entry,
        _count = count;

      function buildHTML() {
        const d = new Date(_key + "T00:00:00");
        const ds = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")} (${_count})`;
        let h = `<div class="hm-tt-date">${ds}</div>`;
        if (!_entry || _count === 0) {
          h += `<div class="hm-tt-empty">${L.no_posts}</div>`;
        } else {
          h += `<ol class="hm-tt-list">`;
          _entry.articles.forEach((a) => {
            h += `<li><a href="${a.url}">${a.title}</a></li>`;
          });
          h += `</ol>`;
        }
        return h;
      }

      function posTooltip(cx, cy) {
        const tw = tooltip.offsetWidth,
          th = tooltip.offsetHeight;
        let x = cx + 14,
          y = cy - th - 8;
        if (x + tw > window.innerWidth - 8) x = cx - tw - 14;
        if (y < 8) y = cy + 20;
        if (y + th > window.innerHeight - 8) y = cy - th - 8;
        tooltip.style.left = x + "px";
        tooltip.style.top = y + "px";
      }

      cell.addEventListener("mouseenter", (e) => {
        if (tooltip.classList.contains("hm-pinned")) return;
        tooltip.innerHTML = buildHTML();
        tooltip.classList.add("hm-visible");
        posTooltip(e.clientX, e.clientY);
      });
      cell.addEventListener("mousemove", (e) => {
        if (tooltip.classList.contains("hm-pinned")) return;
        posTooltip(e.clientX, e.clientY);
      });
      cell.addEventListener("mouseleave", () => {
        if (tooltip.classList.contains("hm-pinned")) return;
        tooltip.classList.remove("hm-visible");
      });
      cell.addEventListener("click", (e) => {
        if (isFuture || isPast) return;
        const same =
          tooltip.classList.contains("hm-pinned") &&
          tooltip.dataset.pinnedKey === _key;
        tooltip.classList.remove("hm-pinned", "hm-visible");
        tooltip.dataset.pinnedKey = "";
        if (same) return;
        tooltip.innerHTML = buildHTML();
        posTooltip(e.clientX, e.clientY);
        tooltip.classList.add("hm-visible", "hm-pinned");
        tooltip.dataset.pinnedKey = _key;
        e.stopPropagation();
      });
      cell.addEventListener("touchstart", (e) => {
        if (isFuture || isPast) return;
        e.preventDefault();
        const touch = e.touches[0];
        const same =
          tooltip.classList.contains("hm-pinned") &&
          tooltip.dataset.pinnedKey === _key;
        tooltip.classList.remove("hm-pinned", "hm-visible");
        tooltip.dataset.pinnedKey = "";
        if (same) return;
        tooltip.innerHTML = buildHTML();
        posTooltip(touch.clientX, touch.clientY);
        tooltip.classList.add("hm-visible", "hm-pinned");
        tooltip.dataset.pinnedKey = _key;
        e.stopPropagation();
      }, { passive: false });

      grid.appendChild(cell);
      cur.setDate(cur.getDate() + 1);
    }

    // Month labels — one span per column
    let prevMonth = -1;
    for (let c = 0; c < colIndex; c++) {
      const span = document.createElement("span");
      span.className = "hm-month-label-cell";
      if (colInfo[c] !== prevMonth) {
        span.textContent = L.months[colInfo[c]];
        span.classList.add("hm-month-label-cell--visible");
        prevMonth = colInfo[c];
      }
      mlabels.appendChild(span);
    }

    // Scroll to the right (most recent) after render
    requestAnimationFrame(() => {
      container.scrollLeft = container.scrollWidth;
    });
  }

  btnPrev.addEventListener("click", () => {
    if (btnPrev.dataset.disabled) return;
    windowOffset++;
    render();
  });
  btnNext.addEventListener("click", () => {
    if (btnNext.dataset.disabled) return;
    windowOffset--;
    render();
  });
  btnPrev.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (btnPrev.dataset.disabled) return;
      windowOffset++;
      render();
    }
  });
  btnNext.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (btnNext.dataset.disabled) return;
      windowOffset--;
      render();
    }
  });
  document.addEventListener("click", () => {
    tooltip.classList.remove("hm-pinned", "hm-visible");
    tooltip.dataset.pinnedKey = "";
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      tooltip.classList.remove("hm-pinned", "hm-visible");
      tooltip.dataset.pinnedKey = "";
    }
  });

  render();
  root.removeAttribute("aria-busy");
})();
