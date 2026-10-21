#!/usr/bin/env python3
"""Compare generated matches with sourced real-world targets.

Dependency-free (standard library only). Contains no real match data.

Input : one or more match folders written by `eventgen generate`
        (each has match.json and events.jsonl), or a parent folder of them.
Output: a table with generator mean / spread and a PASS / FAIL / n/a verdict
        against tools/targets.json.

Assumptions about the schema (taken from synthetic-event-generator-spec.md).
If the built schema differs, change only the constants and `match_metrics`:
  * event `type` in: pass, shot, tackle, possession_change, pressure, foul,
    card, substitution, corner, free_kick, throw_in, goal_kick, penalty
  * shot/penalty `outcome == "goal"` is a goal; `saved` or `goal` is on target
  * pass `outcome == "complete"` is completed; `pass_length_m` is metres
  * `card` events carry `color`; foul events may carry `card` (used as fallback)

Usage:
  python tools/compare_to_targets.py out/match_*            # explicit folders
  python tools/compare_to_targets.py out/ --targets tools/targets.json
  python tools/compare_to_targets.py out/ --strict          # exit 1 on any FAIL
"""
import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

LONG_PASS_M = 32.0  # Opta definition used in the Premier League articles


def read_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def find_match_dirs(paths):
    found = []
    for p in map(Path, paths):
        if (p / "events.jsonl").exists():
            found.append(p)
        elif p.is_dir():
            found.extend(sorted(d for d in p.iterdir() if (d / "events.jsonl").exists()))
    return found


def match_metrics(d):
    """Raw counts for one match (both teams combined)."""
    match = json.loads((d / "match.json").read_text(encoding="utf-8"))
    home = match.get("home_team_id")
    c = Counter()
    last_clock = 0
    cards_from_fouls = Counter()
    subs_on = set()
    prev = None
    last_foul_clock = None
    pending_sub_clock = None
    behind = {"home": False, "away": False}
    fin = (0, 0)
    for e in read_jsonl(d / "events.jsonl"):
        t = e.get("type")
        clk = e.get("match_clock_ms") or 0
        last_clock = max(last_clock, clk)
        fin = (e.get("score_home", 0), e.get("score_away", 0))
        if fin[0] < fin[1]:
            behind["home"] = True
        elif fin[1] < fin[0]:
            behind["away"] = True
        if pending_sub_clock is not None:
            c["substitution_s_sum"] += (clk - pending_sub_clock) / 1000.0
            c["substitution_s_n"] += 1
            pending_sub_clock = None
        if t in ("throw_in", "goal_kick", "corner") and prev is not None and prev.get("type") == "possession_change":
            c[t + "_s_sum"] += (clk - prev.get("match_clock_ms", 0)) / 1000.0
            c[t + "_s_n"] += 1
        if t == "penalty" and last_foul_clock is not None:
            c["penalty_s_sum"] += (clk - last_foul_clock) / 1000.0
            c["penalty_s_n"] += 1
        if t == "foul":
            last_foul_clock = clk
        if t == "substitution":
            subs_on.add(e.get("player_on_id"))
            pending_sub_clock = clk
        if t in ("shot", "penalty") and e.get("outcome") == "goal":
            minute = (e.get("clock_ms") or 0) / 60000.0 + (45 if e.get("period") == 2 else 0)
            c["goals_h2"] += e.get("period") == 2
            c["goals_90p"] += e.get("period") == 2 and (e.get("clock_ms") or 0) >= 2700000
            c["goals_75p"] += minute > 75
            c["goals_f15"] += minute <= 15
            c["goals_head"] += e.get("body_part") == "head" and t == "shot"
            c["goals_nonown"] += 1
            c["sub_goals"] += e.get("player_id") in subs_on
        if t == "shot":
            c["shot_goals"] += e.get("outcome") == "goal"
        if t == "card" and e.get("color") == "red":
            c["reds_all"] += 1
            c["reds_second"] += e.get("reason") == "second yellow"
        prev = e
        if t == "pass":
            c["passes"] += 1
            c["passes_ok"] += e.get("outcome") == "complete"
            c["long_passes"] += (e.get("pass_length_m") or 0) >= LONG_PASS_M
        elif t in ("shot", "penalty"):
            if t == "shot":
                c["shots"] += 1
                c["shots_on_target"] += e.get("outcome") in ("goal", "saved")
            else:
                c["penalties"] += 1
                c["penalty_goals"] += e.get("outcome") == "goal"
            if e.get("outcome") == "goal":
                c["goals"] += 1
                c["goals_home" if e.get("team_id") == home else "goals_away"] += 1
        elif t == "foul":
            c["fouls"] += 1
            if e.get("card"):
                cards_from_fouls[e["card"]] += 1
        elif t == "card":
            c["yellow_cards" if e.get("color") == "yellow" else "red_cards"] += 1
        elif t in ("tackle", "pressure", "corner", "free_kick", "throw_in",
                   "goal_kick", "substitution"):
            c[t + "s" if not t.endswith("s") else t] += 1
    if not (c["yellow_cards"] or c["red_cards"]):  # fallback: card on foul event
        c["yellow_cards"] = cards_from_fouls.get("yellow", 0)
        c["red_cards"] = cards_from_fouls.get("red", 0)
    c["match_length_min"] = last_clock / 60000.0
    c["res_home"], c["res_away"] = fin[0] > fin[1], fin[1] > fin[0]
    c["res_draw"] = fin[0] == fin[1]
    c["goalless_draw"] = fin == (0, 0)
    c["comeback_win"] = (fin[0] > fin[1] and behind["home"]) or (fin[1] > fin[0] and behind["away"])
    c["subs_per_team"] = c["substitutions"] / 2.0
    return c


def summarize(counts):
    """Turn per-match counters into {metric: list of per-match values} and
    dataset-level ratios."""
    per_match = {}
    for key in ("subs_per_team", "passes", "shots", "shots_on_target", "goals", "fouls",
                "yellow_cards", "red_cards", "penalties", "tackles", "pressures",
                "corners", "free_kicks", "throw_ins", "goal_kicks",
                "substitutions", "match_length_min"):
        per_match[key] = [c.get(key, 0) for c in counts]
    per_match["goals_4plus_share"] = [1.0 if c.get("goals", 0) >= 4 else 0.0 for c in counts]
    tot = Counter()
    for c in counts:
        tot.update({k: v for k, v in c.items() if k != "match_length_min"})
    ratios = {
        "pass_completion": tot["passes_ok"] / tot["passes"] if tot["passes"] else None,
        "long_pass_share": tot["long_passes"] / tot["passes"] if tot["passes"] else None,
        "penalty_conversion": tot["penalty_goals"] / tot["penalties"] if tot["penalties"] else None,
        "home_goal_share": tot["goals_home"] / tot["goals"] if tot["goals"] else None,
    }
    n = len(counts) or 1
    g = tot["goals"] or 1
    ratios.update({
        "home_win_share": tot["res_home"] / n, "away_win_share": tot["res_away"] / n,
        "draw_share": tot["res_draw"] / n, "goalless_draw_share": tot["goalless_draw"] / n,
        "comeback_win_share": tot["comeback_win"] / n,
        "goals_second_half_share": tot["goals_h2"] / g, "goals_90plus_share": tot["goals_90p"] / g,
        "goals_after75_share": tot["goals_75p"] / g, "goals_first15_share": tot["goals_f15"] / g,
        "headed_goal_share": tot["goals_head"] / g, "sub_goal_share": tot["sub_goals"] / g,
        "shot_conversion": tot["shot_goals"] / tot["shots"] if tot["shots"] else None,
        "second_yellow_share_of_reds": tot["reds_second"] / tot["reds_all"] if tot["reds_all"] else None,
    })
    for k in ("throw_in", "goal_kick", "corner", "penalty", "substitution"):
        ratios[k + "_s"] = tot[k + "_s_sum"] / tot[k + "_s_n"] if tot[k + "_s_n"] else None
    return per_match, ratios


# generator metric name -> targets.json key
ALIASES = {"passes": "passes_attempted"}


def verdict(value, target):
    if target is None or value is None:
        return "n/a"
    if "point" in target:
        return f"x{value / target['point']:.2f} of sourced point {target['point']}" if target["point"] else "n/a"
    low, high = target.get("low"), target.get("high")
    if low is not None and value < low:
        return f"FAIL (below {low})"
    if high is not None and value > high:
        return f"FAIL (above {high})"
    return "PASS"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", help="match folders or a parent folder")
    ap.add_argument("--targets", default=str(Path(__file__).with_name("targets.json")))
    ap.add_argument("--strict", action="store_true", help="exit 1 if any metric FAILs")
    args = ap.parse_args()

    dirs = find_match_dirs(args.paths)
    if not dirs:
        sys.exit("no match folders found (need events.jsonl + match.json)")
    targets = {k: v for k, v in json.loads(Path(args.targets).read_text(encoding="utf-8")).items()
               if not k.startswith("_")}
    per_match, ratios = summarize([match_metrics(d) for d in dirs])

    print(f"{len(dirs)} matches. Per match, both teams combined.\n")
    print(f"{'metric':<20}{'mean':>9}{'std':>8}{'min':>8}{'max':>8}   verdict vs sourced target")
    fails = 0
    for key, vals in per_match.items():
        tkey = ALIASES.get(key, key)
        mean = statistics.fmean(vals)
        std = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        v = verdict(mean, targets.get(tkey))
        fails += v.startswith("FAIL")
        print(f"{key:<20}{mean:>9.2f}{std:>8.2f}{min(vals):>8.2f}{max(vals):>8.2f}   {v}")
    print("\nDataset-level ratios:")
    for key, val in ratios.items():
        v = verdict(val, targets.get(key))
        fails += v.startswith("FAIL")
        shown = "n/a" if val is None else f"{val:.3f}"
        print(f"{key:<20}{shown:>9}   {v}")
    print("\nNotes: n/a = no sourced target. Spread is not judged: no source gave a real "
          "per-match spread. A PASS only means the mean sits inside the range of the cited seasons.")
    if args.strict and fails:
        sys.exit(1)


if __name__ == "__main__":
    main()
