"""Model validation — the metrics the judges asked to actually see.

WHY THIS FILE EXISTS
--------------------
Both judges scored "Validation & Performance" low because the pitch promised MAE and
F1 but never demonstrated them. This module computes those two headline metrics against
the hand-labeled set in `app/data/labeled_dataset.py`, with plain-English explanations
of what each number means.

The maths here is intentionally written out by hand (no sklearn) so a human reviewer can
read and verify every step — this is a prototype, and explainability beats magic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .data.labeled_dataset import (
    DEFECT_EVAL_REVIEWS,
    HYPE_EVAL_CASES,
)
from .engines.defect_nlp import analyze_reviews
from .engines.hype_decay import forecast_hype

# A single review counts as "model says defect" when its severity clears this line.
# Matches the per-review threshold used inside the defect pipeline.
DEFECT_DECISION_THRESHOLD = 0.4


@dataclass
class ClassificationMetrics:
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    n: int
    explanation: str = ""


@dataclass
class RegressionMetrics:
    mae: float                     # mean absolute error, in days
    per_case: List[Dict] = field(default_factory=list)
    explanation: str = ""


@dataclass
class EvaluationReport:
    defect_classification: ClassificationMetrics
    hype_forecast: RegressionMetrics
    caveats: List[str] = field(default_factory=list)


def _model_flags_defect(text: str, rating: int) -> bool:
    """Run one review through the NLP pipeline and return its yes/no defect decision."""
    result = analyze_reviews([{"text": text, "rating": rating}])
    # defect_rate is 1.0 when the single review was flagged, 0.0 otherwise.
    return result.defect_rate >= 0.5


def evaluate_defect_classifier() -> ClassificationMetrics:
    """F1-score for the localized defect NLP, computed by hand from a confusion matrix.

    Precision = of the reviews we flagged, how many were real defects.
    Recall    = of the real defects, how many we caught.
    F1        = harmonic mean of the two (punishes lopsided models).
    """
    tp = fp = tn = fn = 0
    for row in DEFECT_EVAL_REVIEWS:
        predicted = _model_flags_defect(row["text"], row["rating"])
        actual = row["is_defect"]
        if predicted and actual:
            tp += 1
        elif predicted and not actual:
            fp += 1
        elif not predicted and not actual:
            tn += 1
        else:
            fn += 1

    n = tp + fp + tn + fn
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    accuracy = (tp + tn) / n if n else 0.0

    explanation = (
        f"On {n} hand-labeled reviews the defect detector caught {tp} of {tp + fn} real "
        f"defects (recall {recall:.0%}) and was correct {precision:.0%} of the times it "
        f"raised a flag (precision). F1 balances the two at {f1:.2f}."
    )

    return ClassificationMetrics(
        precision=round(precision, 3), recall=round(recall, 3), f1_score=round(f1, 3),
        accuracy=round(accuracy, 3), true_positives=tp, false_positives=fp,
        true_negatives=tn, false_negatives=fn, n=n, explanation=explanation,
    )


def evaluate_hype_forecaster() -> RegressionMetrics:
    """Mean Absolute Error (in days) between forecast and true remaining-life."""
    abs_errors: List[float] = []
    per_case: List[Dict] = []
    for case in HYPE_EVAL_CASES:
        forecast = forecast_hype(case["observed_series"])
        predicted = forecast.remaining_life_days
        truth = case["true_remaining_life_days"]
        err = abs(predicted - truth)
        abs_errors.append(err)
        per_case.append({
            "name": case["name"],
            "predicted_days": round(predicted, 1),
            "true_days": truth,
            "abs_error_days": round(err, 1),
            "phase": forecast.phase,
        })

    mae = sum(abs_errors) / len(abs_errors) if abs_errors else 0.0
    explanation = (
        f"Across {len(abs_errors)} known trend curves the remaining-life forecast was off "
        f"by {mae:.1f} days on average (MAE). Lower is better; a prototype value this size "
        f"on only {len(abs_errors)} cases is a sanity check, not a guarantee."
    )
    return RegressionMetrics(mae=round(mae, 2), per_case=per_case, explanation=explanation)


def run_full_evaluation() -> EvaluationReport:
    """Produce the complete validation report with honest caveats."""
    return EvaluationReport(
        defect_classification=evaluate_defect_classifier(),
        hype_forecast=evaluate_hype_forecaster(),
        caveats=[
            "Metrics come from a tiny, team-labeled prototype dataset - not independent annotators.",
            "No inter-annotator agreement was measured, so label noise is unquantified.",
            "Real deployment needs hundreds of independently-labeled samples before trusting these numbers.",
            "The hype MAE uses synthetic trend curves; real Google Trends data will be noisier.",
        ],
    )


if __name__ == "__main__":
    # Lets a human run `python -m app.evaluation` and read the metrics directly.
    report = run_full_evaluation()
    print("=== Defect classifier (F1) ===")
    print(report.defect_classification.explanation)
    print(f"F1={report.defect_classification.f1_score} "
          f"precision={report.defect_classification.precision} "
          f"recall={report.defect_classification.recall}")
    print("\n=== Hype forecaster (MAE) ===")
    print(report.hype_forecast.explanation)
    for c in report.hype_forecast.per_case:
        print(f"  {c['name']}: predicted {c['predicted_days']}d vs true {c['true_days']}d "
              f"(error {c['abs_error_days']}d, phase={c['phase']})")
    print("\n=== Caveats ===")
    for c in report.caveats:
        print(f"  - {c}")
