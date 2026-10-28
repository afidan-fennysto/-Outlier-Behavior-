"""Pydantic request/response models for the De-Influence AI API."""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ReviewIn(BaseModel):
    text: str
    rating: Optional[float] = Field(default=None, ge=0, le=5)


class ProductIn(BaseModel):
    """Raw product payload for an ad-hoc scan (what a scraper would feed in)."""
    name: str
    category: str = "top"
    price: float = Field(gt=0)
    currency: str = "RM"
    search_velocity: List[float] = Field(default_factory=list)
    reviews: List[ReviewIn] = Field(default_factory=list)


class ScanRequest(BaseModel):
    """Scan either a demo-catalogue product_id OR a raw product payload."""
    product_id: Optional[str] = None
    product: Optional[ProductIn] = None


class HypeForecastOut(BaseModel):
    peak_day: float
    current_day: int
    phase: str
    decay_velocity: float
    remaining_life_days: float
    hype_health: float
    fitted_params: Dict[str, float]


class DefectOut(BaseModel):
    defect_rate: float
    severity_score: float
    quality_health: float
    category_breakdown: Dict[str, float]
    top_defects: List[Dict]
    reviews_analyzed: int
    rating_gap: float


class TrueCostOut(BaseModel):
    price: float
    currency: str
    expected_wears: int
    cost_per_wear: float
    benchmark_cpw: float
    verdict: str
    savings_vs_benchmark: float


class AlternativeOut(BaseModel):
    """A better catalogue item suggested when the scanned product is CAUTION/AVOID."""
    product_id: str
    name: str
    category: str
    price: float
    currency: str
    platform: str
    longevity_score: float
    recommendation: str
    cost_per_wear: float
    reason: str


class ScanResponse(BaseModel):
    product_id: Optional[str] = None     # set when the product lives in the DB (wishlist/compare)
    product_name: str
    category: str
    longevity_score: float
    regret_probability: float
    recommendation: str
    headline: str
    reasons: List[str]
    # Explainability (CRISPE): shows how the score was built, in plain language.
    score_breakdown: List[Dict]
    how_we_calculated: str
    # Responsible use: confidence level + disclaimers shown with every result.
    confidence: str
    disclaimers: List[str]
    # Personalization: a tailored note when the item matches the user's saved preferences.
    personalized_note: Optional[str] = None
    # A better alternative from the catalogue, shown for CAUTION/AVOID verdicts.
    alternative: Optional[AlternativeOut] = None
    hype: HypeForecastOut
    defects: DefectOut
    truecost: TrueCostOut


class ClassificationMetricsOut(BaseModel):
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    n: int
    explanation: str


class RegressionMetricsOut(BaseModel):
    mae: float
    per_case: List[Dict]
    explanation: str


class EvaluationResponse(BaseModel):
    defect_classification: ClassificationMetricsOut
    hype_forecast: RegressionMetricsOut
    # Richer validation detail so metrics clearly tally with the real benchmark.
    per_defect_type: Dict[str, Dict] = Field(default_factory=dict)
    baseline_rule: Optional[ClassificationMetricsOut] = None
    dataset_source: str = ""
    caveats: List[str]


class ProductSummary(BaseModel):
    id: str
    name: str
    category: str
    price: float
    currency: str
    platform: str
    image_hint: str
    colour: str = ""
    style: str = ""
    in_stock: bool = True


# ---- Personalization (feature #3) ----
class PreferencesIn(BaseModel):
    preferred_style: str = Field(default="", max_length=40)
    favourite_colour: str = Field(default="", max_length=40)
    monthly_budget: float = Field(default=0, ge=0, le=100000)


class PreferencesOut(BaseModel):
    preferred_style: str
    favourite_colour: str
    monthly_budget: float


# ---- Wishlist (feature #4) ----
class WishlistAddIn(BaseModel):
    product_id: str = Field(min_length=1, max_length=120)
    notify_on_restock: bool = False


class WishlistItemOut(BaseModel):
    product: ProductSummary
    notify_on_restock: bool
    in_stock: bool
    added_at: str


# ---- Paste-a-link (emulated) ----
class LinkCheckRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)


class LinkCheckResponse(BaseModel):
    platform: str
    matched: bool          # True = exact demo-link match; False = emulated/mapped result
    note: str
    scan: ScanResponse
