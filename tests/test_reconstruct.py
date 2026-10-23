"""Reconstruct: 3D scenes from synthetic tracking. Facts never change; authored motion stays physical."""
import json
import math
import subprocess
import sys

import pytest

from kvagents.reconstruct import DT, build_scene


@pytest.fixture(scope="module")
def mdir(tmp_path_factory):
    d = tmp_path_factory.mktemp("m") / "match"
    subprocess.run([sys.executable, "-m", "eventgen.cli", "generate", "--seed", "11", "--stories", "random", "--out", str(d)],
                   check=True, capture_output=True)
    sub = next(p for p in d.iterdir() if p.is_dir()) if not (d / "events.jsonl").exists() else d
    return sub


def _events(d):
    return [json.loads(l) for l in open(d / "events.jsonl", encoding="utf-8") if l.strip()]


def _goal_with_assist(evs):
    by = {e["event_id"]: e for e in evs}
    for e in evs:
        if e["type"] == "shot" and e.get("outcome") == "goal" and e.get("assist_event_id") in by:
            a = by[e["assist_event_id"]]
            if e["match_clock_ms"] - a["match_clock_ms"] < 6000:
                return e
    pytest.skip("no goal with a close assist in this seed")


def _max_speed(path):
    return max(math.dist(a, b) for a, b in zip(path, path[1:])) / (DT / 1000.0)


def test_decoy_scene_keeps_facts_and_physics(mdir):
    evs = _events(mdir)
    g = _goal_with_assist(evs)
    t = g["match_clock_ms"]
    sc = build_scene(mdir, mdir / "tracking.jsonl", "M1", "decoy", g["seq"], t - 9000, t + 2000, {})
    assert sc["kind"] == "decoy" and sc["label"].startswith("Illustrative")
    assert len(sc["t"]) == len(sc["ball"]) == len(next(iter(sc["xy"].values())))
    assert 20 <= len(sc["xy"]) <= 22  # a player may be off the pitch in this window
    m = sc["marks"]
    assert {"decoy", "marker", "passer", "scorer"} <= set(m)
    assert m["scorer"] == g["player_id"]
    # authored motion stays within the speed caps (+10% for rounding)
    assert _max_speed(sc["xy"][m["decoy"]]) <= 7.5 * 1.1
    assert _max_speed(sc["xy"][m["marker"]]) <= 8.0 * 1.1
    # attack is normalised to the right-hand goal: the scorer ends in the right half
    assert sc["xy"][m["scorer"]][-1][0] > 52.5
    assert any(f["type"] in ("shot", "penalty") for f in sc["flights"])
    json.dumps(sc)


def test_scene_is_deterministic(mdir):
    g = _goal_with_assist(_events(mdir))
    t = g["match_clock_ms"]
    a = build_scene(mdir, mdir / "tracking.jsonl", "M1", "decoy", g["seq"], t - 9000, t + 2000, {})
    b = build_scene(mdir, mdir / "tracking.jsonl", "M1", "decoy", g["seq"], t - 9000, t + 2000, {})
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_scan_scene_gaze_ends_on_the_chosen_target(mdir):
    evs = _events(mdir)
    by_seq = {e["seq"]: e for e in evs}
    pick = None
    for e in evs:
        if e["type"] == "pass" and e.get("outcome") == "complete" and e.get("receiver_id"):
            for n in evs[e["seq"]: e["seq"] + 8]:
                if n["type"] == "pass" and n["player_id"] == e["receiver_id"] and n["team_id"] == e["team_id"] and \
                        0 < n["match_clock_ms"] - e["match_clock_ms"] < 5000 and n.get("receiver_id"):
                    pick = (e, n)
                    break
        if pick:
            break
    if not pick:
        pytest.skip("no receive-then-pass sequence")
    e, n = pick
    shot = next((x for x in evs if x["type"] == "shot" and x["seq"] > n["seq"]), None)
    if not shot:
        pytest.skip("no later shot")
    t0 = e["match_clock_ms"] - 2000
    t1 = min(shot["match_clock_ms"] + 500, t0 + 30000)
    sc = build_scene(mdir, mdir / "tracking.jsonl", "M2", "scan", shot["seq"], t0, t1,
                     {"scanner": n["player_id"], "recv_seq": e["seq"], "next_seq": n["seq"]})
    s = sc["scan"]
    assert s["pid"] == n["player_id"] and s["target"] == n["receiver_id"]
    assert s["keys"][-1]["look"] == n["receiver_id"]
    assert s["keys"][0]["t"] <= s["t_arrive"] <= s["t_pass"]
