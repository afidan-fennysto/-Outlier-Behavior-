"""Experimental 'check an item from a link' fetcher.

HONEST FEASIBILITY NOTE (read this before trusting it)
------------------------------------------------------
The original idea was a Chrome extension that reads the item ON the Shopee / TikTok Shop
page. At prototype scale a server-side scraper of those sites is NOT reliable: they are
single-page apps behind login walls and bot protection, their review data loads via
authenticated internal APIs, and scraping them violates their Terms of Service (the exact
risk we committed to respecting in app/ethics.py).

So this module does a DELIBERATELY LIMITED, best-effort fetch of a PUBLIC url:
  * It pulls visible text and any JSON-LD product metadata (price / name).
  * It does NOT bypass logins, execute JavaScript, or hit private review APIs.
  * For Shopee / TikTok Shop it will usually find little or nothing - and it says so,
    then points the user to the file-upload flow instead of inventing data.

This keeps the prototype honest: we show the mechanism, flag the limitation, and never
fabricate reviews just to fill the screen.
"""
from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, List, Optional

USER_AGENT = "Mozilla/5.0 (compatible; DeInfluenceAI-prototype/0.1; +research)"
TIMEOUT_SECONDS = 8
BLOCKED_HINTS = ("shopee.", "tiktok.com", "shein.")


@dataclass
class LinkFetchResult:
    url: str
    reachable: bool
    extracted_name: Optional[str] = None
    extracted_price: Optional[float] = None
    reviews: List[Dict] = field(default_factory=list)
    note: str = ""


def _extract_jsonld(html: str) -> Dict:
    """Pull the first JSON-LD product block, if present."""
    for match in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, flags=re.DOTALL | re.IGNORECASE,
    ):
        try:
            data = json.loads(match.strip())
        except json.JSONDecodeError:
            continue
        candidates = data if isinstance(data, list) else [data]
        for obj in candidates:
            if isinstance(obj, dict) and "name" in obj:
                return obj
    return {}


def _price_from_jsonld(obj: Dict) -> Optional[float]:
    offers = obj.get("offers")
    if isinstance(offers, dict):
        price = offers.get("price")
    elif isinstance(offers, list) and offers:
        price = offers[0].get("price")
    else:
        price = obj.get("price")
    try:
        return float(price) if price is not None else None
    except (ValueError, TypeError):
        return None


def fetch_link(url: str) -> LinkFetchResult:
    """Best-effort public fetch. Never fabricates data; explains what it could not get."""
    if not re.match(r"^https?://", url, flags=re.IGNORECASE):
        return LinkFetchResult(url=url, reachable=False,
                               note="Not a valid http(s) URL.")

    # Be upfront about the platforms we know we cannot meaningfully read server-side.
    if any(h in url.lower() for h in BLOCKED_HINTS):
        return LinkFetchResult(
            url=url, reachable=False,
            note=("This platform renders products in-app behind login/bot protection, so a "
                  "server-side read is not reliable and would breach their terms. Use the "
                  "file-upload option with an exported review sheet instead."),
        )

    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            html = resp.read(1_000_000).decode(charset, errors="replace")
    except Exception as exc:  # noqa: BLE001
        return LinkFetchResult(url=url, reachable=False,
                               note=f"Could not fetch the page ({exc}).")

    obj = _extract_jsonld(html)
    name = obj.get("name") if obj else None
    price = _price_from_jsonld(obj) if obj else None

    note = ("Fetched public page metadata. Review text is not available from a public "
            "fetch, so run the analysis with an uploaded review sheet for real results.")
    return LinkFetchResult(
        url=url, reachable=True, extracted_name=name, extracted_price=price,
        reviews=[], note=note,
    )
