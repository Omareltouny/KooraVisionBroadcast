"""Read-only view of one match: events, teams, names, minute labels. Never opens ground_truth.json."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


class MatchView:
    def __init__(self, match_dir: str | Path):
        d = Path(match_dir)
        self.dir = d
        self.meta: dict[str, Any] = json.loads((d / "match.json").read_text(encoding="utf-8"))
        tj = json.loads((d / "teams.json").read_text(encoding="utf-8"))
        self.teams: dict[str, dict[str, Any]] = {t["team_id"]: t for t in tj["teams"]}
        self.players: dict[str, dict[str, Any]] = {}
        self.team_of: dict[str, str] = {}
        for t in tj["teams"]:
            for p in t["players"]:
                self.players[p["player_id"]] = p
                self.team_of[p["player_id"]] = t["team_id"]
        self.events: list[dict[str, Any]] = [json.loads(line) for line in (d / "events.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        self.by_seq = {e["seq"]: e for e in self.events}
        self.by_id = {e["event_id"]: e for e in self.events}
        self.home: str = self.meta["home_team_id"]
        self.away: str = self.meta["away_team_id"]
        self.periods = {p["period"]: p for p in self.meta["periods"]}
        self.L, self.W = 105.0, 68.0
        self._dir = {(p["period"], t): (1 if v == "left_to_right" else -1)
                     for p in self.meta["periods"] for t, v in p["attacking_direction"].items()}

    def opp(self, team_id: str) -> str:
        return self.away if team_id == self.home else self.home

    def direction(self, team_id: str, period: int) -> int:
        return self._dir[(period, team_id)]

    def in_opp_half(self, team_id: str, period: int, x: float) -> bool:
        return (x > self.L / 2) if self.direction(team_id, period) > 0 else (x < self.L / 2)

    def dist_to_goal(self, team_id: str, period: int, x: float, y: float) -> float:
        gx = self.L if self.direction(team_id, period) > 0 else 0.0
        return math.hypot(gx - x, y - self.W / 2)

    def minute_label(self, clock_ms: int, period: int) -> str:
        p = self.periods[period]
        elapsed = (clock_ms - p["start_match_clock_ms"]) / 60000.0
        minute = int((45 * (period - 1) + elapsed) // 1) + 1
        cap = 45 * period
        return str(minute) if minute <= cap else f"{cap}+{minute - cap}"

    def name(self, pid: str, lang: str = "en") -> str:
        p = self.players[pid]
        return (p.get("name_i18n") or {}).get(lang) or p["name"]

    def team_name(self, tid: str, lang: str = "en") -> str:
        t = self.teams[tid]
        return (t.get("name_i18n") or {}).get(lang) or t["name"]

    def names_for(self, ids: list[str], teams: list[str]) -> dict[str, dict[str, str]]:
        out: dict[str, dict[str, str]] = {}
        for i in ids:
            out[i] = {lg: self.name(i, lg) for lg in ("en", "ar", "es")}
        for t in teams:
            out[t] = {lg: self.team_name(t, lg) for lg in ("en", "ar", "es")}
        return out

    def all_names(self) -> set[str]:
        s: set[str] = set()
        for p in self.players.values():
            s.add(p["name"])
            s.update((p.get("name_i18n") or {}).values())
        for t in self.teams.values():
            s.add(t["name"])
            s.update((t.get("name_i18n") or {}).values())
        return s
