"""KooraVision agents: moments, facts, narration, fact-check, desks, workflow engines, model path."""
import json
import re
import shutil

import pytest

from eventgen.io import write_match
from eventgen.simulate import generate_match
from kvagents.explain import explain
from kvagents.interpret import interpret
from kvagents.lang import LANG
from kvagents.llm import CachedModel
from kvagents.match_view import MatchView
from kvagents.models import FactPacket, Narration
from kvagents.narrate import _nf, narrate, render
from kvagents.personalize import Profile, fan_desk, broadcast_desk, MAX_PUSH
from kvagents.pipeline import HAVE_AGENT_FRAMEWORK, run_pipeline
from kvagents.verify import verify_all, verify_narration


@pytest.fixture(scope="module")
def mdir(tmp_path_factory):
    d = tmp_path_factory.mktemp("kv") / "m"
    write_match(generate_match(42, "random"), d)   # random stories: some goals, usually a comeback or a red card
    return d


@pytest.fixture(scope="module")
def mv(mdir):
    return MatchView(mdir)


@pytest.fixture(scope="module")
def moments(mv):
    return interpret(mv)


@pytest.fixture(scope="module")
def packets(mv, moments):
    return explain(mv, moments)


def test_every_goal_becomes_a_goal_moment(mv, moments):
    goals = [e for e in mv.events if e["type"] in ("shot", "penalty") and e.get("outcome") == "goal"]
    assert {m.seq for m in moments if m.kind == "goal"} == {e["seq"] for e in goals}
    ft = [m for m in moments if m.kind == "full_time"]
    assert len(ft) == 1 and ft[0].detail["score"][mv.home] + ft[0].detail["score"][mv.away] == len(goals)


def test_moments_are_ordered_and_importance_in_range(moments):
    assert all(0 <= m.importance <= 1 for m in moments)
    assert [m.match_clock_ms for m in moments] == sorted(m.match_clock_ms for m in moments)
    assert len({m.moment_id for m in moments}) == len(moments)


def test_goal_facts_match_the_events(mv, packets):
    for p in packets:
        if p.kind == "goal":
            e = next(x for x in mv.events if x["player_id"] == p.facts["scorer"] and x["type"] in ("shot", "penalty") and x.get("outcome") == "goal"
                     and mv.minute_label(x["match_clock_ms"], x["period"]) == p.minute)
            assert p.facts["home_goals"] == e["score_home"] and p.facts["away_goals"] == e["score_away"]


def test_all_templates_verify_in_every_language(mv, packets):
    names = mv.all_names()
    for p in packets:
        for lang in LANG:
            for voice in ("broadcast", "fan_for", "fan_against", "fan_neutral"):
                head, body = render(p, lang, voice, mv.meta["venue"])
                assert "{" not in head + body, (p.kind, lang)
                ok, why = verify_narration(p, head, body, lang, names)
                assert ok, (p.moment_id, p.kind, lang, voice, why)


def test_verify_rejects_invented_number_and_foreign_name(mv, packets):
    p = next(x for x in packets if x.kind == "goal")
    head, body = render(p, "en", "broadcast")
    names = mv.all_names()
    assert verify_narration(p, head, body, "en", names)[0]
    assert not verify_narration(p, head, body + " It was his 99th goal.", "en", names)[0]
    other = next(n for n in names if n not in {v for d in p.names.values() for v in d.values()})
    assert not verify_narration(p, head, body + f" {other} was furious.", "en", names)[0]
    assert not verify_narration(p, "Goal", "A goal happened.", "en", names)[0]   # main actor missing
    assert not verify_narration(p, head, body + " Number 06 shirt.", "en", names)[0]  # digits of an id are not facts


def test_surname_alone_counts_for_the_main_actor_but_cannot_smuggle_in_others(mv, packets):
    p = next(x for x in packets if x.kind == "goal")
    names = mv.all_names()
    full = p.names[p.facts["scorer"]]["en"]
    surname = full.split()[-1]
    head, body = f"{full} scores!", f"{surname} fires it in at minute {p.minute.split('+')[0]}."
    allowed = {v for d in p.names.values() for v in d.values()}
    other = next(n for n in names if n not in allowed and len(n.split()) > 1 and n.split()[-1] not in " ".join(allowed))
    ok, _ = verify_narration(p, head, f"{surname} scores. Then {other.split()[-1]} reacts.", "en", names)
    assert not ok                                   # a foreign surname on its own is caught
    ok2, why2 = verify_narration(p, "Goal", f"{surname} scores.", "en", names)
    assert "main actor" not in why2                 # the surname satisfies the main-actor rule


def test_arabic_number_agreement():
    T = LANG["ar"].T
    assert _nf(T, "press_body", 5) == T["press_body_few"]
    assert _nf(T, "press_body", 12) == T["press_body"]
    assert _nf(LANG["en"].T, "c_counter", 5) == LANG["en"].T["c_counter"]


class FakeModel:
    name = "fake"

    def __init__(self, mode):
        self.mode, self.calls = mode, 0

    def complete(self, system, user):
        self.calls += 1
        d = json.loads(user)
        if self.mode == "invent":
            return json.dumps({"headline": d["draft_headline"], "body": d["draft_body"] + " It was the 7th goal of the season."})
        if self.mode == "garbage":
            return "not json"
        return json.dumps({"headline": d["draft_headline"], "body": d["draft_body"]})


def _run_model(mv, packets, moments, mode):
    imp = {m.moment_id: m.importance for m in moments}
    ns, _ = narrate(mv, packets, FakeModel(mode), importance=imp)
    return verify_all(ns, {p.moment_id: p for p in packets}, mv.all_names())


def test_model_drafts_are_accepted_only_when_they_pass_verify(mv, packets, moments):
    final, stats, rej = _run_model(mv, packets, moments, "good")
    assert stats["llm_accepted"] > 0 and stats["llm_rejected"] == 0
    assert any(n.source == "llm" for n in final)
    final, stats, rej = _run_model(mv, packets, moments, "invent")
    assert stats["llm_accepted"] == 0 and stats["llm_rejected"] > 0 and rej
    assert all(n.source == "template" for n in final)
    final, stats, _ = _run_model(mv, packets, moments, "garbage")
    assert stats["llm_accepted"] == 0 and all(n.source == "template" for n in final)


def test_cached_model_replays_offline(tmp_path):
    fake = FakeModel("good")
    c = CachedModel(fake, tmp_path / "c.json")
    a = c.complete("s", json.dumps({"draft_headline": "h", "draft_body": "b"}))
    off = CachedModel(None, tmp_path / "c.json", offline=True)
    assert off.complete("s", json.dumps({"draft_headline": "h", "draft_body": "b"})) == a
    assert fake.calls == 1
    with pytest.raises(LookupError):
        off.complete("other", "x")


def test_fan_desk_voices_language_and_push_cap(mv, moments, packets):
    pk = {p.moment_id: p for p in packets}
    ns, _ = narrate(mv, packets)
    ns, _, _ = verify_all(ns, pk, mv.all_names())
    prof = Profile("f", "ar", "home")
    cards = fan_desk(mv, moments, pk, ns, prof)
    assert cards and all(c.lang == "ar" for c in cards)
    assert sum(c.push for c in cards) <= MAX_PUSH
    for c in cards:
        p = pk[c.moment_id]
        if p.beneficiary == mv.home:
            assert c.voice == "fan_for"
        elif p.beneficiary == mv.away:
            assert c.voice == "fan_against"
    neutral = fan_desk(mv, moments, pk, ns, Profile("n", "en", None))
    assert all(c.voice == "fan_neutral" for c in neutral)
    bro = broadcast_desk(mv, moments, pk, ns)
    assert all(c.tier in "ABC" and len(c.lower_third) <= 70 for c in bro)


def test_comeback_and_its_goal_are_not_both_published(mv, moments, packets):
    pk = {p.moment_id: p for p in packets}
    ns, _ = narrate(mv, packets)
    ns, _, _ = verify_all(ns, pk, mv.all_names())
    bro = broadcast_desk(mv, moments, pk, ns)
    seqs = [(m.seq, m.kind) for m in moments if m.moment_id in {c.moment_id for c in bro}]
    for s, k in seqs:
        if k == "comeback":
            assert (s, "goal") not in seqs


def _read(d, name):
    return json.loads((d / name).read_text(encoding="utf-8"))


@pytest.mark.skipif(not HAVE_AGENT_FRAMEWORK, reason="agent-framework-core not installed")
def test_workflow_engine_and_direct_loop_give_identical_output(mdir, tmp_path):
    _, d1 = run_pipeline(mdir, tmp_path / "fw", engine="framework")
    _, d2 = run_pipeline(mdir, tmp_path / "dr", engine="direct")
    for f in ("moments.json", "packets.json", "narrations.json", "broadcast.json", "fan_fan_ar.json", "fan_fan_es.json", "fan_fan_en.json"):
        assert _read(d1, f) == _read(d2, f), f
    t = _read(d1, "trace.json")
    assert t["engine"] == "microsoft-agent-framework"
    order = [e["agent"] for e in t["framework_events"] if e["event"] == "executor_invoked"]
    assert order[:4] == ["interpret", "explain", "narrate", "verify"] and order[-1] == "publish"
    assert {"broadcast_desk", "fan_desk"} <= set(order)


def test_pipeline_never_needs_ground_truth_and_is_deterministic(mdir, tmp_path):
    copy = tmp_path / "copy"
    shutil.copytree(mdir, copy)
    (copy / "ground_truth.json").unlink()
    _, a = run_pipeline(copy, tmp_path / "o1")
    _, b = run_pipeline(copy, tmp_path / "o2")
    assert _read(a, "narrations.json") == _read(b, "narrations.json")
    man = _read(a, "manifest.json")
    assert man["language_status"]["ar"] == "needs_native_review" and man["mode"] == "templates"


def test_no_agent_module_imports_ground_truth():
    import pathlib
    for p in pathlib.Path("kvagents").glob("*.py"):
        if p.name == "evaluate.py":
            continue
        assert "ground_truth" not in re.sub(r'"""[\s\S]*?"""|#.*', "", p.read_text(encoding="utf-8")), p.name


def test_writer_is_a_real_agent_framework_agent_against_a_local_openai_server(mv, packets, moments):
    """A stdlib server speaks the OpenAI chat API; the Agent Framework Agent calls it; Verify still has the last word."""
    pytest.importorskip("agent_framework.openai")
    import http.server
    import threading

    seen = []

    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append(body)
            user = json.loads(body["messages"][-1]["content"])
            invent = len(seen) % 3 == 0     # every third answer invents a number
            reply = json.dumps({"headline": user["draft_headline"],
                                "body": user["draft_body"] + (" It was his 99th goal." if invent else "")})
            out = json.dumps({"id": "x", "object": "chat.completion", "created": 0, "model": body["model"],
                              "choices": [{"index": 0, "message": {"role": "assistant", "content": reply}, "finish_reason": "stop"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        from kvagents.llm import AgentFrameworkModel
        model = AgentFrameworkModel("fake-model", f"http://127.0.0.1:{srv.server_port}/v1")
        imp = {m.moment_id: m.importance for m in moments}
        ns, _ = narrate(mv, packets, model, importance=imp)
        final, stats, rej = verify_all(ns, {p.moment_id: p for p in packets}, mv.all_names())
    finally:
        srv.shutdown()
    assert seen and seen[0]["messages"][0]["role"] in ("system", "developer")   # the Agent's instructions went out
    assert stats["llm_accepted"] > 0 and stats["llm_rejected"] > 0              # good drafts kept, invented number thrown out
    assert all("99" not in n.body for n in final)


def test_cached_model_retries_after_rate_limit_and_waits_between_calls(tmp_path):
    class Flaky:
        name = "flaky"

        def __init__(self):
            self.n = 0

        def complete(self, system, user):
            self.n += 1
            if self.n <= 2:
                raise RuntimeError("HTTP 429")
            return "ok"

    f = Flaky()
    c = CachedModel(f, tmp_path / "c.json", retries=3, retry_pause=0.0, min_interval=0.0)
    assert c.complete("s", "u") == "ok" and f.n == 3 and c.failures == 2
    dead = CachedModel(type("D", (), {"name": "d", "complete": lambda self, s, u: (_ for _ in ()).throw(RuntimeError("down"))})(),
                       tmp_path / "d.json", retries=1, retry_pause=0.0)
    with pytest.raises(RuntimeError):
        dead.complete("s", "u")


def test_reasoning_model_thinking_is_ignored(mv, packets, moments):
    class Thinker:
        name = "thinker"

        def complete(self, system, user):
            d = json.loads(user)
            return "<think>I should {maybe} change things</think>" + json.dumps({"headline": d["draft_headline"], "body": d["draft_body"]})

    ns, _ = narrate(mv, packets, Thinker(), importance={m.moment_id: m.importance for m in moments})
    final, stats, _ = verify_all(ns, {p.moment_id: p for p in packets}, mv.all_names())
    assert stats["llm_accepted"] > 0
