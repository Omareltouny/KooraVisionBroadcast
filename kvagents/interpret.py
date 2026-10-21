"""Interpret agent: find the moments worth telling from the event stream (no ground truth, no model).

Rules are explicit so they can be explained and tested. Importance is a 0..1 score used later to rank and to decide
what becomes a push notification.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .match_view import MatchView
from .models import Moment

LATE_MINUTE = 75
PRESS_WINDOW_MS = 12 * 60000
PRESS_MIN_TURNOVERS = 6
PRESS_RATE_RATIO = 1.8
STAR_MIN_SHOT_SHARE = 0.60   # share of the team's shots
STAR_MIN_SHOTS = 10
STAR_MIN_GOALS = 3
TOUCH_TYPES = ("pass", "shot", "penalty", "tackle", "free_kick", "corner", "throw_in", "goal_kick")


def _is_goal(e: dict[str, Any]) -> bool:
    return e["type"] in ("shot", "penalty") and e.get("outcome") == "goal"


def _clock_minute(clock_ms: int, period: int, mv: MatchView) -> float:
    p = mv.periods[period]
    return 45 * (period - 1) + (clock_ms - p["start_match_clock_ms"]) / 60000.0


def interpret(mv: MatchView) -> list[Moment]:
    ev = mv.events
    out: list[Moment] = []
    n = 0

    def add(kind, e, team, players, imp, detail, end_seq=None):
        nonlocal n
        n += 1
        out.append(Moment(moment_id=f"M{n:03d}", kind=kind, seq=e["seq"], end_seq=end_seq or e["seq"],
                          match_clock_ms=e["match_clock_ms"], period=e["period"], team_id=team,
                          player_ids=players, importance=round(min(imp, 1.0), 3), detail=detail))

    # ---- goals, comebacks, winners
    score = {mv.home: 0, mv.away: 0}
    goals: list[tuple[dict, dict, dict]] = []   # (event, score_before, score_after)
    for e in ev:
        if _is_goal(e):
            before = dict(score)
            score[e["team_id"]] += 1
            goals.append((e, before, dict(score)))
    final = dict(score)
    margin_final = final[mv.home] - final[mv.away]
    trailing_seen = {mv.home: False, mv.away: False}
    running = {mv.home: 0, mv.away: 0}
    goal_moments: dict[int, Moment] = {}
    for g, before, after in goals:
        t, o = g["team_id"], mv.opp(g["team_id"])
        minute = _clock_minute(g["match_clock_ms"], g["period"], mv)
        was_trailing = before[t] < before[o]
        level_now = after[t] == after[o]
        ahead_now = after[t] > after[o]
        flags = {
            "is_penalty": g["type"] == "penalty",
            "first": sum(before.values()) == 0,
            "equaliser": was_trailing and level_now,
            "go_ahead": (before[t] <= before[o]) and ahead_now,
            "late": minute >= LATE_MINUTE,
            "comeback": was_trailing and (level_now or ahead_now) and minute >= 55,
            "winner": False,
        }
        # winning goal: the (loser's final goals + 1)th goal of the eventual winner
        if final[t] > final[o] and after[t] == final[o] + 1:
            flags["winner"] = True
        imp = 0.60
        imp += 0.12 if flags["equaliser"] else 0.0
        imp += 0.10 if flags["go_ahead"] else 0.0
        imp += 0.08 if flags["late"] else 0.0
        imp += 0.10 if flags["comeback"] else 0.0
        imp += 0.12 if flags["winner"] and flags["late"] else (0.05 if flags["winner"] else 0.0)
        imp += 0.03 if flags["first"] else 0.0
        det = {"score_before": before, "score_after": after, "flags": flags, "scorer": g["player_id"]}
        add("goal", g, t, [g["player_id"]], imp, det)
        goal_moments[g["seq"]] = out[-1]
        if flags["comeback"]:
            add("comeback", g, t, [g["player_id"]], imp + 0.05,
                {"score_before": before, "score_after": after, "late": flags["late"], "goal_seq": g["seq"]})
        trailing_seen[t] = trailing_seen[t]

    # ---- red cards
    reds: dict[str, int] = defaultdict(int)
    for e in ev:
        red = (e["type"] == "card" and e.get("color") == "red") or (e["type"] == "foul" and e.get("card") == "red")
        if red:
            reds[e["team_id"]] += 1
            add("red_card", e, mv.opp(e["team_id"]), [e["player_id"]], 0.80,
                {"carded_team": e["team_id"], "reds_so_far": reds[e["team_id"]], "reason": e.get("reason")})

    # ---- big saves and missed penalties
    for e in ev:
        if e["type"] == "save" and e.get("outcome") in ("parried", "tipped", "caught"):
            shot = mv.by_id.get(e.get("shot_event_id", ""))
            if not shot:
                continue
            d = mv.dist_to_goal(shot["team_id"], shot["period"], shot["x"], shot["y"])
            if d <= 14.0 and shot["type"] != "penalty":
                add("big_save", e, e["team_id"], [e["player_id"], shot["player_id"]],
                    0.40 + (14.0 - d) / 14.0 * 0.12, {"shot_event": shot["seq"], "shot_distance_m": round(d, 1),
                                                       "shooter": shot["player_id"]})
        if e["type"] == "penalty" and e.get("outcome") != "goal":
            add("penalty_miss", e, mv.opp(e["team_id"]), [e["player_id"]], 0.75,
                {"shooting_team": e["team_id"], "outcome": e.get("outcome")})

    # ---- pressing spells: high turnovers in a sliding window versus the match average
    turnovers: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in ev:
        if e["type"] == "possession_change" and e.get("reason") in ("tackle", "interception", "miscontrol"):
            t = e["to_team_id"]
            if mv.in_opp_half(t, e["period"], e["x"]):
                turnovers[t].append(e)
    total_ms = max(e["match_clock_ms"] for e in ev) or 1
    for t, lst in turnovers.items():
        avg_rate = len(lst) / (total_ms / 60000.0)
        best: tuple[float, int, int] | None = None
        times = [x["match_clock_ms"] for x in lst]
        for i, x in enumerate(lst):
            j = i
            while j + 1 < len(lst) and times[j + 1] - times[i] <= PRESS_WINDOW_MS and lst[j + 1]["period"] == x["period"]:
                j += 1
            cnt = j - i + 1
            span = max(times[j] - times[i], 4 * 60000)
            rate = cnt / (span / 60000.0)
            if cnt >= PRESS_MIN_TURNOVERS and rate >= PRESS_RATE_RATIO * avg_rate and (best is None or cnt > best[1]):
                best = (rate, cnt, i)
        if best:
            rate, cnt, i = best
            j = i + cnt - 1
            players = sorted({lst[k]["player_id"] for k in range(i, j + 1)})[:3]
            add("pressing_spell", lst[i], t, players, 0.50 + min(rate / avg_rate - 1.8, 1.5) * 0.08,
                {"turnovers": cnt, "start_ms": times[i], "end_ms": times[j], "rate_per_min": round(rate, 2),
                 "match_avg_rate_per_min": round(avg_rate, 2),
                 "start_label": mv.minute_label(times[i], lst[i]["period"]), "end_label": mv.minute_label(times[j], lst[j]["period"])},
                end_seq=lst[j]["seq"])

    # ---- star performances: one player carries a big share of the team's play
    touches: dict[str, int] = defaultdict(int)
    team_touches: dict[str, int] = defaultdict(int)
    shots: dict[str, int] = defaultdict(int)
    goals_by: dict[str, int] = defaultdict(int)
    key_passes: dict[str, int] = defaultdict(int)
    last_seq: dict[str, int] = {}
    for e in ev:
        if e["type"] in TOUCH_TYPES and e.get("player_id") in mv.players:
            touches[e["player_id"]] += 1
            team_touches[e["team_id"]] += 1
            last_seq[e["player_id"]] = e["seq"]
        if e["type"] in ("shot", "penalty"):
            shots[e["player_id"]] += 1
            goals_by[e["player_id"]] += e.get("outcome") == "goal"
            a = mv.by_id.get(e.get("assist_event_id") or "")
            if a:
                key_passes[a["player_id"]] += 1
    team_shots: dict[str, int] = defaultdict(int)
    for p, c in shots.items():
        team_shots[mv.team_of[p]] += c
    for t in (mv.home, mv.away):
        cands = [(shots[p], goals_by[p], p) for p in mv.players if mv.team_of[p] == t]
        s, g, star = max(cands)
        share = s / max(team_shots[t], 1)
        if (share >= STAR_MIN_SHOT_SHARE and s >= STAR_MIN_SHOTS) or g >= STAR_MIN_GOALS:
            tshare = touches[star] / max(team_touches[t], 1)
            add("star_performance", mv.by_seq[last_seq[star]], t, [star], 0.50 + 0.05 * min(g, 3) + 0.10 * min(share, 0.8),
                {"touches": touches[star], "touch_share_pct": round(tshare * 100), "shot_share_pct": round(share * 100),
                 "shots": s, "goals": g, "key_passes": key_passes[star]})

    # ---- super sub: a substitute scores or sets up a goal after coming on
    subs = {e["player_on_id"]: e for e in ev if e["type"] == "substitution"}
    for m in list(out):
        if m.kind != "goal":
            continue
        g = mv.by_seq[m.seq]
        sc = g["player_id"]
        if sc in subs:
            se = subs[sc]
            add("super_sub", g, g["team_id"], [sc], 0.62,
                {"sub_label": mv.minute_label(se["match_clock_ms"], se["period"]), "goal_seq": g["seq"]})

    # ---- full time
    last = ev[-1]
    winner = mv.home if margin_final > 0 else mv.away if margin_final < 0 else ""
    add("full_time", last, winner, [], 0.90, {"score": final, "winner": winner})

    out.sort(key=lambda m: (m.match_clock_ms, m.seq, m.kind))
    for i, m in enumerate(out, 1):
        m.moment_id = f"M{i:03d}"
    return out
