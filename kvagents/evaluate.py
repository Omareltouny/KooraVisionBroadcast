"""Score the Interpret agent against the planted stories. This is the ONLY place that reads ground_truth.json,
and it is for evaluation, never for the agents themselves."""
from __future__ import annotations

import json
from pathlib import Path

from .interpret import interpret
from .match_view import MatchView


SCORED = ("late_comeback", "pressing_spell", "red_card_turning_point")
MIN_PRESS_TURNOVERS = 6   # a planted "spell" with fewer turnovers is not visible in the data, so it is not scored


def score_match(match_dir: str | Path) -> dict[str, int]:
    mv = MatchView(match_dir)
    gt = json.loads((Path(match_dir) / "ground_truth.json").read_text(encoding="utf-8"))
    moments = interpret(mv)
    r = {"goals_true": 0, "goals_found": 0, "comeback_true": 0, "comeback_found": 0, "press_true": 0, "press_found": 0,
         "red_true": 0, "red_found": 0, "not_scored": 0, "moments_total": len(moments)}
    found_goals = {m.seq for m in moments if m.kind == "goal"}
    for g in gt["goals"]:
        r["goals_true"] += 1
        r["goals_found"] += g["seq"] in found_goals
    for st in gt["stories"]:
        kind = st["type"]
        if kind == "late_comeback":
            r["comeback_true"] += 1
            r["comeback_found"] += any(m.kind == "comeback" and m.detail["goal_seq"] == st["details"]["comeback_goal_seq"] for m in moments)
        elif kind == "pressing_spell" and st["details"].get("turnovers_in_window", 0) >= MIN_PRESS_TURNOVERS:
            r["press_true"] += 1
            r["press_found"] += any(m.kind == "pressing_spell" and m.team_id == st["team_id"] and m.seq <= st["end_seq"]
                                    and m.end_seq >= st["start_seq"] for m in moments)
        elif kind == "red_card_turning_point":
            r["red_true"] += 1
            r["red_found"] += any(m.kind == "red_card" and m.player_ids[0] in st["players_involved"] for m in moments)
        else:
            r["not_scored"] += 1
    return r


def evaluate_dirs(dirs: list[str]) -> int:
    tot: dict[str, int] = {}
    for d in dirs:
        for k, v in score_match(d).items():
            tot[k] = tot.get(k, 0) + v
    print(f"matches: {len(dirs)}")
    print(f"goals found:          {tot['goals_found']}/{tot['goals_true']}")
    print(f"late comebacks found: {tot['comeback_found']}/{tot['comeback_true']}")
    print(f"pressing spells found:{tot['press_found']}/{tot['press_true']}  (planted spells with at least {MIN_PRESS_TURNOVERS} turnovers)")
    print(f"red cards found:      {tot['red_found']}/{tot['red_true']}")
    print(f"not scored (no rule or not visible in the data): {tot['not_scored']} planted stories (star player, quiet-then-chaos, momentum swing)")
    print(f"moments per match: {tot['moments_total'] / len(dirs):.1f}")
    return 0
