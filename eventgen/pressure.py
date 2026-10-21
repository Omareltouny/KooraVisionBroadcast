"""Pressure logic.

Why: pressure is the link between defensive intent and ball-carrier outcomes
(more turnovers, worse pass accuracy). Kept separate so the formula is easy to
explain and change. These are internal drivers only; derived "pressure index"
statistics belong to the Interpret stage, not here.
"""
from __future__ import annotations

from .config import Config


def pressure_probability(cfg: Config, pressing_intensity: float, zone: str, story_mult: float) -> float:
    """Chance that the defending team puts a pressure event on the ball carrier this action."""
    p = cfg.pressure
    return min(p.max_prob, p.base_prob * pressing_intensity * p.zone_factor[zone] * story_mult)


def pressure_level(cfg: Config, distance_m: float) -> float:
    """0 (far) .. 1 (touching): closer presser means harder pass and higher turnover risk."""
    lo, hi = cfg.pressure.distance_m
    return max(0.0, min(1.0, 1.0 - (distance_m - lo) / (hi - lo)))
