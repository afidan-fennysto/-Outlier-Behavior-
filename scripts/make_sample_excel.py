"""Generate a cleaned sample Excel workbook for the upload-demo flow.

Run once:  python scripts/make_sample_excel.py

Produces  app/data/sample_upload.xlsx  with two sheets:

  * "product"  - one row of product meta (name, category, price, currency) plus the
                 weekly search-velocity series spread across v1..vN columns.
  * "reviews"  - one row per review (text, rating).

This mirrors the shape of data a user would export from a review-scrape or a manual
collection, cleaned into tidy columns. It exists so judges can see the file-upload
channel working end-to-end without us scraping any live platform.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent.parent / "app" / "data" / "sample_upload.xlsx"


def build() -> None:
    # --- Product sheet: meta + a weekly search-velocity series (v1..v12) ---
    velocity = [8, 18, 44, 95, 150, 175, 130, 70, 32, 14, 7, 4]  # viral rise then crash
    product_row = {
        "name": "Viral Butterfly Halter Top (uploaded demo)",
        "category": "top",
        "price": 27.90,
        "currency": "RM",
    }
    for i, val in enumerate(velocity, start=1):
        product_row[f"v{i}"] = val
    product_df = pd.DataFrame([product_row])

    # --- Reviews sheet: realistic Malaysian code-switching reviews, already cleaned ---
    reviews = [
        ("Kain gila nipis, lepas basuh sekali terus koyak. Menyesal.", 1),
        ("Material see through dan murahan, tak berbaloi langsung", 2),
        ("Cantik di gambar tapi sampai lain dari gambar", 2),
        ("Jahitan terurai lepas dua kali pakai", 1),
        ("Ok la untuk harga ni, tapi memang nipis sikit", 3),
        ("Warna luntur lepas basuh, kecewa", 2),
        ("Lawa tapi kain panas, tak selesa pakai lama", 2),
        ("Beli untuk content je, pastu simpan dalam almari", 3),
    ]
    reviews_df = pd.DataFrame(reviews, columns=["text", "rating"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUT, engine="openpyxl") as writer:
        product_df.to_excel(writer, sheet_name="product", index=False)
        reviews_df.to_excel(writer, sheet_name="reviews", index=False)

    print(f"Wrote {OUT}")


if __name__ == "__main__":
    build()
