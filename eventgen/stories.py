"""Story definitions, injection (as parameter modifiers) and realization checks.

Why: judges reward explainable moments, so stories are planted on purpose. A
story NEVER writes events. It only changes simulation parameters inside its
window (`modifiers`). After generation `evaluate` inspects the real events,
finds the real seq range and confirms the story is actually visible; if not,
the generator re-simulates with the next deterministic attempt.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal

import yaml
from pydantic import BaseModel, ConfigDict

from .config import Config

STORY_TYPES = ["momentum_swing", "pressing_spell", "late_comeback", "red_card_turning_point",
               "star_player_match", "quiet_then_chaos"]
MIN = 60_000


class Scenario(BaseModel):
    """One planted story as written in a stories YAML file."""
    model_config = ConfigDict(extra="forbid")
    type: Literal["momentum_swing", "pressing_spell", "late_comeback", "red_card_turning_point",
                  "star_player_match", "quiet_then_chaos"]
    team: str = "home"            # home | away | random | a team_id
    start_minute: float | None = None
    end_minute: float | None = None
    strength: float | None = None
    player: str | None = None     # star_player_match only: player_id (else chosen by seed)


@dataclass
class Mod:
    """Parameter modifiers for one team at one instant."""
    shot: float = 1.0
    completion: float = 0.0
    press: float = 1.0
    forward: float = 1.0
    tempo: float = 1.0
    finishing: float = 0.0
    foul: float = 1.0
    tackle: float = 0.0
    force_red: bool = False
    inv: dict[str, float] = field(default_factory=dict)
    fin: dict[str, float] = field(default_factory=dict)
    comp: dict[str, float] = field(default_factory=dict)

    def merge(self, o: "Mod") -> None:
        self.shot *= o.shot
        self.completion += o.completion
        self.press *= o.press
        self.forward *= o.forward
        self.tempo *= o.tempo
        self.finishing += o.finishing
        self.foul *= o.foul
        self.tackle += o.tackle
        self.force_red = self.force_red or o.force_red
        for k, v in o.inv.items():
            self.inv[k] = self.inv.get(k, 1.0) * v
        for k, v in o.fin.items():
            self.fin[k] = self.fin.get(k, 0.0) + v
        for k, v in o.comp.items():
            self.comp[k] = self.comp.get(k, 0.0) + v


@dataclass
class StoryRuntime:
    story_id: str
    type: str
    team_id: str
    opp_id: str
    ws: int
    we: int
    strength: float
    eff: dict[str, float]
    player_id: str | None = None
    activated_ms: int | None = None

    # ------------------------------------------------------------ injection
    def modifiers(self, team: str, now: int, score: dict[str, int]) -> Mod:
        m = Mod()
        e, s = self.eff, self.strength
        t, o = self.team_id, self.opp_id
        tg, og = score[t], score[o]
        span = self.we - self.ws
        if self.type == "momentum_swing":
            if self.ws <= now < self.we:
                dom = t if now < self.ws + span / 2 else o
                if team == dom:
                    m = Mod(completion=e["completion"] * s, shot=1 + e["shot"] * s,
                            press=1 + e["press"] * s, forward=1 + e["forward"] * s)
                else:
                    m = Mod(completion=-e["completion"] * s, shot=max(0.2, 1 - 0.5 * e["shot"] * s),
                            press=max(0.2, 1 - 0.5 * e["press"] * s))
        elif self.type == "pressing_spell":
            if self.ws <= now < self.we:
                if team == t:
                    m = Mod(press=1 + e["press"] * s, tackle=e["tackle_boost"] * s)
                else:
                    m = Mod(completion=e["opp_completion"] * s)
        elif self.type == "late_comeback":
            setup_end = self.ws + e["setup_fraction"] * span
            comeback_start = self.we - e["comeback_fraction"] * span
            if self.ws <= now < setup_end and tg <= og:
                if team == o:
                    m = Mod(shot=1 + e["setup_shot"] * s, finishing=e["setup_finish"] * s)
                else:
                    m = Mod(shot=0.7)
            elif comeback_start <= now < self.we and tg <= og:
                if team == t:
                    m = Mod(shot=1 + e["shot"] * s, finishing=e["finish"] * s, completion=e["completion"] * s,
                            tempo=1 - e["tempo"] * s, forward=1.2)
                else:
                    m = Mod(completion=-0.04 * s, shot=0.7)
        elif self.type == "red_card_turning_point":
            if self.activated_ms is None:
                if team == t and now >= self.ws:
                    m = Mod(foul=e["pre_foul"], force_red=True)
            else:
                if team == t:
                    m = Mod(completion=e["completion"] * s, shot=max(0.1, 1 + e["shot"] * s),
                            press=max(0.1, 1 + e["press"] * s))
                else:
                    m = Mod(shot=1 + e["opp_shot"] * s, completion=e["opp_completion"] * s,
                            press=1 + e["opp_press"] * s)
        elif self.type == "star_player_match":
            if team == t and self.ws <= now < self.we and self.player_id:
                m = Mod(inv={self.player_id: 1 + e["involvement"] * s},
                        fin={self.player_id: e["finish"] * s}, comp={self.player_id: e["completion"] * s})
        elif self.type == "quiet_then_chaos":
            split = self.ws + e["quiet_fraction"] * span
            if self.ws <= now < split:
                m = Mod(tempo=1 + e["quiet_tempo"] * s, shot=max(0.05, 1 + e["quiet_shot"] * s),
                        press=max(0.1, 1 + e["quiet_press"] * s), forward=max(0.3, 1 + e["quiet_forward"] * s))
            elif split <= now < self.we:
                if team == t:
                    m = Mod(shot=1 + e["burst_shot"] * s, tempo=max(0.4, 1 - e["burst_tempo"] * s),
                            completion=e["burst_completion"] * s, press=1 + e["burst_press"] * s)
                else:
                    m = Mod(shot=0.8)
        return m

    def on_event(self, ev: dict[str, Any]) -> None:
        """Hook: the red card story activates when its team really gets a red card."""
        if (self.type == "red_card_turning_point" and self.activated_ms is None and ev["type"] == "card"
                and ev["color"] == "red" and ev["team_id"] == self.team_id and ev["match_clock_ms"] >= self.ws):
            self.activated_ms = ev["match_clock_ms"]

    @property
    def protected_players(self) -> set[str]:
        return {self.player_id} if self.player_id else set()


# ----------------------------------------------------------- scenario input
def resolve_scenarios(spec: Any, rng: random.Random, cfg: Config) -> list[Scenario]:
    """Turn `none | random | yaml path | list` into scenarios (random uses the seed)."""
    if spec in (None, "none", False):
        return []
    if isinstance(spec, list):
        return [s if isinstance(s, Scenario) else Scenario.model_validate(s) for s in spec]
    if spec == "random":
        k = rng.randint(1, cfg.stories.random_max_stories)
        out = []
        for typ in rng.sample(STORY_TYPES, k):
            d = cfg.stories.defaults[typ]
            j = cfg.stories.random_jitter_minutes
            shift = rng.uniform(-j, j)
            lo = max(1.0, d["start_minute"] + shift)
            out.append(Scenario(type=typ, team=rng.choice(["home", "away"]), start_minute=lo,
                                end_minute=min(94.0, lo + (d["end_minute"] - d["start_minute"])),
                                strength=min(1.0, d["strength"] + rng.uniform(-0.1, 0.1))))
        return out
    path = Path(str(spec))
    if not path.exists():
        raise FileNotFoundError(f"stories file not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [Scenario.model_validate(x) for x in raw.get("stories", [])]


def build_runtimes(scenarios: list[Scenario], cfg: Config, rng: random.Random, home_id: str, away_id: str,
                   starters: dict[str, list[Any]]) -> list[StoryRuntime]:
    out: list[StoryRuntime] = []
    for i, sc in enumerate(scenarios, start=1):
        d = cfg.stories.defaults[sc.type]
        team = sc.team
        if team == "random":
            team = rng.choice(["home", "away"])
        tid = {"home": home_id, "away": away_id}.get(team, team)
        if tid not in (home_id, away_id):
            raise ValueError(f"story team {sc.team!r} is not in this match ({home_id}, {away_id})")
        oid = away_id if tid == home_id else home_id
        player = sc.player
        if sc.type == "star_player_match" and not player:
            pool = [p for p in starters[tid] if p.position in ("AM", "W", "ST", "CM")]
            player = rng.choice(pool).player_id
        out.append(StoryRuntime(
            story_id=f"S{i}", type=sc.type, team_id=tid, opp_id=oid,
            ws=int((sc.start_minute if sc.start_minute is not None else d["start_minute"]) * MIN),
            we=int((sc.end_minute if sc.end_minute is not None else d["end_minute"]) * MIN),
            strength=sc.strength if sc.strength is not None else d["strength"],
            eff=cfg.stories.effects[sc.type], player_id=player))
    return out


# ------------------------------------------------------------ realization
@dataclass
class EvalContext:
    cfg: Config
    home_id: str
    away_id: str
    team_names: dict[str, str]
    player_names: dict[str, str]
    direction: Callable[[str, int], int]   # (team_id, period) -> +1 / -1


def _mmss(ms: int) -> str:
    return f"{ms // MIN:02d}:{(ms % MIN) // 1000:02d}"


def _in(ev: Any, lo: int, hi: int) -> bool:
    return lo <= ev.match_clock_ms < hi


def _share(events: list[Any], team: str, lo: int, hi: int) -> tuple[float, int]:
    ps = [e for e in events if e.type == "pass" and _in(e, lo, hi)]
    return (sum(1 for e in ps if e.team_id == team) / len(ps) if ps else 0.0), len(ps)


def _touches(events: list[Any], pid: str, lo: int, hi: int) -> int:
    n = 0
    for e in events:
        if not _in(e, lo, hi):
            continue
        if e.player_id == pid and e.type in ("pass", "shot", "throw_in", "corner", "free_kick", "penalty"):
            n += 1
        elif e.type in ("pass", "throw_in", "corner", "free_kick") and getattr(e, "receiver_id", None) == pid:
            n += 1
    return n


def _team_range(events: list[Any], team: str, lo: int, hi: int) -> tuple[int, int] | None:
    mine = [e for e in events if e.team_id == team and lo <= e.match_clock_ms <= hi]
    return (mine[0].seq, mine[-1].seq) if mine else None


def _top(counter: dict[str, int], n: int = 3) -> list[str]:
    return [k for k, _ in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:n]]


def _truth(rt: StoryRuntime, rng: tuple[int, int], players: list[str], desc: str, details: dict[str, Any],
           ws: int | None = None, we: int | None = None) -> dict[str, Any]:
    return dict(story_id=rt.story_id, type=rt.type, start_seq=rng[0], end_seq=rng[1], team_id=rt.team_id,
                players_involved=players, description=desc, strength=round(rt.strength, 3),
                window_start_ms=rt.ws if ws is None else ws, window_end_ms=rt.we if we is None else we,
                details=details)


def evaluate(rt: StoryRuntime, events: list[Any], ctx: EvalContext) -> dict[str, Any] | None:
    """Return a ground-truth entry if the story is really visible in the events, else None."""
    fn = {"momentum_swing": _eval_momentum, "pressing_spell": _eval_pressing, "late_comeback": _eval_comeback,
          "red_card_turning_point": _eval_red, "star_player_match": _eval_star,
          "quiet_then_chaos": _eval_chaos}[rt.type]
    return fn(rt, events, ctx)


def _eval_momentum(rt, events, ctx):
    mid = rt.ws + (rt.we - rt.ws) // 2
    s1, n1 = _share(events, rt.team_id, rt.ws, mid)
    s2, n2 = _share(events, rt.team_id, mid, rt.we)
    r = ctx.cfg.stories.realization
    if n1 < 10 or n2 < 10 or s1 < 0.5 or s2 > 0.5 or s1 - s2 < r["momentum_min_share_gap"]:
        return None
    rng = _team_range(events, rt.team_id, rt.ws, rt.we)
    if not rng:
        return None
    cnt: dict[str, int] = {}
    for e in events:
        if e.team_id == rt.team_id and e.type == "pass" and _in(e, rt.ws, mid):
            cnt[e.player_id] = cnt.get(e.player_id, 0) + 1
    name, opp = ctx.team_names[rt.team_id], ctx.team_names[rt.opp_id]
    desc = (f"{name} dominate possession from {_mmss(rt.ws)} to {_mmss(mid)} ({s1:.0%} of passes), "
            f"then momentum flips and {opp} take over until {_mmss(rt.we)} ({1 - s2:.0%} of passes).")
    return _truth(rt, rng, _top(cnt), desc, {"flip_at_ms": mid, "dominant_share_first_spell": round(s1, 3),
                                             "dominant_share_second_spell": round(s2, 3)})


def _in_opp_half(e: Any, team: str, ctx: EvalContext) -> bool:
    d = ctx.direction(team, e.period)
    return e.x > 52.5 if d > 0 else e.x < 52.5


def _wins(events: list[Any], team: str, ctx: EvalContext) -> list[Any]:
    return [e for e in events if e.type == "possession_change" and e.to_team_id == team
            and e.reason in ("tackle", "interception", "miscontrol") and _in_opp_half(e, team, ctx)]


def _eval_pressing(rt, events, ctx):
    wins = _wins(events, rt.team_id, ctx)
    inside = [e for e in wins if _in(e, rt.ws, rt.we)]
    mins = (rt.we - rt.ws) / MIN
    last = max((e.match_clock_ms for e in events), default=1)
    base_rate = len(wins) / (last / MIN)
    if len(inside) < ctx.cfg.stories.realization["pressing_min_turnovers"] or len(inside) / mins <= base_rate:
        return None
    cnt: dict[str, int] = {}
    for e in inside:
        cnt[e.player_id] = cnt.get(e.player_id, 0) + 1
    rng = (inside[0].seq, inside[-1].seq)
    name = ctx.team_names[rt.team_id]
    desc = (f"{name} press high between {_mmss(rt.ws)} and {_mmss(rt.we)} and win the ball back "
            f"{len(inside)} times in the opponent half ({len(inside) / mins:.2f}/min vs {base_rate:.2f}/min match average).")
    return _truth(rt, rng, _top(cnt), desc, {"turnovers_in_window": len(inside),
                                             "rate_per_min": round(len(inside) / mins, 3),
                                             "match_avg_rate_per_min": round(base_rate, 3)})


def _eval_comeback(rt, events, ctx):
    t, o = rt.team_id, rt.opp_id
    th = ctx.home_id

    def diff(e):
        return (e.score_home - e.score_away) * (1 if t == th else -1)

    start = rt.we - int(rt.eff["comeback_fraction"] * (rt.we - rt.ws))
    prev, behind, rec = 0, None, None
    for e in events:
        d = diff(e)
        if d < 0 and behind is None:
            behind = e
        if behind is not None and prev < 0 <= d and e.team_id == t and e.match_clock_ms >= start:
            rec = e
        prev = d
    if behind is None or rec is None or diff(events[-1]) < 0:
        return None
    after = [e for e in events if e.team_id == t and e.seq > behind.seq]
    rng = (after[0].seq, rec.seq)
    res = "level" if diff(rec) == 0 else "ahead"
    desc = (f"{ctx.team_names[t]} fall behind at {_mmss(behind.match_clock_ms)} "
            f"({behind.score_home}-{behind.score_away}) and respond with a late goal at "
            f"{_mmss(rec.match_clock_ms)} to get back {res} ({rec.score_home}-{rec.score_away}).")
    return _truth(rt, rng, [rec.player_id], desc, {"conceded_goal_seq": behind.seq, "comeback_goal_seq": rec.seq,
                                                   "final_result": "draw" if diff(events[-1]) == 0 else "win"})


def _eval_red(rt, events, ctx):
    red = next((e for e in events if e.type == "card" and e.color == "red" and e.team_id == rt.team_id
                and e.match_clock_ms >= rt.ws), None)
    if red is None:
        return None
    end = events[-1].match_clock_ms
    r = ctx.cfg.stories.realization
    if (end - red.match_clock_ms) / MIN < r["red_card_min_minutes_after"]:
        return None
    before, nb = _share(events, rt.team_id, 0, red.match_clock_ms)
    after, na = _share(events, rt.team_id, red.match_clock_ms, end + 1)
    if nb < 20 or na < 20 or before - after < r["red_card_min_share_drop"]:
        return None
    rng = _team_range(events, rt.team_id, red.match_clock_ms, end)
    desc = (f"{ctx.team_names[rt.team_id]} are reduced to ten men at {_mmss(red.match_clock_ms)} "
            f"({ctx.player_names[red.player_id]} sent off); their share of passes falls from "
            f"{before:.0%} to {after:.0%} for the rest of the match.")
    return _truth(rt, rng, [red.player_id], desc, {"red_card_seq": red.seq, "pass_share_before": round(before, 3),
                                                   "pass_share_after": round(after, 3)},
                  ws=red.match_clock_ms, we=end)


def star_stats(events: list[Any], pid: str, lo: int, hi: int) -> dict[str, int]:
    assists = {e.assist_event_id for e in events if e.type in ("shot", "penalty") and e.assist_event_id}
    mine = [e for e in events if e.player_id == pid and _in(e, lo, hi)]
    return {"touches": _touches(events, pid, lo, hi),
            "shots": sum(1 for e in mine if e.type in ("shot", "penalty")),
            "goals": sum(1 for e in mine if e.type in ("shot", "penalty") and e.outcome == "goal"),
            "key_passes": sum(1 for e in mine if e.event_id in assists)}


def _eval_star(rt, events, ctx):
    pid = rt.player_id
    team_touch = sum(1 for e in events if e.team_id == rt.team_id and _in(e, rt.ws, rt.we)
                     and e.type in ("pass", "shot", "throw_in", "corner", "free_kick", "penalty"))
    st = star_stats(events, pid, rt.ws, rt.we)
    r = ctx.cfg.stories.realization
    if team_touch == 0:
        return None
    share = st["touches"] / team_touch
    if share < r["star_min_touch_share"] or st["goals"] + st["key_passes"] < r["star_min_goals_plus_key_passes"]:
        return None
    rng = _team_range(events, rt.team_id, rt.ws, rt.we)
    desc = (f"{ctx.player_names[pid]} ({ctx.team_names[rt.team_id]}) has a standout spell between "
            f"{_mmss(rt.ws)} and {_mmss(rt.we)}: {st['touches']} touches ({share:.0%} of the team's), "
            f"{st['shots']} shots, {st['goals']} goals and {st['key_passes']} key passes.")
    return _truth(rt, rng, [pid], desc, {**st, "team_touch_share": round(share, 3)})


def _eval_chaos(rt, events, ctx):
    e = rt.eff
    split = rt.ws + int(e["quiet_fraction"] * (rt.we - rt.ws))
    r = ctx.cfg.stories.realization
    quiet_shots = sum(1 for x in events if x.type in ("shot", "penalty") and _in(x, rt.ws, split))
    burst = [x for x in events if x.type in ("shot", "penalty") and x.team_id == rt.team_id and _in(x, split, rt.we)]
    count = lambda lo, hi: sum(1 for x in events if x.type not in ("pressure",) and _in(x, lo, hi))  # noqa: E731
    quiet_rate = count(rt.ws, split) / ((split - rt.ws) / MIN)
    all_rate = len(events) / (events[-1].match_clock_ms / MIN)
    if quiet_shots > r["quiet_max_shots"] or len(burst) < r["chaos_min_shots"] or quiet_rate >= all_rate:
        return None
    cnt: dict[str, int] = {}
    for x in burst:
        cnt[x.player_id] = cnt.get(x.player_id, 0) + 1
    rng = (_team_range(events, rt.team_id, rt.ws, split) or (burst[0].seq, burst[0].seq))[0], burst[-1].seq
    desc = (f"A quiet, controlled stretch from {_mmss(rt.ws)} to {_mmss(split)} ({quiet_shots} shot(s), "
            f"{quiet_rate:.1f} events/min vs {all_rate:.1f} match average) is followed by a burst of "
            f"{len(burst)} shots from {ctx.team_names[rt.team_id]} before {_mmss(rt.we)}.")
    return _truth(rt, rng, _top(cnt), desc, {"split_ms": split, "quiet_shots": quiet_shots, "burst_shots": len(burst),
                                             "quiet_events_per_min": round(quiet_rate, 2),
                                             "match_events_per_min": round(all_rate, 2)})
