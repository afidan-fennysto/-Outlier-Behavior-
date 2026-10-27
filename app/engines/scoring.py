"""Scoring fusion — the dual-signal analytical engine.

Fuses the three engine outputs into the two headline numbers from the pitch:

  * Product Longevity Score (0-100)  — higher = more durable / worth keeping
  * Regret Probability (0-100)       — likelihood the buyer regrets this impulse purchase

Signal weighting reflects the pitch's thesis that *fused* macro hype-decay + localized
defect sentiment beats either signal alone.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .defect_nlp import DefectAnalysis
from .hype_decay import HypeForecast
from .truecost import TrueCostResult


# Longevity = how durable + how long the thing stays relevant.
W_QUALITY = 0.55   # physical durability (defect pipeline)
W_HYPE = 0.25      # trend relevance (hype forecaster)
W_VALUE = 0.20     # cost-per-wear value

RECOMMENDATION_BANDS = [
    (75, "KEEP", "Solid longevity and value. Safe to buy."),
    (55, "CONSIDER", "Mixed signals — buy only if you truly need it."),
    (35, "CAUTION", "Weak durability or fading trend. Sleep on it."),
    (0,  "AVOID", "High-regret impulse buy. Walk away."),
]


@dataclass
class ProductVerdict:
    longevity_score: float        # 0..100
    regret_probability: float     # 0..100
    recommendation: str           # KEEP | CONSIDER | CAUTION | AVOID
    headline: str
    reasons: List[str] = field(default_factory=list)
    # Transparency: shows exactly how much each signal contributed to the longevity score.
    # Addresses the critique that the score "fuses hype with garment quality" opaquely —
    # now a human can see the split instead of trusting one blended number.
    score_breakdown: List[dict] = field(default_factory=list)
    how_we_calculated: str = ""


def _value_health(truecost: TrueCostResult) -> float:
    """Map cost-per-wear to a 0..100 value-health score."""
    ratio = truecost.cost_per_wear / truecost.benchmark_cpw if truecost.benchmark_cpw else 10.0
    # ratio 1.0 -> ~90 ; ratio 6 -> ~20 ; ratio >=10 -> ~5
    return float(max(5.0, min(100.0, 100.0 - (ratio - 1.0) * 14.0)))


def fuse(
    defects: DefectAnalysis,
    hype: HypeForecast,
    truecost: TrueCostResult,
) -> ProductVerdict:
    value_health = _value_health(truecost)

    # Each signal contributes (weight x its 0-100 health). We keep the three parts separate
    # so the final number is explainable rather than a black box.
    quality_contribution = W_QUALITY * defects.quality_health
    hype_contribution = W_HYPE * hype.hype_health
    value_contribution = W_VALUE * value_health

    longevity_score = quality_contribution + hype_contribution + value_contribution
    longevity_score = round(float(max(0.0, min(100.0, longevity_score))), 1)

    score_breakdown = [
        {"signal": "Garment quality (defect NLP)", "weight": W_QUALITY,
         "health": round(defects.quality_health, 1), "points": round(quality_contribution, 1)},
        {"signal": "Trend relevance (hype decay)", "weight": W_HYPE,
         "health": round(hype.hype_health, 1), "points": round(hype_contribution, 1)},
        {"signal": "Value (cost-per-wear)", "weight": W_VALUE,
         "health": round(value_health, 1), "points": round(value_contribution, 1)},
    ]
    how_we_calculated = (
        f"Longevity {longevity_score}/100 = "
        f"{quality_contribution:.1f} from quality (55% weight) + "
        f"{hype_contribution:.1f} from trend relevance (25%) + "
        f"{value_contribution:.1f} from value (20%). "
        "Quality is weighted highest because a durable item survives a fading trend, "
        "but a fading trend alone does not make a well-made item worthless."
    )

    # Regret probability: driven by defects, fading hype, poor value, and deceptive stars.
    regret = (
        0.40 * (100.0 - defects.quality_health)
        + 0.22 * (100.0 - hype.hype_health)
        + 0.23 * (100.0 - value_health)
        + 0.15 * (defects.severity_score)
    )
    # Deceptive 5-star listings (NLP finds more problems than stars admit) raise regret.
    if defects.rating_gap > 0.1:
        regret += min(15.0, defects.rating_gap * 40.0)
    # A stale / fast-decaying trend amplifies regret (buy-and-cringe risk).
    if hype.phase == "stale":
        regret += 8.0
    regret += hype.decay_velocity * 10.0

    regret_probability = round(float(max(0.0, min(100.0, regret))), 1)

    recommendation, headline = "AVOID", RECOMMENDATION_BANDS[-1][2]
    for threshold, label, note in RECOMMENDATION_BANDS:
        if longevity_score >= threshold and regret_probability <= (100 - threshold + 25):
            recommendation, headline = label, note
            break
    else:
        recommendation, headline = RECOMMENDATION_BANDS[-1][1], RECOMMENDATION_BANDS[-1][2]

    reasons: List[str] = []
    if defects.quality_health < 50:
        top = defects.top_defects[0]["phrase"] if defects.top_defects else "material complaints"
        reasons.append(f"Reviews flag durability/material issues (e.g. \"{top}\").")
    if hype.phase in ("decaying", "stale"):
        reasons.append(
            f"Trend is {hype.phase}; ~{hype.remaining_life_days:.0f} days of relevance left."
        )
    if truecost.verdict in ("poor", "waste"):
        reasons.append(
            f"Cost-Per-Wear is {truecost.currency}{truecost.cost_per_wear:.2f} "
            f"vs {truecost.currency}{truecost.benchmark_cpw:.2f} benchmark."
        )
    if defects.rating_gap > 0.1:
        reasons.append("Star rating looks inflated — NLP finds more problems than the stars admit.")
    if not reasons:
        reasons.append("No major red flags detected across durability, trend, and value signals.")

    return ProductVerdict(
        longevity_score=longevity_score,
        regret_probability=regret_probability,
        recommendation=recommendation,
        headline=headline,
        reasons=reasons,
        score_breakdown=score_breakdown,
        how_we_calculated=how_we_calculated,
    )
