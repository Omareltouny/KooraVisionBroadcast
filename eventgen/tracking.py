"""Synthetic tracking data: positions of 22 players and the ball, 5 times a second.

Why: events say what happened; tracking says where everybody was. It gives the
pipeline real speed, distance and spacing numbers, and a second input to
cross-check events (auto-eventing adapter, see adapters.py).

How: the events are the truth. Every event pins the ball and the acting players
to a place and time. Between pins, players drift to a formation slot that moves
with the ball. A speed and acceleration limit keeps motion physically possible.
The result is a pure function of the match files plus the seed, so the events
never change when tracking is added.
"""
from __future__ import annotations

import bisect
import math
import random
from dataclasses import dataclass, field
from typing import Any

from .config import Config
from .schema import GENERATOR_VERSION, PASS_LIKE, SHOT_LIKE, Match

PROVENANCE = "synthetic_tracking_from_events"
COORDINATES = ("metres, absolute pitch frame: x along the length 0..L, y across the width 0..W; "
               "same frame as events; see match.json periods[].attacking_direction")

# slot positions in the team's own frame (own goal at x=0, attacking towards +x), order = FORMATION_SLOTS
FORMATION_COORDS: dict[str, list[tuple[float, float]]] = {
    "4-3-3": [(4, 34), (32, 10), (27, 25), (27, 43), (32, 58), (44, 34), (56, 22), (56, 46), (72, 12), (80, 34), (72, 56)],
    "4-2-3-1": [(4, 34), (32, 10), (27, 25), (27, 43), (32, 58), (45, 24), (45, 44), (68, 10), (64, 34), (68, 58), (80, 34)],
    "4-4-2": [(4, 34), (32, 10), (27, 25), (27, 43), (32, 58), (58, 10), (54, 25), (54, 43), (58, 58), (78, 27), (78, 41)],
    "3-5-2": [(4, 34), (27, 18), (27, 34), (27, 50), (55, 6), (55, 62), (46, 34), (57, 24), (64, 44), (78, 27), (78, 41)],
}
ROLE_FOLLOW = {"GK": 0.1, "CB": 0.5, "FB": 0.6, "DM": 0.65, "CM": 0.7, "AM": 0.75, "W": 0.75, "ST": 0.8}
FORMATION_ORDER = {
    "4-3-3": ["GK", "FB", "CB", "CB", "FB", "DM", "CM", "CM", "W", "ST", "W"],
    "4-2-3-1": ["GK", "FB", "CB", "CB", "FB", "DM", "DM", "W", "AM", "W", "ST"],
    "4-4-2": ["GK", "FB", "CB", "CB", "FB", "W", "CM", "CM", "W", "ST", "ST"],
    "3-5-2": ["GK", "CB", "CB", "CB", "FB", "FB", "DM", "CM", "AM", "ST", "ST"],
}
_OUTFIELD_CX = {k: sum(c[0] for c in v[1:]) / 10 for k, v in FORMATION_COORDS.items()}
_NO_BALL = ("substitution",)
_NO_PIN = ("substitution", "period_start", "period_end")


@dataclass
class TrackingData:
    header: dict[str, Any]
    frames: list[tuple[int, int, float, float, list[tuple[int, float, float]]]]
    player_index: dict[str, int] = field(default_factory=dict)

    @property
    def hz(self) -> int:
        return int(self.header["hz"])


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def generate_tracking(match: Match, cfg: Config) -> TrackingData:
    """Build the tracking frames for a match (deterministic from the match seed)."""
    tc = cfg.tracking
    if 1000 % tc.hz:
        raise ValueError("tracking.hz must divide 1000")
    L, W = cfg.pitch.length_m, cfg.pitch.width_m
    dt_ms = 1000 // tc.hz
    dt = dt_ms / 1000.0
    rng = random.Random(f"tracking:{match.meta.seed}")
    meta = match.meta
    teams = {t.team_id: t for t in match.teams}
    all_players = [p for t in match.teams for p in t.players]
    idx = {p.player_id: i for i, p in enumerate(all_players)}
    team_of = {p.player_id: t.team_id for t in match.teams for p in t.players}
    pos_of = {p.player_id: p.position for p in all_players}
    opp = {meta.home_team_id: meta.away_team_id, meta.away_team_id: meta.home_team_id}
    direction = {(pm.period, t): (1 if d == "left_to_right" else -1)
                 for pm in meta.periods for t, d in pm.attacking_direction.items()}

    # ---- per-player personality (fixed order -> deterministic)
    vmax = {p.player_id: tc.max_speed_ms * rng.uniform(*tc.speed_factor_range) for p in all_players}
    wander = {p.player_id: (rng.uniform(0, 6.283), rng.uniform(0, 6.283), rng.uniform(*tc.wander_period_s), rng.uniform(*tc.wander_period_s),
                            rng.uniform(0.5, 1.0)) for p in all_players}

    # ---- off-ball runs (own rng so nothing else changes): (start_ms, duration_ms, forward_gain_m)
    rrng = random.Random(f"runs:{meta.seed}")
    runs: dict[str, list[tuple[int, int, float]]] = {}
    run_ptr: dict[str, int] = {}

    # ---- roster intervals and slots
    slot_of: dict[str, int] = {}
    for t in match.teams:
        for i, p in enumerate([p for p in t.players if p.starter][:11]):
            slot_of[p.player_id] = i
    on_from: dict[str, int] = {pid: 0 for pid in slot_of}
    off_at: dict[str, int] = {}
    events = match.events
    for e in events:
        if e.type == "substitution":
            off_at[e.player_off_id] = e.match_clock_ms
            on_from[e.player_on_id] = e.match_clock_ms
            slot_of[e.player_on_id] = slot_of[e.player_off_id]
        elif (e.type == "card" and e.color == "red") or (e.type == "foul" and e.card == "red"):
            off_at.setdefault(e.player_id, e.match_clock_ms)

    for p in all_players:
        form = teams[team_of[p.player_id]].formation
        if p.player_id in slot_of:
            role = FORMATION_ORDER[form][slot_of[p.player_id]]
            lam = tc.runs_per_match.get(role, 0.0)
            lst = []
            for pm in meta.periods:
                span = (pm.end_match_clock_ms - pm.start_match_clock_ms) / 5400000.0
                for _ in range(int(lam * span + rrng.random())):
                    lst.append((int(rrng.uniform(pm.start_match_clock_ms, pm.end_match_clock_ms - 7000)),
                                int(rrng.uniform(*tc.run_dur_s) * 1000), rrng.uniform(*tc.run_gain_m)))
            runs[p.player_id] = sorted(lst)
            run_ptr[p.player_id] = 0

    def on_pitch(pid: str, t: int) -> bool:
        return pid in on_from and on_from[pid] <= t and t < off_at.get(pid, 10**12)

    # ---- ball keyframes and pins (per period)
    ball_kf: dict[int, list[tuple[int, float, float]]] = {}
    pins: dict[str, list[tuple[int, float, float]]] = {}
    poss_tl: dict[int, list[tuple[int, str]]] = {}
    evs = [e for e in events]
    n = len(evs)
    for k, e in enumerate(evs):
        t = e.match_clock_ms
        per = e.period
        kf = ball_kf.setdefault(per, [])
        if e.type not in _NO_BALL:
            # next event time with a ball position (to cap flight time)
            t_next = next((evs[j].match_clock_ms for j in range(k + 1, n)
                           if evs[j].period == per and evs[j].type not in _NO_BALL), None)
            _add_kf(kf, t, e.x, e.y, rng, tc.carry_touch_m)
            if e.type in PASS_LIKE or e.type in SHOT_LIKE:
                speed = e.ball_speed_ms if e.type in PASS_LIKE else e.shot_speed_ms
                dist = math.hypot(e.end_x - e.x, e.end_y - e.y)
                travel = _clamp(dist / max(speed, 1.0) * 1000, 150, 6000)
                arrive = t + travel
                if t_next is not None:
                    arrive = min(arrive, t_next - 50)
                arrive = max(arrive, t + 100)
                _add_kf(kf, int(arrive), e.end_x, e.end_y, rng, tc.carry_touch_m)
                if e.type in PASS_LIKE and e.outcome == "complete" and e.receiver_id and on_pitch(e.receiver_id, int(arrive)):
                    pins.setdefault(e.receiver_id, []).append((int(arrive), e.end_x, e.end_y))
        if e.type not in _NO_PIN and on_pitch(e.player_id, t):
            px, py = e.x, e.y
            if e.type == "pressure":
                d = direction[(per, e.team_id)]
                px = _clamp(e.x - d * e.distance_m, 0, L)
                if on_pitch(e.pressed_player_id, t):
                    pins.setdefault(e.pressed_player_id, []).append((t, e.x, e.y))
            elif e.type == "foul":
                px = _clamp(e.x + 0.9, 0, L)
                if on_pitch(e.fouled_player_id, t):
                    pins.setdefault(e.fouled_player_id, []).append((t, e.x, e.y))
            elif e.type == "tackle" and on_pitch(e.opponent_id, t):
                pins.setdefault(e.opponent_id, []).append((t, e.x, e.y))
            pins.setdefault(e.player_id, []).append((t, px, py))
        # possession timeline
        team = None
        if e.type in PASS_LIKE or e.type in SHOT_LIKE:
            team = e.team_id
        elif e.type == "tackle":
            team = e.team_id if e.outcome == "won" else opp[e.team_id]
        elif e.type == "possession_change":
            team = e.to_team_id
        if team:
            poss_tl.setdefault(per, []).append((t, team))
    for pid, lst in pins.items():
        lst.sort(key=lambda r: r[0])
        clean: list[tuple[int, float, float]] = []
        for r in lst:
            if clean and r[0] - clean[-1][0] < 150:
                clean[-1] = r
            else:
                clean.append(r)
        pins[pid] = clean

    # ---- slot target
    def slot_target(pid: str, t: int, per: int, bx: float, by: float, in_poss: bool,
                    run: float = 0.0) -> tuple[float, float]:
        team = team_of[pid]
        form = teams[team].formation
        sx, sy = FORMATION_COORDS[form][slot_of[pid]]
        role = FORMATION_ORDER[form][slot_of[pid]]
        if role != "GK":
            cx = _OUTFIELD_CX[form]
            sx = cx + (tc.compact_x if in_poss else tc.out_compact_x) * (sx - cx)
            sy = 34.0 + tc.compact_y * (sy - 34.0)
        d = direction[(per, team)]
        nbx = bx if d > 0 else L - bx
        nby = by if d > 0 else W - by
        f = ROLE_FOLLOW[role]
        x = sx + f * tc.ball_shift * (nbx - L / 2)
        if role != "GK":
            x += tc.attack_push_m * (1 if in_poss else 0) - tc.defend_drop_m * (0 if in_poss else 1)
        y = 34.0 + (sy - 34.0) * (1.0 if in_poss else tc.out_compact_y / tc.compact_y) + tc.y_follow * (nby - 34.0)
        x += run
        ph1, ph2, p1, p2, amp = wander[pid]
        x += tc.wander_m * amp * math.sin(6.283 * t / 1000 / p1 + ph1)
        y += tc.wander_m * amp * math.sin(6.283 * t / 1000 / p2 + ph2)
        x, y = _clamp(x, 1.5, L - 1.5), _clamp(y, 1.0, W - 1.0)
        return (x, y) if d > 0 else (L - x, W - y)

    header_players = [dict(index=i, player_id=p.player_id, team_id=team_of[p.player_id], jersey_number=p.jersey_number)
                      for i, p in enumerate(all_players)]
    frames: list[tuple[int, int, float, float, list[tuple[int, float, float]]]] = []
    hit1 = hit3 = total_pins = 0
    state: dict[str, list[float]] = {}
    pin_ptr: dict[str, int] = {}
    pin_err: list[float] = []
    ball_idx: dict[int, int] = {}

    for pm in meta.periods:
        per = pm.period
        kf = ball_kf.get(per, [(pm.start_match_clock_ms, L / 2, W / 2)])
        kts = [r[0] for r in kf]
        ptl = poss_tl.get(per, [])
        ptts = [r[0] for r in ptl]
        t = pm.start_match_clock_ms
        first = True
        pending_check: dict[str, list[tuple[int, float, float]]] = {pid: [] for pid in pins}
        while t <= pm.end_match_clock_ms:
            j = bisect.bisect_right(kts, t) - 1
            if j < 0:
                bx, by = kf[0][1], kf[0][2]
            elif j >= len(kf) - 1:
                bx, by = kf[-1][1], kf[-1][2]
            else:
                a, b = kf[j], kf[j + 1]
                u = (t - a[0]) / max(b[0] - a[0], 1)
                bx, by = a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u
            bx, by = _clamp(bx, 0.0, L), _clamp(by, 0.0, W)
            q = bisect.bisect_right(ptts, t) - 1
            poss = ptl[q][1] if q >= 0 else meta.home_team_id
            row: list[tuple[int, float, float]] = []
            for p in all_players:
                pid = p.player_id
                if not on_pitch(pid, t):
                    state.pop(pid, None)
                    continue
                in_poss = team_of[pid] == poss
                st = state.get(pid)
                if st is None or first:
                    if on_from.get(pid, 0) > 0 and on_from[pid] > pm.start_match_clock_ms and st is None and not first:
                        d0 = direction[(per, team_of[pid])]
                        st = [L / 2, 0.0, 0.0, 0.0]
                    else:
                        sx0, sy0 = slot_target(pid, t, per, L / 2, W / 2, in_poss)
                        st = [sx0, sy0, 0.0, 0.0]
                    state[pid] = st
                    pin_ptr[pid] = bisect.bisect_left([r[0] for r in pins.get(pid, [])], t)
                x, y, vx, vy = st
                pl = pins.get(pid, [])
                ni = pin_ptr.get(pid, 0)
                while ni < len(pl) and pl[ni][0] < t:
                    ni += 1
                pin_ptr[pid] = ni
                vm = vmax[pid]
                run_shift = 0.0
                rl = runs.get(pid)
                if rl:
                    k = run_ptr[pid]
                    while k < len(rl) and t > rl[k][0] + rl[k][1]:
                        k += 1
                    run_ptr[pid] = k
                    if k < len(rl) and rl[k][0] <= t <= rl[k][0] + rl[k][1]:
                        run_shift = rl[k][2] * math.sin(math.pi * (t - rl[k][0]) / rl[k][1]) * (1.0 if in_poss else -0.8)
                tx, ty = slot_target(pid, t, per, bx, by, in_poss, run_shift)
                cmd = 7.0 if abs(run_shift) > 0.5 else tc.slot_speed_ms
                gain = 1.0
                chosen = "slot"
                if ni < len(pl):
                    pt, px, py = pl[ni]
                    dist = math.hypot(px - x, py - y)
                    need = dist / (0.9 * vm) * 1000 + 400
                    if pt - t <= max(tc.lead_ms, need):
                        tx, ty = px, py
                        remain = max((pt - t) / 1000.0, dt)
                        cmd = min(vm, 1.12 * dist / remain)
                        chosen = "pin"
                if chosen == "slot" and ni > 0 and t - pl[ni - 1][0] <= tc.hold_ms:
                    tx, ty = pl[ni - 1][1], pl[ni - 1][2]
                    cmd = 2.5
                    chosen = "hold"
                dx, dy = tx - x, ty - y
                dist = math.hypot(dx, dy)
                if dist > 1e-6:
                    sp = min(cmd, gain * dist / dt) if chosen != "slot" else min(cmd, (3.0 if abs(run_shift) > 0.5 else 1.2) * dist)
                    dvx, dvy = dx / dist * sp, dy / dist * sp
                else:
                    dvx = dvy = 0.0
                ax, ay = dvx - vx, dvy - vy
                am = math.hypot(ax, ay)
                lim = tc.max_accel_ms2 * dt
                if am > lim:
                    ax, ay = ax / am * lim, ay / am * lim
                vx, vy = vx + ax, vy + ay
                sp = math.hypot(vx, vy)
                if sp > vm:
                    vx, vy = vx / sp * vm, vy / sp * vm
                x, y = x + vx * dt, y + vy * dt
                nx_, ny_ = _clamp(x, 0, L), _clamp(y, 0, W)
                if nx_ != x:
                    vx = 0.0
                if ny_ != y:
                    vy = 0.0
                st[0], st[1], st[2], st[3] = nx_, ny_, vx, vy
                row.append((idx[pid], round(nx_, 2), round(ny_, 2)))
                # fidelity: compare position with a pin when its time falls inside this frame
                if ni < len(pl) and t <= pl[ni][0] < t + dt_ms:
                    err = math.hypot(nx_ - pl[ni][1], ny_ - pl[ni][2])
                    total_pins += 1
                    hit1 += err <= 1.5
                    hit3 += err <= 3.0
            frames.append((t, per, round(bx, 2), round(by, 2), row))
            first = False
            t += dt_ms
        for pid in list(state):
            state.pop(pid, None)

    fid = {"pins_checked": float(total_pins),
           "pin_within_1_5m": round(hit1 / total_pins, 4) if total_pins else 1.0,
           "pin_within_3m": round(hit3 / total_pins, 4) if total_pins else 1.0}
    header = dict(type="header", match_id=meta.match_id, hz=tc.hz, pitch_length_m=L, pitch_width_m=W,
                  coordinates=COORDINATES, provenance=PROVENANCE, generator_version=GENERATOR_VERSION,
                  seed=meta.seed, players=header_players, fidelity=fid)
    return TrackingData(header=header, frames=frames, player_index=idx)


def _add_kf(kf: list[tuple[int, float, float]], t: float, x: float, y: float,
            rng: random.Random, touch_m: float) -> None:
    t = int(t)
    if kf:
        lt, lx, ly = kf[-1]
        if t <= lt:
            t = lt + 1
        gap = t - lt
        dist = math.hypot(x - lx, y - ly)
        move = min(gap, max(900, dist / 9.0 * 1000))
        hold = gap - move
        if hold > 50 and dist > 0.5 or hold > 600:
            # the holder keeps the ball close and touches it about every 0.45 s, then it moves in the last part of the gap
            n = int(hold / 450)
            amp = min(touch_m, 0.5 * hold / 1000)
            for k in range(1, n):
                r = amp * rng.uniform(0.4, 1.0)
                a = rng.uniform(0, 6.283)
                kf.append((int(lt + hold * k / n), lx + r * math.cos(a), ly + r * math.sin(a)))
            kf.append((int(t - move), lx, ly))
    kf.append((t, x, y))


# ------------------------------------------------------------- physical stats
def physical_stats(data: TrackingData, sprint_ms: float = 7.0, hsr_ms: float = 5.5) -> dict[str, dict[str, float]]:
    """Per-player distance, top speed, sprints and high-speed running from the frames."""
    hz = data.hz
    dt = 1.0 / hz
    last: dict[int, tuple[float, float, int]] = {}
    dist: dict[int, float] = {}
    hsr: dict[int, float] = {}
    speeds: dict[int, list[float]] = {}
    frames_on: dict[int, int] = {}
    for t, per, bx, by, row in data.frames:
        for i, x, y in row:
            frames_on[i] = frames_on.get(i, 0) + 1
            prev = last.get(i)
            if prev and prev[2] == per:
                d = math.hypot(x - prev[0], y - prev[1])
                v = d / dt
                dist[i] = dist.get(i, 0.0) + d
                if v >= hsr_ms:
                    hsr[i] = hsr.get(i, 0.0) + d
                speeds.setdefault(i, []).append(v)
            last[i] = (x, y, per)
    ids = {v: k for k, v in data.player_index.items()}
    out: dict[str, dict[str, float]] = {}
    w = max(1, hz)  # one second smoothing
    for i, sp in speeds.items():
        sm = [sum(sp[max(0, k - w + 1):k + 1]) / len(sp[max(0, k - w + 1):k + 1]) for k in range(len(sp))]
        sprints, run = 0, 0
        for v in sm:
            if v >= sprint_ms:
                run += 1
                if run == hz:  # one second above the sprint threshold
                    sprints += 1
            else:
                run = 0
        out[ids[i]] = {"distance_m": round(dist.get(i, 0.0), 1), "top_speed_ms": round(max(sm), 2) if sm else 0.0,
                       "top_speed_kmh": round(max(sm) * 3.6, 1) if sm else 0.0, "sprints": float(sprints),
                       "high_speed_distance_m": round(hsr.get(i, 0.0), 1),
                       "minutes_on_pitch": round(frames_on.get(i, 0) / hz / 60, 1)}
    return out
