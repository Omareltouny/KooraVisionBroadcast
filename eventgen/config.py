"""Load and validate the YAML config; list placeholder values.

Why: every tunable lives in config/default.yaml; this module fails fast on a
missing or mistyped key and can list every UNCALIBRATED placeholder so
docs/UNCALIBRATED.md never drifts from the config.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "default.yaml"
FloatPair = list[float]


class _S(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Competition(_S):
    name: str
    season: str
    num_clubs: int
    first_kickoff_utc: str
    matchday_interval_days: int


class Pitch(_S):
    length_m: float
    width_m: float
    goal_width_m: float
    penalty_area_depth_m: float
    penalty_area_width_m: float
    penalty_spot_m: float


class MatchCfg(_S):
    period_length_ms: int
    formations: list[str]
    stoppage_min_ms: int
    stoppage_max_ms: int
    stoppage_per_foul_ms: int
    stoppage_per_card_ms: int
    stoppage_per_sub_ms: int
    stoppage_per_goal_ms: int
    max_substitutions: int
    sub_count_range: list[int]
    sub_minute_range: list[float]


class TeamStyle(_S):
    attack_intensity: FloatPair
    pressing_intensity: FloatPair
    buildup_directness: FloatPair
    quality: FloatPair


class PlayerCfg(_S):
    skill_range: FloatPair
    involvement_range: FloatPair
    skill_pass_weight: float
    skill_finish_weight: float


class Roles(_S):
    anchor_x: dict[str, float]
    involvement: dict[str, float]
    shot_mult: dict[str, float]
    anchor_spread_x: float
    lane_spread_y: float


class Passing(_S):
    base_weights: dict[str, float]
    cross_weight: float
    cross_min_x: float
    cross_wide_band_m: float
    length_m: dict[str, FloatPair]
    completion: dict[str, float]
    pressure_penalty: float
    failure_split: dict[str, float]
    speed_ms: dict[str, FloatPair]
    goalkeeper_long_mult: float
    goal_kick_short_prob: float


class Pressure(_S):
    base_prob: float
    max_prob: float
    zone_factor: dict[str, float]
    distance_m: FloatPair
    duration_ms: list[int]
    tackle_attempt_prob: float
    tackle_win_prob: float
    quality_weight: float


class Foul(_S):
    defender_foul_prob: float
    box_foul_mult: float
    offensive_foul_prob: float
    yellow_prob: float
    second_yellow_mult: float
    red_prob: float


class Shot(_S):
    max_distance_m: float
    distance_exponent: float
    weight_scale: float
    block_prob: float
    off_target_base: float
    off_target_per_m: float
    post_prob: float
    goal_near: float
    goal_decay_m: float
    goal_min: float
    goal_max: float
    speed_ms: FloatPair
    assist_window_ms: int
    header_prob: float
    header_zone_m: float
    after_saved: dict[str, float]
    after_blocked: dict[str, float]
    after_post: dict[str, float]
    after_off_target: dict[str, float]


class Penalty(_S):
    outcome_weights: dict[str, float]


class Timing(_S):
    action_ms: dict[str, list[int]]
    dead_ball_ms: dict[str, list[int]]
    event_gap_ms: list[int]


class Bounds(_S):
    pass_speed_ms: FloatPair
    shot_speed_ms: FloatPair


class StoriesCfg(_S):
    max_attempts: int
    random_max_stories: int
    random_jitter_minutes: float
    defaults: dict[str, dict[str, float]]
    effects: dict[str, dict[str, float]]
    realization: dict[str, float]


class TrackingCfg(_S):
    hz: int
    max_speed_ms: float
    speed_factor_range: FloatPair
    max_accel_ms2: float
    slot_speed_ms: float
    lead_ms: int
    hold_ms: int
    ball_shift: float
    attack_push_m: float
    defend_drop_m: float
    wander_m: float
    wander_period_s: FloatPair
    compact_x: float
    compact_y: float
    carry_touch_m: float
    runs_per_match: dict[str, float]
    run_gain_m: FloatPair
    run_dur_s: FloatPair
    y_follow: float
    out_compact_y: float
    out_compact_x: float


class GameCfg(_S):
    home_shot_mult: float
    home_completion_bonus: float
    early_minutes: float
    early_shot_mult: float
    second_half_shot_mult: float
    late_ramp: float
    trailing_boost: float
    leading_cut: float
    sub_shot_mult: float
    sub_involvement_mult: float


class Config(_S):
    competition: Competition
    pitch: Pitch
    match: MatchCfg
    team_style: TeamStyle
    player: PlayerCfg
    roles: Roles
    passing: Passing
    pressure: Pressure
    foul: Foul
    shot: Shot
    penalty: Penalty
    timing: Timing
    bounds: Bounds
    stories: StoriesCfg
    tracking: TrackingCfg
    game: GameCfg


def load_config(path: str | Path | None = None) -> Config:
    """Load a YAML config (default: config/default.yaml) and validate it."""
    p = Path(path) if path else DEFAULT_CONFIG_PATH
    if not p.exists():
        raise FileNotFoundError(f"config file not found: {p}")
    with open(p, encoding="utf-8") as fh:
        raw: dict[str, Any] = yaml.safe_load(fh)
    return Config.model_validate(raw)


_KEY = re.compile(r"^(\s*)([A-Za-z0-9_]+):\s*(.*)$")


def uncalibrated_entries(path: str | Path | None = None) -> list[tuple[str, str, str]]:
    """Return (dotted.key, value, description) for each `# UNCALIBRATED` line."""
    p = Path(path) if path else DEFAULT_CONFIG_PATH
    stack: list[tuple[int, str]] = []
    out: list[tuple[str, str, str]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = _KEY.match(line)
        if not m:
            continue
        indent, key, rest = len(m.group(1)), m.group(2), m.group(3)
        while stack and stack[-1][0] >= indent:
            stack.pop()
        stack.append((indent, key))
        if "# UNCALIBRATED" in rest:
            value, _, comment = rest.partition("# UNCALIBRATED")
            desc = comment.lstrip(" -:").strip()
            out.append((".".join(k for _, k in stack), value.strip(), desc))
    return out


def uncalibrated_markdown(path: str | Path | None = None) -> str:
    rows = ["| Config key | Placeholder value | Controls |", "|---|---|---|"]
    for key, value, desc in uncalibrated_entries(path):
        rows.append(f"| `{key}` | `{value}` | {desc} |")
    return "\n".join(rows) + "\n"


if __name__ == "__main__":
    sys.stdout.write(uncalibrated_markdown(sys.argv[1] if len(sys.argv) > 1 else None))
