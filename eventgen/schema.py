"""Single source of truth for all data shapes (pydantic v2).

Why: every stage of the hackathon pipeline reads these files, so the shapes
are defined once here and exported as JSON Schema for other agents.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

GENERATOR_VERSION = "1.1.0"

Position = Literal["GK", "CB", "FB", "DM", "CM", "AM", "W", "ST"]
Direction = Literal["left_to_right", "right_to_left"]
BodyPart = Literal["right_foot", "left_foot", "head", "hands"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------- teams
class Player(Strict):
    player_id: str
    name: str
    name_i18n: dict[str, str]
    jersey_number: int = Field(ge=1, le=99)
    position: Position
    starter: bool
    bio_tags: list[str]


class Team(Strict):
    team_id: str
    name: str
    name_i18n: dict[str, str]
    short_name: str
    primary_color: str
    secondary_color: str
    formation: str
    players: list[Player]


class TeamsFile(Strict):
    match_id: str
    teams: list[Team]


# ---------------------------------------------------------------- match
class PeriodMeta(Strict):
    period: int
    start_match_clock_ms: int
    end_match_clock_ms: int
    scheduled_duration_ms: int
    stoppage_ms: int
    attacking_direction: dict[str, Direction]  # team_id -> direction (fixed pitch frame)


class Score(Strict):
    home: int
    away: int


class MatchMeta(Strict):
    match_id: str
    competition: str
    season: str
    matchday: int
    kickoff_utc: str
    venue: str
    home_team_id: str
    away_team_id: str
    seed: int
    generator_version: str
    periods: list[PeriodMeta]
    final_score: Score


# --------------------------------------------------------------- events
class EventBase(Strict):
    event_id: str
    match_id: str
    seq: int = Field(ge=1)
    period: int = Field(ge=1, le=2)
    clock_ms: int = Field(ge=0)
    match_clock_ms: int = Field(ge=0)
    type: str
    team_id: str
    player_id: str
    x: float
    y: float
    possession_id: int
    score_home: int
    score_away: int


class _PassLike(EventBase):
    end_x: float
    end_y: float
    receiver_id: str | None
    outcome: Literal["complete", "incomplete", "intercepted", "out"]
    ball_speed_ms: float
    pass_length_m: float
    body_part: BodyPart


class _ShotLike(EventBase):
    end_x: float
    end_y: float
    outcome: Literal["goal", "saved", "off_target", "blocked", "post"]
    shot_speed_ms: float
    body_part: BodyPart
    assist_event_id: str | None


class PassEvent(_PassLike):
    type: Literal["pass"]


class ThrowInEvent(_PassLike):
    type: Literal["throw_in"]


class CornerEvent(_PassLike):
    type: Literal["corner"]


class FreeKickEvent(_PassLike):
    type: Literal["free_kick"]


class GoalKickEvent(_PassLike):
    type: Literal["goal_kick"]


class SaveEvent(EventBase):
    """Goalkeeper stops an on-target shot. `team_id` is the keeper's team."""
    type: Literal["save"]
    shot_event_id: str
    outcome: Literal["caught", "parried", "tipped"]


class ShotEvent(_ShotLike):
    type: Literal["shot"]


class PenaltyEvent(_ShotLike):
    type: Literal["penalty"]


class TackleEvent(EventBase):
    type: Literal["tackle"]
    opponent_id: str
    outcome: Literal["won", "lost"]


class PossessionChangeEvent(EventBase):
    type: Literal["possession_change"]
    from_team_id: str
    to_team_id: str
    reason: Literal["tackle", "interception", "out_of_play", "foul", "shot_result", "miscontrol"]


class PressureEvent(EventBase):
    type: Literal["pressure"]
    pressed_player_id: str
    distance_m: float
    duration_ms: int


class FoulEvent(EventBase):
    type: Literal["foul"]
    fouled_player_id: str
    card: Literal["yellow", "red"] | None


class CardEvent(EventBase):
    type: Literal["card"]
    color: Literal["yellow", "red"]
    reason: str


class SubstitutionEvent(EventBase):
    type: Literal["substitution"]
    player_off_id: str
    player_on_id: str


class PeriodStartEvent(EventBase):
    type: Literal["period_start"]


class PeriodEndEvent(EventBase):
    type: Literal["period_end"]


Event = Annotated[
    Union[
        PassEvent, ThrowInEvent, CornerEvent, FreeKickEvent, GoalKickEvent, ShotEvent, PenaltyEvent, SaveEvent,
        TackleEvent, PossessionChangeEvent, PressureEvent, FoulEvent, CardEvent,
        SubstitutionEvent, PeriodStartEvent, PeriodEndEvent,
    ],
    Field(discriminator="type"),
]
EVENT_ADAPTER: TypeAdapter[Any] = TypeAdapter(Event)
EVENTS_ADAPTER: TypeAdapter[Any] = TypeAdapter(list[Event])

PASS_LIKE = ("pass", "throw_in", "corner", "free_kick", "goal_kick")
SHOT_LIKE = ("shot", "penalty")
OWNER_ACTIONS = PASS_LIKE + SHOT_LIKE


# --------------------------------------------------------- ground truth
class StoryTruth(Strict):
    story_id: str
    type: str
    start_seq: int
    end_seq: int
    team_id: str
    players_involved: list[str]
    description: str
    strength: float
    window_start_ms: int
    window_end_ms: int
    details: dict[str, Any]


class TeamStats(Strict):
    goals: int
    shots: int
    shots_on_target: int
    passes: int
    passes_complete: int
    pass_completion: float
    possession_pct: float
    tackles: int
    tackles_won: int
    pressures: int
    fouls: int
    yellow_cards: int
    red_cards: int
    corners: int
    goal_kicks: int
    saves: int
    throw_ins: int
    free_kicks: int
    penalties: int
    substitutions: int
    turnovers_won: int


class GroundTruth(Strict):
    match_id: str
    generator_version: str
    seed: int
    generation_attempt: int
    note: str
    stories: list[StoryTruth]
    unrealized_stories: list[dict[str, Any]]
    team_params: dict[str, dict[str, float | str]]
    final_score: Score
    final_stats: dict[str, TeamStats]
    goals: list[dict[str, Any]]


# ------------------------------------------------------------ tracking
class TrackingPlayer(Strict):
    index: int
    player_id: str
    team_id: str
    jersey_number: int


class TrackingHeader(Strict):
    """First line of tracking.jsonl."""
    type: Literal["header"]
    match_id: str
    hz: int
    pitch_length_m: float
    pitch_width_m: float
    coordinates: str
    provenance: str
    generator_version: str
    seed: int
    players: list[TrackingPlayer]
    fidelity: dict[str, float]


class TrackingFrame(Strict):
    """One line of tracking.jsonl after the header.

    `p` lists only players on the pitch: [index into header.players, x, y].
    """
    type: Literal["frame"]
    t: int = Field(ge=0, description="match clock in ms")
    period: int
    ball: list[float] = Field(min_length=2, max_length=2)
    p: list[list[float]]


@dataclass
class Match:
    """A generated match, all four output files in memory."""
    meta: MatchMeta
    teams: list[Team]
    events: list[Any]
    ground_truth: GroundTruth
    extras: dict[str, Any] = field(default_factory=dict)

    @property
    def match_id(self) -> str:
        return self.meta.match_id


def export_json_schema(out_dir: str | Path) -> list[Path]:
    """Write JSON Schema files so other agents can read the contracts."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    items = {
        "event.schema.json": EVENT_ADAPTER.json_schema(),
        "match.schema.json": MatchMeta.model_json_schema(),
        "teams.schema.json": TeamsFile.model_json_schema(),
        "ground_truth.schema.json": GroundTruth.model_json_schema(),
        "tracking_header.schema.json": TrackingHeader.model_json_schema(),
        "tracking_frame.schema.json": TrackingFrame.model_json_schema(),
    }
    paths = []
    for name, schema in items.items():
        p = out / name
        p.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        paths.append(p)
    return paths
