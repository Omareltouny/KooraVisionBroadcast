"""Possession-loop match simulation.

Why: a match is a chain of possessions; each step picks the next action from
probabilities that depend on zone, role, team style and pressure. All numbers
come from the config. One seeded `random.Random` is passed explicitly, so the
same seed gives byte-identical output.
"""
from __future__ import annotations

import math
import random
from dataclasses import replace
from datetime import datetime, timedelta
from typing import Any

from .config import Config, load_config
from .groundtruth import build_ground_truth
from .league import Club, League, away_kit, build_league
from .pressure import pressure_level, pressure_probability
from .schema import (EVENTS_ADAPTER, GENERATOR_VERSION, PASS_LIKE, Match, MatchMeta, PeriodMeta, Score)
from .stories import (EvalContext, Mod, StoryRuntime, build_runtimes, evaluate, resolve_scenarios)

DEAD_REASONS = ("out_of_play", "foul")


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


class MatchSimulator:
    def __init__(self, cfg: Config, rng: random.Random, match_id: str, home: Club, away: Club,
                 runtimes: list[StoryRuntime]) -> None:
        self.cfg, self.rng, self.match_id = cfg, rng, match_id
        self.L, self.W = cfg.pitch.length_m, cfg.pitch.width_m
        self.clubs = {home.team_id: home, away.team_id: away}
        self.home_id, self.away_id = home.team_id, away.team_id
        self.ids = (self.home_id, self.away_id)
        self.rts = runtimes
        self.pos_of = {p.player_id: p.position for c in self.clubs.values() for p in c.team.players}
        self.attr = {pid: a for c in self.clubs.values() for pid, a in c.attrs.items()}
        self.lane = {pid: a.lane_y for pid, a in self.attr.items()}  # local copy: subs inherit lanes
        self.on_pitch = {t: [p.player_id for p in c.team.players if p.starter] for t, c in self.clubs.items()}
        self.bench = {t: [p.player_id for p in c.team.players if not p.starter] for t, c in self.clubs.items()}
        self.score = {self.home_id: 0, self.away_id: 0}
        self.yellows: dict[str, int] = {}
        self.events: list[dict[str, Any]] = []
        self.periods: list[PeriodMeta] = []
        self.seq = self.poss_id = self.clock = self.offset = self.stop_acc = 0
        self.period = 1
        self.dir: dict[str, int] = {}
        self.poss = self.home_id
        self.carrier = ""
        self.ball = (self.L / 2, self.W / 2)
        self.pressed = 0.0
        self.last_pass: dict[str, Any] | None = None
        m = cfg.match
        self.subbed_on: set[str] = set()
        self.sub_plan = {t: sorted(int(rng.uniform(*m.sub_minute_range) * 60000)
                                   for _ in range(min(m.max_substitutions, rng.randint(*m.sub_count_range))))
                         for t in self.ids}

    # ------------------------------------------------------------ helpers
    def opp(self, t: str) -> str:
        return self.away_id if t == self.home_id else self.home_id

    def flip(self, x: float, y: float) -> tuple[float, float]:
        return self.L - x, self.W - y

    def _abs(self, frame: str, x: float, y: float) -> tuple[float, float]:
        if self.dir[frame] < 0:
            x, y = self.L - x, self.W - y
        return round(_clamp(x, 0, self.L), 2), round(_clamp(y, 0, self.W), 2)

    def _tick(self, ms: float) -> None:
        self.clock += int(ms)

    def _gap(self) -> None:
        self._tick(self.rng.randint(*self.cfg.timing.event_gap_ms))

    def _range(self, rng_pair: Any) -> float:
        return self.rng.uniform(rng_pair[0], rng_pair[1])

    def _match_clock(self) -> int:
        return self.offset + self.clock

    def _game_mod(self, team: str) -> Mod:
        """Home edge, cautious start, late push and score-dependent attacking."""
        g = self.cfg.game
        m = Mod()
        if team == self.home_id:
            m.shot *= g.home_shot_mult
            m.completion += g.home_completion_bonus
        minute = self.clock / 60000.0
        if self.period == 1 and minute < g.early_minutes:
            m.shot *= g.early_shot_mult
        if self.period == 2:
            m.shot *= g.second_half_shot_mult * (1.0 + g.late_ramp * min(minute / 45.0, 1.0))
        diff = self.score[team] - self.score[self.opp(team)]
        if diff < 0:
            m.shot *= 1.0 + g.trailing_boost * min(-diff, 2)
        elif diff > 0:
            m.shot *= 1.0 - g.leading_cut * min(diff, 2)
        return m

    def _mods(self, team: str) -> Mod:
        m = self._game_mod(team)
        for rt in self.rts:
            m.merge(rt.modifiers(team, self._match_clock(), self.score))
        return m

    def _emit(self, type_: str, team: str, player: str, x: float, y: float, frame: str | None = None,
              end: tuple[float, float] | None = None, **fields: Any) -> dict[str, Any]:
        frame = frame or team
        ax, ay = self._abs(frame, x, y)
        self.seq += 1
        ev: dict[str, Any] = dict(
            event_id=f"{self.match_id}-E{self.seq:05d}", match_id=self.match_id, seq=self.seq, period=self.period,
            clock_ms=self.clock, match_clock_ms=self._match_clock(), type=type_, team_id=team, player_id=player,
            x=ax, y=ay, possession_id=self.poss_id, score_home=self.score[self.home_id],
            score_away=self.score[self.away_id])
        if end is not None:
            ex, ey = self._abs(frame, *end)
            ev["end_x"], ev["end_y"] = ex, ey
            if type_ in PASS_LIKE:
                ev["pass_length_m"] = round(math.hypot(ex - ax, ey - ay), 2)
        ev.update(fields)
        self.events.append(ev)
        for rt in self.rts:
            rt.on_event(ev)
        return ev

    # -------------------------------------------------------- player choice
    def _pick(self, team: str, nx: float, ny: float, exclude: tuple[str, ...] = (), purpose: str = "pass") -> str:
        r, mods = self.cfg.roles, self._mods(team)
        ids, ws = [], []
        for pid in self.on_pitch[team]:
            if pid in exclude:
                continue
            pos = self.pos_of[pid]
            if purpose == "press" and pos == "GK":
                continue
            w = (math.exp(-(((r.anchor_x[pos] - nx) / r.anchor_spread_x) ** 2))
                 * math.exp(-(((self.lane[pid] - ny) / r.lane_spread_y) ** 2))
                 * self.attr[pid].involvement * r.involvement[pos] * mods.inv.get(pid, 1.0)
                 * (self.cfg.game.sub_involvement_mult if pid in self.subbed_on else 1.0))
            ids.append(pid)
            ws.append(w + 1e-12)
        return self.rng.choices(ids, ws)[0]

    def _gk(self, team: str) -> str:
        return next(p for p in self.on_pitch[team] if self.pos_of[p] == "GK")

    def _taker(self, team: str, near_goal: bool, nx: float, ny: float) -> str:
        t = self.clubs[team].set_piece_taker_id
        if near_goal and t in self.on_pitch[team] and self.rng.random() < 0.7:
            return t
        return self._pick(team, nx, ny, purpose="press")

    # ------------------------------------------------------------ possession
    def _change_possession(self, team: str, player: str, nx: float, ny: float, reason: str) -> None:
        frm = self.poss
        self.poss_id += 1
        self.poss, self.carrier, self.ball = team, player, (nx, ny)
        self._emit("possession_change", team, player, nx, ny, from_team_id=frm, to_team_id=team, reason=reason)
        self.last_pass = None

    def _dead(self, kind: str) -> None:
        self._tick(self._range(self.cfg.timing.dead_ball_ms[kind]))
        self._check_subs()

    # --------------------------------------------------------- substitutions
    def _check_subs(self) -> None:
        if self.period != 2:
            return
        for t in self.ids:
            while self.sub_plan[t] and self.sub_plan[t][0] <= self._match_clock():
                self.sub_plan[t].pop(0)
                self._substitute(t)

    def _substitute(self, team: str) -> None:
        prot = {p for rt in self.rts if rt.team_id == team for p in rt.protected_players}
        outs = [p for p in self.on_pitch[team] if self.pos_of[p] != "GK" and p != self.carrier and p not in prot]
        if not outs or not self.bench[team]:
            return
        off = self.rng.choice(outs)
        same = [b for b in self.bench[team] if self.pos_of[b] == self.pos_of[off]]
        pool = same or [b for b in self.bench[team] if self.pos_of[b] != "GK"]
        if not pool:
            return
        on = self.rng.choice(pool)
        self._emit("substitution", team, off, self.L / 2, 0.0, player_off_id=off, player_on_id=on)
        self.on_pitch[team][self.on_pitch[team].index(off)] = on
        self.bench[team].remove(on)
        self.subbed_on.add(on)
        self.lane[on] = self.lane[off]
        self.stop_acc += self.cfg.match.stoppage_per_sub_ms
        self._tick(self._range(self.cfg.timing.dead_ball_ms["substitution"]))

    # ----------------------------------------------------------- main step
    def _step(self) -> None:
        cfg = self.cfg
        A = self.poss
        D = self.opp(A)
        bx, by = self.ball
        mA, mD = self._mods(A), self._mods(D)
        zone = "own_third" if bx < 35 else ("middle" if bx < 70 else "final_third")
        self.pressed = 0.0
        p = pressure_probability(cfg, self.clubs[D].profile["pressing_intensity"], zone, mD.press)
        if self.rng.random() < p:
            presser = self._pick(D, *self.flip(bx, by), purpose="press")
            dist = round(self._range(cfg.pressure.distance_m), 2)
            self._emit("pressure", D, presser, bx, by, frame=A, pressed_player_id=self.carrier, distance_m=dist,
                       duration_ms=self.rng.randint(*cfg.pressure.duration_ms))
            self.pressed = pressure_level(cfg, dist)
            self._gap()
            if self.rng.random() < cfg.pressure.tackle_attempt_prob * (0.5 + self.pressed):
                if self._contest(presser, mA, mD):
                    return
        if (self.pos_of[self.carrier] != "GK"
                and self.rng.random() < cfg.foul.offensive_foul_prob * mA.foul):
            self._attacker_foul()
            return
        sw = self._shot_weight(mA)
        if self.rng.random() < sw / (sw + 1.0):
            self._shot(mA)
        else:
            self._pass(self._choose_pass_type(A, mA), "pass", mA=mA)

    def _contest(self, presser: str, mA: Mod, mD: Mod) -> bool:
        cfg = self.cfg
        A, D = self.poss, self.opp(self.poss)
        bx, by = self.ball
        foul_p = cfg.foul.defender_foul_prob * mD.foul * (cfg.foul.box_foul_mult if self._in_box(bx, by) else 1.0)
        if self.rng.random() < foul_p:
            self._defender_foul(presser, mD)
            return True
        win = _clamp(cfg.pressure.tackle_win_prob + mD.tackle + cfg.pressure.quality_weight
                     * (self.clubs[D].profile["quality"] - self.clubs[A].profile["quality"]), 0.05, 0.95)
        won = self.rng.random() < win
        self._emit("tackle", D, presser, bx, by, frame=A, opponent_id=self.carrier, outcome="won" if won else "lost")
        self._gap()
        self._tick(self._range(cfg.timing.action_ms["tackle"]))
        if won:
            self._change_possession(D, presser, *self.flip(bx, by), "tackle")
        return won

    def _in_box(self, x: float, y: float) -> bool:
        p = self.cfg.pitch
        return x >= self.L - p.penalty_area_depth_m and abs(y - self.W / 2) <= p.penalty_area_width_m / 2

    # ------------------------------------------------------------------ fouls
    def _card_decision(self, fouler: str, mods: Mod) -> str | None:
        f = self.cfg.foul
        if mods.force_red:
            return "red"
        yellow = f.yellow_prob * (f.second_yellow_mult if self.yellows.get(fouler, 0) >= 1 else 1.0)
        r = self.rng.random()
        return "red" if r < f.red_prob else ("yellow" if r < f.red_prob + yellow else None)

    def _foul_and_cards(self, team: str, fouler: str, frame: str, fx: float, fy: float, fouled: str,
                        color: str | None) -> None:
        self._emit("foul", team, fouler, fx, fy, frame=frame, fouled_player_id=fouled, card=color)
        self.stop_acc += self.cfg.match.stoppage_per_foul_ms
        if color:
            self._gap()
            second = color == "yellow" and self.yellows.get(fouler, 0) >= 1
            reasons = [(color, "reckless foul" if color == "yellow" else "serious foul play")]
            if color == "yellow":
                self.yellows[fouler] = self.yellows.get(fouler, 0) + 1
            if second:
                reasons.append(("red", "second yellow"))
            for col, why in reasons:
                self._emit("card", team, fouler, fx, fy, frame=frame, color=col, reason=why)
                self.stop_acc += self.cfg.match.stoppage_per_card_ms
                self._gap()
                if col == "red":
                    self.on_pitch[team].remove(fouler)
            self._tick(self._range(self.cfg.timing.dead_ball_ms["card"]))
        else:
            self._tick(self._range(self.cfg.timing.dead_ball_ms["foul"]))

    def _defender_foul(self, fouler: str, mD: Mod) -> None:
        A, D = self.poss, self.opp(self.poss)
        bx, by = self.ball
        color = self._card_decision(fouler, mD)
        self._foul_and_cards(D, fouler, A, bx, by, self.carrier, color)
        if self._in_box(bx, by):
            self._penalty()
        else:
            self._check_subs()
            taker = self._taker(A, bx > 55, bx, by)
            self._pass("free_kick", "free_kick", passer=taker, start=(bx, by))

    def _attacker_foul(self) -> None:
        A, D = self.poss, self.opp(self.poss)
        bx, by = self.ball
        victim = self._pick(D, *self.flip(bx, by), purpose="press")
        color = self._card_decision(self.carrier, self._mods(A))
        self._foul_and_cards(A, self.carrier, A, bx, by, victim, color)
        nx, ny = self.flip(bx, by)
        self._change_possession(D, victim, nx, ny, "foul")
        self._check_subs()
        taker = self._taker(D, nx > 55, nx, ny)
        self._pass("free_kick", "free_kick", passer=taker, start=(nx, ny))

    # ------------------------------------------------------------------ shots
    def _shot_weight(self, mA: Mod) -> float:
        s = self.cfg.shot
        bx, by = self.ball
        d = math.hypot(self.L - bx, self.W / 2 - by)
        if d >= s.max_distance_m:
            return 0.0
        pos = self.pos_of[self.carrier]
        return (s.weight_scale * (1 - d / s.max_distance_m) ** s.distance_exponent
                * self.cfg.roles.shot_mult[pos] * self.clubs[self.poss].profile["attack_intensity"] * mA.shot
                * mA.inv.get(self.carrier, 1.0) ** 0.5
                * (self.cfg.game.sub_shot_mult if self.carrier in self.subbed_on else 1.0))

    def _shot_end(self, outcome: str, bx: float, by: float) -> tuple[float, float]:
        half = self.cfg.pitch.goal_width_m / 2
        c = self.W / 2
        if outcome == "goal":
            return self.L, c + self.rng.choice([-1, 1]) * self.rng.uniform(1.5, half - 0.2)
        if outcome == "saved":
            return self.L, c + self.rng.uniform(-half + 0.2, half - 0.2)
        if outcome == "post":
            return self.L, c + self.rng.choice([-1, 1]) * half
        if outcome == "off_target":
            side = self.rng.choice([-1, 1])
            return self.L, _clamp(c + side * (half + self.rng.uniform(0.5, 6.0)), 0, self.W)
        dx, dy = self.L - bx, c - by
        n = math.hypot(dx, dy) or 1.0
        k = self.rng.uniform(1.0, 4.0)
        return bx + dx / n * k, by + dy / n * k

    def _shot(self, mA: Mod) -> None:
        s = self.cfg.shot
        A, D = self.poss, self.opp(self.poss)
        bx, by = self.ball
        shooter = self.carrier
        d = math.hypot(self.L - bx, self.W / 2 - by)
        block_p = s.block_prob * (0.8 + 0.5 * self.pressed)
        off_p = s.off_target_base + s.off_target_per_m * d
        r = self.rng.random()
        if r < block_p:
            outcome = "blocked"
        elif r < block_p + off_p:
            outcome = "off_target"
        elif r < block_p + off_p + s.post_prob:
            outcome = "post"
        else:
            gp = _clamp(s.goal_near * math.exp(-d / s.goal_decay_m)
                        + (self.attr[shooter].skill - 0.65) * self.cfg.player.skill_finish_weight
                        + mA.finishing + mA.fin.get(shooter, 0.0), s.goal_min, s.goal_max)
            outcome = "goal" if self.rng.random() < gp else "saved"
        assist = None
        lp = self.last_pass
        if (lp and lp["receiver"] == shooter and lp["poss"] == self.poss_id
                and self._match_clock() - lp["t"] <= s.assist_window_ms):
            assist = lp["event_id"]
        if outcome == "goal":
            self.score[A] += 1
        end = self._shot_end(outcome, bx, by)
        body = ("head" if (bx > self.L - s.header_zone_m and self.rng.random() < s.header_prob)
                else self.rng.choice(["right_foot", "left_foot"]))
        ev = self._emit("shot", A, shooter, bx, by, end=end, outcome=outcome,
                        shot_speed_ms=round(self._range(s.speed_ms), 2), body_part=body, assist_event_id=assist)
        self._after_shot(outcome, bx, by, ev, end, self._range(self.cfg.timing.action_ms["shot"]))

    def _penalty(self) -> None:
        A = self.poss
        on = self.on_pitch[A]
        t = self.clubs[A].set_piece_taker_id
        taker = t if t in on else max((p for p in on if self.pos_of[p] != "GK"), key=lambda p: self.attr[p].skill)
        self._tick(self._range(self.cfg.timing.dead_ball_ms["penalty"]))
        w = self.cfg.penalty.outcome_weights
        outcome = self.rng.choices(list(w), list(w.values()))[0]
        spot = (self.L - self.cfg.pitch.penalty_spot_m, self.W / 2)
        if outcome == "goal":
            self.score[A] += 1
        end = self._shot_end(outcome, *spot)
        ev = self._emit("penalty", A, taker, *spot, end=end, outcome=outcome,
                        shot_speed_ms=round(self._range(self.cfg.shot.speed_ms), 2),
                        body_part=self.rng.choice(["right_foot", "left_foot"]), assist_event_id=None)
        self.carrier = taker
        self.ball = spot
        self._after_shot(outcome, *spot, ev, end, self._range(self.cfg.timing.action_ms["shot"]))

    def _goal_kick(self, team: str) -> None:
        """Dead time, then the goalkeeper restarts play from the six-yard box."""
        self._dead("goal_kick")
        self._pass("goal_kick", "goal_kick", passer=self._gk(team),
                   start=(5.5, self.W / 2 + self._range((-9.0, 9.0))))

    def _after_shot(self, outcome: str, bx: float, by: float, shot_ev: dict[str, Any],
                    end: tuple[float, float], dur: float) -> None:
        cfg = self.cfg
        A, D = self.poss, self.opp(self.poss)
        gk = self._gk(D)
        goalmouth = (self._range((2.0, 8.0)), self.W / 2 + self._range((-4.0, 4.0)))
        if outcome == "goal":
            self._tick(dur)
            self.stop_acc += cfg.match.stoppage_per_goal_ms
            self._dead("goal")
            kicker = self._pick(D, self.L / 2, self.W / 2)
            self._change_possession(D, kicker, self.L / 2, self.W / 2, "shot_result")
            self._tick(self._range(cfg.timing.dead_ball_ms["kickoff"]))
            return
        table = {"saved": cfg.shot.after_saved, "blocked": cfg.shot.after_blocked, "post": cfg.shot.after_post,
                 "off_target": cfg.shot.after_off_target}[outcome]
        branch = self.rng.choices(list(table), list(table.values()))[0]
        if outcome == "saved":
            flight = _clamp(math.hypot(end[0] - bx, end[1] - by) / max(shot_ev["shot_speed_ms"], 1.0) * 1000, 250, 1500)
            self._tick(flight)
            kind = {"keeper": "caught", "corner": "tipped"}.get(branch, "parried")
            self._emit("save", D, gk, self.L - 0.4, end[1], frame=A, shot_event_id=shot_ev["event_id"], outcome=kind)
            self._tick(max(dur - flight, 600))
        else:
            self._tick(dur)
        if branch == "corner":
            self._corner(A)
        elif branch == "rebound":
            self.ball = (self.L - self._range((3, 8)), self.W / 2 + self._range((-6, 6)))
            self.carrier = self._pick(A, *self.ball)
        elif branch == "keeper":
            self._change_possession(D, gk, *goalmouth, "shot_result")
            self._dead("keeper_hold")
        elif branch == "goal_kick":
            self._change_possession(D, gk, *goalmouth, "shot_result")
            self._goal_kick(D)
        else:  # defender wins the loose ball
            nx, ny = self.flip(bx, by)
            self._change_possession(D, self._pick(D, nx, ny, purpose="press"), nx, ny, "shot_result")

    def _corner(self, team: str) -> None:
        side = self.rng.choice([0.0, self.W])
        self._dead("corner")
        self.poss_id += 1  # a corner starts a fresh possession for the same team
        taker = self._taker(team, True, self.L, side)
        self._pass("corner", "corner", passer=taker, start=(self.L, side))

    # ----------------------------------------------------------------- passes
    def _choose_pass_type(self, A: str, mA: Mod) -> str:
        p = self.cfg.passing
        bx, by = self.ball
        d = self.clubs[A].profile["buildup_directness"]
        w = dict(p.base_weights)
        w["forward"] *= (0.5 + d) * mA.forward
        w["long"] *= (0.3 + 2 * d) * (1.8 if bx < 30 else 1.0) * (0.3 if bx > 70 else 1.0)
        w["back"] *= (1.5 - d) * (1.6 if bx > 75 else 1.0)
        if bx >= p.cross_min_x and min(by, self.W - by) <= p.cross_wide_band_m:
            w["cross"] = p.cross_weight
        if self.pos_of[self.carrier] == "GK":
            w["long"] *= p.goalkeeper_long_mult
        return self.rng.choices(list(w), list(w.values()))[0]

    def _target(self, kind: str, sx: float, sy: float) -> tuple[float, float]:
        p, r = self.cfg.passing, self.rng
        L, W = self.L, self.W
        if kind == "corner":
            tx, ty = L - r.uniform(3, 12), W / 2 + r.gauss(0, 6)
        elif kind == "throw_in":
            tx, ty = sx + r.uniform(-8, 16), sy + (1 if sy < W / 2 else -1) * r.uniform(4, 18)
        elif kind == "cross" or (kind == "free_kick" and sx >= p.cross_min_x - 12):
            tx, ty = L - r.uniform(4, 16), W / 2 + r.gauss(0, 6)
        else:
            if kind == "goal_kick":
                geo = "goal_kick_short" if r.random() < p.goal_kick_short_prob else "long"
            else:
                geo = r.choice(["forward", "long", "short"]) if kind == "free_kick" else kind
            n = r.uniform(*p.length_m[geo])
            ang = {"short": lambda: r.uniform(-math.pi, math.pi),
                   "goal_kick_short": lambda: r.uniform(-math.pi / 3, math.pi / 3),
                   "forward": lambda: r.uniform(-math.pi / 4, math.pi / 4),
                   "long": lambda: r.uniform(-math.pi / 3, math.pi / 3),
                   "back": lambda: math.pi + r.uniform(-0.6, 0.6),
                   "lateral": lambda: r.choice([-1, 1]) * math.pi / 2 + r.uniform(-0.3, 0.3)}[geo]()
            tx, ty = sx + n * math.cos(ang), sy + n * math.sin(ang)
        return _clamp(tx, 1, L - 1), _clamp(ty, 1, W - 1)

    def _out_point(self, sx: float, sy: float, tx: float, ty: float) -> tuple[float, float, str] | None:
        """Where a misplayed pass leaves the pitch: along its line if it overshoots, else the nearest touchline."""
        dx, dy = tx - sx, ty - sy
        if math.hypot(dx, dy) < 1e-6:
            return None
        k = self.rng.uniform(1.3, 3.0)
        if not (0 < sx + dx * k < self.L and 0 < sy + dy * k < self.W):
            ts = {}
            if dx > 0:
                ts["right"] = (self.L - sx) / dx
            elif dx < 0:
                ts["left"] = -sx / dx
            if dy > 0:
                ts["top"] = (self.W - sy) / dy
            elif dy < 0:
                ts["bottom"] = -sy / dy
            side = min(ts, key=ts.get)
            t = ts[side]
            return _clamp(sx + dx * t, 0, self.L), _clamp(sy + dy * t, 0, self.W), side
        # stays inside along its line: the ball runs on and leaves over the nearer touchline
        return _clamp(tx, 1, self.L - 1), (0.0 if ty < self.W / 2 else self.W), ("bottom" if ty < self.W / 2 else "top")

    def _pass(self, kind: str, event_type: str, passer: str | None = None, start: tuple[float, float] | None = None,
              mA: Mod | None = None) -> None:
        cfg, rng = self.cfg, self.rng
        A, D = self.poss, self.opp(self.poss)
        mA = mA or self._mods(A)
        sx, sy = start or self.ball
        passer = passer or self.carrier
        self.ball, self.carrier = (sx, sy), passer
        tx, ty = self._target(kind, sx, sy)
        receiver = self._pick(A, tx, ty, exclude=(passer,))
        p = (cfg.passing.completion[kind] + self.clubs[A].profile["quality"]
             + (self.attr[passer].skill - 0.65) * cfg.player.skill_pass_weight + mA.completion
             + mA.comp.get(passer, 0.0) - cfg.passing.pressure_penalty * self.pressed)
        p = _clamp(p, 0.05, 0.98)
        speed = round(self._range(cfg.passing.speed_ms[kind]), 2)
        aerial = ((kind in ("long", "cross", "corner") or (kind == "goal_kick" and math.hypot(tx - sx, ty - sy) > 28))
                  and rng.random() < 0.12)
        body = "hands" if kind == "throw_in" else ("head" if aerial else rng.choice(["right_foot", "left_foot"]))
        dur = self._range(cfg.timing.action_ms.get(kind, cfg.timing.action_ms["short"])) * mA.tempo
        common = dict(ball_speed_ms=speed, body_part=body)
        if rng.random() < p:
            ev = self._emit(event_type, A, passer, sx, sy, end=(tx, ty), receiver_id=receiver, outcome="complete",
                            **common)
            self._tick(dur)
            self.ball, self.carrier = (tx, ty), receiver
            self.last_pass = dict(event_id=ev["event_id"], receiver=receiver, poss=self.poss_id,
                                  t=self._match_clock())
            return
        fs = cfg.passing.failure_split
        kindf = rng.choices(list(fs), list(fs.values()))[0]
        out = None
        if kindf == "out":
            out = self._out_point(sx, sy, tx, ty)
            if out is None:
                kindf = "incomplete"
        if kindf == "intercepted":
            f = rng.uniform(0.3, 1.0)
            end = (sx + (tx - sx) * f, sy + (ty - sy) * f)
        elif kindf == "incomplete":
            end = (_clamp(tx + rng.gauss(0, 3), 1, self.L - 1), _clamp(ty + rng.gauss(0, 3), 1, self.W - 1))
        else:
            end = (out[0], out[1])
        self._emit(event_type, A, passer, sx, sy, end=end, receiver_id=None, outcome=kindf, **common)
        self._tick(dur)
        if kindf in ("intercepted", "incomplete"):
            nx, ny = self.flip(*end)
            who = self._pick(D, nx, ny, purpose="press")
            self._change_possession(D, who, nx, ny, "interception" if kindf == "intercepted" else "miscontrol")
            return
        ex, ey, side = out
        if side == "right":      # over the opponent byline: goal kick
            self._change_possession(D, self._gk(D), 5.5, self.W / 2, "out_of_play")
            self._goal_kick(D)
        elif side == "left":     # over own byline: corner for the opponent
            cx, cy = self.flip(0.0, 0.0 if ey < self.W / 2 else self.W)
            taker = self._taker(D, True, cx, cy)
            self._change_possession(D, taker, cx, cy, "out_of_play")
            self._dead("corner")
            self._pass("corner", "corner", passer=taker, start=(cx, cy))
        else:                    # touchline: throw-in for the opponent
            nx, ny = self.flip(ex, ey)
            thrower = self._pick(D, nx, ny, purpose="press")
            self._change_possession(D, thrower, nx, ny, "out_of_play")
            self._dead("throw_in")
            self._pass("throw_in", "throw_in", passer=thrower, start=(nx, ny))

    # ---------------------------------------------------------------- periods
    def _end_ms(self) -> int:
        m = self.cfg.match
        add = _clamp(math.ceil(self.stop_acc / 60000) * 60000, m.stoppage_min_ms, m.stoppage_max_ms)
        return m.period_length_ms + int(add)

    def _start_period(self, period: int, kick: str) -> None:
        self.period, self.clock, self.stop_acc = period, 0, 0
        self.dir = ({self.home_id: 1, self.away_id: -1} if period == 1 else {self.home_id: -1, self.away_id: 1})
        self.poss_id += 1
        self.poss = kick
        self.ball = (self.L / 2, self.W / 2)
        self.carrier = self._pick(kick, *self.ball)
        self._emit("period_start", kick, self.carrier, *self.ball)
        self._gap()

    def _end_period(self, start_offset: int) -> None:
        base = self.cfg.match.period_length_ms
        self.clock = max(self.clock, self._end_ms())
        self._emit("period_end", self.poss, self.carrier, *self.ball, frame=self.poss)
        dirs = {t: ("left_to_right" if self.dir[t] > 0 else "right_to_left") for t in self.ids}
        self.periods.append(PeriodMeta(period=self.period, start_match_clock_ms=start_offset,
                                       end_match_clock_ms=self.offset + self.clock, scheduled_duration_ms=base,
                                       stoppage_ms=self.clock - base, attacking_direction=dirs))

    def run(self) -> list[dict[str, Any]]:
        first = self.rng.choice(self.ids)
        for period in (1, 2):
            start_offset = self.offset
            self._start_period(period, first if period == 1 else self.opp(first))
            while self.clock < self._end_ms():
                self._step()
            self._end_period(start_offset)
            self.offset = self.offset + self.clock
        return self.events


# --------------------------------------------------------------------- API
def _kickoff(cfg: Config, matchday: int) -> str:
    t = datetime.fromisoformat(cfg.competition.first_kickoff_utc.replace("Z", "+00:00"))
    return (t + timedelta(days=cfg.competition.matchday_interval_days * (matchday - 1))).strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_match(seed: int, stories: Any = "random", config: Config | str | None = None,
                   league: League | None = None, fixture: int = 0) -> Match:
    """Generate one full match from a seed.

    `stories`: "random" | "none" | path to a stories YAML | list of Scenario/dicts.
    Teams come from the fictional league built from `seed` (or a supplied league).
    """
    cfg = config if isinstance(config, Config) else load_config(config)
    league = league or build_league(seed, cfg)
    matchday, hi, ai = league.fixtures[fixture % len(league.fixtures)]
    home, away = league.clubs[hi], league.clubs[ai]
    kit = away_kit(home.team.primary_color, away.team.primary_color, away.team.secondary_color)
    if kit != (away.team.primary_color, away.team.secondary_color):  # shirt clash: away team wears its away kit
        away = replace(away, team=away.team.model_copy(update={"primary_color": kit[0], "secondary_color": kit[1]}))
    match_id = f"m{seed:05d}-{home.team.short_name.lower()}-{away.team.short_name.lower()}"
    scenarios = resolve_scenarios(stories, random.Random(f"stories:{seed}"), cfg)
    starters = {c.team_id: [p for p in c.team.players if p.starter] for c in (home, away)}
    team_names = {home.team_id: home.team.name, away.team_id: away.team.name}
    player_names = {p.player_id: p.name for c in (home, away) for p in c.team.players}
    attempts = cfg.stories.max_attempts if scenarios else 1
    best: tuple[int, int, Any] | None = None
    for attempt in range(attempts):
        rts = build_runtimes(scenarios, cfg, random.Random(f"star:{seed}"), home.team_id, away.team_id, starters)
        sim = MatchSimulator(cfg, random.Random(f"match:{seed}:{attempt}"), match_id, home, away, rts)
        events = EVENTS_ADAPTER.validate_python(sim.run())
        dirs = {(p.period, t): (1 if d == "left_to_right" else -1) for p in sim.periods
                for t, d in p.attacking_direction.items()}
        ctx = EvalContext(cfg, home.team_id, away.team_id, team_names, player_names,
                          lambda t, per: dirs[(per, t)])
        results = [(rt, evaluate(rt, events, ctx)) for rt in rts]
        n_ok = sum(1 for _, r in results if r)
        if best is None or n_ok > best[0]:
            best = (n_ok, attempt, (sim, events, results))
        if n_ok == len(rts):
            break
    assert best is not None
    _, attempt, (sim, events, results) = best
    score = Score(home=sim.score[home.team_id], away=sim.score[away.team_id])
    meta = MatchMeta(match_id=match_id, competition=cfg.competition.name, season=cfg.competition.season,
                     matchday=matchday, kickoff_utc=_kickoff(cfg, matchday), venue=home.venue,
                     home_team_id=home.team_id, away_team_id=away.team_id, seed=seed,
                     generator_version=GENERATOR_VERSION, periods=sim.periods, final_score=score)
    truth = build_ground_truth(meta, events, [home, away], [r for _, r in results if r],
                               [dict(story_id=rt.story_id, type=rt.type, team_id=rt.team_id,
                                     reason="story not visible in the events after the allowed attempts")
                                for rt, r in results if not r], attempt)
    return Match(meta=meta, teams=[home.team, away.team], events=events, ground_truth=truth)


def generate_league(seed: int, n_matches: int, stories: Any = "random",
                    config: Config | str | None = None) -> list[Match]:
    """Several matches of one small fictional league; match i uses seed + i."""
    cfg = config if isinstance(config, Config) else load_config(config)
    league = build_league(seed, cfg)
    return [generate_match(seed + i, stories, cfg, league=league, fixture=i) for i in range(n_matches)]
