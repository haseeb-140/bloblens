/* BlobLens UI — vanilla JS, no build step. */
(() => {
  "use strict";

  const els = {
    q: document.getElementById("q"),
    timing: document.getElementById("timing"),
    stats: document.getElementById("stats"),
    results: document.getElementById("results"),
    summary: document.getElementById("summary"),
    empty: document.getElementById("empty"),
    more: document.getElementById("more"),
    sort: document.getElementById("sort"),
    clear: document.getElementById("clear"),
    facetContainer: document.getElementById("facet-container"),
    facetExtension: document.getElementById("facet-extension"),
  };

  const state = {
    q: "",
    container: null,
    ext: null,
    sort: "",
    offset: 0,
    limit: 20,
    total: 0,
    seq: 0, // guards against out-of-order responses
  };

  // ------------------------------------------------------------- utils

  const esc = (s) =>
    String(s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));

  // Server highlights with <mark>; escape everything else.
  const safeHighlight = (s) =>
    esc(s).replace(/&lt;mark&gt;/g, "<mark>").replace(/&lt;\/mark&gt;/g, "</mark>");

  const fmtSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    const units = ["KB", "MB", "GB", "TB"];
    let value = bytes;
    let unit = -1;
    do { value /= 1024; unit += 1; } while (value >= 1024 && unit < units.length - 1);
    return `${value.toFixed(value < 10 ? 1 : 0)} ${units[unit]}`;
  };

  const fmtDate = (epoch) =>
    new Date(epoch * 1000).toISOString().slice(0, 16).replace("T", " ");

  const debounce = (fn, ms) => {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), ms);
    };
  };

  // ------------------------------------------------------------- search

  async function runSearch({ append = false } = {}) {
    if (!append) state.offset = 0;
    const seq = ++state.seq;

    const params = new URLSearchParams({
      q: state.q,
      limit: state.limit,
      offset: state.offset,
    });
    if (state.container) params.set("container", state.container);
    if (state.ext) params.set("ext", state.ext);
    if (state.sort) params.set("sort", state.sort);

    let data;
    try {
      const res = await fetch(`/api/search?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      data = await res.json();
    } catch (err) {
      if (seq !== state.seq) return;
      els.summary.textContent = `Search failed: ${err.message}`;
      return;
    }
    if (seq !== state.seq) return; // a newer query already landed

    state.total = data.total;
    els.timing.textContent = `${data.processing_ms} ms`;
    els.summary.textContent = state.q || state.container || state.ext
      ? `${data.total.toLocaleString()} result${data.total === 1 ? "" : "s"}`
      : `${data.total.toLocaleString()} blobs indexed`;

    if (!append) els.results.replaceChildren();
    for (const hit of data.hits) els.results.append(renderHit(hit));

    const shown = els.results.children.length;
    els.empty.hidden = shown > 0;
    els.more.hidden = shown >= data.total;
    renderFacets(data.facets || {});
    els.clear.hidden = !(state.container || state.ext);
  }

  function renderHit(hit) {
    const li = document.createElement("li");
    li.className = "result";
    li.innerHTML = `
      <div class="result-head">
        <span class="result-name">${safeHighlight(hit.name_html)}</span>
        <span class="chip">${esc(hit.container)}</span>
        ${hit.extension ? `<span class="chip ext">.${esc(hit.extension)}</span>` : ""}
      </div>
      <div class="result-path">${safeHighlight(hit.path_html)}</div>
      ${hit.excerpt_html && hit.excerpt_html.includes("<mark>")
        ? `<div class="result-excerpt">${safeHighlight(hit.excerpt_html)}</div>` : ""}
      <div class="result-meta">
        <span>${fmtSize(hit.size)}</span>
        <span>${fmtDate(hit.last_modified)} UTC</span>
        <button class="download" type="button">Download</button>
      </div>`;
    li.querySelector(".download").addEventListener("click", (ev) =>
      download(ev.currentTarget, hit.container, hit.path));
    return li;
  }

  async function download(btn, container, path) {
    btn.disabled = true;
    btn.textContent = "Creating link…";
    try {
      const params = new URLSearchParams({ container, path });
      const res = await fetch(`/api/download?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const { url } = await res.json();
      window.open(url, "_blank", "noopener");
      btn.textContent = "Download";
    } catch {
      btn.textContent = "Link failed — retry";
    } finally {
      btn.disabled = false;
    }
  }

  // ------------------------------------------------------------- facets

  function renderFacets(facets) {
    renderFacetList(els.facetContainer, facets.container || {}, "container");
    renderFacetList(els.facetExtension, facets.extension || {}, "ext");
  }

  function renderFacetList(root, values, key) {
    root.replaceChildren();
    const entries = Object.entries(values).sort((a, b) => b[1] - a[1]).slice(0, 12);
    if (!entries.length && state[key]) entries.push([state[key], 0]);
    for (const [value, count] of entries) {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = state[key] === value ? "active" : "";
      btn.innerHTML =
        `<span>${key === "ext" ? "." : ""}${esc(value)}</span>` +
        `<span class="count">${count.toLocaleString()}</span>`;
      btn.addEventListener("click", () => {
        state[key] = state[key] === value ? null : value;
        runSearch();
      });
      li.append(btn);
      root.append(li);
    }
  }

  // -------------------------------------------------------------- stats

  async function loadStats() {
    try {
      const res = await fetch("/api/stats");
      const data = await res.json();
      const when = data.last_sync
        ? new Date(data.last_sync).toISOString().slice(11, 16) + " UTC"
        : "pending";
      els.stats.textContent =
        `${data.documents.toLocaleString()} docs · sync ${when}`;
    } catch {
      els.stats.textContent = "stats unavailable";
    }
  }

  // -------------------------------------------------------------- wire up

  els.q.addEventListener("input", debounce(() => {
    state.q = els.q.value.trim();
    runSearch();
  }, 180));

  els.sort.addEventListener("change", () => {
    state.sort = els.sort.value;
    runSearch();
  });

  els.clear.addEventListener("click", () => {
    state.container = null;
    state.ext = null;
    runSearch();
  });

  els.more.addEventListener("click", () => {
    state.offset += state.limit;
    runSearch({ append: true });
  });

  runSearch();
  loadStats();
  setInterval(loadStats, 60_000);
})();
