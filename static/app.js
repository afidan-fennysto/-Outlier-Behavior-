/* De-Influence AI — client router + page renderers.
 * A tiny hash-based router keeps each section on its own page (no framework, offline-safe).
 */
const $ = (s, root = document) => root.querySelector(s);
const HISTORY_KEY = "deinfluence.history.v2";
const COMPARE = new Map();
let LAST_SCAN = null;
let DEBUG_ENABLED = false;

/* ---------------- shared helpers ---------------- */
function toast(msg) { const t = $("#toast"); t.textContent = msg; t.classList.add("show"); setTimeout(() => t.classList.remove("show"), 2200); }
function esc(s) { return String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }
function color(v, inv = false) { const s = inv ? 100 - v : v; return s >= 66 ? "var(--good)" : s >= 40 ? "var(--warn)" : "var(--bad)"; }
function ring(v, label, inv = false) {
  const r = 62, c = 2 * Math.PI * r, off = c * (1 - v / 100), col = color(v, inv);
  return `<div class="ring"><svg width="150" height="150">
    <circle cx="75" cy="75" r="${r}" stroke="rgba(255,255,255,.08)" stroke-width="12" fill="none"/>
    <circle cx="75" cy="75" r="${r}" stroke="${col}" stroke-width="12" fill="none" stroke-linecap="round"
      stroke-dasharray="${c}" stroke-dashoffset="${off}"/></svg>
    <div class="mid"><div class="n" style="color:${col}">${v.toFixed(0)}</div><div class="k">${label}</div></div></div>`;
}
async function getJSON(url) { const r = await fetch(url); if (!r.ok) throw new Error("Request failed"); return r.json(); }
async function postJSON(url, body) {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || "Request failed");
  return r.json();
}

/* ---------------- private local scan history ---------------- */
function loadHistory() { try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]"); } catch { return []; } }
function saveScan(d) {
  const h = loadHistory();
  h.unshift({ t: Date.now(), id: d.product_id, name: d.product_name, category: d.category,
    longevity: d.longevity_score, regret: d.regret_probability, recommendation: d.recommendation,
    phase: d.hype.phase, cpw: d.truecost.cost_per_wear, verdict: d.truecost.verdict,
    defects: (d.defects.top_defects || []).map(x => x.category) });
  localStorage.setItem(HISTORY_KEY, JSON.stringify(h.slice(0, 100)));
}
function clearHistory() { localStorage.removeItem(HISTORY_KEY); }

/* ================= PAGES ================= */
const PAGES = {
  analyse:   { label: "Analyse",    render: pageAnalyse },
  dashboard: { label: "Dashboard",  render: pageDashboard },
  personalize:{ label: "Personalize", render: pagePersonalize },
  compare:   { label: "Compare",    render: pageCompare },
  wishlist:  { label: "Wishlist",   render: pageWishlist },
  why:       { label: "Why us",     render: pageWhy },
  validation:{ label: "Validation", render: pageValidation },
};

function head(eyebrow, title, sub) {
  return `<div class="page-head"><div class="eyebrow">${eyebrow}</div>
    <h1>${title}</h1><p>${sub}</p></div>`;
}
function footer() {
  return `<footer>Dual-signal engine · localized Malaysian defect NLP × Gompertz trend-decay × Cost-Per-Wear.
    Catalogue &amp; preferences in a local SQLite database · scan history private to your device ·
    OWASP-aligned security. Scores are decision-support, not financial advice.</footer>`;
}

/* ---- Analyse (home) ---- */
function pageAnalyse(view) {
  view.innerHTML = head("Anti-impulse intelligence",
    'Know before you buy. <span class="grad-text">Spend on pieces that last.</span>',
    "Paste a Shopee, TikTok Shop or Shein product link for an instant Longevity Score, Regret Probability and Cost-Per-Wear.") +
    `<div class="card glass">
      <div class="row">
        <div style="flex:3"><label>Product link</label>
          <input type="text" id="linkInput" placeholder="https://shopee.com.my/... or https://www.tiktok.com/shop/..." /></div>
        <button id="linkBtn">Analyse link</button>
      </div>
      <p class="hint" style="margin-top:10px">We don't fetch live store pages (platform restrictions +
        security). Links resolve against our own product database — an exact match when we know the item,
        otherwise a clearly-labelled emulated demo result.</p>
      <div style="margin-top:14px"><label>Or try a known demo item</label>
        <div class="tags" id="demos" style="margin-top:6px"><span class="loading">Loading…</span></div></div>
    </div>
    <div id="result"></div>` + footer();

  $("#linkBtn").addEventListener("click", scanLink);
  $("#linkInput").addEventListener("keydown", e => { if (e.key === "Enter") scanLink(); });
  loadDemos();
  if (LAST_SCAN) show(LAST_SCAN);   // keep last verdict when navigating back
}

async function loadDemos() {
  try {
    const items = await getJSON("/api/products");
    $("#demos").innerHTML = items.map(p => `<button class="chip-btn" data-id="${p.id}">${esc(p.name)}</button>`).join("");
    document.querySelectorAll("#demos .chip-btn").forEach(b => b.addEventListener("click", () => scanById(b.dataset.id)));
  } catch { $("#demos").innerHTML = '<span class="hint">Demo list unavailable offline.</span>'; }
}
async function scanById(id) { busy(); try { show(await postJSON("/api/scan", { product_id: id })); } catch (e) { fail(e); } }
async function scanLink() {
  const url = $("#linkInput").value.trim();
  if (!url) { toast("Paste a product link"); return; }
  busy();
  try { const d = await postJSON("/api/check-link", { url });
    if (!d.matched) toast("Emulated demo result"); show(d.scan, d);
  } catch (e) { fail(e); }
}
function busy() { const r = $("#result"); if (r) r.innerHTML = '<div class="glass loading">Analysing durability, trend decay and cost-per-wear…</div>'; }
function fail(e) {
  const off = !navigator.onLine, r = $("#result"); if (!r) return;
  r.innerHTML = `<div class="glass note" style="border-left-color:var(--bad)"><b>${off ? "You are offline" : "Something went wrong"}</b>
    <p style="margin:8px 0 0">${off ? "Live analysis needs the server. Your saved dashboard still works offline." : esc(e.message)}</p></div>`;
}

function show(d, link) {
  LAST_SCAN = d; saveScan(d);
  const h = d.hype, df = d.defects, tc = d.truecost;
  const tags = (df.top_defects || []).slice(0, 5).map(x => `<span class="tag">${esc(x.phrase)}</span>`).join("") || '<span class="kv">No defect phrases detected</span>';
  const persona = d.personalized_note ? `<div class="persona">${esc(d.personalized_note)}</div>` : "";
  const canWish = !!d.product_id;
  const alt = d.alternative ? `
    <div class="card glass" style="margin-top:14px;border:1px solid rgba(45,212,191,.35)">
      <div class="cap" style="color:var(--brand1);font-size:11px;letter-spacing:1px;text-transform:uppercase">Better alternative</div>
      <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-top:6px">
        <div><div style="font-weight:650;font-size:15px">${esc(d.alternative.name)}</div>
          <div class="hint" style="margin:4px 0 0">${esc(d.alternative.reason)}</div></div>
        <div style="text-align:right"><span class="pill ${d.alternative.recommendation}">${d.alternative.recommendation}</span>
          <div class="hint" style="margin-top:6px">${d.alternative.currency}${d.alternative.price.toFixed(2)} · longevity ${d.alternative.longevity_score.toFixed(0)}</div></div>
        <button class="soft mini" id="altScan" data-id="${d.alternative.product_id}">Analyse it</button>
      </div></div>` : "";
  const banner = (link && !link.matched)
    ? `<div class="glass note" style="border-left-color:var(--warn);margin:0 0 14px"><b>Emulated demo result</b><p style="margin:6px 0 0">${esc(link.note)}</p></div>` : "";
  $("#result").innerHTML = `${banner}
    <div class="verdict glass">${ring(d.longevity_score, "Longevity")}
      <div>
        <div class="tagline"><span class="pill ${d.recommendation}">${d.recommendation}</span>
          <span class="tag-s">${d.confidence} confidence</span>
          <span class="tag-s">Regret ${d.regret_probability.toFixed(0)}%</span></div>
        <p class="headline">${esc(d.headline)}</p>
        <ul class="reasons">${d.reasons.map(r => `<li>${esc(r)}</li>`).join("")}</ul>${persona}
        <div class="verdict-actions">
          <button class="soft mini" id="addCompare">Add to compare</button>
          <button class="soft mini" id="addWish" ${canWish ? "" : 'disabled title="Demo items only"'}>♥ Wishlist</button>
        </div>
      </div>
    </div>
    <div class="grid3" style="margin-top:14px">
      <div class="card glass metric"><div class="cap">Hype-cycle decay</div>
        <div class="big" style="color:${color(h.hype_health)};text-transform:capitalize">${h.phase}</div>
        <div class="track"><i style="width:${h.hype_health}%;background:${color(h.hype_health)}"></i></div>
        <div class="kv"><span>Hype health</span><b>${h.hype_health}/100</b></div>
        <div class="kv"><span>Relevance left</span><b>~${h.remaining_life_days.toFixed(0)} days</b></div>
        <div class="kv"><span>Decay velocity</span><b>${(h.decay_velocity * 100).toFixed(0)}%/2wk</b></div></div>
      <div class="card glass metric"><div class="cap">Defect NLP · ${df.reviews_analyzed} reviews</div>
        <div class="big" style="color:${color(df.quality_health)}">${df.quality_health}</div>
        <div class="track"><i style="width:${df.quality_health}%;background:${color(df.quality_health)}"></i></div>
        <div class="kv"><span>Defect rate</span><b>${(df.defect_rate * 100).toFixed(0)}%</b></div>
        <div class="kv"><span>Rating integrity</span><b>${df.rating_gap > 0.1 ? "inflated" : "ok"}</b></div>
        <div class="tags">${tags}</div></div>
      <div class="card glass metric"><div class="cap">TrueCost · per wear</div>
        <div class="big" style="color:${(tc.verdict === "excellent" || tc.verdict === "fair") ? "var(--good)" : "var(--bad)"}">${tc.currency}${tc.cost_per_wear.toFixed(2)}</div>
        <div class="kv"><span>Sticker price</span><b>${tc.currency}${tc.price.toFixed(2)}</b></div>
        <div class="kv"><span>Expected wears</span><b>${tc.expected_wears}</b></div>
        <div class="kv"><span>Benchmark</span><b>${tc.currency}${tc.benchmark_cpw.toFixed(2)}</b></div></div>
    </div>
    <div class="card glass" style="margin-top:14px"><h3>How the longevity score was composed</h3>
      <p class="hint" style="margin-top:6px">${esc(d.how_we_calculated)}</p>
      <table><tr><th>Signal</th><th>Health</th><th>Weight</th><th>Points</th></tr>
        ${d.score_breakdown.map(s => `<tr><td>${esc(s.signal)}</td><td>${s.health}/100</td><td>${(s.weight * 100).toFixed(0)}%</td><td><b>${s.points}</b></td></tr>`).join("")}
      </table></div>
    ${alt}
    <div class="glass note"><b>Responsible use</b><ul>${d.disclaimers.map(x => `<li>${esc(x)}</li>`).join("")}</ul></div>`;
  $("#addCompare").addEventListener("click", () => { addCompare(d); });
  if (canWish) $("#addWish").addEventListener("click", () => addWish(d.product_id));
  $("#altScan")?.addEventListener("click", (e) => scanById(e.target.dataset.id));
  $("#result").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

/* ---- Dashboard ---- */
function pageDashboard(view) {
  const h = loadHistory();
  let body;
  if (!h.length) {
    body = '<div class="glass empty">No items analysed yet. Analyse a link on the Analyse page and your patterns appear here — privately, on this device.</div>';
  } else {
    const n = h.length, avg = k => h.reduce((s, x) => s + x[k], 0) / n;
    const avgL = avg("longevity"), avgR = avg("regret"), avgC = avg("cpw");
    const avoided = h.filter(x => x.recommendation === "AVOID" || x.recommendation === "CAUTION").length;
    const recos = ["KEEP", "CONSIDER", "CAUTION", "AVOID"];
    const rc = Object.fromEntries(recos.map(r => [r, h.filter(x => x.recommendation === r).length]));
    const rcol = { KEEP: "var(--good)", CONSIDER: "var(--warn)", CAUTION: "#fb923c", AVOID: "var(--bad)" };
    const catCount = {}; h.forEach(x => (x.defects || []).forEach(c => catCount[c] = (catCount[c] || 0) + 1));
    const cats = Object.entries(catCount).sort((a, b) => b[1] - a[1]).slice(0, 5); const cmax = cats.length ? cats[0][1] : 1;
    const phases = ["rising", "cresting", "decaying", "stale"];
    const pc = Object.fromEntries(phases.map(p => [p, h.filter(x => x.phase === p).length])); const pmax = Math.max(1, ...Object.values(pc));
    body = `<div class="grid4">
      <div class="card glass stat"><div class="big">${n}</div><div class="cap">Items analysed</div></div>
      <div class="card glass stat"><div class="big" style="color:${color(avgL)}">${avgL.toFixed(0)}</div><div class="cap">Avg longevity</div></div>
      <div class="card glass stat"><div class="big" style="color:${color(avgR, true)}">${avgR.toFixed(0)}%</div><div class="cap">Avg regret risk</div></div>
      <div class="card glass stat"><div class="big">${avoided}</div><div class="cap">Flagged to avoid</div></div></div>
    <div class="grid2" style="margin-top:14px">
      <div class="card glass panel"><h3>Recommendation mix</h3>
        ${recos.map(r => `<div class="barline"><span class="lbl">${r}</span>
          <span class="meter"><i style="width:${(rc[r] / n * 100).toFixed(0)}%;background:${rcol[r]}"></i></span>
          <span class="val">${rc[r]}</span></div>`).join("")}</div>
      <div class="card glass panel"><h3>Where the problems are</h3>
        ${cats.length ? cats.map(([c, v]) => `<div class="barline"><span class="lbl">${esc(c)}</span>
          <span class="meter"><i style="width:${(v / cmax * 100).toFixed(0)}%"></i></span><span class="val">${v}</span></div>`).join("")
          : '<div class="kv">No defect categories recorded yet.</div>'}</div>
      <div class="card glass panel"><h3>Trend-phase flow</h3>
        <div class="flow">${phases.map(p => `<div class="col"><div class="stack" style="height:${(pc[p] / pmax * 100).toFixed(0)}%"></div>
          <div class="cl" style="text-transform:capitalize">${p}</div><div class="cl">${pc[p]}</div></div>`).join("")}</div></div>
      <div class="card glass panel"><h3>Average cost-per-wear</h3>
        <div class="big" style="font-size:34px;font-weight:800;margin:4px 0">RM${avgC.toFixed(2)}</div>
        <div class="kv"><span>Sustainable benchmark</span><b>RM0.80</b></div>
        <div class="kv"><span>Items beating benchmark</span><b>${h.filter(x => x.cpw <= 0.8).length} / ${n}</b></div>
        <div class="row" style="margin-top:12px"><button class="ghost mini" id="exportBtn">Export my data</button>
          <button class="ghost mini" id="clearBtn">Clear history</button></div></div>
    </div>`;
  }
  view.innerHTML = head("Private analytics", "Your insight dashboard",
    "A live view of what you've analysed. This history is stored only in your browser.") + body + footer();
  $("#clearBtn")?.addEventListener("click", () => { if (confirm("Clear your local scan history?")) { clearHistory(); route(); } });
  $("#exportBtn")?.addEventListener("click", () => {
    const b = new Blob([JSON.stringify(loadHistory(), null, 2)], { type: "application/json" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(b); a.download = "de-influence-history.json"; a.click(); URL.revokeObjectURL(a.href);
  });
}

/* ---- Personalize ---- */
async function pagePersonalize(view) {
  view.innerHTML = head("Make it yours", "Personalize your verdicts",
    "Save your taste and budget. We tailor each verdict to you — stored privately in the app's local database.") +
    `<div class="card glass"><div class="row">
      <div><label>Preferred style</label><input id="pStyle" placeholder="streetwear" /></div>
      <div><label>Favourite colour</label><input id="pColour" placeholder="black" /></div>
      <div><label>Monthly budget (RM)</label><input id="pBudget" type="number" min="0" step="10" placeholder="200" /></div>
      <button id="savePrefs">Save</button></div>
      <p class="hint" style="margin-top:12px">When a scanned item matches your style, colour or budget, the verdict shows a tailored "For you" note.</p>
    </div>` + footer();
  try { const p = await getJSON("/api/preferences");
    $("#pStyle").value = p.preferred_style || ""; $("#pColour").value = p.favourite_colour || "";
    if (p.monthly_budget) $("#pBudget").value = p.monthly_budget; } catch {}
  $("#savePrefs").addEventListener("click", async () => {
    try { await postJSON("/api/preferences", { preferred_style: $("#pStyle").value.trim(),
      favourite_colour: $("#pColour").value.trim(), monthly_budget: parseFloat($("#pBudget").value || "0") });
      toast("Preferences saved"); } catch (e) { toast(e.message); }
  });
}

/* ---- Compare ---- */
function addCompare(d) { COMPARE.set(d.product_id || d.product_name, d); toast("Added to compare"); }
function pageCompare(view) {
  let body;
  if (!COMPARE.size) {
    body = '<div class="glass empty">Analyse items on the Analyse page and tap "Add to compare" to line them up here.</div>';
  } else {
    const items = [...COMPARE.values()];
    const rows = [
      ["Recommendation", d => `<span class="pill ${d.recommendation}" style="font-size:11px">${d.recommendation}</span>`],
      ["Longevity", d => `<b style="color:${color(d.longevity_score)}">${d.longevity_score}</b>`],
      ["Regret %", d => `<b style="color:${color(d.regret_probability, true)}">${d.regret_probability}%</b>`],
      ["Trend phase", d => d.hype.phase],
      ["Quality health", d => d.defects.quality_health],
      ["Cost / wear", d => `${d.truecost.currency}${d.truecost.cost_per_wear.toFixed(2)}`],
      ["Expected wears", d => d.truecost.expected_wears],
      ["Confidence", d => d.confidence],
    ];
    body = `<div class="card glass scroll-x"><table class="cmp-table">
      <tr><th></th>${items.map(d => `<th class="me">${esc(d.product_name)}</th>`).join("")}</tr>
      ${rows.map(([lbl, fn]) => `<tr><td style="color:var(--muted)">${lbl}</td>${items.map(d => `<td>${fn(d)}</td>`).join("")}</tr>`).join("")}
    </table></div><div class="row" style="margin-top:12px"><button class="ghost mini" id="cmpClear">Clear comparison</button></div>`;
  }
  view.innerHTML = head("Side by side", "Compare items",
    "Line up two or more analysed items to see which is the smarter buy.") + body + footer();
  $("#cmpClear")?.addEventListener("click", () => { COMPARE.clear(); route(); });
}

/* ---- Wishlist ---- */
async function pageWishlist(view) {
  view.innerHTML = head("Saved for later", "Your wishlist",
    "Favourite demo items and track stock. Email restock alerts are planned for a future release.") +
    '<div id="wishlistView"><div class="loading">Loading…</div></div>' + footer();
  renderWishlist();
}
async function addWish(id) { try { await postJSON("/api/wishlist", { product_id: id, notify_on_restock: false }); toast("Added to wishlist"); } catch (e) { toast(e.message); } }
async function renderWishlist() {
  const el = $("#wishlistView"); if (!el) return;
  try {
    const items = await getJSON("/api/wishlist");
    if (!items.length) { el.innerHTML = '<div class="glass empty">No favourites yet. Analyse a demo item and tap ♥ Wishlist.</div>'; return; }
    el.innerHTML = items.map(w => `<div class="glass wl-item">
      <div class="meta"><div class="nm">${esc(w.product.name)}</div>
        <div class="sub">${w.product.currency}${w.product.price.toFixed(2)} · ${esc(w.product.category)}</div></div>
      <span class="stock ${w.in_stock ? "in" : "out"}">${w.in_stock ? "In stock" : "Out of stock"}</span>
      <span class="soon" title="Email restock alerts are planned">Email alerts — coming soon</span>
      <button class="ghost mini" data-id="${w.product.id}">Remove</button></div>`).join("");
    el.querySelectorAll("button[data-id]").forEach(b => b.addEventListener("click", async () => {
      await fetch("/api/wishlist/" + encodeURIComponent(b.dataset.id), { method: "DELETE" }); renderWishlist();
    }));
  } catch { el.innerHTML = '<div class="glass empty">Wishlist unavailable offline.</div>'; }
}

/* ---- Why us ---- */
async function pageWhy(view) {
  view.innerHTML = head("Market positioning", "Why De-Influence wins",
    "A category of one: no competitor fuses localized defect NLP, trend-decay forecasting and cost-per-wear into one pre-purchase regret score.") +
    '<div id="positioning"><div class="loading">Loading…</div></div>' + footer();
  try {
    const v = await getJSON("/api/positioning");
    const cols = v.columns, order = ["deinfluence", "price_trackers", "review_summarizers", "marketplace_native"];
    const mark = s => s === "yes" ? '<td class="c-yes">✓</td>' : s === "partial" ? '<td class="c-partial">~</td>' : '<td class="c-no">—</td>';
    $("#positioning").innerHTML = `
      <div class="grid3">${v.value_props.map(p => `<div class="glass vp"><h4>${esc(p.title)}</h4><p>${esc(p.detail)}</p></div>`).join("")}</div>
      <div class="card glass scroll-x" style="margin-top:14px"><h3>How we compare</h3>
        <table><tr><th>Capability</th>${order.map(k => `<th${k === "deinfluence" ? ' class="me" style="color:var(--brand1)"' : ""}>${esc(cols[k])}</th>`).join("")}</tr>
          ${v.comparison.map(r => `<tr><td style="color:var(--muted)">${esc(r.capability)}</td>${order.map(k => mark(r[k])).join("")}</tr>`).join("")}
        </table></div>`;
  } catch { $("#positioning").innerHTML = '<div class="glass empty">Positioning unavailable offline.</div>'; }
}

/* ---- Validation ---- */
async function pageValidation(view) {
  view.innerHTML = head("Proof, not promises", "Model validation",
    "Measured on the team's real 50-row Malaysian review benchmark. Download the exact dataset below for full transparency.") +
    '<div id="validation"><div class="loading">Loading metrics…</div></div>' + footer();
  try {
    const v = await getJSON("/api/evaluation");
    const dc = v.defect_classification, hf = v.hype_forecast, base = v.baseline_rule, types = v.per_defect_type || {};
    const rows = await getJSON("/api/evaluation/dataset");
    $("#validation").innerHTML = `
      <div class="grid2">
        <div class="card glass panel"><h3>Defect detector · ${esc(v.dataset_source || "benchmark")}</h3>
          <div class="big" style="font-size:30px;font-weight:800;color:var(--brand1)">F1 ${dc.f1_score.toFixed(2)}</div>
          <div class="kv"><span>Precision</span><b>${dc.precision.toFixed(2)}</b></div>
          <div class="kv"><span>Recall</span><b>${dc.recall.toFixed(2)}</b></div>
          <div class="kv"><span>Accuracy</span><b>${(dc.accuracy * 100).toFixed(0)}%</b></div>
          ${base ? `<div class="kv"><span>Dataset baseline F1</span><b>${base.f1_score.toFixed(2)}</b></div>` : ""}
          <p class="hint" style="margin-top:8px">${esc(dc.explanation)}</p></div>
        <div class="card glass panel"><h3>Recall by defect type</h3>
          ${Object.entries(types).map(([t, b]) => `<div class="barline"><span class="lbl">${esc(t)}</span>
            <span class="meter"><i style="width:${(b.recall * 100).toFixed(0)}%"></i></span><span class="val">${(b.recall * 100).toFixed(0)}%</span></div>`).join("") || '<div class="kv">No data.</div>'}
          <p class="hint" style="margin-top:8px">Hype forecast MAE: <b>${hf.mae.toFixed(1)} days</b></p></div>
      </div>
      <div class="card glass" style="margin-top:14px">
        <div class="row" style="justify-content:space-between;align-items:center">
          <h3 style="margin:0">Validation dataset (${rows.length} labeled rows)</h3>
          <a href="/api/evaluation/dataset/download"><button class="mini">Download .xlsx</button></a>
        </div>
        <p class="hint" style="margin-top:8px">The exact data the model is scored on — download it or review every row below.</p>
        <div class="scroll-x" style="max-height:340px;overflow-y:auto;margin-top:8px"><table>
          <tr><th>#</th><th>Review</th><th>Human label</th><th>Defect type</th><th>Rule pred.</th></tr>
          ${rows.map(r => `<tr><td>${r.id}</td><td>${esc(r.review_text)}</td><td>${r.human_label}</td><td>${esc(r.defect_type)}</td><td>${r.rule_prediction}</td></tr>`).join("")}
        </table></div></div>
      <div class="glass note"><b>Honest limitations</b><ul>${v.caveats.map(c => `<li>${esc(c)}</li>`).join("")}</ul></div>`;
  } catch { $("#validation").innerHTML = '<div class="glass empty">Validation metrics unavailable offline.</div>'; }
}

/* ---- Debug (only when server has DEINFLUENCE_DEBUG=1) ---- */
async function pageDebug(view) {
  view.innerHTML = head("Developer tools", "Debug &amp; inspection",
    "Live read-only view of the database and engine internals. Enabled via DEINFLUENCE_DEBUG=1 in the terminal.") +
    '<div id="dbg"><div class="loading">Loading snapshot…</div></div>' + footer();
  try {
    const s = await getJSON("/api/debug/snapshot");
    const cfg = s.engine_config, dbd = s.database;
    const tableBlocks = Object.entries(dbd.tables).map(([name, t]) => `
      <div class="card glass" style="margin-top:14px"><h3>${name} <span class="hint" style="font-size:12px">(${t.row_count} rows)</span></h3>
        <div class="scroll-x" style="max-height:300px;overflow-y:auto"><table class="mono">
          <tr>${t.columns.map(c => `<th>${esc(c)}</th>`).join("")}</tr>
          ${t.rows.map(r => `<tr>${t.columns.map(c => `<td>${esc(String(r[c] ?? ""))}</td>`).join("")}</tr>`).join("") || `<tr><td colspan="${t.columns.length}" class="hint">empty</td></tr>`}
        </table></div></div>`).join("");
    $("#dbg").innerHTML = `
      <div class="card glass"><h3>Database</h3>
        <div class="kv"><span>SQLite file</span><b class="mono">${esc(dbd.db_path)}</b></div></div>
      <div class="card glass" style="margin-top:14px"><h3>Engine configuration</h3>
        <div class="kv"><span>Scoring weights</span><b class="mono">quality ${cfg.scoring_weights.quality} · hype ${cfg.scoring_weights.hype} · value ${cfg.scoring_weights.value}</b></div>
        <div class="kv"><span>Sustainable CPW benchmark</span><b>RM${cfg.sustainable_cpw_benchmark}</b></div>
        <div class="kv"><span>Defect categories</span><b>${cfg.defect_categories.join(", ")}</b></div>
        <div class="kv"><span>Defect lexicon size</span><b>${cfg.defect_lexicon_size} phrases</b></div>
        <div class="kv"><span>Recommendation bands</span><b class="mono">${cfg.recommendation_bands.map(b => b.label + "≥" + b.min_longevity).join(" · ")}</b></div></div>
      ${tableBlocks}`;
  } catch (e) { $("#dbg").innerHTML = `<div class="glass empty">Debug snapshot unavailable (${esc(e.message)}).</div>`; }
}

/* ================= ROUTER ================= */
function buildNav(active) {
  const items = Object.entries(PAGES).map(([k, p]) =>
    `<a href="#/${k}" class="${k === active ? "active" : ""}">${p.label}</a>`);
  if (DEBUG_ENABLED) items.push(`<a href="#/debug" class="debug ${active === "debug" ? "active" : ""}">Debug</a>`);
  $("#nav").innerHTML = items.join("");
  $("#nav").classList.remove("open");
}
function currentRoute() {
  const key = (location.hash || "#/analyse").replace(/^#\//, "").split("/")[0];
  if (key === "debug" && DEBUG_ENABLED) return "debug";
  return PAGES[key] ? key : "analyse";
}
function route() {
  const key = currentRoute();
  buildNav(key);
  const view = $("#view");
  window.scrollTo({ top: 0 });
  (key === "debug" ? pageDebug : PAGES[key].render)(view);
}

/* ---- online indicator ---- */
function setNet() { const on = navigator.onLine; $("#netDot").className = "dot" + (on ? "" : " off"); $("#netTxt").textContent = on ? "Online" : "Offline"; }

/* ---- boot ---- */
async function boot() {
  try { const h = await getJSON("/api/health"); DEBUG_ENABLED = !!h.debug_enabled; } catch {}
  setNet();
  window.addEventListener("online", setNet);
  window.addEventListener("offline", setNet);
  window.addEventListener("hashchange", route);
  $("#hamburger").addEventListener("click", () => $("#nav").classList.toggle("open"));
  if (!location.hash) location.hash = "#/analyse";
  route();
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
}
boot();
