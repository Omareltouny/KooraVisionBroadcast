"""Explain agent: for every moment, work out *why* it happened and collect the facts the writers may use.

The output FactPacket is a closed list: Narrate may state only these numbers, names and causes, and Verify checks it.
Optional tracking adds one fact: how many of the scoring team's players were inside the box at the shot.
"""
from __future__ import annotations

import math
from typing import Any

from .match_view import MatchView
from .models import FactPacket, Moment

SET_PIECES = ("corner", "free_kick", "throw_in")
CAUSE_PRIORITY = ["penalty", "set_piece", "counter_attack", "high_press_win", "long_build_up", "header", "long_range"]


class _Track:
    """Small index over TrackingData: ball path length in a window and players in the box at a time."""

    def __init__(self, data: Any, mv: MatchView):
        self.frames = data.frames
        self.times = [f[0] for f in data.frames]
        self.team_of_idx = {p["index"]: p["team_id"] for p in data.header["players"]}
        self.mv = mv

    def _at(self, t_ms: int) -> int:
        import bisect
        return min(max(bisect.bisect_left(self.times, t_ms), 0), len(self.times) - 1)

    def ball_path_m(self, t0: int, t1: int) -> float:
        i, j = self._at(t0), self._at(t1)
        d = 0.0
        for k in range(i, j):
            a, b = self.frames[k], self.frames[k + 1]
            if a[1] == b[1]:
                d += math.hypot(b[2] - a[2], b[3] - a[3])
        return d

    def box_counts(self, t_ms: int, team: str, period: int) -> tuple[int, int]:
        """(attackers, defenders) inside the penalty area the team attacks, at time t."""
        f = self.frames[self._at(t_ms)]
        goal_x = self.mv.L if self.mv.direction(team, period) > 0 else 0.0
        att = dfn = 0
        for i, x, y in f[4]:
            if abs(x - goal_x) <= 16.5 and 13.84 <= y <= 54.16:
                if self.team_of_idx[i] == team:
                    att += 1
                else:
                    dfn += 1
        return att, dfn


def _possession(mv: MatchView, shot: dict[str, Any]) -> dict[str, Any]:
    """Describe the move that ended in `shot`: start event, passes, duration, progression."""
    pid, t = shot["possession_id"], shot["team_id"]
    chain = [e for e in mv.events if e["possession_id"] == pid and e["seq"] <= shot["seq"]]
    team_chain = [e for e in chain if e["team_id"] == t]
    first = team_chain[0] if team_chain else shot
    passes = sum(1 for e in team_chain if e["type"] == "pass" and e.get("outcome") == "complete")
    secs = max((shot["match_clock_ms"] - first["match_clock_ms"]) / 1000.0, 0.0)
    d = mv.direction(t, shot["period"])
    progression = (shot["x"] - first["x"]) * d
    prev = mv.by_seq.get(first["seq"] - 1)
    started_by = first["type"]
    reason = first.get("reason") if first["type"] == "possession_change" else None
    return {"passes": passes, "secs": round(secs, 1), "progression_m": round(progression, 1), "first": first,
            "started_by": started_by, "reason": reason, "prev": prev}


def _causes(mv: MatchView, shot: dict[str, Any], dist: float, poss: dict[str, Any]) -> list[str]:
    tags: set[str] = set()
    first = poss["first"]
    if shot["type"] == "penalty":
        tags.add("penalty")
    if first["type"] in SET_PIECES and first["seq"] != shot["seq"]:
        tags.add("set_piece")
    elif poss["secs"] <= 12 and poss["progression_m"] >= 40 and first["seq"] != shot["seq"]:
        tags.add("counter_attack")
    if first["type"] == "possession_change" and first.get("reason") in ("tackle", "interception", "miscontrol") \
            and mv.in_opp_half(shot["team_id"], shot["period"], first["x"]):
        tags.add("high_press_win")
    if poss["passes"] >= 8:
        tags.add("long_build_up")
    if "head" in str(shot.get("body_part") or ""):
        tags.add("header")
    if dist >= 22 and shot["type"] != "penalty":
        tags.add("long_range")
    return [c for c in CAUSE_PRIORITY if c in tags]


def explain(mv: MatchView, moments: list[Moment], tracking: Any = None) -> list[FactPacket]:
    packets: list[FactPacket] = []
    tr = _Track(tracking, mv) if tracking is not None else None
    # shots per team, used by full time
    shots = {mv.home: 0, mv.away: 0}
    passes = {mv.home: [0, 0], mv.away: [0, 0]}
    for e in mv.events:
        if e["type"] in ("shot", "penalty"):
            shots[e["team_id"]] += 1
        elif e["type"] == "pass":
            passes[e["team_id"]][0] += 1
            passes[e["team_id"]][1] += e.get("outcome") == "complete"
    # when each team last fell behind (for comeback context)
    behind_at: dict[str, tuple[int, int]] = {}
    sc = {mv.home: 0, mv.away: 0}
    for e in mv.events:
        if e["type"] in ("shot", "penalty") and e.get("outcome") == "goal":
            t = e["team_id"]
            sc[t] += 1
            o = mv.opp(t)
            if sc[t] > sc[o] and sc[t] - sc[o] == 1 and (sc[o] > 0 or True):
                behind_at[o] = (e["match_clock_ms"], e["period"])

    for m in moments:
        e = mv.by_seq[m.seq]
        label = mv.minute_label(m.match_clock_ms, m.period)
        t = m.team_id
        o = mv.opp(t) if t else ""
        facts: dict[str, Any] = {"home": mv.home, "away": mv.away, "venue": mv.meta.get("venue", "")}
        causes: list[str] = []
        ids = list(m.player_ids)
        teams = [mv.home, mv.away]
        beneficiary = t

        if m.kind == "goal":
            sa = m.detail["score_after"]
            dist = mv.dist_to_goal(t, e["period"], e["x"], e["y"])
            poss = _possession(mv, e)
            assist = mv.by_id.get(e.get("assist_event_id") or "")
            facts.update({"scorer": e["player_id"], "team": t, "opp": o, "home_goals": sa[mv.home], "away_goals": sa[mv.away],
                          "shot_distance_m": int(round(dist)), "body_part": e.get("body_part"), "flags": m.detail["flags"]})
            if e["type"] != "penalty":
                facts.update({"buildup_passes": poss["passes"], "buildup_seconds": int(round(poss["secs"])),
                              "progression_m": int(round(poss["progression_m"]))})
            if assist and assist["player_id"] != e["player_id"]:
                facts["assist"] = assist["player_id"]
                ids.append(assist["player_id"])
            causes = _causes(mv, e, dist, poss)
            if tr is not None:
                if e["type"] != "penalty":
                    att, _dfn = tr.box_counts(e["match_clock_ms"], t, e["period"])
                    if att >= 3:
                        facts["attackers_in_box"] = att
        elif m.kind == "comeback":
            sa, sb = m.detail["score_after"], m.detail["score_before"]
            g = mv.by_seq[m.detail["goal_seq"]]
            bt = behind_at.get(t)
            facts.update({"scorer": g["player_id"], "team": t, "opp": o, "home_goals": sa[mv.home], "away_goals": sa[mv.away],
                          "deficit": sb[o] - sb[t], "late": m.detail["late"],
                          "behind_minute": mv.minute_label(*bt) if bt else label})
        elif m.kind == "red_card":
            carded = m.detail["carded_team"]
            beneficiary = o if False else m.team_id
            facts.update({"player": e["player_id"], "team": carded, "opp": mv.opp(carded), "men_left": 11 - m.detail["reds_so_far"],
                          "home_goals": e["score_home"], "away_goals": e["score_away"], "reason": m.detail.get("reason") or ""})
        elif m.kind == "big_save":
            facts.update({"keeper": e["player_id"], "shooter": m.detail["shooter"], "team": t, "opp": o,
                          "shot_distance_m": int(round(m.detail["shot_distance_m"])), "save_outcome": e.get("outcome")})
        elif m.kind == "penalty_miss":
            facts.update({"shooter": e["player_id"], "team": m.detail["shooting_team"], "opp": mv.opp(m.detail["shooting_team"]),
                          "outcome": m.detail.get("outcome") or "missed"})
        elif m.kind == "pressing_spell":
            d = m.detail
            facts.update({"team": t, "opp": o, "turnovers": d["turnovers"], "start_label": d["start_label"], "end_label": d["end_label"],
                          "rate_per_min": round(d["rate_per_min"], 1), "avg_rate_per_min": round(d["match_avg_rate_per_min"], 1)})
        elif m.kind == "star_performance":
            d = m.detail
            facts.update({"player": m.player_ids[0], "team": t, "opp": o, "shots": d["shots"], "goals": d["goals"],
                          "key_passes": d["key_passes"], "touches": d["touches"], "shot_share_pct": d["shot_share_pct"]})
        elif m.kind == "super_sub":
            g = mv.by_seq[m.detail["goal_seq"]]
            facts.update({"player": g["player_id"], "team": t, "opp": o, "sub_label": m.detail["sub_label"],
                          "home_goals": g["score_home"], "away_goals": g["score_away"]})
        elif m.kind == "full_time":
            sa = m.detail["score"]
            w = m.detail["winner"]
            facts.update({"home_goals": sa[mv.home], "away_goals": sa[mv.away], "winner": w,
                          "loser": mv.opp(w) if w else "", "shots_home": shots[mv.home], "shots_away": shots[mv.away],
                          "pass_pct_home": int(round(100 * passes[mv.home][1] / max(passes[mv.home][0], 1))),
                          "pass_pct_away": int(round(100 * passes[mv.away][1] / max(passes[mv.away][0], 1)))})
            beneficiary = w
        packets.append(FactPacket(moment_id=m.moment_id, kind=m.kind, beneficiary=beneficiary, minute=label,
                                  facts=facts, causes=causes, names=mv.names_for(ids, teams)))
    return packets
