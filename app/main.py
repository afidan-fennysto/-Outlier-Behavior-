"""De-Influence AI — FastAPI application.

Serves the analysis API and the offline-capable web dashboard. Security controls live in
app/security.py, mapped to the OWASP Top 10.

Data model: a local SQLite database (app/db.py) is the single source of truth for the
catalogue, user preferences and the wishlist. The user's scan *history* still lives only in
their browser. No accounts, no PII at rest (email capture for wishlist alerts is a future
feature, shown as "coming soon").
"""
from __future__ import annotations

import mimetypes
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Some Windows installs register .js / .css as text/plain in the system registry, which makes
# browsers refuse to run our scripts ("MIME type ('text/plain') is not executable"). Force the
# correct types so StaticFiles always serves them with an executable/stylable content type.
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/javascript", ".mjs")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/manifest+json", ".webmanifest")

from . import db, debug
from .data.benchmark import BENCHMARK_PATH, load_benchmark
from .engines.defect_nlp import analyze_reviews
from .engines.hype_decay import forecast_hype
from .engines.scoring import fuse
from .engines.truecost import simulate_true_cost
from .ethics import confidence_band, responsible_use_disclaimers, sanitize_public_text
from .evaluation import run_full_evaluation
from .link_resolver import resolve_link
from .personalization import personalized_note
from .positioning import market_positioning
from .security import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    allowed_origins,
)
from .schemas import (
    AlternativeOut,
    ClassificationMetricsOut,
    DefectOut,
    EvaluationResponse,
    HypeForecastOut,
    LinkCheckRequest,
    LinkCheckResponse,
    PreferencesIn,
    PreferencesOut,
    ProductSummary,
    RegressionMetricsOut,
    ScanRequest,
    ScanResponse,
    TrueCostOut,
    WishlistAddIn,
    WishlistItemOut,
)

_PROD = os.environ.get("DEINFLUENCE_ENV", "").lower() == "production"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db(seed=True)   # create tables + seed the catalogue once
    yield


app = FastAPI(
    title="De-Influence AI",
    description=(
        "The Micro-Trend Lifespan & Fast-Fashion Regret Predictor. Converts deceptive "
        "social-commerce hype into an objective Product Longevity Score, Regret Probability "
        "and Cost-Per-Wear. Team: Outlier Behaviour."
    ),
    version="0.3.0",
    docs_url=None if _PROD else "/docs",
    redoc_url=None if _PROD else "/redoc",
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
    allow_credentials=False,
)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


# ---------------------------------------------------------------------------
# Core analysis pipeline
# ---------------------------------------------------------------------------
def _score_product(product: dict):
    """Run the three engines + fusion on a product. Returns (defects, hype, truecost, verdict)."""
    reviews = [
        {"text": r.get("text", ""), "rating": r.get("rating")}
        for r in product.get("reviews", [])
    ]
    defects = analyze_reviews(reviews)
    hype = forecast_hype(product.get("search_velocity", []))
    truecost = simulate_true_cost(
        price=float(product.get("price", 0) or 0),
        category=product.get("category", "default"),
        quality_health=defects.quality_health,
        hype_remaining_days=hype.remaining_life_days,
        currency=product.get("currency", "RM"),
        hype_phase=hype.phase,
    )
    verdict = fuse(defects, hype, truecost)
    return defects, hype, truecost, verdict


def _find_alternative(scanned: dict, verdict) -> "AlternativeOut | None":
    """For a weak verdict (CAUTION/AVOID), suggest a stronger catalogue item in the same category.

    Scores each in-stock candidate (no recursion - we never look for alternatives of
    alternatives) and returns the best one that clearly beats the scanned item.
    """
    if verdict.recommendation not in ("CAUTION", "AVOID"):
        return None
    best, best_v = None, None
    for cand in db.alternative_candidates(scanned.get("category", ""), scanned.get("id", "")):
        _, _, cand_tc, cand_v = _score_product(cand)
        # Only suggest something meaningfully better and itself worth keeping.
        if cand_v.recommendation in ("KEEP", "CONSIDER") and \
           cand_v.longevity_score >= verdict.longevity_score + 15:
            if best_v is None or cand_v.longevity_score > best_v.longevity_score:
                best, best_v, best_tc = cand, cand_v, cand_tc
    if best is None:
        return None
    same_cat = best["category"] == scanned.get("category", "")
    where = "in the same category" if same_cat else "from our durable picks"

    # Illustrative "partner discount" (demo only — we have no real affiliate partners yet).
    # Shows how the business model would nudge users toward durable staples. Flagged in the UI.
    discount_pct = 10
    orig_price = round(float(best["price"]), 2)
    discounted_price = round(orig_price * (1 - discount_pct / 100.0), 2)

    return AlternativeOut(
        product_id=best["id"], name=best["name"], category=best["category"],
        price=orig_price, currency=best["currency"], platform=best["platform"],
        longevity_score=best_v.longevity_score, recommendation=best_v.recommendation,
        cost_per_wear=best_tc.cost_per_wear,
        discount_pct=discount_pct, discounted_price=discounted_price, discount_is_demo=True,
        reason=(f"Scores {best_v.longevity_score:.0f} vs {verdict.longevity_score:.0f} on "
                f"longevity at {best['currency']}{best_tc.cost_per_wear:.2f}/wear - a better keep "
                f"{where}."),
    )


def _run_pipeline(product: dict) -> ScanResponse:
    defects, hype, truecost, verdict = _score_product(product)

    series_points = len(product.get("search_velocity", []))
    band = confidence_band(defects.reviews_analyzed, series_points)
    safe_reasons = [sanitize_public_text(r) for r in verdict.reasons]

    # Personalization note (feature #3), using whatever preferences are saved.
    try:
        note = personalized_note(product, db.get_preferences())
    except Exception:
        note = None

    # Alternative suggestion for weak verdicts (feature: "steer to a better staple").
    try:
        alternative = _find_alternative(product, verdict)
    except Exception:
        alternative = None

    return ScanResponse(
        product_id=product.get("id"),
        product_name=product.get("name", "Unnamed product"),
        category=product.get("category", "default"),
        longevity_score=verdict.longevity_score,
        regret_probability=verdict.regret_probability,
        recommendation=verdict.recommendation,
        headline=verdict.headline,
        reasons=safe_reasons,
        score_breakdown=verdict.score_breakdown,
        how_we_calculated=verdict.how_we_calculated,
        confidence=band.level,
        disclaimers=responsible_use_disclaimers(defects.reviews_analyzed, series_points),
        personalized_note=note,
        alternative=alternative,
        hype=HypeForecastOut(**hype.__dict__),
        defects=DefectOut(**defects.__dict__),
        truecost=TrueCostOut(**truecost.__dict__),
    )


def _summary(p: dict) -> ProductSummary:
    return ProductSummary(
        id=p["id"], name=p["name"], category=p["category"], price=p["price"],
        currency=p["currency"], platform=p["platform"], image_hint="",
        colour=p.get("colour", ""), style=p.get("style", ""), in_stock=p.get("in_stock", True),
    )


# ---------------------------------------------------------------------------
# Health + catalogue
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "de-influence-ai", "version": app.version,
            "debug_enabled": debug.debug_enabled()}


@app.get("/api/products", response_model=list[ProductSummary])
def products() -> list[ProductSummary]:
    return [_summary(p) for p in db.list_products()]


@app.get("/api/products/{product_id}", response_model=ScanResponse)
def product_scan(product_id: str) -> ScanResponse:
    product = db.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Unknown product id.")
    return _run_pipeline(product)


@app.post("/api/scan", response_model=ScanResponse)
def scan(req: ScanRequest) -> ScanResponse:
    if req.product_id:
        product = db.get_product(req.product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Unknown product id.")
        return _run_pipeline(product)
    if req.product:
        payload = req.product.model_dump()
        payload["reviews"] = [
            {"text": r["text"], "rating": r.get("rating")} for r in payload.get("reviews", [])
        ]
        return _run_pipeline(payload)
    raise HTTPException(status_code=400, detail="Provide either 'product_id' or 'product'.")


# ---------------------------------------------------------------------------
# Paste-a-link (emulated): the primary input. No network fetch; resolves via SQLite.
# ---------------------------------------------------------------------------
@app.post("/api/check-link", response_model=LinkCheckResponse)
def check_link(req: LinkCheckRequest) -> LinkCheckResponse:
    """Resolve a pasted product URL to a catalogue item and analyse it.

    IMPORTANT: this does NOT fetch the URL (OWASP A10 SSRF-safe). It parses the link and maps
    it to a seeded product in our SQLite database - an exact demo-link match if we have one,
    otherwise a deterministic, clearly-labelled emulated result.
    """
    resolved, product = resolve_link(req.url)
    if not resolved.ok or product is None:
        raise HTTPException(status_code=400, detail=resolved.note)
    scan = _run_pipeline(product)
    return LinkCheckResponse(
        platform=resolved.platform, matched=resolved.matched, note=resolved.note, scan=scan,
    )


# ---------------------------------------------------------------------------
# Preferences (feature #3)
# ---------------------------------------------------------------------------
@app.get("/api/preferences", response_model=PreferencesOut)
def get_preferences() -> PreferencesOut:
    return PreferencesOut(**db.get_preferences())


@app.post("/api/preferences", response_model=PreferencesOut)
def set_preferences(req: PreferencesIn) -> PreferencesOut:
    saved = db.set_preferences(req.preferred_style, req.favourite_colour, req.monthly_budget)
    return PreferencesOut(**saved)


# ---------------------------------------------------------------------------
# Wishlist (feature #4) — email alerts are a future feature (no PII stored yet)
# ---------------------------------------------------------------------------
@app.get("/api/wishlist", response_model=list[WishlistItemOut])
def get_wishlist() -> list[WishlistItemOut]:
    items = []
    for w in db.list_wishlist():
        items.append(WishlistItemOut(
            product=_summary(w["product"]), notify_on_restock=w["notify_on_restock"],
            in_stock=w["in_stock"], added_at=w["added_at"],
        ))
    return items


@app.post("/api/wishlist", response_model=list[WishlistItemOut])
def add_wishlist(req: WishlistAddIn) -> list[WishlistItemOut]:
    if not db.add_to_wishlist(req.product_id, req.notify_on_restock):
        raise HTTPException(status_code=404, detail="Unknown product id.")
    return get_wishlist()


@app.delete("/api/wishlist/{product_id}", response_model=list[WishlistItemOut])
def remove_wishlist(product_id: str) -> list[WishlistItemOut]:
    db.remove_from_wishlist(product_id)
    return get_wishlist()


# ---------------------------------------------------------------------------
# Market positioning (feature #5)
# ---------------------------------------------------------------------------
@app.get("/api/positioning")
def positioning() -> dict:
    return market_positioning()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
@app.get("/api/evaluation", response_model=EvaluationResponse)
def evaluation() -> EvaluationResponse:
    report = run_full_evaluation()
    baseline = (
        ClassificationMetricsOut(**report.baseline_rule.__dict__)
        if report.baseline_rule else None
    )
    return EvaluationResponse(
        defect_classification=ClassificationMetricsOut(**report.defect_classification.__dict__),
        hype_forecast=RegressionMetricsOut(**report.hype_forecast.__dict__),
        per_defect_type=report.per_defect_type,
        baseline_rule=baseline,
        dataset_source=report.dataset_source,
        caveats=report.caveats,
    )


@app.get("/api/evaluation/dataset")
def evaluation_dataset() -> list[dict]:
    """The exact labeled rows the model is validated on, for judge transparency."""
    return [
        {"id": r.id, "review_text": r.text, "human_label": "Defect" if r.is_defect else "No Defect",
         "defect_type": r.defect_type, "rule_prediction": "Defect" if r.rule_prediction else "No Defect"}
        for r in load_benchmark()
    ]


@app.get("/api/evaluation/dataset/download")
def evaluation_dataset_download() -> FileResponse:
    """Download the original Sample_Data.xlsx benchmark (read-only, path-pinned).

    OWASP: the path is a fixed constant (no user input -> no path traversal, A01/A03). The
    file is served read-only with a safe content type and attachment disposition.
    """
    if not BENCHMARK_PATH.exists():
        raise HTTPException(status_code=404, detail="Benchmark file not found.")
    return FileResponse(
        BENCHMARK_PATH,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="De-Influence_AI_validation_benchmark.xlsx",
    )


# ---------------------------------------------------------------------------
# Debug (only mounted when DEINFLUENCE_DEBUG=1 — toggle from the terminal)
# ---------------------------------------------------------------------------
if debug.debug_enabled():
    @app.get("/api/debug/snapshot")
    def debug_snapshot() -> dict:
        return debug.full_snapshot()


# ---------------------------------------------------------------------------
# Static + PWA
# ---------------------------------------------------------------------------
@app.get("/")
def dashboard() -> FileResponse:
    index = STATIC_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="Dashboard not built.")
    return FileResponse(index)


@app.get("/sw.js")
def service_worker() -> FileResponse:
    sw = STATIC_DIR / "sw.js"
    if not sw.exists():
        raise HTTPException(status_code=404, detail="Service worker not found.")
    return FileResponse(sw, media_type="application/javascript")


# Serve the core assets with explicit, pinned content types so they always load - never
# subject to a mis-configured OS MIME registry (belt-and-suspenders alongside the mimetypes
# fix above). Must be declared BEFORE the /static mount so they take precedence.
@app.get("/static/app.js")
def app_js() -> FileResponse:
    f = STATIC_DIR / "app.js"
    if not f.exists():
        raise HTTPException(status_code=404, detail="app.js not found.")
    return FileResponse(f, media_type="application/javascript")


@app.get("/static/app.css")
def app_css() -> FileResponse:
    f = STATIC_DIR / "app.css"
    if not f.exists():
        raise HTTPException(status_code=404, detail="app.css not found.")
    return FileResponse(f, media_type="text/css")


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
