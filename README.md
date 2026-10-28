# De-Influence AI

**Team:** Outlier Behaviour · **Project:** The Micro-Trend Lifespan & Fast-Fashion Regret Predictor

An AI decision-support engine that converts deceptive social-commerce hype into an objective,
data-backed **Product Longevity Score (0-100)**, **Regret Probability**, and **Cost-Per-Wear**
estimate - helping Gen Z and young adults on TikTok Shop / Shopee / Shein avoid impulse spending
on low-quality viral fast-fashion.

This repository contains a runnable MVP: the core intelligence engine, an installable
offline-capable glassmorphism web app (analyse, compare, personalize, wishlist, insight
dashboard), a SQLite data layer, a model-validation module, and an OWASP-aligned security and
responsible-use layer.

> **New here? Start with [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md)** — a plain, step-by-step
> guide to running the app, enabling debug mode, and finding the database. For a one-line start:
> `python -m pip install -r requirements.txt` then `python -m uvicorn app.main:app --port 8000`
> and open `http://127.0.0.1:8000`.

## CRISPE prompt design

The assistant is framed with the **CRISPE** prompt-engineering framework -
**Capacity, Role, Insight, Statement, Personality, Experiment** - documented in
`.kiro/steering/crispe-prompt-design.md`. In short: it acts with the *capacity* of a
product-durability analyst, in the *role* of a neutral anti-impulse advisor to the shopper,
given the *insight* of defect + hype + cost signals, with the *statement* to return a
KEEP/CONSIDER/CAUTION/AVOID call plus plain-language reasons, a *personality* that is honest
and never shames the shopper, and an *experiment* mindset where outputs are validated by MAE/F1.

Separately, the code is kept human-explainable (prototype requirement): the maths (Gompertz fit,
F1, MAE) is written by hand with no hidden ML magic, and every scan returns a "how we calculated
this" breakdown.

## How users add an item

The UX shoppers actually want is "paste a link, get a verdict." We can't read live Shopee /
TikTok Shop pages (logins, bot protection, ToS), and fetching them server-side would be an SSRF
risk. So the link feature is **emulated, safely**:

1. **Paste a product link** (primary) - `POST /api/check-link`. The server **never fetches the
   URL**. It parses the link and resolves it against our own SQLite catalogue: an exact match
   when the demo link is known, otherwise a deterministic, clearly-labelled *emulated* result
   mapped from the link to a representative item. From the user's view it's instant; from a
   security view it's string parsing + a local DB read (OWASP A10 SSRF: no outbound request).
2. **Demo catalogue** - one-tap known items.

OCR, manual entry, and CSV/Excel upload were all phased out to keep the prototype focused on the
paste-a-link experience.

## Validated against the real benchmark

The defect classifier is evaluated against the team's supplied **50-row Malaysian review
benchmark** (`app/data/Sample_Data.xlsx`) via `app/data/benchmark.py` and `app/evaluation.py`.
On that data it scores **F1 ≈ 0.91, accuracy 94%** and **beats the dataset's own baseline rule**
(F1 ≈ 0.83). Per-defect-type recall (Fabric Sheerness, Stitching, Sizing, Thermal) is reported so
coverage is visible. Run `python -m app.evaluation` to print it.

> Honest note: the workbook's prose summary quotes an 18/32 split and TP=14; the actual rows are
> 16/34. We compute metrics from the real rows and state this discrepancy rather than hiding it.

## Feature set

- **Paste-a-link input** (feature #6): paste a Shopee/TikTok/Shein link for an instant verdict,
  resolved safely against the SQLite catalogue with no outbound request (emulated when the exact
  item is unknown). OCR, manual entry and CSV/Excel upload were phased out.
- **Compare** two or more analysed items side by side in a compare tray (feature #2).
- **Personalize** (feature #3): save a preferred style, favourite colour and monthly budget;
  verdicts gain a tailored note when an item matches.
- **Wishlist** (feature #4): favourite saved items and see live stock status. Email restock
  alerts are shown as **"coming soon"** — no email/PII is collected yet, by design.
- **Better-alternative suggestion**: when a verdict is CAUTION/AVOID, the engine scores other
  in-stock catalogue items and recommends a clearly-better one (higher longevity, lower
  cost-per-wear) with a one-click "Analyse it".
- **Why-us positioning** (feature #5): an honest capability matrix vs price trackers, generic AI
  review tools and marketplace ratings, plus investor-facing value props.

## Data layer: SQLite (feature #7)

The catalogue, preferences and wishlist live in a local **SQLite** database (`app/db.py`,
`app/data/deinfluence.db`) — free, zero-setup, and a genuine relational store. It is seeded once
from the demo items and the real `Sample_Data.xlsx` benchmark, after which **the database is the
single source of truth** (not a hardcoded dict). All queries use parameter binding (A03).

## Privacy, offline, and the live dashboard

- **Private by design.** No accounts, no PII at rest (email capture is deferred). The server
  stores catalogue/preferences/wishlist in local SQLite; the user's *scan history* lives only in
  their browser and powers the live dashboard. "Export my data" / "Clear history" are available.
- **Works offline.** The service worker (`static/sw.js`) precaches the app shell and read-only
  endpoints, so the installed app opens and the dashboard works with no connection. Live analysis
  needs the server and fails gracefully when offline.

## Security (OWASP Top 10)

Controls are collected in `app/security.py`, each tagged with its OWASP 2021 category: strict CORS
allow-list, security headers (CSP, X-Frame-Options, nosniff, Referrer-Policy) on every response,
upload **and image** size/type caps **with magic-byte checks** (A03/A08), a per-IP rate limiter,
parameterised SQLite queries (A03), sanitized error messages (A09), pinned dependencies (A06),
no PII at rest (A02/A04), and no server-side outbound requests (A10 — the link feature is gone).

## Reaching app-based shoppers: web app (PWA) vs Chrome extension

Judge feedback noted a Chrome extension "misses app-based shoppers" - Shopee and TikTok Shop are
used mostly inside their phone apps, where a desktop browser extension never runs. Our prototype
answer is to ship the dashboard as an **installable Progressive Web App (PWA)**:

- `static/manifest.webmanifest` + `static/sw.js` let a shopper "Add to Home screen" and open
  De-Influence as a standalone app icon on their phone - no browser, no app-store review.
- The service worker precaches the app shell, so the installed app **works offline**.

This is the pragmatic middle ground: a browser extension only covers desktop browser shoppers; a
native app is too much for a hackathon; a PWA reaches phone users across platforms today and keeps
a clean upgrade path to a real extension / native integration later.

### Test / install it on your phone

PWA install ("Add to Home screen" as a real app) requires **HTTPS** - a plain
`http://<PC-IP>:8000` LAN address will load on the phone but will NOT offer install. Two options:

**A. Just view it on the phone (no install) - same Wi-Fi, 30 seconds**

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_mobile.ps1
```

It prints `http://<your-PC-IP>:8000`. Open that on your phone (same Wi-Fi). If it does not load,
allow Python through the Windows Firewall for Private networks when prompted.

**B. Actually install it on the phone - free HTTPS tunnel**

```powershell
# Terminal A - the app
python -m uvicorn app.main:app --port 8000

# Terminal B - the tunnel
powershell -ExecutionPolicy Bypass -File scripts/run_tunnel.ps1
```

`run_tunnel.ps1` downloads the official `cloudflared.exe` to `tools/` the first time (~55 MB,
no account, no npm) and then opens the tunnel. It prints a `https://<random>.trycloudflare.com`
URL. Open that on your phone, then:

- **Android / Chrome:** menu (dots) -> *Add to Home screen* / *Install app*.
- **iPhone / Safari:** Share -> *Add to Home Screen*.

You get a De-Influence app icon that opens standalone (no browser chrome) and keeps working
offline once installed.

> The tunnel URL is random and temporary - fine for a demo. For a permanent URL, deploy the app
> to any HTTPS host (Render, Railway, Fly.io, etc.).

## The three signature engines

| Engine | What it does | From the pitch |
|---|---|---|
| **Hype-Cycle Decay Forecaster** | Fits a Gompertz curve to a trend's search-velocity history and forecasts remaining shelf-life | "predicting trend shelf-life via Gompertz curves" |
| **Localized NLP Defect Pipeline** | Lexicon-based Malaysian colloquial / code-switching defect detector ("kain nipis", "tak berbaloi", "gila nipis") that goes beyond 5-star noise | "extracting defect patterns beyond 5-star rating noise" |
| **TrueCost Simulator** | Real-time Cost-Per-Wear from price and predicted wearable lifespan | "calculating real-time Cost-Per-Wear" |

These three signals are fused into a **Product Longevity Score** and a **Regret Probability**.
The score is **decomposable** - the API and dashboard show exactly how many points each signal
contributed, so the "dual-signal" number is transparent rather than a black box.

## Quick start

Dependencies: `fastapi`, `uvicorn`, `pydantic`, `numpy`, `pandas`, `openpyxl`,
`python-multipart` (plus `pytest`, `httpx` for tests).

```powershell
# 1. (optional) virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows PowerShell
# source .venv/bin/activate     # macOS / Linux

# 2. install dependencies
python -m pip install -r requirements.txt

# 3. run the server
python -m uvicorn app.main:app --reload
```

Then open:
- **http://127.0.0.1:8000** - the dashboard
- **http://127.0.0.1:8000/docs** - the interactive API

> Tip: use `python -m uvicorn ...` (not bare `uvicorn`) so it works even when the scripts
> folder is not on your PATH.

## See the validation metrics directly

```powershell
python -m app.evaluation
```

Prints F1/precision/recall/accuracy vs the benchmark, the dataset's baseline for comparison,
per-defect-type recall, the hype MAE, and the honest limitations - handy for the pitch Q&A.

## Project layout

```
app/                      BACKEND (FastAPI)
  main.py                 App + all routes; wires middleware and the analysis pipeline
  db.py                   SQLite data layer (catalogue, preferences, wishlist) - source of truth
  schemas.py              Pydantic request/response models
  security.py             OWASP Top 10 controls (headers, CORS allow-list, rate limit)
  link_resolver.py        Emulated paste-a-link -> SQLite catalogue (no network fetch)
  personalization.py      Tailored note from saved preferences
  ethics.py               Responsible-use safeguards (defamation, privacy, confidence)
  evaluation.py           F1 (defect) + MAE (hype) validation against the real benchmark
  positioning.py          Competitor comparison + value props (stakeholder-facing)
  debug.py                Read-only inspection snapshot (only when DEINFLUENCE_DEBUG=1)
  engines/
    defect_nlp.py         Localized Malaysian NLP defect pipeline (5 defect categories)
    hype_decay.py         Gompertz hype-cycle decay forecaster
    truecost.py           Cost-Per-Wear simulator
    scoring.py            Fusion -> explainable Longevity Score + Regret Probability
  data/
    sample_products.py    One-time SEED data for the SQLite catalogue
    benchmark.py          Loads the real 50-row Sample_Data.xlsx benchmark
    labeled_dataset.py    Synthetic hype-curve cases for the MAE check
    Sample_Data.xlsx      Real 50-row Malaysian review benchmark (ground truth)
    deinfluence.db        SQLite DB (generated at runtime; gitignored)

static/                   FRONTEND (installable, offline-capable PWA)
  index.html              App shell + header/nav
  app.css                 All styles (glassmorphism, responsive)
  app.js                  Hash router + one renderer per page
  sw.js                   Service worker (install + offline precache)
  manifest.webmanifest    PWA manifest
  icon.svg                App icon

docs/                     FOR JUDGES
  USER_MANUAL.md          Step-by-step: run it, enable debug, find the database
  architecture.md         System map + OWASP mapping
  user-flow.md            Mermaid user-interaction flowchart + pitch narration

scripts/
  db_peek.py              Print the SQLite DB contents
  run_mobile.ps1          Serve on the LAN for phone testing
  run_tunnel.ps1          Free HTTPS tunnel so the PWA can be installed on a phone

tests/
  conftest.py             Isolates the SQLite DB to a temp file for tests
  test_engines.py         47 tests: engines, fusion, ethics, validation, DB, link, security, debug
```

## Pages (multi-page web app)

The UI is split into clean subpages via a lightweight hash router (`#/analyse`, `#/dashboard`,
etc.) - no more one-giant-scroll page:

- **Analyse** (home) - paste a link, get a verdict
- **Dashboard** - private analytics of what you've analysed
- **Personalize** - style / colour / budget
- **Compare** - side-by-side of saved items
- **Wishlist** - favourites + stock (email alerts "coming soon")
- **Why us** - competitor matrix + value props
- **Validation** - F1/MAE metrics **plus a downloadable copy of the validation dataset**
- **Debug** - only appears when the server is started with `DEINFLUENCE_DEBUG=1`

## API

- `POST /api/scan` - scan by `product_id` or raw `product` payload.
- `POST /api/check-link` - paste a product URL; resolves via SQLite and returns a verdict (no fetch).
- `GET /api/products` · `GET /api/products/{id}` - list / scan catalogue items.
- `GET`/`POST /api/preferences` - read / save personalization.
- `GET`/`POST /api/wishlist` · `DELETE /api/wishlist/{id}` - manage favourites.
- `GET /api/positioning` - competitor comparison + value props.
- `GET /api/evaluation` - validation report (F1 vs benchmark, baseline, per-type recall, MAE).
- `GET /api/evaluation/dataset` - the labeled validation rows (JSON, for transparency).
- `GET /api/evaluation/dataset/download` - download the original `Sample_Data.xlsx` (read-only).
- `GET /api/health` - health + whether debug mode is on.
- `GET /api/debug/snapshot` - **only when `DEINFLUENCE_DEBUG=1`**: read-only DB + engine config.

## Tests

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```

Expected: `49 passed`.

## Showing judges the validation data (transparency)

The Validation page has a **Download .xlsx** button that serves the exact
`Sample_Data.xlsx` the model is scored on, and renders every labeled row inline. This is served
read-only from a fixed path (no user input -> no path traversal, OWASP A01/A03).

## Debug / last-minute inspection

Start the server with the debug flag to unlock a read-only Debug page (and `/api/debug/snapshot`):

```powershell
$env:DEINFLUENCE_DEBUG = "1"      # Windows PowerShell
python -m uvicorn app.main:app --reload
```

It shows the SQLite file path, every table's rows, and the engine configuration (scoring weights,
thresholds, lexicon size). Without the flag the endpoint and page do not exist (OWASP A05).

To inspect the DB from the terminal instead:

```powershell
python scripts/db_peek.py
```

The SQLite file lives at `app/data/deinfluence.db`. To restore a clean demo state, call
`app.db.reset_catalogue()` (wipes and reseeds in place).

## Data, assumptions and limitations (stated on purpose)

- The defect classifier is validated on the real **50-row Sample_Data.xlsx** benchmark; the
  seeded demo catalogue lets the app run offline with no external keys.
- The benchmark is **small and synthetic**, with no inter-annotator agreement, so the metrics are
  a strong sanity check, not proof. Real deployment needs hundreds of independently-labeled rows.
- Scores are **decision-support, not financial advice**, and describe a product's regret risk -
  never a factual or legal accusation against a named seller.
- The user's scan history is **private to their device** (browser storage); the server keeps none.
