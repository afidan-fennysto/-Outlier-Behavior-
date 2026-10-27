"""Hype-Cycle Decay Forecaster.

Models a micro-trend's search-velocity history with a Gompertz curve and forecasts
how much "hype life" the trend has left. A trend that has already crested and is
decaying fast is a strong signal that a viral fast-fashion item will feel dated
(and regretted) quickly.

The Gompertz function:

    y(t) = a * exp(-b * exp(-c * t))

    a : asymptote (saturation level of cumulative interest)
    b : displacement along the time axis
    c : growth rate

We fit (a, b, c) to the *cumulative* search-interest series with a small, dependency-light
Levenberg-Marquardt-style least-squares routine (no scipy needed), then derive:

  * peak day        - when the instantaneous growth (derivative) is maximal (t = ln(b)/c)
  * decay velocity  - normalized rate of decline past the peak (0..1, higher = dying faster)
  * remaining life  - estimated days until interest falls below a "stale" threshold
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List

import numpy as np


@dataclass
class HypeForecast:
    peak_day: float
    current_day: int
    phase: str                      # "rising" | "cresting" | "decaying" | "stale"
    decay_velocity: float           # 0..1  (fraction of hype lost per week near now)
    remaining_life_days: float      # estimated days of relevant hype left
    hype_health: float              # 0..100  (100 = fresh/rising, 0 = dead trend)
    fitted_params: dict = field(default_factory=dict)


def _gompertz(t: np.ndarray, a: float, b: float, c: float) -> np.ndarray:
    return a * np.exp(-b * np.exp(-c * t))


def _fit_gompertz(t: np.ndarray, y: np.ndarray, iters: int = 500) -> tuple[float, float, float]:
    """Dependency-light Gompertz fit via damped Gauss-Newton (Levenberg-Marquardt).

    Returns (a, b, c). Falls back to sensible defaults if the data is degenerate.
    """
    y_max = float(np.max(y)) if y.size else 1.0
    if y_max <= 0:
        return 1.0, 1.0, 0.1

    # Initial guesses: a slightly above observed max, moderate displacement/growth.
    a = y_max * 1.05
    b = 2.0
    c = 0.15
    lam = 1e-3

    for _ in range(iters):
        pred = _gompertz(t, a, b, c)
        resid = y - pred

        inner = np.exp(-c * t)
        exp_term = np.exp(-b * inner)
        d_a = exp_term
        d_b = a * exp_term * (-inner)
        d_c = a * exp_term * (b * inner * t)

        J = np.vstack([d_a, d_b, d_c]).T          # (n, 3)
        JTJ = J.T @ J
        JTr = J.T @ resid

        # Levenberg-Marquardt damping for stability.
        A = JTJ + lam * np.eye(3)
        try:
            delta = np.linalg.solve(A, JTr)
        except np.linalg.LinAlgError:
            break

        a_n, b_n, c_n = a + delta[0], b + delta[1], c + delta[2]
        # Keep parameters in a valid region.
        a_n = max(a_n, 1e-6)
        b_n = max(b_n, 1e-6)
        c_n = min(max(c_n, 1e-4), 5.0)

        new_resid = y - _gompertz(t, a_n, b_n, c_n)
        if np.sum(new_resid ** 2) < np.sum(resid ** 2):
            a, b, c = a_n, b_n, c_n
            lam = max(lam * 0.7, 1e-9)
        else:
            lam = min(lam * 2.5, 1e6)

    return float(a), float(b), float(c)


def forecast_hype(search_velocity: List[float], stale_fraction: float = 0.25) -> HypeForecast:
    """Fit the hype curve and derive forecast metrics.

    Parameters
    ----------
    search_velocity:
        Per-period (e.g. weekly) search-interest values, oldest first. Represents how
        much the micro-trend is being searched for over time.
    stale_fraction:
        Fraction of the asymptote below which a trend is considered "stale/dead".
    """
    v = np.asarray(search_velocity, dtype=float)
    if v.size < 3:
        # Not enough history to model a cycle — treat as unknown/neutral.
        return HypeForecast(
            peak_day=float(v.size),
            current_day=int(v.size),
            phase="rising" if v.size and v[-1] >= (v[0] if v.size else 0) else "unknown",
            decay_velocity=0.0,
            remaining_life_days=30.0,
            hype_health=55.0,
            fitted_params={},
        )

    t = np.arange(v.size, dtype=float)
    # Gompertz describes cumulative adoption; integrate the velocity to get it.
    cumulative = np.cumsum(v)

    a, b, c = _fit_gompertz(t, cumulative)

    # Peak of the *instantaneous* curve (derivative max) is at t = ln(b)/c.
    peak_day = math.log(b) / c if b > 1 else 0.0
    current_day = v.size - 1

    # Decay velocity: compare recent instantaneous interest to the peak.
    dense_t = np.linspace(0, max(v.size * 2, peak_day + v.size), 400)
    inst = a * b * c * np.exp(-c * dense_t) * np.exp(-b * np.exp(-c * dense_t))
    peak_inst = float(np.max(inst)) if inst.size else 1.0
    peak_inst = peak_inst if peak_inst > 0 else 1.0

    now_inst = float(a * b * c * math.exp(-c * current_day) * math.exp(-b * math.exp(-c * current_day)))
    ratio_now = now_inst / peak_inst

    # Short horizon slope (next ~2 weeks) normalized -> decay velocity.
    future = current_day + 2
    fut_inst = float(a * b * c * math.exp(-c * future) * math.exp(-b * math.exp(-c * future)))
    decay_velocity = max(0.0, (now_inst - fut_inst) / peak_inst)
    decay_velocity = min(decay_velocity, 1.0)

    # Recent *raw* trajectory. The Gompertz derivative can read as "past peak" for a
    # steadily-climbing series (saturation assumption), so we cross-check against the
    # actual tail slope: a series whose last observations are still rising is NOT decaying.
    tail = v[-min(4, v.size):]
    tail_slope = float(tail[-1] - tail[0]) / max(1, tail.size - 1)
    recent_mean = float(np.mean(tail))
    rising_now = tail_slope > 0 and tail[-1] >= recent_mean

    # Phase classification.
    if rising_now and ratio_now > stale_fraction:
        # Raw interest is still climbing — treat as live, not decaying.
        phase = "rising" if current_day < peak_day + 1.0 else "cresting"
    elif current_day < peak_day - 0.5:
        phase = "rising"
    elif current_day <= peak_day + 1.0:
        phase = "cresting"
    elif ratio_now > stale_fraction:
        phase = "decaying"
    else:
        phase = "stale"

    # Remaining life: days until instantaneous interest drops below stale threshold.
    threshold = stale_fraction * peak_inst
    remaining_life_days = 0.0
    for dt in np.arange(0, 180, 1.0):
        tt = current_day + dt
        val = a * b * c * math.exp(-c * tt) * math.exp(-b * math.exp(-c * tt))
        if val < threshold:
            remaining_life_days = float(dt)
            break
    else:
        remaining_life_days = 180.0
    if phase in ("rising", "cresting"):
        # Still climbing/at the top — plenty of relevance left.
        remaining_life_days = max(remaining_life_days, 45.0)

    # Hype health: fresh rising trends score high; dead ones score low.
    hype_health = float(np.clip(ratio_now * 100.0, 0.0, 100.0))
    if phase == "rising":
        hype_health = max(hype_health, 70.0)

    return HypeForecast(
        peak_day=round(peak_day, 2),
        current_day=current_day,
        phase=phase,
        decay_velocity=round(decay_velocity, 3),
        remaining_life_days=round(remaining_life_days, 1),
        hype_health=round(hype_health, 1),
        fitted_params={"a": round(a, 3), "b": round(b, 3), "c": round(c, 4)},
    )
