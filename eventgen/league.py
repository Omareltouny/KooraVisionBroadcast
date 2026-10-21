"""Fictional clubs, players and localized names.

Why: the hackathon forbids real names, so every name is assembled from invented
syllables. Each syllable carries an Arabic rendering so `name_i18n` stays
consistent. A separate RNG stream is used so league creation never perturbs
match simulation.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from .config import Config
from .schema import Player, Team

CONSONANTS = [("b", "ب"), ("d", "د"), ("f", "ف"), ("g", "ج"), ("h", "ه"), ("k", "ك"), ("l", "ل"),
              ("m", "م"), ("n", "ن"), ("r", "ر"), ("s", "س"), ("t", "ت"), ("v", "ف"), ("z", "ز")]
VOWELS = [("a", "ا"), ("i", "ي"), ("o", "و"), ("u", "و"), ("e", "ي")]
PLACE_SUFFIXES = [("moor", "مور"), ("wick", "ويك"), ("mere", "ميري"), ("haven", "هيفن"),
                  ("stead", "ستيد"), ("burg", "بورغ"), ("dale", "ديل")]
CLUB_SUFFIXES = [("United", "يونايتد", "Unido"), ("Athletic", "أتلتيك", "Atlético"),
                 ("Rovers", "روفرز", "Rovers"), ("City", "سيتي", "Ciudad"), ("Wanderers", "واندرارز", "Errantes")]
PALETTE = [("#C8102E", "#FFFFFF"), ("#0B3D91", "#F2C94C"), ("#0E7C3A", "#FFFFFF"), ("#5B2A86", "#F5F5F5"),
           ("#F28C28", "#1B1B1B"), ("#111111", "#E5E5E5"), ("#00A3A3", "#FFFFFF"), ("#8B1E3F", "#F2D16B")]
FORMATION_SLOTS = {
    "4-3-3": ["GK", "FB", "CB", "CB", "FB", "DM", "CM", "CM", "W", "ST", "W"],
    "4-2-3-1": ["GK", "FB", "CB", "CB", "FB", "DM", "DM", "W", "AM", "W", "ST"],
    "4-4-2": ["GK", "FB", "CB", "CB", "FB", "W", "CM", "CM", "W", "ST", "ST"],
    "3-5-2": ["GK", "CB", "CB", "CB", "FB", "FB", "DM", "CM", "AM", "ST", "ST"],
}
BENCH_SLOTS = ["GK", "CB", "FB", "CM", "AM", "W", "ST"]
STARTER_NUMBERS = [1, 2, 3, 4, 5, 6, 8, 10, 7, 9, 11]
LANE_RANGE = {"FB": (10, 58), "W": (10, 58), "CB": (22, 46), "CM": (24, 44), "DM": (24, 44),
              "AM": (24, 44), "ST": (28, 40)}


def colour_distance(a: str, b: str) -> float:
    """"Redmean" RGB distance between two #RRGGBB colours (0 identical, about 765 black vs white)."""
    ar, ag, ab = (int(a[i:i + 2], 16) for i in (1, 3, 5))
    br, bg, bb = (int(b[i:i + 2], 16) for i in (1, 3, 5))
    rm = (ar + br) / 2
    return (((2 + rm / 256) * (ar - br) ** 2 + 4 * (ag - bg) ** 2 + (2 + (255 - rm) / 256) * (ab - bb) ** 2)) ** 0.5


MIN_KIT_DISTANCE = 150.0  # below this two shirts are hard to tell apart (also for red-green colour blindness we avoid red vs green)


def away_kit(home_primary: str, primary: str, secondary: str) -> tuple[str, str]:
    """Colours the away team wears so the two shirts are easy to tell apart (swap, else white or black)."""
    for p, s in ((primary, secondary), (secondary, primary), ("#FFFFFF", primary), ("#111111", primary)):
        if colour_distance(home_primary, p) >= MIN_KIT_DISTANCE:
            return p, s
    return "#FFFFFF", "#111111"


@dataclass
class PlayerAttrs:
    """Hidden simulation attributes (never written to teams.json)."""
    skill: float
    involvement: float
    lane_y: float


@dataclass
class Club:
    team: Team
    profile: dict[str, float]
    attrs: dict[str, PlayerAttrs]
    set_piece_taker_id: str
    venue: str

    @property
    def team_id(self) -> str:
        return self.team.team_id


@dataclass
class League:
    clubs: list[Club]
    fixtures: list[tuple[int, int, int]] = field(default_factory=list)  # (matchday, home_idx, away_idx)


def _syll(rng: random.Random, closed: bool = False) -> tuple[str, str]:
    c, ca = rng.choice(CONSONANTS)
    v, va = rng.choice(VOWELS)
    s, sa = c + v, ca + va
    if closed:
        c2, c2a = rng.choice(CONSONANTS)
        s, sa = s + c2, sa + c2a
    return s, sa


def _word(rng: random.Random, n: int, closed_last: bool) -> tuple[str, str]:
    parts = [_syll(rng, closed=(closed_last and i == n - 1)) for i in range(n)]
    return "".join(p[0] for p in parts).capitalize(), "".join(p[1] for p in parts)


def _person_name(rng: random.Random, used: set[str]) -> tuple[str, dict[str, str]]:
    while True:
        f, fa = _word(rng, 3, closed_last=rng.random() < 0.4)
        s, sa = _word(rng, rng.choice([2, 3]), closed_last=True)
        full = f"{f} {s}"
        if full not in used:
            used.add(full)
            return full, {"en": full, "ar": f"{fa} {sa}", "es": full}


def _lanes(positions: list[str]) -> dict[int, float]:
    lanes: dict[int, float] = {}
    for pos in set(positions):
        idx = [i for i, p in enumerate(positions) if p == pos]
        lo, hi = LANE_RANGE.get(pos, (34, 34))
        for k, i in enumerate(idx):
            lanes[i] = 34.0 if (len(idx) == 1 or pos == "GK") else lo + (hi - lo) * k / (len(idx) - 1)
    return lanes


def _build_club(rng: random.Random, cfg: Config, idx: int, used_names: set[str], used_places: set[str],
                used_short: set[str]) -> Club:
    while True:
        stem, stem_ar = _word(rng, 1, closed_last=True)
        suf, suf_ar = rng.choice(PLACE_SUFFIXES)
        place = stem + suf
        if place not in used_places:
            used_places.add(place)
            break
    csuf, csuf_ar, csuf_es = rng.choice(CLUB_SUFFIXES)
    short = place[:3].upper()
    while short in used_short:
        short = (place[:2] + rng.choice("ABCDEFGHJKLMNPRSTVZ")).upper()
    used_short.add(short)
    primary, secondary = PALETTE[idx % len(PALETTE)]
    team_id = f"T{idx + 1:02d}"
    formation = rng.choice(cfg.match.formations)
    slots = FORMATION_SLOTS[formation] + BENCH_SLOTS
    numbers = STARTER_NUMBERS + list(range(12, 12 + len(BENCH_SLOTS)))
    lanes = _lanes(FORMATION_SLOTS[formation])
    sk, inv = cfg.player.skill_range, cfg.player.involvement_range
    players: list[Player] = []
    attrs: dict[str, PlayerAttrs] = {}
    for i, pos in enumerate(slots):
        name, i18n = _person_name(rng, used_names)
        pid = f"{team_id}-P{numbers[i]:02d}"
        players.append(Player(player_id=pid, name=name, name_i18n=i18n, jersey_number=numbers[i],
                              position=pos, starter=i < 11, bio_tags=[]))
        attrs[pid] = PlayerAttrs(skill=rng.uniform(*sk), involvement=rng.uniform(*inv),
                                 lane_y=lanes.get(i, 34.0))
    starters = [p for p in players if p.starter]
    taker = rng.choice([p for p in starters if p.position in ("AM", "CM", "W")] or starters)
    taker.bio_tags += ["set-piece taker", "penalty taker"]
    rng.choice([p for p in starters if p.position in ("CB", "CM", "DM")]).bio_tags.append("captain")
    for p in starters:
        if p.position == "ST":
            p.bio_tags.append("target man")
            break
    ts = cfg.team_style
    profile = {
        "attack_intensity": round(rng.uniform(*ts.attack_intensity), 3),
        "pressing_intensity": round(rng.uniform(*ts.pressing_intensity), 3),
        "buildup_directness": round(rng.uniform(*ts.buildup_directness), 3),
        "quality": round(rng.uniform(*ts.quality), 3),
    }
    team = Team(
        team_id=team_id, name=f"{place} {csuf}",
        name_i18n={"en": f"{place} {csuf}", "ar": f"{stem_ar}{suf_ar} {csuf_ar}", "es": f"{csuf_es} {place}"},
        short_name=short, primary_color=primary, secondary_color=secondary, formation=formation, players=players)
    return Club(team=team, profile=profile, attrs=attrs, set_piece_taker_id=taker.player_id,
                venue=f"{place} {rng.choice(['Park', 'Arena', 'Ground', 'Field'])}")


def _round_robin(n: int) -> list[tuple[int, int, int]]:
    teams: list[int | None] = list(range(n)) + ([None] if n % 2 else [])
    m = len(teams)
    out: list[tuple[int, int, int]] = []
    for rnd in range(m - 1):
        for k in range(m // 2):
            a, b = teams[k], teams[m - 1 - k]
            if a is not None and b is not None:
                out.append((rnd + 1, a, b) if (rnd + k) % 2 == 0 else (rnd + 1, b, a))
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]
    return out


def build_league(seed: int, cfg: Config) -> League:
    """Deterministically create the fictional clubs and fixture list from a seed."""
    rng = random.Random(f"league:{seed}")
    used_names: set[str] = set()
    used_places: set[str] = set()
    used_short: set[str] = set()
    n = max(2, cfg.competition.num_clubs)
    clubs = [_build_club(rng, cfg, i, used_names, used_places, used_short) for i in range(n)]
    return League(clubs=clubs, fixtures=_round_robin(n))
