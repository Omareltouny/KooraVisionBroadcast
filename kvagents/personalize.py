"""Desks: pick, rank and shape the verified narrations for each audience.

Broadcast desk: neutral voice, a lower-third line and a priority tier per moment (for a producer or a highlights editor).
Fan desk: per-fan feed in the fan's language, voiced for or against their club, with a push / feed split.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .lang import LANG
from .match_view import MatchView
from .models import Card, FactPacket, Moment, Narration

LOWER_THIRD_MAX = 70
TIER_A, TIER_B = 0.80, 0.60
MAX_PUSH = 6


@dataclass
class Profile:
    id: str
    lang: str
    follows: str | None = None      # "home" | "away" | team id | None
    push_min: float = 0.70
    feed_min: float = 0.40
    label: str = ""


DEFAULT_PROFILES = [
    Profile("fan_ar", "ar", "home", label="Arabic-speaking fan of the home club"),
    Profile("fan_es", "es", "away", label="Spanish-speaking fan of the away club"),
    Profile("fan_en", "en", None, label="Neutral English-speaking fan"),
]


def dedupe(moments: list[Moment]) -> list[Moment]:
    """A comeback moment and its goal share an event: keep the comeback (the bigger story)."""
    comeback_seq = {m.seq for m in moments if m.kind == "comeback"}
    return [m for m in moments if not (m.kind == "goal" and m.seq in comeback_seq)]


def _lookup(narrations: list[Narration]) -> dict[tuple[str, str, str], Narration]:
    return {(n.moment_id, n.lang, n.voice): n for n in narrations if n.verified and n.source in ("template", "llm")}


def _lower_third(minute: str, headline: str) -> str:
    s = f"{minute}' | {headline}"
    return s if len(s) <= LOWER_THIRD_MAX else s[: LOWER_THIRD_MAX - 1].rstrip() + "…"


def broadcast_desk(mv: MatchView, moments: list[Moment], packets: dict[str, FactPacket], narrations: list[Narration],
                   lang: str = "en") -> list[Card]:
    look = _lookup(narrations)
    cards: list[Card] = []
    for m in dedupe(moments):
        n = look.get((m.moment_id, lang, "broadcast"))
        if not n:
            continue
        tier = "A" if m.importance >= TIER_A else "B" if m.importance >= TIER_B else "C"
        cards.append(Card("broadcast", m.kind, m.moment_id, packets[m.moment_id].minute, lang, "broadcast", n.headline, n.body,
                          m.importance, push=False, lower_third=_lower_third(packets[m.moment_id].minute, n.headline),
                          source=n.source, review=LANG[lang].STATUS, tier=tier))
    return cards


def _follow_team(mv: MatchView, profile: Profile) -> str | None:
    f = profile.follows
    return mv.home if f == "home" else mv.away if f == "away" else f


def fan_desk(mv: MatchView, moments: list[Moment], packets: dict[str, FactPacket], narrations: list[Narration],
             profile: Profile) -> list[Card]:
    look = _lookup(narrations)
    fan_team = _follow_team(mv, profile)
    scored: list[tuple[float, Moment]] = []
    for m in dedupe(moments):
        p = packets[m.moment_id]
        involves = fan_team is not None and fan_team in (p.facts.get("team"), p.facts.get("opp"), p.beneficiary, m.team_id,
                                                         p.facts.get("home") if m.kind == "full_time" else None,
                                                         p.facts.get("away") if m.kind == "full_time" else None)
        score = m.importance + (0.15 if involves else 0.0) - (0.10 if (fan_team and not involves and m.kind in ("pressing_spell", "big_save", "star_performance")) else 0.0)
        if score >= profile.feed_min:
            scored.append((score, m))
    pushes = {m.moment_id for _, m in sorted(scored, key=lambda x: -x[0])[:MAX_PUSH] if _ >= profile.push_min}
    cards: list[Card] = []
    for score, m in sorted(scored, key=lambda x: (x[1].match_clock_ms, x[1].seq)):
        p = packets[m.moment_id]
        if fan_team is None or not p.beneficiary:
            voice = "fan_neutral"
        else:
            voice = "fan_for" if p.beneficiary == fan_team else "fan_against"
        n = look.get((m.moment_id, profile.lang, voice)) or look.get((m.moment_id, profile.lang, "fan_neutral"))
        if not n:
            continue
        cards.append(Card(profile.id, m.kind, m.moment_id, p.minute, profile.lang, n.voice, n.headline, n.body,
                          round(min(score, 1.0), 3), push=m.moment_id in pushes, source=n.source, review=LANG[profile.lang].STATUS))
    return cards


def profiles_from_json(items: list[dict[str, Any]]) -> list[Profile]:
    return [Profile(**i) for i in items]
