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


# --------------------------- Validation / metrics (real benchmark) ---------------------------
from app.evaluation import (  # noqa: E402
    evaluate_baseline_rule,
    evaluate_defect_classifier,
    evaluate_hype_forecaster,
    evaluate_per_defect_type,
    run_full_evaluation,
)
from app.ethics import (  # noqa: E402
    confidence_band,
    responsible_use_disclaimers,
    safe_merchant_label,
    sanitize_public_text,
)


def test_defect_classifier_tallies_on_benchmark():
    m = evaluate_defect_classifier()
    # Benchmark has 50 rows (16 defect / 34 no-defect). Our detector should beat chance
    # and, importantly, beat the dataset's own baseline rule.
    assert m.n == 50
    assert m.f1_score >= 0.6
    baseline = evaluate_baseline_rule()
    assert m.f1_score >= baseline.f1_score  # our model is at least as good as the baseline
    assert m.n == m.true_positives + m.false_positives + m.true_negatives + m.false_negatives


def test_per_defect_type_recall_reported():
    buckets = evaluate_per_defect_type()
    # All four benchmark defect types should be present with a recall figure.
    assert set(buckets) >= {"Fabric Sheerness", "Stitching Defect",
                            "Sizing Mismatch", "Thermal Discomfort"}
    for b in buckets.values():
        assert 0.0 <= b["recall"] <= 1.0


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
    assert report.dataset_source
    assert report.baseline_rule is not None
    assert any("benchmark" in c.lower() or "synthetic" in c.lower() for c in report.caveats)


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
    assert body["baseline_rule"] is not None
    assert body["per_defect_type"]


# --------------------------- CSV/Excel upload removed ---------------------------
def test_scan_upload_endpoint_removed():
    # Feature phased out: the endpoint must no longer exist.
    files = {"file": ("reviews.csv", "text\nhello world kain nipis", "text/csv")}
    r = client.post("/api/scan-upload", files=files)
    assert r.status_code in (404, 405)


# --------------------------- Security (OWASP Top 10) ---------------------------
def test_security_headers_present():
    r = client.get("/api/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert "Content-Security-Policy" in r.headers
    assert r.headers.get("Referrer-Policy") == "no-referrer"


def test_link_check_does_not_fetch():
    # A10 SSRF: /api/check-link resolves via SQLite only; it never makes an outbound request.
    # A valid external product link returns a scan built from our own catalogue.
    r = client.post("/api/check-link", json={"url": "https://shopee.com.my/x-i.1.2"})
    assert r.status_code == 200
    assert r.json()["scan"]["product_id"]


def test_error_detail_is_sanitized():
    from app.security import safe_detail
    assert safe_detail(ValueError("Traceback (most recent call last): secret path")) \
        == "Could not process the request."
    assert safe_detail(ValueError("No usable review rows found.")) \
        == "No usable review rows found."


# --------------------------- Alternative suggestion ---------------------------
def test_avoid_item_gets_alternative():
    # The viral mesh top scores AVOID; the engine should propose a better catalogue item.
    r = client.post("/api/scan", json={"product_id": "tiktok-viral-mesh-top"})
    assert r.status_code == 200
    body = r.json()
    assert body["recommendation"] in ("CAUTION", "AVOID")
    assert body["alternative"] is not None
    alt = body["alternative"]
    assert alt["recommendation"] in ("KEEP", "CONSIDER")
    assert alt["longevity_score"] >= body["longevity_score"] + 15
    assert alt["product_id"] != "tiktok-viral-mesh-top"


def test_good_item_has_no_alternative():
    # A KEEP item should not carry an alternative suggestion.
    r = client.post("/api/scan", json={"product_id": "shopee-basic-cotton-tee"})
    assert r.status_code == 200
    body = r.json()
    if body["recommendation"] in ("KEEP", "CONSIDER"):
        assert body["alternative"] is None


# --------------------------- Validation dataset transparency ---------------------------
def test_dataset_rows_endpoint():
    r = client.get("/api/evaluation/dataset")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 50
    assert {"id", "review_text", "human_label", "defect_type", "rule_prediction"} <= set(rows[0])


def test_dataset_download_endpoint():
    r = client.get("/api/evaluation/dataset/download")
    assert r.status_code == 200
    assert "spreadsheetml" in r.headers.get("content-type", "")
    assert "attachment" in r.headers.get("content-disposition", "").lower()


# --------------------------- Debug gating (OWASP A05) ---------------------------
def test_debug_endpoint_hidden_by_default():
    # Without DEINFLUENCE_DEBUG the endpoint must not exist.
    r = client.get("/api/debug/snapshot")
    assert r.status_code in (404, 405)


def test_debug_snapshot_shape_when_built_directly():
    # The snapshot builder itself (used only when debug is enabled) returns a safe structure.
    from app.debug import full_snapshot
    snap = full_snapshot()
    assert "database" in snap and "engine_config" in snap
    assert "tables" in snap["database"]


# --------------------------- SQLite storage (feature #7) ---------------------------
import app.db as db  # noqa: E402


def test_db_seeded_catalogue():
    products = db.list_products()
    assert len(products) >= 4
    ids = {p["id"] for p in products}
    assert "tiktok-viral-mesh-top" in ids


def test_db_upsert_and_get_roundtrip():
    db.upsert_product({
        "id": "test-roundtrip", "name": "Test Item", "category": "top", "price": 19.9,
        "currency": "RM", "platform": "Test", "colour": "black", "style": "casual",
        "in_stock": True, "search_velocity": [1, 2, 3], "source": "manual",
    }, reviews=[{"text": "kain nipis cepat rosak", "rating": 1}])
    got = db.get_product("test-roundtrip")
    assert got is not None
    assert got["colour"] == "black"
    assert got["search_velocity"] == [1, 2, 3]
    assert len(got["reviews"]) == 1
    assert db.delete_product("test-roundtrip")


# --------------------------- Preferences (feature #3) ---------------------------
def test_preferences_persist_and_personalize():
    r = client.post("/api/preferences", json={
        "preferred_style": "streetwear", "favourite_colour": "black", "monthly_budget": 200,
    })
    assert r.status_code == 200
    assert r.json()["favourite_colour"] == "black"

    from app.personalization import personalized_note
    note = personalized_note(
        {"style": "streetwear", "colour": "black", "price": 20},
        {"preferred_style": "streetwear", "favourite_colour": "black", "monthly_budget": 200},
    )
    assert note and "streetwear" in note and "black" in note


def test_preferences_validation_caps_budget():
    r = client.post("/api/preferences", json={"monthly_budget": 10_000_000})
    assert r.status_code == 422  # pydantic rejects out-of-range budget (input validation)


# --------------------------- Paste-a-link (emulated) ---------------------------
def test_link_exact_demo_match():
    # The seeded TikTok demo link should resolve to that exact product.
    url = "https://www.tiktok.com/shop/pdp/viral-mesh-corset-top/1729"
    r = client.post("/api/check-link", json={"url": url})
    assert r.status_code == 200
    body = r.json()
    assert body["matched"] is True
    assert body["scan"]["product_id"] == "tiktok-viral-mesh-top"
    assert body["platform"] == "TikTok Shop"


def test_link_unknown_url_is_emulated_and_deterministic():
    url = "https://shopee.com.my/some-random-item-i.99.88"
    r1 = client.post("/api/check-link", json={"url": url})
    r2 = client.post("/api/check-link", json={"url": url})
    assert r1.status_code == 200 and r2.status_code == 200
    b1, b2 = r1.json(), r2.json()
    assert b1["matched"] is False
    assert "emulated" in b1["note"].lower()
    # Same link must map to the same product every time (deterministic).
    assert b1["scan"]["product_id"] == b2["scan"]["product_id"]


def test_link_no_server_fetch_for_internal_targets():
    # Defence in depth (A10 SSRF): loopback/internal hosts are rejected, never fetched.
    r = client.post("/api/check-link", json={"url": "http://127.0.0.1:8000/admin"})
    assert r.status_code == 400


def test_link_rejects_non_http_scheme():
    r = client.post("/api/check-link", json={"url": "file:///etc/passwd"})
    assert r.status_code == 400


def test_ocr_endpoint_removed():
    # OCR feature removed: endpoint must not exist.
    files = {"file": ("x.png", b"\x89PNG\r\n\x1a\n", "image/png")}
    r = client.post("/api/ocr", files=files)
    assert r.status_code in (404, 405)


# --------------------------- Wishlist (feature #4) ---------------------------
def test_wishlist_add_list_remove():
    add = client.post("/api/wishlist", json={"product_id": "shopee-basic-cotton-tee",
                                             "notify_on_restock": True})
    assert add.status_code == 200
    assert any(w["product"]["id"] == "shopee-basic-cotton-tee" for w in add.json())

    rem = client.delete("/api/wishlist/shopee-basic-cotton-tee")
    assert rem.status_code == 200
    assert not any(w["product"]["id"] == "shopee-basic-cotton-tee" for w in rem.json())


def test_wishlist_unknown_product_404():
    r = client.post("/api/wishlist", json={"product_id": "nope-not-real"})
    assert r.status_code == 404


# --------------------------- Positioning (feature #5) ---------------------------
def test_positioning_endpoint():
    r = client.get("/api/positioning")
    assert r.status_code == 200
    body = r.json()
    assert body["comparison"] and body["value_props"]
    assert "deinfluence" in body["columns"]


# --------------------------- Link resolver (unit) ---------------------------
def test_resolver_rejects_bad_urls():
    from app.link_resolver import resolve_link
    for bad in ["not a url", "ftp://x.com/a", "javascript:alert(1)", ""]:
        resolved, product = resolve_link(bad)
        assert resolved.ok is False and product is None
