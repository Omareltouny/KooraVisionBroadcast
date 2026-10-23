"""The multi-agent workflow, built on Microsoft Agent Framework (workflow graph with fan-out and fan-in).

    Interpret -> Explain -> Narrate -> Verify -+-> Broadcast desk -+-> Publish
                                               +-> Fan desk -------+

Each agent is an Executor with one handler. They pass one RunState along and log a TraceEntry for every handoff.
If agent-framework is not installed the same agents run in a plain loop (engine = "direct"); results are identical.
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .explain import explain
from .interpret import interpret
from .lang import LANG
from .match_view import MatchView
from .models import RunState, TraceEntry
from .narrate import narrate
from .personalize import DEFAULT_PROFILES, Profile, broadcast_desk, fan_desk
from .verify import verify_all

try:  # module level on purpose: Agent Framework resolves handler annotations from module globals
    from agent_framework import Executor, WorkflowBuilder, WorkflowContext, handler
    HAVE_AGENT_FRAMEWORK = True
except ImportError:  # pragma: no cover
    HAVE_AGENT_FRAMEWORK = False


# ---------------------------------------------------------------- agent steps (plain functions, used by both engines)
def _tracking(state_dir: str):
    p = Path(state_dir) / "tracking.jsonl"
    if not p.exists():
        return None
    from eventgen.io import read_tracking
    return read_tracking(p)


class Ctx:
    """Things the agents need that are not part of the message: match view, model, profiles."""

    def __init__(self, match_dir: str, model=None, profiles: list[Profile] | None = None, use_tracking: bool = True,
                 approvals=None):
        self.mv = MatchView(match_dir)
        self.model = model
        self.profiles = profiles or DEFAULT_PROFILES
        self.use_tracking = use_tracking
        # held drafts a native reader approved, as "moment|lang|voice"; a dict maps match ids to such sets
        if isinstance(approvals, dict):
            approvals = approvals.get(self.mv.meta.get("match_id", ""), set()) | approvals.get("", set())
        self.approvals = set(approvals or ())


def step_interpret(state: RunState, ctx: Ctx) -> None:
    t0 = time.perf_counter()
    state.moments = interpret(ctx.mv)
    kinds: dict[str, int] = {}
    for m in state.moments:
        kinds[m.kind] = kinds.get(m.kind, 0) + 1
    state.trace.append(TraceEntry("Interpret", "find moments", (time.perf_counter() - t0) * 1000,
                                  f"{len(ctx.mv.events)} events", f"{len(state.moments)} moments: {kinds}",
                                  ["rule-based; sees only the event stream"]))


def step_explain(state: RunState, ctx: Ctx) -> None:
    t0 = time.perf_counter()
    tr = _tracking(state.match_dir) if ctx.use_tracking else None
    state.packets = explain(ctx.mv, state.moments, tr)
    with_cause = sum(1 for p in state.packets if p.causes)
    state.trace.append(TraceEntry("Explain", "causes and facts", (time.perf_counter() - t0) * 1000,
                                  f"{len(state.moments)} moments", f"{len(state.packets)} fact packets, {with_cause} with a cause",
                                  ["tracking used" if tr is not None else "no tracking file; event facts only"]))


def step_narrate(state: RunState, ctx: Ctx) -> None:
    t0 = time.perf_counter()
    imp = {m.moment_id: m.importance for m in state.moments}
    state.narrations, notes = narrate(ctx.mv, state.packets, ctx.model, importance=imp)
    drafts = sum(1 for n in state.narrations if n.source == "llm_draft")
    state.mode = "templates+llm" if drafts else "templates"
    state.trace.append(TraceEntry("Narrate", "write en/ar/es", (time.perf_counter() - t0) * 1000,
                                  f"{len(state.packets)} fact packets", f"{len(state.narrations)} texts ({drafts} model drafts waiting for Verify)",
                                  notes or ["templates only (no model)"]))


def step_verify(state: RunState, ctx: Ctx) -> None:
    t0 = time.perf_counter()
    pk = {p.moment_id: p for p in state.packets}
    state.narrations, stats, rej = verify_all(state.narrations, pk, ctx.mv.all_names(), ctx.approvals)
    state.trace.append(TraceEntry("Verify", "fact-check", (time.perf_counter() - t0) * 1000, "all texts", json.dumps(stats), rej[:8]))


def step_broadcast(state: RunState, ctx: Ctx) -> None:
    t0 = time.perf_counter()
    pk = {p.moment_id: p for p in state.packets}
    state.broadcast = broadcast_desk(ctx.mv, state.moments, pk, state.narrations, "en")
    tiers = {t: sum(1 for c in state.broadcast if c.tier == t) for t in "ABC"}
    state.trace.append(TraceEntry("Broadcast desk", "rank for producers", (time.perf_counter() - t0) * 1000,
                                  f"{len(state.moments)} moments", f"{len(state.broadcast)} cards, tiers {tiers}", []))


def step_fan(state: RunState, ctx: Ctx) -> None:
    t0 = time.perf_counter()
    pk = {p.moment_id: p for p in state.packets}
    notes = []
    for prof in ctx.profiles:
        cards = fan_desk(ctx.mv, state.moments, pk, state.narrations, prof)
        state.fan_feeds[prof.id] = cards
        notes.append(f"{prof.id} ({prof.lang}, follows {prof.follows}): {len(cards)} cards, {sum(c.push for c in cards)} push")
    state.trace.append(TraceEntry("Fan desk", "personalise feeds", (time.perf_counter() - t0) * 1000,
                                  f"{len(state.moments)} moments, {len(ctx.profiles)} profiles", f"{sum(len(v) for v in state.fan_feeds.values())} cards", notes))


def publish(state: RunState, ctx: Ctx, out_dir: str | Path, framework_events: list[dict[str, Any]], engine: str) -> Path:
    mid = ctx.mv.meta["match_id"]
    d = Path(out_dir) / mid
    d.mkdir(parents=True, exist_ok=True)

    def dump(name: str, obj: Any) -> None:
        (d / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")

    dump("moments.json", [asdict(m) for m in state.moments])
    dump("packets.json", [asdict(p) for p in state.packets])
    dump("narrations.json", [asdict(n) for n in state.narrations])
    dump("broadcast.json", [asdict(c) for c in state.broadcast])
    for pid, cards in state.fan_feeds.items():
        dump(f"fan_{pid}.json", [asdict(c) for c in cards])
    dump("trace.json", {"engine": engine, "agents": [asdict(t) for t in state.trace], "framework_events": framework_events})
    dump("manifest.json", {
        "match_id": mid, "home": ctx.mv.team_name(ctx.mv.home), "away": ctx.mv.team_name(ctx.mv.away),
        "score": f"{ctx.mv.meta['final_score']['home']}-{ctx.mv.meta['final_score']['away']}", "mode": state.mode, "engine": engine,
        "model": getattr(ctx.model, "name", None), "language_status": {k: v.STATUS for k, v in LANG.items()},
        "profiles": [asdict(p) for p in ctx.profiles],
        "note": "Synthetic match from a fictional league. Text is template- or model-written and fact-checked by the Verify agent."})
    return d


# ---------------------------------------------------------------- Agent Framework graph
def _build_workflow(ctx: Ctx):
    def make(agent_id: str, fn):
        class _Agent(Executor):
            def __init__(self):
                super().__init__(id=agent_id)

            @handler
            async def run(self, state: RunState, wf: WorkflowContext[RunState]) -> None:
                fn(state, ctx)
                await wf.send_message(state)
        _Agent.__name__ = f"{agent_id.title().replace(' ', '')}Agent"
        return _Agent()

    class _Publish(Executor):
        def __init__(self):
            super().__init__(id="publish")

        @handler
        async def run(self, states: list[RunState], wf: WorkflowContext[None, RunState]) -> None:
            await wf.yield_output(states[0])  # fan-in: both desks worked on the same RunState

    a_int, a_exp, a_nar, a_ver = make("interpret", step_interpret), make("explain", step_explain), make("narrate", step_narrate), make("verify", step_verify)
    d_bro, d_fan, pub = make("broadcast_desk", step_broadcast), make("fan_desk", step_fan), _Publish()
    return (WorkflowBuilder(start_executor=a_int)
            .add_chain([a_int, a_exp, a_nar, a_ver])
            .add_fan_out_edges(a_ver, [d_bro, d_fan])
            .add_fan_in_edges([d_bro, d_fan], pub)
            .build())


async def _run_framework(state: RunState, ctx: Ctx) -> tuple[RunState, list[dict[str, Any]]]:
    wf = _build_workflow(ctx)
    events: list[dict[str, Any]] = []
    result = state
    t0 = time.perf_counter()
    async for ev in wf.run(state, stream=True):
        if ev.type in ("executor_invoked", "executor_completed"):
            events.append({"event": ev.type, "agent": getattr(ev, "executor_id", None), "t_ms": round((time.perf_counter() - t0) * 1000, 1)})
        elif ev.type == "output":
            result = ev.data
    return result, events


def run_pipeline(match_dir: str | Path, out_dir: str | Path, model=None, profiles: list[Profile] | None = None,
                 use_tracking: bool = True, engine: str = "auto", approvals=None) -> tuple[RunState, Path]:
    ctx = Ctx(str(match_dir), model, profiles, use_tracking, approvals)
    state = RunState(match_dir=str(match_dir))
    events: list[dict[str, Any]] = []
    used = "direct"
    if engine in ("auto", "framework"):
        if HAVE_AGENT_FRAMEWORK:
            state, events = asyncio.run(_run_framework(state, ctx))
            used = "microsoft-agent-framework"
        elif engine == "framework":
            raise ImportError("agent-framework-core is not installed")
    if used == "direct":
        for fn in (step_interpret, step_explain, step_narrate, step_verify, step_broadcast, step_fan):
            fn(state, ctx)
    return state, publish(state, ctx, out_dir, events, used)
