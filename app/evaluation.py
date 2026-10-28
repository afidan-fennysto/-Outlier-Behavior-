"""Model validation — the metrics the judges asked to actually see.

WHY THIS FILE EXISTS
--------------------
Both judges scored "Validation & Performance" low because the pitch promised MAE and
F1 but never demonstrated them. This module computes those metrics against the REAL
50-row Malaysian review benchmark the team supplied (`app/data/Sample_Data.xlsx`), so the
numbers tally with real labeled data. The hype MAE still uses a small synthetic set of
trend curves, clearly flagged as such.

The maths here is intentionally written out by hand (no sklearn) so a human reviewer can
read and verify every step — this is a prototype, and explainability beats magic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .data.benchmark import benchmark_available, load_benchmark
from .data.labeled_dataset import HYPE_EVAL_CASES
from .engines.defect_nlp import analyze_reviews
from .engines.hype_decay import forecast_hype


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
    per_defect_type: Dict[str, Dict] = field(default_factory=dict)
    baseline_rule: Optional["ClassificationMetrics"] = None
    dataset_source: str = ""
    caveats: List[str] = field(default_factory=list)


def _model_flags_defect(text: str) -> bool:
    """Run one review through the NLP pipeline and return its yes/no defect decision."""
    result = analyze_reviews([{"text": text}])
    # defect_rate is 1.0 when the single review was flagged, 0.0 otherwise.
    return result.defect_rate >= 0.5


def _confusion(predictions: List[bool], truths: List[bool]) -> ClassificationMetrics:
    """Build a confusion matrix and the four headline metrics from it."""
    tp = fp = tn = fn = 0
    for predicted, actual in zip(predictions, truths):
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
    return ClassificationMetrics(
        precision=round(precision, 4), recall=round(recall, 4), f1_score=round(f1, 4),
        accuracy=round(accuracy, 4), true_positives=tp, false_positives=fp,
        true_negatives=tn, false_negatives=fn, n=n,
    )


def evaluate_defect_classifier() -> ClassificationMetrics:
    """F1-score for our localized defect NLP, measured on the real 50-row benchmark."""
    rows = load_benchmark()
    predictions = [_model_flags_defect(r.text) for r in rows]
    truths = [r.is_defect for r in rows]
    m = _confusion(predictions, truths)
    m.explanation = (
        f"On the {m.n}-row Malaysian benchmark our detector caught {m.true_positives} of "
        f"{m.true_positives + m.false_negatives} real defects (recall {m.recall:.0%}) and was "
        f"correct {m.precision:.0%} of the times it flagged (precision). "
        f"F1 {m.f1_score:.2f}, accuracy {m.accuracy:.0%}."
    )
    return m


def evaluate_baseline_rule() -> ClassificationMetrics:
    """The file's own baseline Rule_Prediction vs truth, for an apples-to-apples compare."""
    rows = load_benchmark()
    m = _confusion([r.rule_prediction for r in rows], [r.is_defect for r in rows])
    m.explanation = (
        f"Baseline rule in the dataset: F1 {m.f1_score:.2f}, accuracy {m.accuracy:.0%} "
        f"(TP={m.true_positives}, FP={m.false_positives}, TN={m.true_negatives}, "
        f"FN={m.false_negatives})."
    )
    return m


def evaluate_per_defect_type() -> Dict[str, Dict]:
    """Recall broken down by the four benchmark defect types, so coverage is visible."""
    rows = load_benchmark()
    buckets: Dict[str, Dict] = {}
    for r in rows:
        if not r.is_defect:
            continue
        key = r.defect_type or "Unspecified"
        bucket = buckets.setdefault(key, {"caught": 0, "total": 0})
        bucket["total"] += 1
        if _model_flags_defect(r.text):
            bucket["caught"] += 1
    for key, b in buckets.items():
        b["recall"] = round(b["caught"] / b["total"], 3) if b["total"] else 0.0
    return buckets


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
    if not benchmark_available():
        empty = ClassificationMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0,
                                      "Benchmark file not found.")
        return EvaluationReport(
            defect_classification=empty,
            hype_forecast=evaluate_hype_forecaster(),
            dataset_source="Sample_Data.xlsx (missing)",
            caveats=["Benchmark Sample_Data.xlsx was not found; defect metrics unavailable."],
        )
    return EvaluationReport(
        defect_classification=evaluate_defect_classifier(),
        hype_forecast=evaluate_hype_forecaster(),
        per_defect_type=evaluate_per_defect_type(),
        baseline_rule=evaluate_baseline_rule(),
        dataset_source="Sample_Data.xlsx (50 real Malaysian reviews)",
        caveats=[
            "Metrics come from a 50-row synthetic benchmark - not independent, real-world data.",
            "The workbook's prose says 18/32 split and TP=14 etc.; the actual rows are 16/34, "
            "so we report metrics computed from the real rows, not the summary text.",
            "No inter-annotator agreement was measured, so label noise is unquantified.",
            "The hype MAE uses synthetic trend curves; real Google Trends data will be noisier.",
        ],
    )


if __name__ == "__main__":
    # Lets a human run `python -m app.evaluation` and read the metrics directly.
    report = run_full_evaluation()
    print(f"=== Defect classifier on {report.dataset_source} ===")
    print(report.defect_classification.explanation)
    if report.baseline_rule:
        print("  " + report.baseline_rule.explanation)
    print("\n  Recall by defect type:")
    for dtype, b in report.per_defect_type.items():
        print(f"    {dtype}: {b['caught']}/{b['total']} (recall {b['recall']:.0%})")
    print("\n=== Hype forecaster (MAE) ===")
    print(report.hype_forecast.explanation)
    for c in report.hype_forecast.per_case:
        print(f"  {c['name']}: predicted {c['predicted_days']}d vs true {c['true_days']}d "
              f"(error {c['abs_error_days']}d, phase={c['phase']})")
    print("\n=== Caveats ===")
    for c in report.caveats:
        print(f"  - {c}")
