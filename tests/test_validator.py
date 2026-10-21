"""One test per invariant: the validator must fail on hand-corrupted data."""
import pytest

from eventgen.validate import validate_match


def rules(m):
    return {v.rule for v in validate_match(m)}


def first(m, pred):
    return next(e for e in m.events if pred(e))


def test_clean(fresh):
    assert validate_match(fresh) == []


def test_rule1_seq_gap(fresh):
    fresh.events[10].seq += 1
    assert 1 in rules(fresh)


def test_rule1_clock_backwards(fresh):
    fresh.events[50].match_clock_ms = 0
    assert 1 in rules(fresh)


def test_rule2_coordinates(fresh):
    first(fresh, lambda e: e.type == "pass").x = 200.0
    assert 2 in rules(fresh)


def test_rule3_unknown_player(fresh):
    first(fresh, lambda e: e.type == "pass").player_id = "NOPE"
    assert 3 in rules(fresh)


def test_rule3_actor_wrong_team(fresh):
    e = first(fresh, lambda e: e.type == "pass")
    e.team_id = fresh.meta.away_team_id if e.team_id == fresh.meta.home_team_id else fresh.meta.home_team_id
    assert 3 in rules(fresh)


def test_rule4_event_after_substitution(fresh):
    sub = first(fresh, lambda e: e.type == "substitution")
    later = first(fresh, lambda e: e.seq > sub.seq and e.type == "pass" and e.team_id == sub.team_id
                  and e.player_id != sub.player_off_id)
    later.player_id = sub.player_off_id
    assert 4 in rules(fresh)


def test_rule4_event_after_red_card(fresh_red):
    m, red = fresh_red
    later = first(m, lambda e: e.seq > red.seq and e.type == "pass" and e.team_id == red.team_id)
    later.player_id = red.player_id
    assert 4 in rules(m)


@pytest.fixture()
def fresh_red():
    from eventgen import generate_match
    m = generate_match(3, [{"type": "red_card_turning_point", "team": "home"}])
    red = first(m, lambda e: e.type == "card" and e.color == "red")
    return m, red


def test_rule5_possession_change_team(fresh):
    e = first(fresh, lambda e: e.type == "possession_change")
    e.to_team_id = e.from_team_id
    assert 5 in rules(fresh)


def test_rule5_next_action_wrong_team(fresh):
    pc = first(fresh, lambda e: e.type == "possession_change")
    nxt = first(fresh, lambda e: e.seq > pc.seq and e.type in ("pass", "shot"))
    nxt.team_id = pc.from_team_id
    assert 5 in rules(fresh)


def test_rule6_score_changes_without_goal(fresh):
    e = first(fresh, lambda e: e.type == "pass")
    e.score_home += 1
    assert 6 in rules(fresh)


def test_rule6_final_score(fresh):
    fresh.meta.final_score.home += 1
    assert 6 in rules(fresh)


def test_rule7_pass_length(fresh):
    first(fresh, lambda e: e.type == "pass").pass_length_m += 5
    assert 7 in rules(fresh)


def test_rule8_pass_speed(fresh):
    first(fresh, lambda e: e.type == "pass").ball_speed_ms = -1.0
    assert 8 in rules(fresh)


def test_rule8_shot_speed(fresh):
    first(fresh, lambda e: e.type == "shot").shot_speed_ms = 999.0
    assert 8 in rules(fresh)


def test_rule9_too_many_players(fresh):
    # the "player off" is someone who is not on the pitch, so the arriving player makes 12
    sub = first(fresh, lambda e: e.type == "substitution")
    team = next(t for t in fresh.teams if t.team_id == sub.team_id)
    bench = next(p.player_id for p in team.players if not p.starter and p.player_id != sub.player_on_id)
    sub.player_off_id = bench
    assert 9 in rules(fresh)


def test_rule10_story_seq_missing(fresh_story):
    fresh_story.ground_truth.stories[0].end_seq = 10**7
    assert 10 in rules(fresh_story)


def test_rule10_story_wrong_team(fresh_story):
    st = fresh_story.ground_truth.stories[0]
    other = fresh_story.meta.away_team_id if st.team_id == fresh_story.meta.home_team_id else fresh_story.meta.home_team_id
    st.team_id = other
    assert 10 in rules(fresh_story)


@pytest.fixture()
def fresh_story():
    from eventgen import generate_match
    return generate_match(3, [{"type": "pressing_spell", "team": "home"}])


# ------------------------------------------------ rule 16: goalkeeper events
def test_rule16_save_must_answer_a_saved_shot(fresh):
    e = first(fresh, lambda e: e.type == "save")
    e.shot_event_id = "does-not-exist"
    assert 16 in rules(fresh)


def test_rule16_save_by_outfield_player(fresh):
    e = first(fresh, lambda e: e.type == "save")
    team = next(t for t in fresh.teams if t.team_id == e.team_id)
    e.player_id = next(p.player_id for p in team.players if p.starter and p.position != "GK")
    assert 16 in rules(fresh)


def test_rule16_saved_shot_without_save(fresh):
    i = next(i for i, e in enumerate(fresh.events) if e.type == "save")
    del fresh.events[i]
    for k, e in enumerate(fresh.events, start=1):
        e.seq = k
    assert 16 in rules(fresh)


def test_rule16_goal_kick_by_outfield_player(fresh):
    e = first(fresh, lambda e: e.type == "goal_kick")
    team = next(t for t in fresh.teams if t.team_id == e.team_id)
    e.player_id = next(p.player_id for p in team.players if p.starter and p.position != "GK")
    assert 16 in rules(fresh)
