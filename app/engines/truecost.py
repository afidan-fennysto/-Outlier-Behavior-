"""TrueCost Simulator — real-time Cost-Per-Wear.

Cost-Per-Wear (CPW) reframes a "cheap" viral item by its true cost over its usable life:

    CPW = price / expected_wears

Fast fashion is seductive because the sticker price is low, but a RM25 top that survives
3 wears costs RM8.33/wear, while a RM90 staple worn 120 times costs RM0.75/wear. This
engine estimates expected wears from the product's predicted durability and the trend's
remaining relevance, then compares it against a sustainable-staple benchmark.
"""
from __future__ import annotations

from dataclasses import dataclass


# Rough category baselines: how many wears a *well-made* item of this type can deliver.
CATEGORY_MAX_WEARS = {
    "top": 120, "tshirt": 100, "dress": 60, "outerwear": 150,
    "bottom": 130, "accessory": 200, "shoes": 180, "bag": 250,
    "default": 100,
}

# A sustainable wardrobe staple benchmark (what we reroute regret-prone users toward).
SUSTAINABLE_CPW_BENCHMARK = 0.80  # RM per wear


@dataclass
class TrueCostResult:
    price: float
    currency: str
    expected_wears: int
    cost_per_wear: float
    benchmark_cpw: float
    verdict: str                 # "excellent" | "fair" | "poor" | "waste"
    savings_vs_benchmark: float  # +ve means WORSE than a staple (money leaked per item)


def simulate_true_cost(
    price: float,
    category: str,
    quality_health: float,   # 0..100 from the defect pipeline
    hype_remaining_days: float,
    currency: str = "RM",
    hype_phase: str = "decaying",
) -> TrueCostResult:
    """Estimate Cost-Per-Wear.

    expected_wears is bounded by physical durability (quality_health) and, for items whose
    appeal is purely trend-driven, by how long the micro-trend stays wearable-without-cringe.

    The trend cap is only applied aggressively to items riding a *dying* micro-trend
    ("stale"/"decaying"). A durable wardrobe staple with steady interest is driven by its
    durability, not by a short-lived hype window — otherwise we would wrongly punish the
    exact sustainable pieces we want to steer users toward.
    """
    cat = category.lower().strip() if category else "default"
    max_wears = CATEGORY_MAX_WEARS.get(cat, CATEGORY_MAX_WEARS["default"])

    # Durability ceiling: scale max wears by material quality.
    durability_wears = max_wears * (quality_health / 100.0)

    if hype_phase in ("stale", "decaying"):
        # Trend-driven item on a fading curve: ~2 wears/week of remaining relevance,
        # with a small floor (even a dead-trend piece gets worn privately a few times).
        trend_wears = max(3.0, (hype_remaining_days / 7.0) * 2.0)
        expected_wears = max(1, int(round(min(durability_wears, trend_wears))))
    else:
        # Rising / cresting / stable interest: durability drives usable life.
        expected_wears = max(1, int(round(durability_wears)))

    cost_per_wear = round(price / expected_wears, 2)
    savings_vs_benchmark = round(cost_per_wear - SUSTAINABLE_CPW_BENCHMARK, 2)

    if cost_per_wear <= SUSTAINABLE_CPW_BENCHMARK:
        verdict = "excellent"
    elif cost_per_wear <= SUSTAINABLE_CPW_BENCHMARK * 2.5:
        verdict = "fair"
    elif cost_per_wear <= SUSTAINABLE_CPW_BENCHMARK * 6:
        verdict = "poor"
    else:
        verdict = "waste"

    return TrueCostResult(
        price=round(price, 2),
        currency=currency,
        expected_wears=expected_wears,
        cost_per_wear=cost_per_wear,
        benchmark_cpw=SUSTAINABLE_CPW_BENCHMARK,
        verdict=verdict,
        savings_vs_benchmark=savings_vs_benchmark,
    )
