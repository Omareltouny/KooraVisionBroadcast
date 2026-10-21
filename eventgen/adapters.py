"""Auto-eventing adapter: turn tracking (ball and player positions) back into pass events.

Why: the hackathon asks for auto-eventing. We do NOT process video. This is a
labelled mock of the second half of that pipeline (positions in, events out),
so the pipeline can be shown to accept tracking from any source. Provenance is
written on every detected event, and `evaluate_round_trip` scores the result
against the generator's own events.
"""
from __future__ import annotations

import math
from typing import Any

from .schema import Match
from .tracking import TrackingData

PROVENANCE = "auto_eventing_mock_from_tracking"


def _nearest(row: list[tuple[int, float, float]], bx: float, by: float, reach: float) -> tuple[int, float, float] | None:
    best, bd = None, reach
    for i, x, y in row:
        d = math.hypot(x - bx, y - by)
        if d <= bd:
            best, bd = (i, x, y), d
    return best


def detect_passes(data: TrackingData, start_ms: float = 6.0, end_ms: float = 4.0, reach_m: float = 5.0) -> list[dict[str, Any]]:
    """Find kicks from the ball trajectory, like a real auto-eventing step would.

    A kick starts when the ball speed jumps above `start_ms` and ends when it falls below `end_ms`. The passer is the
    nearest player to the ball at the start, the receiver the nearest at the end (both within `reach_m`). Same team =
    pass, other team = turnover. This copes with dribbling and a ball that is never exactly at a player's feet.
    """
    ids = {v: k for k, v in data.player_index.items()}
    team = {p["index"]: p["team_id"] for p in data.header["players"]}
    fr = data.frames
    dt = 1.0 / data.hz
    out: list[dict[str, Any]] = []
    k, n = 1, len(fr)
    while k < n:
        t, per, bx, by, _row = fr[k]
        pt, pper, pbx, pby, prow = fr[k - 1]
        v = math.hypot(bx - pbx, by - pby) / dt if pper == per else 0.0
        if v < start_ms:
            k += 1
            continue
        j = k
        while j + 1 < n and fr[j + 1][1] == per and math.hypot(fr[j + 1][2] - fr[j][2], fr[j + 1][3] - fr[j][3]) / dt >= end_ms:
            j += 1
        s = _nearest(prow, pbx, pby, reach_m)
        e = fr[min(j + 1, n - 1)]
        r = _nearest(e[4], e[2], e[3], reach_m)
        if s and r and (r[0] != s[0] or e[0] - pt > 1500):
            dist = math.hypot(e[2] - pbx, e[3] - pby)
            dur = max((e[0] - pt) / 1000.0, 0.2)
            kind = "pass" if team[s[0]] == team[r[0]] else "turnover"
            out.append(dict(type=kind, t=pt, period=per, player_id=ids[s[0]], receiver_id=ids[r[0]],
                            team_id=team[s[0]], x=s[1], y=s[2], end_x=r[1], end_y=r[2],
                            ball_speed_ms=round(dist / dur, 2), provenance=PROVENANCE))
        k = j + 1
    return out


def evaluate_round_trip(match: Match, detected: list[dict[str, Any]], tol_ms: int = 1000) -> dict[str, float]:
    """Score detected completed passes against the true ones (same passer and receiver within +-tol_ms)."""
    truth = [e for e in match.events if e.type in ("pass", "throw_in", "corner", "free_kick")
             and e.outcome == "complete" and e.receiver_id]
    det = [d for d in detected if d["type"] == "pass"]
    used: set[int] = set()
    tp, speed_err = 0, []
    for e in truth:
        for k, d in enumerate(det):
            if k in used or d["player_id"] != e.player_id or d["receiver_id"] != e.receiver_id:
                continue
            if abs(d["t"] - e.match_clock_ms) <= tol_ms:
                used.add(k)
                tp += 1
                speed_err.append(abs(d["ball_speed_ms"] - e.ball_speed_ms))
                break
    prec = tp / len(det) if det else 0.0
    rec = tp / len(truth) if truth else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"true_passes": float(len(truth)), "detected_passes": float(len(det)), "matched": float(tp),
            "precision": round(prec, 3), "recall": round(rec, 3), "f1": round(f1, 3),
            "ball_speed_mae_ms": round(sum(speed_err) / len(speed_err), 2) if speed_err else 0.0}
