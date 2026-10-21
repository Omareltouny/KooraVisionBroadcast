"""Build ground_truth.json: planted stories plus stats computed straight from events.

Why: Interpret and Explain stages are evaluated against this file, so every
number here is recomputed from the raw events and can be cross-checked.
"""
from __future__ import annotations

from typing import Any

from .league import Club
from .schema import GENERATOR_VERSION, GroundTruth, MatchMeta, Score, StoryTruth, TeamStats

NOTE = ("Evaluation only. The Interpret and Explain stages must NOT read this file at runtime.")


def compute_stats(events: list[Any], team_ids: list[str]) -> dict[str, TeamStats]:
    c = {t: dict.fromkeys(["goals", "shots", "shots_on_target", "passes", "passes_complete", "tackles",
                           "tackles_won", "pressures", "fouls", "yellow_cards", "red_cards", "corners",
                           "goal_kicks", "saves", "throw_ins", "free_kicks", "penalties", "substitutions", "turnovers_won"], 0)
         for t in team_ids}
    held = dict.fromkeys(team_ids, 0)
    owner: str | None = None
    prev_clock = 0
    for e in events:
        if owner is not None:
            held[owner] += e.match_clock_ms - prev_clock
        prev_clock = e.match_clock_ms
        k, t = c[e.team_id], e.team_id
        if e.type in ("period_start", "corner") or e.type == "possession_change":
            owner = e.team_id if e.type != "possession_change" else e.to_team_id
        if e.type in ("shot", "penalty"):
            k["shots"] += 1
            k["shots_on_target"] += e.outcome in ("goal", "saved")
            k["goals"] += e.outcome == "goal"
            k["penalties"] += e.type == "penalty"
        elif e.type == "pass":
            k["passes"] += 1
            k["passes_complete"] += e.outcome == "complete"
        elif e.type == "tackle":
            k["tackles"] += 1
            k["tackles_won"] += e.outcome == "won"
        elif e.type == "pressure":
            k["pressures"] += 1
        elif e.type == "foul":
            k["fouls"] += 1
        elif e.type == "card":
            k["yellow_cards" if e.color == "yellow" else "red_cards"] += 1
        elif e.type == "corner":
            k["corners"] += 1
        elif e.type == "goal_kick":
            k["goal_kicks"] += 1
        elif e.type == "save":
            k["saves"] += 1
        elif e.type == "throw_in":
            k["throw_ins"] += 1
        elif e.type == "free_kick":
            k["free_kicks"] += 1
        elif e.type == "substitution":
            k["substitutions"] += 1
        elif e.type == "possession_change" and e.reason in ("tackle", "interception", "miscontrol"):
            c[e.to_team_id]["turnovers_won"] += 1
        del t
    total = sum(held.values()) or 1
    out = {}
    for t in team_ids:
        k = c[t]
        out[t] = TeamStats(**k, pass_completion=round(k["passes_complete"] / k["passes"], 4) if k["passes"] else 0.0,
                           possession_pct=round(100 * held[t] / total, 2))
    return out


def build_ground_truth(meta: MatchMeta, events: list[Any], clubs: list[Club], stories: list[dict[str, Any]],
                       unrealized: list[dict[str, Any]], attempt: int) -> GroundTruth:
    ids = [c.team_id for c in clubs]
    goals = [dict(seq=e.seq, match_clock_ms=e.match_clock_ms, team_id=e.team_id, player_id=e.player_id,
                  type=e.type) for e in events if e.type in ("shot", "penalty") and e.outcome == "goal"]
    return GroundTruth(
        match_id=meta.match_id, generator_version=GENERATOR_VERSION, seed=meta.seed, generation_attempt=attempt,
        note=NOTE, stories=[StoryTruth(**s) for s in stories], unrealized_stories=unrealized,
        team_params={c.team_id: {**c.profile, "formation": c.team.formation} for c in clubs},
        final_score=Score(home=sum(g["team_id"] == ids[0] for g in goals),
                          away=sum(g["team_id"] == ids[1] for g in goals)),
        final_stats=compute_stats(events, ids), goals=goals)
