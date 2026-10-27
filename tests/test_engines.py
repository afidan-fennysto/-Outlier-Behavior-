"""Unit tests for the three engines, the fusion scorer, and the API."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.engines.defect_nlp import analyze_reviews
from app.engines.hype_decay import forecast_hype
from app.engines.scoring import fuse
from app.engines.truecost import simulate_true_cost
from app.main import app

client = TestClient(app)


# --------------------------- Hype decay ---------------------------
def test_hype_detects_decaying_trend():
    # Rise then sharp fall => not rising, hype health well below max.
    series = [5, 20, 60, 120, 150, 90, 40, 15, 6, 3]
    f = forecast_hype(series)
    assert f.phase in ("decaying", "stale", "cresting")
    assert 0 <= f.hype_health <= 100
    assert f.remaining_life_days >= 0


def test_hype_detects_rising_trend():
    series = [2, 4, 9, 18, 35, 70, 120]
    f = forecast_hype(series)
    assert f.phase in ("rising", "cresting")
    assert f.hype_health >= 60


def test_hype_short_series_is_neutral():
    f = forecast_hype([10, 20])
    assert 0 <= f.hype_health <= 100


# --------------------------- Defect NLP ---------------------------
def test_nlp_flags_malay_slang_defects():
    reviews = [
        {"text": "Kain gila nipis, cepat rosak. Menyesal beli.", "rating": 1},
        {"text": "Tak berbaloi, material murahan", "rating": 2},
    ]
    a = analyze_reviews(reviews)
    assert a.defect_rate > 0.5
    assert a.quality_health < 60
    cats = {d["category"] for d in a.top_defects}
    assert {"material", "durability", "value"} & cats


def test_nlp_respects_negation():
    # "tak nipis" (not thin) must NOT count as a thin-material defect.
    clean = analyze_reviews([{"text": "Kain tak nipis, tebal dan berbaloi", "rating": 5}])
    assert clean.quality_health > 60
    assert clean.defect_rate < 0.5


def test_nlp_good_reviews_stay_clean():
    reviews = [
        {"text": "Kain tebal, tahan lama, berbaloi sangat", "rating": 5},
        {"text": "Good quality, selesa dan kemas", "rating": 5},
    ]
    a = analyze_reviews(reviews)
    assert a.quality_health >= 70
    assert a.defect_rate == 0.0


def test_nlp_detects_rating_inflation():
    # Defect language but a 5-star rating => inflated-star signal.
    a = analyze_reviews([{"text": "Kain gila nipis cepat rosak tak berbaloi", "rating": 5}])
    assert a.rating_gap > 0


# --------------------------- TrueCost ---------------------------
def test_truecost_penalizes_low_quality_short_trend():
    tc = simulate_true_cost(price=30.0, category="top", quality_health=20, hype_remaining_days=10)
    assert tc.expected_wears < 10
    assert tc.cost_per_wear > tc.benchmark_cpw
    assert tc.verdict in ("poor", "waste")


def test_truecost_rewards_durable_staple():
    tc = simulate_true_cost(price=90.0, category="tshirt", quality_health=95, hype_remaining_days=300)
    assert tc.expected_wears > 50
    assert tc.verdict in ("excellent", "fair")


# --------------------------- Fusion ---------------------------
def test_fuse_regret_item_gets_avoid():
    defects = analyze_reviews([
        {"text": "Kain gila nipis cepat rosak, tak berbaloi, menyesal", "rating": 1},
        {"text": "Broke after 2 wears, waste of money", "rating": 1},
    ])
    hype = forecast_hype([5, 20, 60, 120, 150, 90, 40, 15, 6, 3])
    tc = simulate_true_cost(24.0, "top", defects.quality_health, hype.remaining_life_days,
                            hype_phase=hype.phase)
    v = fuse(defects, hype, tc)
    assert v.recommendation in ("CAUTION", "AVOID")
    assert v.regret_probability > 50
    assert v.longevity_score < 60


def test_fuse_quality_staple_gets_keep():
    defects = analyze_reviews([
        {"text": "Kain tebal, tahan lama, berbaloi", "rating": 5},
        {"text": "Good quality, well made, worth it", "rating": 5},
    ])
    hype = forecast_hype([30, 32, 35, 36, 38, 40, 42])
    tc = simulate_true_cost(39.0, "tshirt", defects.quality_health, hype.remaining_life_days,
                            hype_phase=hype.phase)
    v = fuse(defects, hype, tc)
    assert v.longevity_score >= 60
    assert v.regret_probability < 55
    # A durable staple must not be mislabeled a "waste" purely on trend grounds.
    assert tc.verdict in ("excellent", "fair", "poor")
    assert tc.expected_wears > 20


# --------------------------- API ---------------------------
def test_api_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_api_list_products():
    r = client.get("/api/products")
    assert r.status_code == 200
    assert len(r.json()) >= 3


def test_api_scan_by_id():
    r = client.post("/api/scan", json={"product_id": "tiktok-viral-mesh-top"})
    assert r.status_code == 200
    body = r.json()
    assert 0 <= body["longevity_score"] <= 100
    assert 0 <= body["regret_probability"] <= 100
    assert body["recommendation"] in ("KEEP", "CONSIDER", "CAUTION", "AVOID")


def test_api_scan_raw_payload():
    payload = {
        "product": {
            "name": "Ad-hoc test top", "category": "top", "price": 25.0, "currency": "RM",
            "search_velocity": [5, 20, 60, 120, 150, 90, 40, 15, 6, 3],
            "reviews": [{"text": "kain nipis cepat rosak tak berbaloi", "rating": 1}],
        }
    }
    r = client.post("/api/scan", json=payload)
    assert r.status_code == 200
    assert r.json()["product_name"] == "Ad-hoc test top"


def test_api_unknown_product_404():
    r = client.post("/api/scan", json={"product_id": "does-not-exist"})
    assert r.status_code == 404


# --------------------------- Validation / metrics ---------------------------
from app.evaluation import (  # noqa: E402
    evaluate_defect_classifier,
    evaluate_hype_forecaster,
    run_full_evaluation,
)
from app.ethics import (  # noqa: E402
    confidence_band,
    responsible_use_disclaimers,
    safe_merchant_label,
    sanitize_public_text,
)


def test_defect_f1_is_reasonable():
    m = evaluate_defect_classifier()
    # On the labeled set the detector should be clearly better than chance.
    assert 0.0 <= m.f1_score <= 1.0
    assert m.f1_score >= 0.6
    assert m.n == m.true_positives + m.false_positives + m.true_negatives + m.false_negatives
    assert m.explanation


def test_hype_mae_is_computed():
    m = evaluate_hype_forecaster()
    assert m.mae >= 0.0
    assert len(m.per_case) == 4
    for case in m.per_case:
        assert case["abs_error_days"] >= 0
    assert m.explanation


def test_full_evaluation_has_caveats():
    report = run_full_evaluation()
    assert report.caveats
    assert any("label" in c.lower() or "prototype" in c.lower() for c in report.caveats)


# --------------------------- Ethics / responsible use ---------------------------
def test_merchant_label_is_anonymous_and_stable():
    a = safe_merchant_label("TrendyShopKL")
    b = safe_merchant_label("TrendyShopKL")
    assert a == b                      # stable for grouping
    assert "TrendyShopKL" not in a     # never reveals the real name
    assert a.startswith("seller-")


def test_sanitize_removes_defamatory_words():
    out = sanitize_public_text("This seller is a scammer and a fraudster")
    assert "scammer" not in out.lower()
    assert "fraudster" not in out.lower()


def test_confidence_band_reflects_evidence():
    assert confidence_band(reviews_analyzed=6, series_points=8).level == "high"
    assert confidence_band(reviews_analyzed=3, series_points=4).level == "medium"
    assert confidence_band(reviews_analyzed=1, series_points=2).level == "low"


def test_disclaimers_always_present():
    d = responsible_use_disclaimers(reviews_analyzed=1, series_points=2)
    assert any("Confidence" in x for x in d)
    assert any("not financial advice" in x.lower() for x in d)


# --------------------------- New scan response fields ---------------------------
def test_scan_includes_explainability_and_safeguards():
    r = client.post("/api/scan", json={"product_id": "tiktok-viral-mesh-top"})
    assert r.status_code == 200
    body = r.json()
    assert body["how_we_calculated"]
    assert len(body["score_breakdown"]) == 3
    assert body["confidence"] in ("high", "medium", "low")
    assert body["disclaimers"]


def test_evaluation_endpoint():
    r = client.get("/api/evaluation")
    assert r.status_code == 200
    body = r.json()
    assert 0.0 <= body["defect_classification"]["f1_score"] <= 1.0
    assert body["hype_forecast"]["mae"] >= 0.0
    assert body["caveats"]


# --------------------------- Ingestion (CSV / Excel upload) ---------------------------
from app.ingestion import IngestionError, parse_csv, parse_excel, parse_upload  # noqa: E402
from app.link_fetch import fetch_link  # noqa: E402


def _csv_bytes(text: str) -> bytes:
    return text.encode("utf-8")


def test_parse_csv_reviews():
    csv = "text,rating\nkain nipis cepat rosak,1\nberbaloi tebal,5\n"
    product = parse_csv(_csv_bytes(csv))
    assert len(product["reviews"]) == 2
    assert product["reviews"][0]["rating"] == 1.0


def test_parse_csv_requires_text_column():
    try:
        parse_csv(_csv_bytes("comment,stars\nhello,3\n"))
        assert False, "expected IngestionError"
    except IngestionError:
        pass


def test_parse_csv_drops_blank_rows():
    csv = "text,rating\n  ,1\nreal review tebal,5\n"
    product = parse_csv(_csv_bytes(csv))
    assert len(product["reviews"]) == 1


def test_parse_upload_rejects_unknown_type():
    try:
        parse_upload("data.txt", b"whatever")
        assert False, "expected IngestionError"
    except IngestionError:
        pass


def test_parse_sample_excel_if_present():
    # The shipped sample workbook should parse into a product with reviews + velocity.
    from pathlib import Path
    xlsx = Path(__file__).resolve().parent.parent / "app" / "data" / "sample_upload.xlsx"
    if not xlsx.exists():
        return  # generated on demand; skip if not built yet
    product = parse_excel(xlsx.read_bytes())
    assert product["reviews"]
    assert len(product["search_velocity"]) >= 6
    assert product["price"] > 0


def test_scan_upload_endpoint_with_csv():
    csv = "text,rating\nkain gila nipis cepat rosak tak berbaloi,1\nmenyesal beli rugi,1\n"
    files = {"file": ("reviews.csv", csv, "text/csv")}
    r = client.post("/api/scan-upload", files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["recommendation"] in ("KEEP", "CONSIDER", "CAUTION", "AVOID")
    assert body["defects"]["reviews_analyzed"] == 2


def test_scan_upload_bad_file_is_400():
    files = {"file": ("notes.txt", "hello", "text/plain")}
    r = client.post("/api/scan-upload", files=files)
    assert r.status_code == 400


# --------------------------- Link fetch (experimental, honest) ---------------------------
def test_link_fetch_blocks_known_platforms():
    res = fetch_link("https://shopee.com.my/product/123")
    assert res.reachable is False
    assert "upload" in res.note.lower()
    assert res.reviews == []


def test_link_fetch_rejects_non_url():
    res = fetch_link("not a url")
    assert res.reachable is False


def test_check_link_endpoint_returns_honest_note():
    r = client.post("/api/check-link", json={"url": "https://tiktok.com/shop/item/1"})
    assert r.status_code == 200
    body = r.json()
    assert body["scan"] is None
    assert body["reachable"] is False
    assert body["note"]
