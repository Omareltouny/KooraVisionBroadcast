import json
import time

import pytest

from eventgen import areplay, generate_match, replay
from eventgen.config import load_config, uncalibrated_entries
from eventgen.io import read_match, write_match
from eventgen.replay import CallableSink, FileSink
from eventgen.schema import EVENT_ADAPTER, export_json_schema
from eventgen.validate import validate_match


def test_full_match_shape(match42):
    ev = match42.events
    assert ev[0].type == "period_start" and ev[-1].type == "period_end"
    assert ev[-1].match_clock_ms >= 90 * 60_000
    assert [p.period for p in match42.meta.periods] == [1, 2]
    types = {e.type for e in ev}
    assert {"pass", "shot", "tackle", "possession_change", "pressure", "foul", "substitution"} <= types


def test_validator_passes_on_20_seeds(cfg):
    for seed in range(100, 120):
        m = generate_match(seed, "none", cfg)
        assert validate_match(m, cfg) == [], seed


def test_names_are_fictional_and_localized(match42):
    for t in match42.teams:
        assert {"en", "ar"} <= set(t.name_i18n)
        assert all({"en", "ar"} <= set(p.name_i18n) for p in t.players)
        assert len(t.players) == 18 and sum(p.starter for p in t.players) == 11


def test_determinism_bytes(tmp_path):
    a = write_match(generate_match(5, "random"), tmp_path / "a")
    b = write_match(generate_match(5, "random"), tmp_path / "b")
    for name in ("events.jsonl", "match.json", "teams.json", "ground_truth.json"):
        assert (a / name).read_bytes() == (b / name).read_bytes()


def test_different_seeds_differ(tmp_path):
    a = write_match(generate_match(1, "none"), tmp_path / "a")
    b = write_match(generate_match(2, "none"), tmp_path / "b")
    assert (a / "events.jsonl").read_bytes() != (b / "events.jsonl").read_bytes()


def test_schema_round_trip(tmp_path, match42):
    d = write_match(match42, tmp_path / "m")
    back = read_match(d)
    assert [e.model_dump() for e in back.events] == [e.model_dump() for e in match42.events]
    assert back.meta == match42.meta and back.teams == match42.teams
    # every line re-serializes identically
    for line, ev in zip((d / "events.jsonl").read_text().splitlines(), back.events):
        assert EVENT_ADAPTER.validate_json(line).model_dump_json() == line == ev.model_dump_json()


def test_schema_export(tmp_path):
    paths = export_json_schema(tmp_path)
    assert {p.name for p in paths} == {"event.schema.json", "match.schema.json", "teams.schema.json",
                                       "ground_truth.schema.json",
                                     "tracking_header.schema.json", "tracking_frame.schema.json"}
    assert json.loads((tmp_path / "event.schema.json").read_text())


def test_ground_truth_stats_match_events(match42):
    gt = match42.ground_truth
    goals = [e for e in match42.events if e.type in ("shot", "penalty") and e.outcome == "goal"]
    assert len(goals) == len(gt.goals) == sum(s.goals for s in gt.final_stats.values())
    assert (gt.final_score.home, gt.final_score.away) == (match42.meta.final_score.home, match42.meta.final_score.away)


# --------------------------------------------------------------- stories
def _story(typ, seed=3, team="home"):
    m = generate_match(seed, [{"type": typ, "team": team}])
    assert validate_match(m) == []
    st = [s for s in m.ground_truth.stories if s.type == typ]
    assert st, f"{typ} not realized"
    return m, st[0]


def _passes(m, team, lo, hi):
    return [e for e in m.events if e.type == "pass" and e.team_id == team and lo <= e.match_clock_ms < hi]


def test_momentum_swing_direction():
    m, s = _story("momentum_swing")
    mid = (s.window_start_ms + s.window_end_ms) // 2
    def share(lo, hi):
        tot = [e for e in m.events if e.type == "pass" and lo <= e.match_clock_ms < hi]
        return len(_passes(m, s.team_id, lo, hi)) / len(tot)
    assert share(s.window_start_ms, mid) > share(mid, s.window_end_ms)


def test_pressing_spell_more_wins_than_average():
    m, s = _story("pressing_spell")
    wins = [e for e in m.events if e.type == "possession_change" and e.to_team_id == s.team_id
            and e.reason in ("tackle", "interception", "miscontrol")]
    inside = [e for e in wins if s.window_start_ms <= e.match_clock_ms < s.window_end_ms]
    last = m.events[-1].match_clock_ms
    assert len(inside) / ((s.window_end_ms - s.window_start_ms) / 60000) > len(wins) / (last / 60000)


def test_late_comeback_and_red_card_and_star_and_chaos():
    m, s = _story("late_comeback")
    sc = m.meta.final_score
    mine, other = (sc.home, sc.away) if s.team_id == m.meta.home_team_id else (sc.away, sc.home)
    assert mine >= other
    behind = s.details["conceded_goal_seq"]
    assert behind < s.end_seq == s.details["comeback_goal_seq"]

    m, s = _story("red_card_turning_point")
    red = next(e for e in m.events if e.seq == s.details["red_card_seq"])
    assert red.type == "card" and red.color == "red" and red.team_id == s.team_id
    assert s.details["pass_share_after"] < s.details["pass_share_before"]

    m, s = _story("star_player_match")
    pid = s.players_involved[0]
    inside = [e for e in m.events if s.window_start_ms <= e.match_clock_ms < s.window_end_ms and e.team_id == s.team_id]
    touches = sum(1 for e in inside if e.player_id == pid)
    assert touches / len(inside) > 1 / 11   # more than an average share of the team's actions

    m, s = _story("quiet_then_chaos")
    split = s.details["split_ms"]
    assert s.details["burst_shots"] > s.details["quiet_shots"]
    assert s.details["quiet_events_per_min"] < s.details["match_events_per_min"]


def test_stories_random_and_none_and_yaml(tmp_path):
    assert generate_match(9, "none").ground_truth.stories == []
    m = generate_match(9, "random")
    assert 1 <= len(m.ground_truth.stories) + len(m.ground_truth.unrealized_stories) <= 2
    y = tmp_path / "s.yaml"
    y.write_text("stories:\n  - {type: pressing_spell, team: away}\n  - {type: red_card_turning_point, team: home}\n")
    m = generate_match(4, str(y))
    assert {s.type for s in m.ground_truth.stories} == {"pressing_spell", "red_card_turning_point"}
    assert validate_match(m) == []


# ---------------------------------------------------------------- replay
def test_replay_speed_zero_order(match42):
    out = list(replay(match42, speed=0))
    assert [e.seq for e in out] == [e.seq for e in match42.events]


def test_replay_from_files_and_sinks(tmp_path, match42):
    d = write_match(match42, tmp_path / "m")
    with FileSink(tmp_path / "out.jsonl") as fs:
        n = sum(1 for _ in replay(d, speed=0, sink=fs))
    assert n == len(match42.events)
    assert (tmp_path / "out.jsonl").read_text() == (d / "events.jsonl").read_text()
    seen = []
    list(replay(d, speed=0, sink=CallableSink(seen.append)))
    assert len(seen) == n


def test_replay_timing_roughly_right(match42):
    sl = match42.events[:40]
    span = (sl[-1].match_clock_ms - sl[0].match_clock_ms) / 1000
    speed = span / 0.5          # should take about half a second
    t = time.monotonic()
    list(replay(sl, speed=speed))
    took = time.monotonic() - t
    assert 0.35 < took < 1.5


def test_areplay(match42):
    import asyncio

    async def run():
        return [e async for e in areplay(match42.events[:30], speed=0)]
    assert [e.seq for e in asyncio.run(run())] == [e.seq for e in match42.events[:30]]


# ------------------------------------------------------------- config docs
def test_uncalibrated_doc_lists_every_placeholder():
    doc = open("docs/UNCALIBRATED.md", encoding="utf-8").read()
    missing = [k for k, _, _ in uncalibrated_entries() if f"`{k}`" not in doc]
    assert not missing, missing


def test_config_loads_and_bad_config_fails(tmp_path):
    load_config()
    bad = tmp_path / "bad.yaml"
    bad.write_text("competition: {name: x}\n")
    with pytest.raises(Exception):
        load_config(bad)


# ------------------------------------------------ goalkeeper events and shape
def test_saves_and_goal_kicks_exist_and_are_counted(match42):
    types = [e.type for e in match42.events]
    assert types.count("save") > 3 and types.count("goal_kick") > 5
    stats = match42.ground_truth.final_stats
    assert sum(s.saves for s in stats.values()) == types.count("save")
    assert sum(s.goal_kicks for s in stats.values()) == types.count("goal_kick")


def test_every_save_follows_its_shot(match42):
    by_id = {e.event_id: e for e in match42.events}
    for e in match42.events:
        if e.type == "save":
            sh = by_id[e.shot_event_id]
            assert sh.outcome == "saved" and sh.seq < e.seq and sh.team_id != e.team_id


def test_shirt_colours_are_easy_to_tell_apart(cfg):
    from eventgen.league import MIN_KIT_DISTANCE, build_league, colour_distance
    from eventgen.simulate import generate_match
    league = build_league(7, cfg)
    for fx in range(len(league.fixtures)):
        m = generate_match(7, "none", cfg, league, fixture=fx)
        a, b = m.teams
        assert colour_distance(a.primary_color, b.primary_color) >= MIN_KIT_DISTANCE, (fx, a.primary_color, b.primary_color)
