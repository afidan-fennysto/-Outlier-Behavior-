"""Localized NLP Defect Pipeline.

Extracts *defect signals* from e-commerce reviews — going beyond the noise of a 5-star
rating. The differentiator (from the pitch's Unfair Advantages) is a localized Malaysian
lexicon that understands colloquial, code-switching slang used by real Shopee / TikTok Shop
shoppers: "kain nipis", "gila nipis", "tak berbaloi", "cepat rosak", "kain panas", etc.

This is a transparent, explainable lexicon + rule layer (the MVP baseline that the roadmap
later upgrades into a fine-tuned transformer). Each review is scored for defect severity
across durability, material-quality, sizing, and value categories, with Malay-English
negation and intensifier handling.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List


# ---------------------------------------------------------------------------
# Localized defect lexicon. weight = severity contribution (0..1 scale per hit).
# Terms are matched on normalized text (lowercased, accent-stripped).
# ---------------------------------------------------------------------------
DEFECT_LEXICON: Dict[str, List[tuple[str, float]]] = {
    # Durability / stitching failures (benchmark type: "Stitching Defect").
    "durability": [
        ("cepat rosak", 0.9), ("mudah rosak", 0.9), ("rosak", 0.6),
        ("koyak", 0.85), ("tercabut", 0.8), ("terburai", 0.85), ("terurai", 0.8),
        ("jahitan terurai", 0.9), ("jahitan terbuka", 0.9), ("jahitan senget", 0.85),
        ("benang terkeluar", 0.85), ("loose thread", 0.8), ("poor stitching", 0.85),
        ("longgar", 0.5), ("patah", 0.8),
        ("broke after", 0.95), ("fell apart", 0.95), ("ripped", 0.85),
        ("tore", 0.85), ("stitching came", 0.9), ("came undone", 0.8),
        ("stopped working", 0.8), ("after 2 wears", 0.9), ("after one wash", 0.9),
        ("luntur", 0.7), ("faded", 0.7), ("color bleed", 0.75), ("warna tanggal", 0.75),
    ],
    # Material quality + sheerness (benchmark type: "Fabric Sheerness").
    "material": [
        ("kain nipis", 0.85), ("gila nipis", 0.9), ("nipis", 0.6),
        ("kain jarang", 0.8), ("jarang", 0.55), ("nampak inner", 0.85),
        ("nampak bra", 0.85), ("transparent", 0.8), ("see through", 0.8),
        ("see-through", 0.8), ("tak breathable", 0.75),
        ("murahan", 0.7), ("kualiti rendah", 0.8), ("kualiti teruk", 0.85),
        ("quality teruk", 0.85), ("cheap material", 0.8), ("thin material", 0.8),
        ("kasar", 0.5), ("gatal", 0.55), ("itchy", 0.55),
        ("plastik", 0.6), ("macam plastik", 0.75), ("flimsy", 0.8), ("feels cheap", 0.8),
    ],
    # Sizing / fit (benchmark type: "Sizing Mismatch").
    "sizing": [
        ("tak muat", 0.6), ("ketat", 0.6), ("sempit", 0.5), ("kebesaran", 0.5),
        ("kekecilan", 0.6), ("saiz tak kena", 0.6), ("tak ngam", 0.6),
        ("cutting kecil", 0.7), ("kecil gila", 0.75), ("terlalu kecil", 0.7),
        ("fit macam", 0.6), ("tak ikut size chart", 0.75), ("cannot wear", 0.7),
        ("too small", 0.5), ("too big", 0.5), ("runs small", 0.6), ("sizing off", 0.6),
        ("kecut", 0.7), ("shrunk", 0.75), ("mengecut", 0.7),
    ],
    # Thermal comfort (benchmark type: "Thermal Discomfort").
    "thermal": [
        ("kain panas", 0.7), ("material panas", 0.75), ("panas sangat", 0.8),
        ("panas gila", 0.8), ("memerangkap haba", 0.8),
        ("tak serap peluh", 0.75), ("melekit", 0.7), ("rimas", 0.65),
        ("not breathable", 0.75),
    ],
    # Value / regret language.
    "value": [
        ("tak berbaloi", 0.85), ("x berbaloi", 0.85), ("rugi", 0.75),
        ("menyesal", 0.8), ("regret", 0.8), ("waste of money", 0.9),
        ("buang duit", 0.85), ("tak worth", 0.8), ("not worth", 0.8),
        ("tak puas hati", 0.7), ("tipu", 0.8), ("scam", 0.9),
        ("menipu", 0.85), ("different from picture", 0.7),
        ("lain dari gambar", 0.7), ("tak sama gambar", 0.7),
    ],
}

# Positive terms let us avoid flagging genuinely-good products and handle contrast.
POSITIVE_TERMS = [
    "berbaloi", "worth it", "tebal", "kemas", "elok", "cantik", "tahan lama",
    "durable", "good quality", "kualiti baik", "best", "puas hati", "recommended",
    "soft", "selesa", "comfortable", "well made", "sturdy",
]

NEGATORS = {"tak", "tidak", "bukan", "not", "no", "never", "x", "xde", "takde"}
INTENSIFIERS = {"gila": 1.4, "sangat": 1.3, "amat": 1.3, "super": 1.3, "very": 1.3,
                "really": 1.2, "betul": 1.2, "memang": 1.2, "terlalu": 1.3, "sgt": 1.3}


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _intensifier_near(tokens: List[str], idx: int, window: int = 2) -> float:
    mult = 1.0
    for j in range(max(0, idx - window), idx):
        mult = max(mult, INTENSIFIERS.get(tokens[j], 1.0))
    return mult


def _negated(tokens: List[str], start_idx: int, window: int = 3) -> bool:
    for j in range(max(0, start_idx - window), start_idx):
        if tokens[j] in NEGATORS:
            return True
    return False


@dataclass
class DefectAnalysis:
    defect_rate: float                       # 0..1  fraction of reviews with a real defect
    severity_score: float                    # 0..100  weighted defect severity (higher = worse)
    quality_health: float                    # 0..100  (100 = clean, 0 = heavily defective)
    category_breakdown: Dict[str, float] = field(default_factory=dict)
    top_defects: List[Dict] = field(default_factory=list)
    reviews_analyzed: int = 0
    rating_gap: float = 0.0                  # star-sentiment divergence (deceptive 5-star signal)


def analyze_reviews(reviews: List[Dict]) -> DefectAnalysis:
    """Analyze a list of reviews.

    Each review is a dict: {"text": str, "rating": optional int 1..5}.
    """
    if not reviews:
        return DefectAnalysis(
            defect_rate=0.0, severity_score=0.0, quality_health=60.0,
            category_breakdown={k: 0.0 for k in DEFECT_LEXICON},
            top_defects=[], reviews_analyzed=0, rating_gap=0.0,
        )

    category_totals: Dict[str, float] = {k: 0.0 for k in DEFECT_LEXICON}
    phrase_counter: Counter = Counter()
    phrase_category: Dict[str, str] = {}
    defective_reviews = 0
    star_based_bad = 0           # reviews whose stars (<=2) say "bad"
    sentiment_based_bad = 0      # reviews our NLP flags as defective

    for review in reviews:
        text = _normalize(str(review.get("text", "")))
        if not text:
            continue
        tokens = text.split()
        review_defect = 0.0

        for category, terms in DEFECT_LEXICON.items():
            for phrase, weight in terms:
                if phrase not in text:
                    continue
                idx = text.find(phrase)
                token_idx = len(text[:idx].split())
                if _negated(tokens, token_idx):
                    # "tak nipis" / "not cheap" -> defect negated.
                    continue
                mult = _intensifier_near(tokens, token_idx)
                hit = min(weight * mult, 1.0)
                category_totals[category] += hit
                review_defect = max(review_defect, hit)
                phrase_counter[phrase] += 1
                phrase_category[phrase] = category

        # Positive-term dampening: a strongly positive review softens a weak flag.
        pos_hits = sum(1 for p in POSITIVE_TERMS if p in text and not _negated(tokens, len(text[:text.find(p)].split())))
        if pos_hits and review_defect < 0.6:
            review_defect *= 0.5

        if review_defect >= 0.4:
            defective_reviews += 1
            sentiment_based_bad += 1

        rating = review.get("rating")
        if isinstance(rating, (int, float)) and rating <= 2:
            star_based_bad += 1

    n = len([r for r in reviews if str(r.get("text", "")).strip()])
    n = max(n, 1)

    defect_rate = defective_reviews / n
    total_severity = sum(category_totals.values())
    # Normalize severity to 0..100 against review count (saturating).
    severity_score = float(min(100.0, (total_severity / n) * 55.0))

    quality_health = float(max(0.0, 100.0 - severity_score - defect_rate * 25.0))
    quality_health = round(min(quality_health, 100.0), 1)

    category_breakdown = {
        k: round(min(100.0, (v / n) * 70.0), 1) for k, v in category_totals.items()
    }

    top_defects = [
        {"phrase": p, "category": phrase_category[p], "mentions": c}
        for p, c in phrase_counter.most_common(6)
    ]

    # Rating gap: deceptive 5-star signal. If our NLP finds many more problems than the
    # star ratings suggest, the listing's stars are likely inflated/gamed.
    rating_gap = round((sentiment_based_bad - star_based_bad) / n, 3)

    return DefectAnalysis(
        defect_rate=round(defect_rate, 3),
        severity_score=round(severity_score, 1),
        quality_health=quality_health,
        category_breakdown=category_breakdown,
        top_defects=top_defects,
        reviews_analyzed=n,
        rating_gap=rating_gap,
    )
