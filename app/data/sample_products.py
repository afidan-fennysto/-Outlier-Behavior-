"""One-time SEED data for the SQLite catalogue (NOT the runtime source of truth).

`app/db.py` reads this once on first startup to seed the `products` table, after which the
DATABASE is the single source of truth. This file is not queried at request time.

`demo_url` lets the emulated-link feature resolve a pasted Shopee/TikTok link to a specific
seeded item (string match in SQLite, no network fetch).

Each seed product carries a synthetic search-velocity series and realistic Malaysian-shopper
reviews so the app is demonstrable offline with no external keys.
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
        "source_url": "https://www.tiktok.com/shop/pdp/viral-mesh-corset-top/1729",
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
        "source_url": "https://shopee.com.my/Everyday-Heavyweight-Cotton-Tee-i.1122.3344",
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
        "source_url": "https://www.shein.com/y2k-parachute-cargo-pants-p-55667.html",
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
        "source_url": "https://www.tiktok.com/shop/pdp/coquette-fairycore-mini-dress/8842",
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

    # ---- Quality "KEEP" items across categories (so alternatives vary by category) ----
    "shopee-linen-shirt": {
        "id": "shopee-linen-shirt",
        "name": "Breathable Linen Button-Up (Everyday)",
        "category": "top",
        "price": 59.00,
        "currency": "RM",
        "platform": "Shopee",
        "colour": "white",
        "style": "casual",
        "source_url": "https://shopee.com.my/Breathable-Linen-Button-Up-i.2200.7788",
        "search_velocity": [22, 24, 25, 27, 28, 30, 31, 33, 34, 35, 36, 37],
        "reviews": [
            {"text": "Kain linen tebal dan berkualiti, sejuk dipakai. Berbaloi!", "rating": 5},
            {"text": "Jahitan kemas, tahan lama. Dah pakai banyak kali still elok.", "rating": 5},
            {"text": "Breathable and selesa untuk cuaca panas. Recommended.", "rating": 5},
            {"text": "Saiz kena, material premium untuk harga ni.", "rating": 4},
            {"text": "Good quality, tak luntur, worth it.", "rating": 5},
        ],
    },
    "shopee-denim-jacket": {
        "id": "shopee-denim-jacket",
        "name": "Heavy Denim Jacket (Wardrobe Staple)",
        "category": "outerwear",
        "price": 95.00,
        "currency": "RM",
        "platform": "Shopee",
        "colour": "blue",
        "style": "casual",
        "source_url": "https://shopee.com.my/Heavy-Denim-Jacket-i.3300.9911",
        "search_velocity": [40, 41, 42, 42, 43, 44, 45, 45, 46, 47, 48, 49],
        "reviews": [
            {"text": "Denim tebal dan kukuh, memang tahan bertahun. Berbaloi gila.", "rating": 5},
            {"text": "Jahitan kemas, zip pun smooth. Puas hati sangat.", "rating": 5},
            {"text": "Classic piece, senang match. Quality memang top.", "rating": 5},
            {"text": "Sikit berat tapi itu sebab kain dia tebal, bagus.", "rating": 4},
            {"text": "Worth every ringgit, tahan lama.", "rating": 5},
        ],
    },
    "lazada-canvas-sneakers": {
        "id": "lazada-canvas-sneakers",
        "name": "Classic Canvas Low-Top Sneakers",
        "category": "shoes",
        "price": 79.00,
        "currency": "RM",
        "platform": "Lazada",
        "colour": "white",
        "style": "casual",
        "source_url": "https://www.lazada.com.my/products/classic-canvas-sneakers-i440.html",
        "search_velocity": [50, 51, 52, 52, 53, 54, 55, 55, 56, 57, 58, 59],
        "reviews": [
            {"text": "Tapak kukuh, jahitan kemas. Selesa pakai jalan jauh.", "rating": 5},
            {"text": "Canvas tebal, tak senang rosak. Berbaloi.", "rating": 5},
            {"text": "Saiz tepat, senang match outfit. Recommended.", "rating": 4},
            {"text": "Dah pakai 6 bulan still elok, quality bagus.", "rating": 5},
            {"text": "Worth it, selesa dan tahan lama.", "rating": 5},
        ],
    },
    "shopee-tailored-trousers": {
        "id": "shopee-tailored-trousers",
        "name": "Tailored Straight-Leg Trousers",
        "category": "bottom",
        "price": 68.00,
        "currency": "RM",
        "platform": "Shopee",
        "colour": "black",
        "style": "office",
        "source_url": "https://shopee.com.my/Tailored-Straight-Leg-Trousers-i.5500.3366",
        "search_velocity": [26, 27, 28, 29, 30, 31, 31, 32, 33, 34, 35, 36],
        "reviews": [
            {"text": "Kain tebal berkualiti, jatuh cantik. Tahan lama, berbaloi.", "rating": 5},
            {"text": "Jahitan kemas, zip kukuh. Sesuai untuk kerja.", "rating": 5},
            {"text": "Saiz tepat ikut chart, selesa dipakai seharian.", "rating": 4},
            {"text": "Warna tak luntur, material premium. Puas hati.", "rating": 5},
            {"text": "Worth it, classic dan tahan.", "rating": 5},
        ],
    },
    "shopee-midi-dress": {
        "id": "shopee-midi-dress",
        "name": "Tailored Midi Work Dress",
        "category": "dress",
        "price": 72.00,
        "currency": "RM",
        "platform": "Shopee",
        "colour": "black",
        "style": "office",
        "source_url": "https://shopee.com.my/Tailored-Midi-Work-Dress-i.4400.2255",
        "search_velocity": [18, 20, 21, 23, 24, 25, 26, 27, 28, 29, 30, 31],
        "reviews": [
            {"text": "Cutting cantik dan kemas, material jatuh elok. Berbaloi.", "rating": 5},
            {"text": "Sesuai untuk kerja, kain tak jarang, selesa.", "rating": 5},
            {"text": "Quality premium, jahitan kemas. Puas hati.", "rating": 4},
            {"text": "Warna tak lari lepas basuh. Tahan lama.", "rating": 5},
            {"text": "Worth it untuk office wear.", "rating": 4},
        ],
    },

    # ---- More trend-driven "AVOID" items (so the demo has range) ----
    "tiktok-feather-top": {
        "id": "tiktok-feather-top",
        "name": "Viral Feather-Trim Party Top",
        "category": "top",
        "price": 27.90,
        "currency": "RM",
        "platform": "TikTok Shop",
        "colour": "pink",
        "style": "party",
        "source_url": "https://www.tiktok.com/shop/pdp/feather-trim-party-top/5512",
        "search_velocity": [8, 24, 70, 140, 175, 130, 70, 30, 14, 7, 4, 3],
        "reviews": [
            {"text": "Bulu feather gugur merata lepas sekali pakai. Menyesal.", "rating": 1},
            {"text": "Kain nipis, jahitan terurai bahagian ketiak.", "rating": 2},
            {"text": "Cantik untuk gambar je, tak tahan lama. Tak berbaloi.", "rating": 2},
            {"text": "Material murahan, gatal bila pakai.", "rating": 1},
            {"text": "Buang duit, pakai sekali terus simpan.", "rating": 1},
        ],
    },
    "shein-cargo-skirt": {
        "id": "shein-cargo-skirt",
        "name": "Micro Cargo Mini Skirt (Fading Hype)",
        "category": "bottom",
        "price": 33.00,
        "currency": "RM",
        "platform": "Shein",
        "colour": "khaki",
        "style": "streetwear",
        "source_url": "https://www.shein.com/micro-cargo-mini-skirt-p-77889.html",
        "search_velocity": [30, 90, 150, 120, 80, 45, 22, 12, 7, 5, 3, 2],
        "reviews": [
            {"text": "Zip rosak dalam seminggu, jahitan longgar.", "rating": 2},
            {"text": "Kain nipis dan jarang, kena pakai inner.", "rating": 2},
            {"text": "Dah tak trend, material tak berbaloi.", "rating": 1},
            {"text": "Saiz tak kena, kecil gila dari size chart.", "rating": 2},
            {"text": "Rugi beli, cepat rosak.", "rating": 1},
        ],
    },
}


def list_products() -> List[dict]:
    return list(SAMPLE_PRODUCTS.values())


def get_product(product_id: str) -> dict | None:
    return SAMPLE_PRODUCTS.get(product_id)
