"""File ingestion - turn an uploaded CSV / Excel file into a product dict.

WHY THIS FILE EXISTS
--------------------
A real-time "check this link" scraper for Shopee / TikTok Shop is not realistic at
prototype scale (login walls, bot protection, and the very Terms-of-Service / scraping
risk we promised to respect in app/ethics.py). So the pragmatic prototype input is a
FILE UPLOAD: the user provides a cleaned CSV/Excel of a product's reviews (and optionally
its search-velocity series), and we run the exact same analysis pipeline on it.

SUPPORTED SHAPES
----------------
1. Excel (.xlsx) with two sheets:
     - "product": columns name, category, price, currency, and v1..vN search-velocity.
     - "reviews": columns text, rating.
2. CSV of reviews only: columns text[, rating]. Product meta falls back to defaults and
   the caller can override name/category/price via the request.

The parser is defensive and explainable: unknown columns are ignored, missing values get
sensible defaults, and a clear error is raised when the required 'text' column is absent.
"""
from __future__ import annotations

import io
from typing import Dict, List

import pandas as pd


class IngestionError(ValueError):
    """Raised when an uploaded file cannot be parsed into a product."""


def _clean_reviews(df: pd.DataFrame) -> List[Dict]:
    """Extract (text, rating) rows, dropping blanks."""
    cols = {c.lower().strip(): c for c in df.columns}
    if "text" not in cols:
        raise IngestionError("Reviews need a 'text' column.")
    text_col = cols["text"]
    rating_col = cols.get("rating")

    reviews: List[Dict] = []
    for _, row in df.iterrows():
        text = str(row[text_col]).strip()
        if not text or text.lower() == "nan":
            continue
        rating = None
        if rating_col is not None:
            try:
                rating = float(row[rating_col])
            except (ValueError, TypeError):
                rating = None
        reviews.append({"text": text, "rating": rating})
    if not reviews:
        raise IngestionError("No usable review rows found (every 'text' cell was empty).")
    return reviews


def _velocity_from_product_row(row: pd.Series) -> List[float]:
    """Collect v1, v2, ... columns in order into a numeric series."""
    v_cols = sorted(
        [c for c in row.index if str(c).lower().startswith("v") and str(c)[1:].isdigit()],
        key=lambda c: int(str(c)[1:]),
    )
    series: List[float] = []
    for c in v_cols:
        try:
            series.append(float(row[c]))
        except (ValueError, TypeError):
            continue
    return series


def parse_excel(data: bytes) -> Dict:
    """Parse the two-sheet Excel workbook into a product dict."""
    try:
        sheets = pd.read_excel(io.BytesIO(data), sheet_name=None, engine="openpyxl")
    except Exception as exc:  # noqa: BLE001 - surface a friendly message
        raise IngestionError(f"Could not read Excel file: {exc}") from exc

    # Case-insensitive sheet lookup.
    lower = {name.lower(): name for name in sheets}
    if "reviews" not in lower:
        raise IngestionError("Excel must contain a 'reviews' sheet.")

    reviews = _clean_reviews(sheets[lower["reviews"]])

    product: Dict = {
        "name": "Uploaded product",
        "category": "top",
        "price": 30.0,
        "currency": "RM",
        "search_velocity": [],
        "reviews": reviews,
    }

    if "product" in lower:
        pdf = sheets[lower["product"]]
        if not pdf.empty:
            prow = pdf.iloc[0]
            pcols = {c.lower().strip(): c for c in pdf.columns}
            if "name" in pcols:
                product["name"] = str(prow[pcols["name"]])
            if "category" in pcols:
                product["category"] = str(prow[pcols["category"]])
            if "currency" in pcols:
                product["currency"] = str(prow[pcols["currency"]])
            if "price" in pcols:
                try:
                    product["price"] = float(prow[pcols["price"]])
                except (ValueError, TypeError):
                    pass
            product["search_velocity"] = _velocity_from_product_row(prow)

    return product


def parse_csv(data: bytes) -> Dict:
    """Parse a reviews-only CSV into a product dict with default meta."""
    try:
        df = pd.read_csv(io.BytesIO(data))
    except Exception as exc:  # noqa: BLE001
        raise IngestionError(f"Could not read CSV file: {exc}") from exc

    reviews = _clean_reviews(df)
    return {
        "name": "Uploaded product (CSV)",
        "category": "top",
        "price": 30.0,
        "currency": "RM",
        "search_velocity": [],
        "reviews": reviews,
    }


def parse_upload(filename: str, data: bytes) -> Dict:
    """Dispatch on file extension."""
    name = (filename or "").lower()
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return parse_excel(data)
    if name.endswith(".csv"):
        return parse_csv(data)
    raise IngestionError("Unsupported file type. Upload a .xlsx or .csv file.")
