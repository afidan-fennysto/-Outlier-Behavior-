"""Market positioning — why De-Influence AI beats existing options (feature #5).

This powers the stakeholder-facing "how we compare" section. It is honest: we list real
categories of alternative and where they fall short for the specific problem (impulse fast-
fashion regret for Malaysian Gen-Z shoppers), then state our differentiators.

Kept as structured data (served via the API) so the pitch deck and the app stay in sync.
"""
from __future__ import annotations

from typing import Dict, List

# Capability matrix: how each alternative handles the jobs that matter for our problem.
# Values: "yes" | "partial" | "no".
COMPARISON: List[Dict] = [
    {
        "capability": "Localized Malaysian / code-switch defect detection",
        "deinfluence": "yes",
        "price_trackers": "no",        # e.g. generic price-history extensions
        "review_summarizers": "partial",  # generic AI review summaries (English-centric)
        "marketplace_native": "no",    # Shopee/TikTok's own ratings
    },
    {
        "capability": "Trend-decay / 'will I cringe wearing this' forecast",
        "deinfluence": "yes",
        "price_trackers": "no",
        "review_summarizers": "no",
        "marketplace_native": "no",
    },
    {
        "capability": "Cost-Per-Wear (true cost, not sticker price)",
        "deinfluence": "yes",
        "price_trackers": "partial",
        "review_summarizers": "no",
        "marketplace_native": "no",
    },
    {
        "capability": "Explainable score (shows how the number was built)",
        "deinfluence": "yes",
        "price_trackers": "no",
        "review_summarizers": "partial",
        "marketplace_native": "no",
    },
    {
        "capability": "Validated accuracy on a labeled benchmark (F1/MAE)",
        "deinfluence": "yes",
        "price_trackers": "no",
        "review_summarizers": "no",
        "marketplace_native": "no",
    },
    {
        "capability": "Privacy-first (no account, data stays on device)",
        "deinfluence": "yes",
        "price_trackers": "partial",
        "review_summarizers": "no",
        "marketplace_native": "no",
    },
    {
        "capability": "Works offline as an installable app (PWA)",
        "deinfluence": "yes",
        "price_trackers": "no",
        "review_summarizers": "no",
        "marketplace_native": "no",
    },
]

COLUMN_LABELS = {
    "deinfluence": "De-Influence AI",
    "price_trackers": "Price trackers",
    "review_summarizers": "Generic AI review tools",
    "marketplace_native": "Marketplace ratings",
}

# The investor one-liners: why this is worth buying / backing.
VALUE_PROPS: List[Dict] = [
    {
        "title": "A category of one",
        "detail": "No competitor fuses localized defect NLP, trend-decay forecasting and "
                  "cost-per-wear into a single pre-purchase regret score. Trackers only watch "
                  "price; review tools only summarize; neither predicts regret.",
    },
    {
        "title": "Defensible moat",
        "detail": "The Malaysian code-switch defect lexicon is hard to copy and improves with "
                  "every uploaded screenshot - a data flywheel generic English tools cannot match.",
    },
    {
        "title": "Trust by design",
        "detail": "Validated on a labeled benchmark (F1 ~0.91, beating the dataset baseline), "
                  "fully explainable scores, privacy-first storage, and OWASP-aligned security.",
    },
    {
        "title": "Clear monetization",
        "detail": "Freemium B2C (premium scans, wishlist alerts) plus B2B/ESG dashboards on "
                  "aggregate deceptive-listing intelligence for regulators and sustainable brands.",
    },
    {
        "title": "Low cost to run",
        "detail": "Runs on free, local components (SQLite, on-device OCR, no paid APIs required "
                  "for the core), so unit economics stay healthy from day one.",
    },
]


def market_positioning() -> Dict:
    return {
        "columns": COLUMN_LABELS,
        "comparison": COMPARISON,
        "value_props": VALUE_PROPS,
    }
