"""Self-contained demo catalogue so the MVP runs offline (no scraper/API keys needed).

Each product carries a synthetic search-velocity series (weekly Google-Trends-style interest)
and a small corpus of realistic Malaysian-shopper reviews mixing English and Malay slang.
In production these come from the n8n ingestion pipelines described in the roadmap.
"""
from __future__ import annotations

from typing import Dict, List


SAMPLE_PRODUCTS: Dict[str, dict] = {
    "tiktok-viral-mesh-top": {
        "id": "tiktok-viral-mesh-top",
        "name": "Viral Mesh Corset Top (TikTok Famous)",
        "category": "top",
        "price": 23.90,
        "currency": "RM",
        "platform": "TikTok Shop",
        "image_hint": "👚",
        # Classic micro-trend: explosive rise, sharp crest, now decaying fast.
        "search_velocity": [5, 9, 20, 55, 120, 180, 150, 90, 45, 22, 12, 7],
        "reviews": [
            {"text": "Kain gila nipis, lepas basuh sekali terus koyak. Menyesal beli.", "rating": 1},
            {"text": "Material sangat murahan dan see through. Tak berbaloi langsung.", "rating": 2},
            {"text": "Cantik di gambar tapi sampai lain dari gambar. Jahitan terurai.", "rating": 2},
            {"text": "Ok la for the price but memang nipis sikit", "rating": 3},
            {"text": "Broke after 2 wears, waste of money seriously", "rating": 1},
            {"text": "Nice design, pakai sekali je untuk content pastu simpan", "rating": 4},
        ],
    },
    "shopee-basic-cotton-tee": {
        "id": "shopee-basic-cotton-tee",
        "name": "Everyday Heavyweight Cotton Tee",
        "category": "tshirt",
        "price": 39.00,
        "currency": "RM",
        "platform": "Shopee",
        # Evergreen staple: slow steady interest, not a spiking micro-trend.
        "search_velocity": [30, 32, 35, 33, 36, 38, 37, 39, 40, 41, 42, 43],
        "reviews": [
            {"text": "Kain tebal dan kemas, tahan lama. Berbaloi sangat!", "rating": 5},
            {"text": "Good quality cotton, selesa dan tak luntur lepas banyak kali basuh", "rating": 5},
            {"text": "Well made, worth it. Dah beli 3 helai.", "rating": 5},
            {"text": "Saiz kena, material elok. Recommended.", "rating": 4},
            {"text": "Slightly kebesaran but quality memang best", "rating": 4},
        ],
    },
    "shein-trend-cargo": {
        "id": "shein-trend-cargo",
        "name": "Y2K Parachute Cargo Pants (Shein Hype)",
        "category": "bottom",
        "price": 55.00,
        "currency": "RM",
        "platform": "Shein",
        # Mid trend: still cresting, strong but mixed reviews.
        "search_velocity": [10, 25, 48, 80, 110, 130, 128, 120, 100, 85, 70, 60],
        "reviews": [
            {"text": "Material ok, tak nipis. Tapi zip cepat rosak sikit.", "rating": 3},
            {"text": "Trendy gila, tapi jahitan longgar kat pocket", "rating": 3},
            {"text": "Worth it for the look, saiz runs small so size up", "rating": 4},
            {"text": "Cantik and tebal, puas hati", "rating": 5},
            {"text": "Warna tanggal sikit lepas basuh but overall ok", "rating": 3},
        ],
    },
    "tiktok-fairy-dress": {
        "id": "tiktok-fairy-dress",
        "name": "Coquette Fairycore Mini Dress (Dead Trend)",
        "category": "dress",
        "price": 31.50,
        "currency": "RM",
        "platform": "TikTok Shop",
        # Already dead: trend crested long ago, interest near zero now.
        "search_velocity": [80, 160, 140, 90, 50, 25, 12, 6, 4, 3, 2, 2],
        "reviews": [
            {"text": "Dah tak trend pun. Kain panas and gatal, tak selesa.", "rating": 2},
            {"text": "Cheap material, tercabut manik lepas sekali pakai", "rating": 1},
            {"text": "Tipu, lain dari gambar. Rugi beli.", "rating": 1},
            {"text": "Lawa tapi kain nipis dan mudah rosak", "rating": 2},
            {"text": "Buang duit je, menyesal", "rating": 1},
        ],
    },
}


def list_products() -> List[dict]:
    return list(SAMPLE_PRODUCTS.values())


def get_product(product_id: str) -> dict | None:
    return SAMPLE_PRODUCTS.get(product_id)
