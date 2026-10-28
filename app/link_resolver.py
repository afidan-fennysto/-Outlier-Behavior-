"""Emulated 'paste a link' resolver — the demo-friendly primary input.

WHY THIS FILE EXISTS
--------------------
Shoppers want to paste a Shopee / TikTok Shop URL and get an instant verdict. We cannot
legally/technically fetch those live pages (login walls, bot protection, ToS), and doing so
server-side would be an SSRF risk. So this feature EMULATES the experience safely:

  1. We NEVER fetch the URL. No outbound request is made (OWASP A10 SSRF: not applicable).
  2. We parse the URL as a plain string to detect the platform and an identifier.
  3. We look the URL up in our own SQLite catalogue (exact match on source_url).
  4. If there is no exact match, we deterministically map the URL to one of the seeded
     demo products (stable hash -> catalogue index), so the user always gets an instant,
     consistent result for a given link.

This is honest demo behaviour: the link is a KEY INTO OUR DATABASE, not a network call. The
UI labels results from an unmatched link as an emulated demo so stakeholders aren't misled.

SECURITY (OWASP)
----------------
  A10 SSRF  - no server-side request is ever made to the pasted URL.
  A03       - URL is validated with a strict scheme/host allow-list and length cap; the DB
              lookup is parameter-bound in db.py.
  A04       - stateless resolution; nothing about the URL is stored unless it already seeds a
              catalogue item.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

MAX_URL_LEN = 2048
# Platforms we recognise for the demo (host substring -> label).
KNOWN_PLATFORMS = {
    "shopee": "Shopee",
    "tiktok": "TikTok Shop",
    "shein": "Shein",
    "lazada": "Lazada",
    "zalora": "Zalora",
}


@dataclass
class ResolvedLink:
    ok: bool
    platform: str = ""
    matched: bool = False          # True when the URL exactly matched a seeded item
    note: str = ""
    product_id: Optional[str] = None


def _detect_platform(host: str) -> str:
    for key, label in KNOWN_PLATFORMS.items():
        if key in host:
            return label
    return ""


def _validate_url(url: str) -> Optional[str]:
    """Return a cleaned URL if it is a safe http(s) link, else None. No fetching."""
    if not url or len(url) > MAX_URL_LEN:
        return None
    url = url.strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return None
    if not parsed.netloc or "." not in parsed.netloc:
        return None
    # Reject anything that looks like an internal/loopback target (defence in depth,
    # even though we never make a request).
    host = parsed.netloc.lower()
    if host.startswith(("localhost", "127.", "0.", "10.", "192.168.", "169.254.")) \
       or host.endswith(".local"):
        return None
    return url


def resolve_link(url: str):
    """Resolve a pasted URL to a catalogue product. Imports db lazily to avoid cycles.

    Returns (ResolvedLink, product_dict_or_None).
    """
    from . import db

    cleaned = _validate_url(url)
    if cleaned is None:
        return ResolvedLink(ok=False, note="That doesn't look like a valid product link."), None

    host = urlparse(cleaned).netloc.lower()
    platform = _detect_platform(host)

    # 1) Exact demo-link match in the DB.
    product = db.find_by_source_url(cleaned)
    if product:
        return ResolvedLink(
            ok=True, platform=platform or product.get("platform", ""), matched=True,
            note="Matched a known demo product from the link.",
            product_id=product["id"],
        ), product

    # 2) Deterministic fallback: hash the URL -> pick a stable catalogue item.
    digest = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()
    index = int(digest[:8], 16)
    product = db.pick_product_by_index(index)
    if not product:
        return ResolvedLink(ok=False, note="No catalogue items available to analyse."), None

    plat_txt = f"{platform} " if platform else ""
    return ResolvedLink(
        ok=True, platform=platform, matched=False,
        note=(f"We can't read live {plat_txt}pages (platform restrictions), so this is an "
              f"emulated demo result mapped from your link to a representative catalogue item."),
        product_id=product["id"],
    ), product
