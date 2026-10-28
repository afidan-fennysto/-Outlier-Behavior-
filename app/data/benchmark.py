"""Load the real 50-row Malaysian review benchmark from Sample_Data.xlsx.

WHY THIS FILE EXISTS
--------------------
The team supplied a labeled benchmark (`app/data/Sample_Data.xlsx`) with 50 Malaysian
e-commerce fashion reviews. Each row has the review text, the human label (Defect /
No Defect), the defect type, and a baseline rule prediction. This is the ground truth our
defect classifier is validated against, so the reported metrics "tally" with real data
instead of a toy set.

HONEST NOTE ON THE FILE
-----------------------
The workbook's prose summary quotes 18 Defect / 32 No Defect and a confusion matrix of
TP=14, FP=4, TN=28, FN=4. The actual data rows, however, contain 16 Defect / 34 No Defect,
and the file's own `Rule_Prediction` column yields TP=12, FP=1, TN=33, FN=4. We evaluate
against the ACTUAL rows (not the prose) and surface this discrepancy rather than hiding it.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import pandas as pd

BENCHMARK_PATH = Path(__file__).resolve().parent / "Sample_Data.xlsx"
SHEET_NAME = "de_influence_ai_50_row_benchmar"


@dataclass(frozen=True)
class BenchmarkRow:
    id: int
    text: str
    is_defect: bool            # human ground-truth label
    defect_type: str           # "" when No Defect
    rule_prediction: bool      # the file's baseline rule prediction


@lru_cache(maxsize=1)
def load_benchmark() -> List[BenchmarkRow]:
    """Read and clean the benchmark sheet (cached so we parse the file once)."""
    if not BENCHMARK_PATH.exists():
        return []
    df = pd.read_excel(BENCHMARK_PATH, sheet_name=SHEET_NAME, engine="openpyxl").fillna("")
    rows: List[BenchmarkRow] = []
    for _, r in df.iterrows():
        label = str(r["Actual_Human_Label"]).strip().lower()
        pred = str(r["Rule_Prediction"]).strip().lower()
        rows.append(BenchmarkRow(
            id=int(r["ID"]),
            text=str(r["Review_Text"]).strip(),
            is_defect=(label == "defect"),
            defect_type=str(r["Actual_Defect_Type"]).strip(),
            rule_prediction=(pred == "defect"),
        ))
    return rows


def benchmark_available() -> bool:
    return BENCHMARK_PATH.exists()
