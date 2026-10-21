"""Invariant checks for a generated match (spec section 11, rules 1-10).

Why: downstream stages trust this data, so the validator fails loudly with the
offending `seq` and rule number rather than letting a bad file through.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import Config, load_config
from .io import read_match
from .schema import OWNER_ACTIONS, PASS_LIKE, Match

EPS = 1e-6
PLAYER_FIELDS = ("receiver_id", "opponent_id", "pressed_player_id", "fouled_player_id", "player_on_id")
NEW_POSSESSION_TYPES = ("period_start", "possession_change", "corner")


@dataclass
class Violation:
    rule: int
    seq: int | None
    message: str

    def __str__(self) -> str:
        return f"rule {self.rule} violated at seq {self.seq}: {self.message}"


class ValidationError(Exception):
    def __init__(self, violations: list[Violation]) -> None:
        super().__init__("\n".join(str(v) for v in violations[:20]))
        self.violations = violations


def validate_match(match: Match, cfg: Config | None = None) -> list[Violation]:
    cfg = cfg or load_config()
    L, W = cfg.pitch.length_m, cfg.pitch.width_m
    v: list[Violation] = []
    add = lambda rule, seq, msg: v.append(Violation(rule, seq, msg))  # noqa: E731
    team_of = {p.player_id: t.team_id for t in match.teams for p in t.players}
    team_ids = {t.team_id for t in match.teams}
    home, away = match.meta.home_team_id, match.meta.away_team_id
    on = {t.team_id: {p.player_id for p in t.players if p.starter} for t in match.teams}
    gone: set[str] = set()
    used_on: set[str] = set()
    events = match.events
    prev_seq, prev_clock = 0, -1
    score = {home: 0, away: 0}
    owner: dict[int, str] = {}
    prev_poss: int | None = None
    pending_to: str | None = None
    by_seq = {e.seq: e for e in events}
    by_id = {e.event_id: e for e in events}
    pos_of = {p.player_id: p.position for t in match.teams for p in t.players}
    saved_shots = {e.event_id for e in events if e.type in ("shot", "penalty") and e.outcome == "saved"}
    saves_seen: set[str] = set()

    for e in events:
        s = e.seq
        # 1 ordering
        if (prev_seq == 0 and s != 1) or (prev_seq and s != prev_seq + 1):
            add(1, s, f"seq must start at 1 and increase by 1 (previous {prev_seq})")
        if e.match_clock_ms < prev_clock:
            add(1, s, f"match_clock_ms went backwards ({prev_clock} -> {e.match_clock_ms})")
        prev_seq, prev_clock = s, e.match_clock_ms
        # 2 coordinates
        for name in ("x", "y", "end_x", "end_y"):
            val = getattr(e, name, None)
            if val is None:
                continue
            hi = L if name.endswith("x") else W
            if not (-EPS <= val <= hi + EPS):
                add(2, s, f"{name}={val} outside the pitch")
        if e.type == "pass" and e.outcome == "out":
            if not (min(e.end_x, L - e.end_x) < EPS or min(e.end_y, W - e.end_y) < EPS):
                add(2, s, "out-of-play pass must end on the pitch boundary")
        # 3 identities
        for fld in ("player_id",) + PLAYER_FIELDS + ("player_off_id",):
            pid = getattr(e, fld, None)
            if pid is not None and pid not in team_of:
                add(3, s, f"{fld}={pid} not in teams.json")
        if e.team_id not in team_ids:
            add(3, s, f"team_id={e.team_id} not in teams.json")
        elif team_of.get(e.player_id) != e.team_id:
            add(3, s, f"actor {e.player_id} does not belong to {e.team_id}")
        for fld in ("from_team_id", "to_team_id"):
            if getattr(e, fld, e.team_id) not in team_ids:
                add(3, s, f"{fld} not in teams.json")
        # 16 goalkeeper events: goal kicks and saves are taken by a keeper, a save answers a saved shot
        if e.type in ("save", "goal_kick") and pos_of.get(e.player_id) != "GK":
            add(16, s, f"{e.type} by {e.player_id}, who is not a goalkeeper")
        if e.type == "save":
            sh = by_id.get(e.shot_event_id)
            if sh is None or sh.type not in ("shot", "penalty") or sh.outcome != "saved":
                add(16, s, f"save {e.event_id} does not answer a saved shot ({e.shot_event_id})")
            elif sh.team_id == e.team_id or sh.seq >= e.seq:
                add(16, s, "save must come after the shot and from the other team")
            if e.shot_event_id in saves_seen:
                add(16, s, f"shot {e.shot_event_id} has more than one save")
            saves_seen.add(e.shot_event_id)
        # 4 sent off / subbed off
        for fld in ("player_id",) + PLAYER_FIELDS:
            pid = getattr(e, fld, None)
            if pid in gone:
                add(4, s, f"{fld}={pid} produced/was in an event after leaving the pitch")
            elif pid is not None and pid in team_of and pid not in on[team_of[pid]] and e.type != "substitution":
                add(4, s, f"{fld}={pid} is not on the pitch")
        # 9 / substitutions & cards change who is on the pitch
        if e.type == "substitution":
            t = e.team_id
            if e.player_off_id not in on.get(t, set()):
                add(4, s, f"player_off {e.player_off_id} is not on the pitch")
            if e.player_on_id in used_on or e.player_on_id in on.get(t, set()) or team_of.get(e.player_on_id) != t:
                add(3, s, f"player_on {e.player_on_id} is invalid or already used")
            on[t].discard(e.player_off_id)
            gone.add(e.player_off_id)
            on[t].add(e.player_on_id)
            used_on.add(e.player_on_id)
        elif e.type == "card" and e.color == "red":
            on[e.team_id].discard(e.player_id)
            gone.add(e.player_id)
        for t, s_on in on.items():
            if len(s_on) > 11:
                add(9, s, f"{t} has {len(s_on)} players on the pitch")
        # 6 scores
        is_goal = e.type in ("shot", "penalty") and e.outcome == "goal"
        if is_goal:
            score[e.team_id] += 1
        if (e.score_home, e.score_away) != (score[home], score[away]):
            add(6, s, f"score {e.score_home}-{e.score_away} but goals imply {score[home]}-{score[away]}")
            score = {home: e.score_home, away: e.score_away}
        # 7 geometry, 8 speeds
        if e.type in PASS_LIKE:
            d = math.hypot(e.end_x - e.x, e.end_y - e.y)
            if abs(d - e.pass_length_m) > 0.05:
                add(7, s, f"pass_length_m={e.pass_length_m} but geometry gives {d:.2f}")
            lo, hi = cfg.bounds.pass_speed_ms
            if not (e.ball_speed_ms > 0 and lo <= e.ball_speed_ms <= hi):
                add(8, s, f"ball_speed_ms={e.ball_speed_ms} outside [{lo}, {hi}]")
        if e.type in ("shot", "penalty"):
            lo, hi = cfg.bounds.shot_speed_ms
            if not (e.shot_speed_ms > 0 and lo <= e.shot_speed_ms <= hi):
                add(8, s, f"shot_speed_ms={e.shot_speed_ms} outside [{lo}, {hi}]")
        # 5 possession
        if prev_poss is not None and e.possession_id != prev_poss:
            if e.possession_id != prev_poss + 1 or e.type not in NEW_POSSESSION_TYPES:
                add(5, s, f"possession_id {prev_poss} -> {e.possession_id} outside a possession start event")
        prev_poss = e.possession_id
        if e.type == "possession_change":
            if e.to_team_id == e.from_team_id or e.team_id != e.to_team_id:
                add(5, s, "possession_change must hand the ball to the acting team")
            if owner.get(e.possession_id - 1) not in (None, e.from_team_id):
                add(5, s, "from_team_id is not the team that owned the previous possession")
            owner[e.possession_id] = e.to_team_id
            pending_to = e.to_team_id
        elif e.type in ("period_start", "corner") and e.possession_id not in owner:
            owner[e.possession_id] = e.team_id
        if e.type in ("period_start", "period_end"):
            pending_to = None
        if e.type in OWNER_ACTIONS:
            if owner.get(e.possession_id) not in (None, e.team_id):
                add(5, s, f"{e.type} by {e.team_id} inside a possession owned by {owner[e.possession_id]}")
            if pending_to is not None and e.team_id != pending_to:
                add(5, s, f"first action after possession_change is by {e.team_id}, expected {pending_to}")
            pending_to = None

    if events:
        last = events[-1]
        fs = match.meta.final_score
        if (fs.home, fs.away) != (score[home], score[away]) or (fs.home, fs.away) != (last.score_home, last.score_away):
            add(6, last.seq, f"match.json final_score {fs.home}-{fs.away} != events {score[home]}-{score[away]}")
    for sid in sorted(saved_shots - saves_seen):
        add(16, by_id[sid].seq, f"saved shot {sid} has no save event")
    # 10 ground truth
    for st in match.ground_truth.stories:
        for fld in ("start_seq", "end_seq"):
            ev = by_seq.get(getattr(st, fld))
            if ev is None:
                add(10, getattr(st, fld), f"story {st.story_id} {fld} does not exist")
            elif ev.team_id != st.team_id:
                add(10, ev.seq, f"story {st.story_id} {fld} points at {ev.team_id}, expected {st.team_id}")
        if st.start_seq > st.end_seq:
            add(10, st.start_seq, f"story {st.story_id} start_seq after end_seq")
    return v


def assert_valid(match: Match, cfg: Config | None = None) -> None:
    violations = validate_match(match, cfg)
    if violations:
        raise ValidationError(violations)


def validate_tracking(match: Match, data: Any, cfg: Config | None = None) -> list[Violation]:
    """Tracking rules 11-15: structure, pitch bounds, physics, roster, agreement with events."""
    cfg = cfg or load_config()
    tc = cfg.tracking
    L, W = cfg.pitch.length_m, cfg.pitch.width_m
    v: list[Violation] = []

    def add(rule: int, t: int | None, msg: str) -> None:
        v.append(Violation(rule, t, msg))

    hdr = data.header
    hz = int(hdr["hz"])
    dt_ms = 1000 // hz
    if hdr.get("match_id") != match.meta.match_id:
        add(11, None, "tracking header match_id differs from match.json")
    n_players = len(hdr["players"])
    team_of = {p["index"]: p["team_id"] for p in hdr["players"]}
    # 11 frame grid: every period fully covered at the stated rate
    by_period: dict[int, list[Any]] = {}
    for f in data.frames:
        by_period.setdefault(f[1], []).append(f)
    for pm in match.meta.periods:
        fr = by_period.get(pm.period, [])
        want = (pm.end_match_clock_ms - pm.start_match_clock_ms) // dt_ms + 1
        if len(fr) != want:
            add(11, pm.start_match_clock_ms, f"period {pm.period}: {len(fr)} frames, expected {want}")
        for a, b in zip(fr, fr[1:]):
            if b[0] - a[0] != dt_ms:
                add(11, b[0], f"frame step {b[0] - a[0]} ms, expected {dt_ms}")
                break
    max_v = tc.max_speed_ms * 1.02
    max_a = tc.max_accel_ms2 + 2.0
    last: dict[int, tuple[float, float, float, float | None]] = {}
    bad_speed = bad_accel = 0
    for t, per, bx, by, row in data.frames:
        if not (-0.01 <= bx <= L + 0.01 and -0.01 <= by <= W + 0.01):
            add(12, t, f"ball outside pitch ({bx}, {by})")
        count = {}
        for i, x, y in row:
            if not 0 <= i < n_players:
                add(12, t, f"unknown player index {i}")
                continue
            if not (-0.01 <= x <= L + 0.01 and -0.01 <= y <= W + 0.01):
                add(12, t, f"player {i} outside pitch ({x}, {y})")
            count[team_of[i]] = count.get(team_of[i], 0) + 1
            prev = last.get(i)
            if prev and prev[3] == per and t - prev[2] == dt_ms:
                sp = math.hypot(x - prev[0], y - prev[1]) / (dt_ms / 1000)
                if sp > max_v:
                    bad_speed += 1
            last[i] = (x, y, t, per)
        for team, c in count.items():
            if c > 11:
                add(12, t, f"{c} players of {team} on pitch")
    if bad_speed:
        add(13, None, f"{bad_speed} frame steps faster than {max_v:.1f} m/s")
    # 14 roster agrees with events (sent-off and subbed-off players never reappear)
    gone: dict[str, int] = {}
    for e in match.events:
        if e.type == "substitution":
            gone[e.player_off_id] = e.match_clock_ms
        elif (e.type == "card" and e.color == "red") or (e.type == "foul" and e.card == "red"):
            gone.setdefault(e.player_id, e.match_clock_ms)
    pid_of = {p["index"]: p["player_id"] for p in hdr["players"]}
    seen_after: set[str] = set()
    for t, per, bx, by, row in data.frames:
        for i, x, y in row:
            pid = pid_of.get(i)
            if pid in gone and t >= gone[pid]:
                seen_after.add(pid)
    for pid in sorted(seen_after):
        add(14, gone[pid], f"{pid} is in tracking after leaving the pitch")
    # 15 agreement with events: ball at the event position, actor near it
    times = [f[0] for f in data.frames]
    import bisect as _b
    checked = near = ball_ok = 0
    for e in match.events:
        if e.type in ("substitution", "period_start", "period_end"):
            continue
        k = _b.bisect_left(times, e.match_clock_ms)
        k = min(k, len(times) - 1)
        if k > 0 and abs(times[k - 1] - e.match_clock_ms) < abs(times[k] - e.match_clock_ms):
            k -= 1
        t, per, bx, by, row = data.frames[k]
        if per != e.period:
            continue
        checked += 1
        if math.hypot(bx - e.x, by - e.y) <= 4.0:
            ball_ok += 1
        idx = next((i for i, pid in pid_of.items() if pid == e.player_id), None)
        pos = next(((x, y) for i, x, y in row if i == idx), None)
        if pos is not None and math.hypot(pos[0] - e.x, pos[1] - e.y) <= 5.0:
            near += 1
    if checked:
        if ball_ok / checked < 0.95:
            add(15, None, f"ball is near the event position for only {ball_ok}/{checked} events")
        if near / checked < 0.85:
            add(15, None, f"acting player is near the event position for only {near}/{checked} events")
    return v


def validate_dir(path: str | Path, cfg: Config | None = None) -> list[Violation]:
    from .io import TRACKING_FILE, read_tracking
    match = read_match(path)
    out = validate_match(match, cfg)
    tf = Path(path) / TRACKING_FILE
    if tf.exists():
        out += validate_tracking(match, read_tracking(tf), cfg)
    return out
