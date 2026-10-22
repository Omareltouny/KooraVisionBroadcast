"""Plain data objects passed between agents. All are JSON-serialisable with `asdict`."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

LANGS = ("en", "ar", "es")
VOICES = ("broadcast", "fan_for", "fan_against", "fan_neutral")


@dataclass
class Moment:
    """Something worth telling, found by the Interpret agent."""
    moment_id: str
    kind: str                      # goal | red_card | big_save | penalty_miss | comeback | pressing_spell | star_performance | super_sub | full_time
    seq: int                       # event the moment is anchored to (first event for windows)
    end_seq: int
    match_clock_ms: int
    period: int
    team_id: str                   # team the moment belongs to ("" for a draw)
    player_ids: list[str]
    importance: float              # 0..1
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class FactPacket:
    """Everything the Narrate agent may say about a moment: numbers, names and causes. Nothing else may be stated."""
    moment_id: str
    kind: str
    beneficiary: str               # team that gains from it; "" if neutral
    minute: str                    # display label, e.g. "67" or "45+2"
    facts: dict[str, Any]          # numbers and flags
    causes: list[str]              # cause tags in priority order
    names: dict[str, dict[str, str]]  # id -> {lang: name} for every player and team the text may mention


@dataclass
class Narration:
    moment_id: str
    lang: str
    voice: str
    headline: str
    body: str
    source: str                    # "template" | "llm_draft" (waiting for Verify) | "llm" (passed Verify)
    verified: bool = True
    rejected_llm: str = ""         # why an LLM draft was thrown away, if it was
    held_headline: str = ""        # an LLM draft that passed Verify but is held back for a native reader (see verify.held_languages)
    held_body: str = ""


@dataclass
class Card:
    """What a desk publishes for one audience member."""
    audience: str
    kind: str
    moment_id: str
    minute: str
    lang: str
    voice: str
    headline: str
    body: str
    importance: float
    push: bool = False
    lower_third: str = ""
    source: str = "template"
    review: str = ""               # translation status of the language used
    tier: str = ""                 # broadcast priority A/B/C


@dataclass
class TraceEntry:
    agent: str
    step: str
    took_ms: float
    inputs: str
    outputs: str
    notes: list[str] = field(default_factory=list)


@dataclass
class RunState:
    """Mutable state handed from agent to agent (the workflow message)."""
    match_dir: str
    moments: list[Moment] = field(default_factory=list)
    packets: list[FactPacket] = field(default_factory=list)
    narrations: list[Narration] = field(default_factory=list)
    broadcast: list[Card] = field(default_factory=list)
    fan_feeds: dict[str, list[Card]] = field(default_factory=dict)
    trace: list[TraceEntry] = field(default_factory=list)
    mode: str = "templates"


def to_dict(obj: Any) -> Any:
    return asdict(obj)
