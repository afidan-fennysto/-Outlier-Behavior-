# De-Influence AI

**Team:** Outlier Behaviour · **Project:** The Micro-Trend Lifespan & Fast-Fashion Regret Predictor

An AI decision-support engine that converts deceptive social-commerce hype into an objective,
data-backed **Product Longevity Score (0-100)**, **Regret Probability**, and **Cost-Per-Wear**
estimate - helping Gen Z and young adults on TikTok Shop / Shopee / Shein avoid impulse spending
on low-quality viral fast-fashion.

This repository contains a runnable MVP of the core intelligence engine, a web dashboard
("manual URL scan" channel from the pitch), a model-validation module, and a
responsible-use/safeguards layer.

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

## How users give us data (the three input channels)

A real-time scraper that reads a live Shopee / TikTok Shop page is **not** realistic at prototype
scale - those apps sit behind logins and bot protection, and scraping them breaches their terms
(see `app/ethics.py`). So the prototype offers three honest channels, in order of reliability:

1. **Upload a review sheet (recommended)** - `POST /api/scan-upload` accepts a cleaned CSV or
   Excel file and runs the full analysis. A ready sample is at `app/data/sample_upload.xlsx`
   (regenerate with `python scripts/make_sample_excel.py`).
2. **Check a link (experimental)** - `POST /api/check-link` does a best-effort public fetch. For
   Shopee / TikTok Shop it tells the user honestly that it cannot read the page and points them to
   upload, rather than inventing reviews.
3. **Try a demo item** - the built-in sample catalogue.

## Reaching app-based shoppers: web app (PWA) vs Chrome extension

Judge feedback noted a Chrome extension "misses app-based shoppers" - Shopee and TikTok Shop are
used mostly inside their phone apps, where a desktop browser extension never runs. Our prototype
answer is to ship the dashboard as an **installable Progressive Web App (PWA)**:

- `static/manifest.webmanifest` + `static/sw.js` let a shopper "Add to Home screen" and open
  De-Influence as a standalone app icon on their phone - no browser, no app-store review.
- The manifest declares a **Web Share Target**, so a shopper can tap *Share* on a product in the
  Shopee/TikTok app and send the link straight into De-Influence.

This is the pragmatic middle ground: a browser extension only covers desktop browser shoppers; a
native app is too much for a hackathon; a PWA reaches phone users across platforms today and keeps
a clean upgrade path to a real extension / native share integration later.

## The three signature engines

| Engine | What it does | From the pitch |
|---|---|---|
| **Hype-Cycle Decay Forecaster** | Fits a Gompertz curve to a trend's search-velocity history and forecasts remaining shelf-life | "predicting trend shelf-life via Gompertz curves" |
| **Localized NLP Defect Pipeline** | Lexicon-based Malaysian colloquial / code-switching defect detector ("kain nipis", "tak berbaloi", "gila nipis") that goes beyond 5-star noise | "extracting defect patterns beyond 5-star rating noise" |
| **TrueCost Simulator** | Real-time Cost-Per-Wear from price and predicted wearable lifespan | "calculating real-time Cost-Per-Wear" |

These three signals are fused into a **Product Longevity Score** and a **Regret Probability**.
The score is **decomposable** - the API and dashboard show exactly how many points each signal
contributed, so the "dual-signal" number is transparent rather than a black box.

## What changed in response to judge feedback

Both judges scored **Validation & Performance** as the weakest area, and one judge flagged that
**defamation and scraping risks were unaddressed**. This version adds:

- **`app/evaluation.py` + `/api/evaluation`** - real metrics on a hand-labeled set:
  **F1-score** for the defect classifier and **MAE (days)** for the hype-decay forecast, each
  with a plain-English explanation and **honest caveats** about the tiny prototype dataset.
- **`app/ethics.py`** - a responsible-use layer: seller-name anonymisation (defamation guard),
  a documented data-sourcing/scraping policy, a privacy note, human-oversight disclaimer, and a
  **confidence band** (high/medium/low) that downgrades thin-evidence scans.
- **Explainable scoring** - each scan returns `score_breakdown` and `how_we_calculated`.
- **Dashboard** - now shows the score breakdown, a confidence badge, responsible-use
  disclaimers, and a Model Validation panel.

## Quick start

Dependencies: `fastapi`, `uvicorn`, `pydantic`, `numpy` (plus `pytest`, `httpx` for tests).

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

Prints the F1-score, the MAE per trend case, and the limitations - handy for the pitch Q&A.

## Project layout

```
app/
  main.py                 FastAPI app, scan/upload/link/evaluation endpoints, PWA routes
  schemas.py              Pydantic request/response models
  ethics.py               Responsible-use safeguards (defamation, scraping, confidence)
  evaluation.py           MAE + F1 validation against the labeled dataset
  ingestion.py            Parse uploaded CSV / Excel into a product
  link_fetch.py           Experimental, honest public-URL fetch
  engines/
    hype_decay.py         Gompertz hype-cycle decay forecaster
    defect_nlp.py         Localized Malaysian NLP defect pipeline
    truecost.py           Cost-Per-Wear simulator
    scoring.py            Fusion -> explainable Longevity Score + Regret Probability
  data/
    sample_products.py    Demo catalogue (runs with no external API keys)
    labeled_dataset.py    Hand-labeled ground truth for validation
    sample_upload.xlsx    Cleaned sample file for the upload channel
scripts/
  make_sample_excel.py    Regenerates sample_upload.xlsx
static/
  index.html              Web dashboard (3 input channels, breakdown, validation, disclaimers)
  manifest.webmanifest    PWA manifest + Web Share Target
  sw.js                   Service worker (installable web app)
  icon.svg                App icon
.kiro/steering/
  crispe-prompt-design.md CRISPE framing of the assistant
tests/
  test_engines.py         35 tests: engines, fusion, ethics, validation, ingestion, link, API
```

## API

- `POST /api/scan` - scan a product by `product_id` (demo catalogue) or by raw `product` payload.
  Returns longevity score, regret probability, recommendation, **score breakdown**,
  **how_we_calculated**, **confidence**, **disclaimers**, plus the hype / defect / truecost detail.
- `POST /api/scan-upload` - upload a CSV / Excel review sheet and analyse it (file field `file`).
- `POST /api/check-link` - experimental best-effort public URL fetch (honest fallback).
- `GET /api/products` - list the demo catalogue.
- `GET /api/products/{product_id}` - scan one demo product.
- `GET /api/evaluation` - model validation report (F1, MAE, caveats).
- `GET /api/health` - service health check.

## Tests

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```

Expected: `35 passed`.

## Data, assumptions and limitations (stated on purpose)

- The MVP ships with a **self-contained synthetic catalogue** so it runs offline. In production
  these inputs (search-velocity series, review corpus, price history) come from official platform
  APIs or user-initiated single-page lookups - **not** silent bulk scraping (see `app/ethics.py`).
- The validation set is **tiny and team-labeled**, with no inter-annotator agreement, so the
  metrics are a sanity check, not proof. Real deployment needs hundreds of independently-labeled
  samples.
- Scores are **decision-support, not financial advice**, and describe a product's regret risk -
  never a factual or legal accusation against a named seller.
