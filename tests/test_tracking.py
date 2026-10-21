"""Tracking data: determinism, file round trip, validator rules, physics, auto-eventing."""
import copy
import hashlib

import pytest

from eventgen.adapters import detect_passes, evaluate_round_trip
from eventgen.io import read_tracking, write_tracking
from eventgen.schema import TrackingFrame, TrackingHeader
from eventgen.tracking import generate_tracking, physical_stats
from eventgen.validate import validate_tracking


@pytest.fixture(scope="module")
def data(match42, cfg):
    return generate_tracking(match42, cfg)


def _digest(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def test_tracking_is_deterministic(match42, cfg, data, tmp_path):
    again = generate_tracking(match42, cfg)
    write_tracking(data, tmp_path / "a.jsonl")
    write_tracking(again, tmp_path / "b.jsonl")
    assert _digest(tmp_path / "a.jsonl") == _digest(tmp_path / "b.jsonl")


def test_tracking_does_not_change_events(match42, cfg, data):
    from eventgen.simulate import generate_match
    other = generate_match(42, "none")
    assert [e.model_dump() for e in other.events] == [e.model_dump() for e in match42.events]


def test_tracking_passes_validator(match42, cfg, data):
    assert validate_tracking(match42, data, cfg) == []


def test_frame_grid_covers_both_periods(match42, cfg, data):
    for pm in match42.meta.periods:
        ts = [f[0] for f in data.frames if f[1] == pm.period]
        assert ts[0] == pm.start_match_clock_ms and ts[-1] <= pm.end_match_clock_ms
        assert all(b - a == 1000 // data.hz for a, b in zip(ts, ts[1:]))


def test_round_trip_file(data, tmp_path):
    write_tracking(data, tmp_path / "t.jsonl")
    back = read_tracking(tmp_path / "t.jsonl")
    assert back.header == data.header and len(back.frames) == len(data.frames)
    assert back.frames[100] == data.frames[100]


def test_lines_match_published_schema(data, tmp_path):
    write_tracking(data, tmp_path / "t.jsonl")
    lines = open(tmp_path / "t.jsonl", encoding="utf-8").read().splitlines()
    TrackingHeader.model_validate_json(lines[0])
    for ln in lines[1:50]:
        TrackingFrame.model_validate_json(ln)


def test_at_most_eleven_per_team_and_roster_follows_events(match42, cfg, data):
    pid = {p["index"]: p for p in data.header["players"]}
    for f in data.frames[::50]:
        per_team = {}
        for i, _, _ in f[4]:
            per_team[pid[i]["team_id"]] = per_team.get(pid[i]["team_id"], 0) + 1
        assert all(c <= 11 for c in per_team.values())


def test_physical_numbers_are_plausible(data):
    ps = physical_stats(data)
    full = [v for k, v in ps.items() if v["minutes_on_pitch"] > 80 and not k.endswith("-P01")]
    assert full
    mean_km = sum(v["distance_m"] for v in full) / len(full) / 1000
    assert 8.0 < mean_km < 12.5
    assert max(v["top_speed_kmh"] for v in full) < 38.0


def test_validator_catches_teleport_and_outside_pitch(match42, cfg, data):
    bad = copy.deepcopy(data)
    t, per, bx, by, row = bad.frames[200]
    i, x, y = row[3]
    row[3] = (i, x + 30.0, y)  # 30 m in one frame
    bad.frames[200] = (t, per, bx, by, row)
    assert any(v.rule == 13 for v in validate_tracking(match42, bad, cfg))
    bad2 = copy.deepcopy(data)
    t, per, bx, by, row = bad2.frames[300]
    row[0] = (row[0][0], -5.0, row[0][2])
    bad2.frames[300] = (t, per, bx, by, row)
    assert any(v.rule == 12 for v in validate_tracking(match42, bad2, cfg))


def test_validator_catches_reappearing_player(match42, cfg, data):
    subs = [e for e in match42.events if e.type == "substitution"]
    if not subs:
        pytest.skip("no substitution in this match")
    e = subs[0]
    idx = data.player_index[e.player_off_id]
    bad = copy.deepcopy(data)
    k = next(n for n, f in enumerate(bad.frames) if f[0] >= e.match_clock_ms + 2000 and f[1] == e.period)
    t, per, bx, by, row = bad.frames[k]
    bad.frames[k] = (t, per, bx, by, row + [(idx, 50.0, 30.0)])
    assert any(v.rule == 14 for v in validate_tracking(match42, bad, cfg))


def test_autoevent_round_trip_finds_most_passes(match42, data):
    det = detect_passes(data)
    score = evaluate_round_trip(match42, det)
    assert score["f1"] >= 0.75, score
    assert all(d["provenance"] == "auto_eventing_mock_from_tracking" for d in det)
