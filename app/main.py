"""De-Influence AI — FastAPI application.

Exposes the scan API and serves the web-dashboard "manual URL scan" channel.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .data.sample_products import get_product, list_products
from .engines.defect_nlp import analyze_reviews
from .engines.hype_decay import forecast_hype
from .engines.scoring import fuse
from .engines.truecost import simulate_true_cost
from .ethics import confidence_band, responsible_use_disclaimers, sanitize_public_text
from .evaluation import run_full_evaluation
from .ingestion import IngestionError, parse_upload
from .link_fetch import fetch_link
from .schemas import (
    ClassificationMetricsOut,
    DefectOut,
    EvaluationResponse,
    HypeForecastOut,
    LinkCheckRequest,
    LinkCheckResponse,
    ProductSummary,
    RegressionMetricsOut,
    ScanRequest,
    ScanResponse,
    TrueCostOut,
)

app = FastAPI(
    title="De-Influence AI",
    description=(
        "The Micro-Trend Lifespan & Fast-Fashion Regret Predictor. Converts deceptive "
        "social-commerce hype into an objective Product Longevity Score, Regret Probability "
        "and Cost-Per-Wear. Team: Outlier Behaviour."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # browser-extension overlay would call cross-origin
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def _run_pipeline(product: dict) -> ScanResponse:
    """Run all three engines + fusion on a product dict."""
    reviews = [
        {"text": r.get("text", ""), "rating": r.get("rating")}
        for r in product.get("reviews", [])
    ]
    defects = analyze_reviews(reviews)
    hype = forecast_hype(product.get("search_velocity", []))
    truecost = simulate_true_cost(
        price=float(product["price"]),
        category=product.get("category", "default"),
        quality_health=defects.quality_health,
        hype_remaining_days=hype.remaining_life_days,
        currency=product.get("currency", "RM"),
        hype_phase=hype.phase,
    )
    verdict = fuse(defects, hype, truecost)

    # Responsible-use layer: attach a confidence level and disclaimers, and scrub any
    # defamatory wording from the user-facing reasons before returning them.
    series_points = len(product.get("search_velocity", []))
    band = confidence_band(defects.reviews_analyzed, series_points)
    safe_reasons = [sanitize_public_text(r) for r in verdict.reasons]

    return ScanResponse(
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
        hype=HypeForecastOut(**hype.__dict__),
        defects=DefectOut(**defects.__dict__),
        truecost=TrueCostOut(**truecost.__dict__),
    )


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "de-influence-ai", "version": app.version}


@app.get("/api/products", response_model=list[ProductSummary])
def products() -> list[ProductSummary]:
    return [
        ProductSummary(
            id=p["id"], name=p["name"], category=p["category"], price=p["price"],
            currency=p["currency"], platform=p["platform"], image_hint=p.get("image_hint", "🛍️"),
        )
        for p in list_products()
    ]


@app.get("/api/products/{product_id}", response_model=ScanResponse)
def product_scan(product_id: str) -> ScanResponse:
    product = get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Unknown product_id '{product_id}'")
    return _run_pipeline(product)


@app.post("/api/scan", response_model=ScanResponse)
def scan(req: ScanRequest) -> ScanResponse:
    if req.product_id:
        product = get_product(req.product_id)
        if product is None:
            raise HTTPException(status_code=404, detail=f"Unknown product_id '{req.product_id}'")
        return _run_pipeline(product)

    if req.product:
        payload = req.product.model_dump()
        payload["reviews"] = [
            {"text": r["text"], "rating": r.get("rating")} for r in payload.get("reviews", [])
        ]
        return _run_pipeline(payload)

    raise HTTPException(status_code=400, detail="Provide either 'product_id' or 'product'.")


@app.post("/api/scan-upload", response_model=ScanResponse)
async def scan_upload(file: UploadFile = File(...)) -> ScanResponse:
    """Upload a cleaned CSV / Excel review sheet and run the full analysis on it.

    This is the prototype's primary 'real data' channel: a reliable, ToS-safe alternative
    to scraping a live product page.
    """
    data = await file.read()
    try:
        product = parse_upload(file.filename or "", data)
    except IngestionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _run_pipeline(product)


@app.post("/api/check-link", response_model=LinkCheckResponse)
def check_link(req: LinkCheckRequest) -> LinkCheckResponse:
    """Experimental: best-effort public fetch of a product URL.

    Honest by design - if the page yields enough to analyse we return a scan, otherwise we
    explain why and point the user to the upload flow instead of inventing data.
    """
    result = fetch_link(req.url)
    scan: ScanResponse | None = None
    if result.reachable and result.reviews:
        product = {
            "name": result.extracted_name or "Linked product",
            "category": "top",
            "price": result.extracted_price or 30.0,
            "currency": "RM",
            "search_velocity": [],
            "reviews": result.reviews,
        }
        scan = _run_pipeline(product)
    return LinkCheckResponse(
        url=result.url, reachable=result.reachable, extracted_name=result.extracted_name,
        extracted_price=result.extracted_price, note=result.note, scan=scan,
    )


@app.get("/api/evaluation", response_model=EvaluationResponse)
def evaluation() -> EvaluationResponse:
    """Model validation metrics (MAE for hype decay, F1 for defect NLP).

    Added in response to judge feedback that validation was not demonstrated. Runs the
    engines against a hand-labeled dataset and reports the metrics with honest caveats.
    """
    report = run_full_evaluation()
    return EvaluationResponse(
        defect_classification=ClassificationMetricsOut(**report.defect_classification.__dict__),
        hype_forecast=RegressionMetricsOut(**report.hype_forecast.__dict__),
        caveats=report.caveats,
    )


@app.get("/")
def dashboard() -> FileResponse:
    index = STATIC_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="Dashboard not built.")
    return FileResponse(index)


@app.get("/sw.js")
def service_worker() -> FileResponse:
    """Serve the service worker from the site root so its scope covers the whole app.

    A service worker can only control pages at or below its own URL path, so the PWA
    needs sw.js at '/sw.js', not '/static/sw.js'.
    """
    sw = STATIC_DIR / "sw.js"
    if not sw.exists():
        raise HTTPException(status_code=404, detail="Service worker not found.")
    return FileResponse(sw, media_type="application/javascript")


# Mount static assets last so API routes take precedence.
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
