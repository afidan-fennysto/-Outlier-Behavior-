"""Personalization — tailor the verdict to the user's saved preferences (feature #3).

The user can save a preferred style, favourite colour, and monthly budget. When a scanned
product matches those, we add a short, plain-language note. This is intentionally simple and
transparent (prototype): it never overrides the objective score, it only adds context so the
recommendation feels personal.

PRIVACY: preferences are a single local record in SQLite (no account, no sharing).
"""
from __future__ import annotations

from typing import Dict, Optional


def personalized_note(product: Dict, preferences: Dict) -> Optional[str]:
    """Return a tailored note, or None when there is nothing personal to say."""
    style = (preferences.get("preferred_style") or "").strip().lower()
    colour = (preferences.get("favourite_colour") or "").strip().lower()
    budget = float(preferences.get("monthly_budget") or 0)

    p_style = (product.get("style") or "").strip().lower()
    p_colour = (product.get("colour") or "").strip().lower()
    price = float(product.get("price") or 0)

    notes = []
    if style and p_style and style == p_style:
        notes.append(f"matches your preferred {style} style")
    if colour and p_colour and colour == p_colour:
        notes.append(f"comes in your favourite colour ({colour})")
    if budget > 0 and price > 0:
        if price <= budget * 0.15:
            notes.append(f"is an easy fit for your RM{budget:.0f} monthly budget")
        elif price > budget * 0.5:
            notes.append(
                f"would use over half your RM{budget:.0f} monthly budget - worth pausing on"
            )

    if not notes:
        return None
    return "For you: this item " + "; ".join(notes) + "."
