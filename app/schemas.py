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


class ScanResponse(BaseModel):
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
    caveats: List[str]


class LinkCheckRequest(BaseModel):
    url: str


class LinkCheckResponse(BaseModel):
    url: str
    reachable: bool
    extracted_name: Optional[str] = None
    extracted_price: Optional[float] = None
    note: str
    # When the fetch yields enough to analyse, we include a scan; otherwise scan is None
    # and the note explains why (keeping the prototype honest, never fabricating data).
    scan: Optional[ScanResponse] = None


class ProductSummary(BaseModel):
    id: str
    name: str
    category: str
    price: float
    currency: str
    platform: str
    image_hint: str
