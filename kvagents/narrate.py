"""Narrate agent: write each moment in en, ar and es, in four voices (broadcast, fan_for, fan_against, fan_neutral).

Always writes from templates (exact numbers, no model). If a model is supplied it may restyle the important ones,
but only inside the fact packet, and Verify throws away anything that adds a number or name.
"""
from __future__ import annotations

import json
import re
import zlib

from .lang import LANG
from .match_view import MatchView
from .models import FactPacket, Narration

STYLE_SYSTEM = (
    "You are a football commentator. Rewrite the given match note in the requested language and voice. "
    "Use ONLY the facts provided. Do not add any number, minute, name, club, or claim that is not in the facts. "
    "Write every number as digits, never as words. Use the names and the venue exactly as given in the facts, in the "
    "requested script (an Arabic text must contain no Latin letters). "
    "Do not say who won, that the match ended, or call anything a victory unless the facts say so. "
    "Keep it to one headline (max 12 words) and one or two sentences, in correct grammar. "
    'Reply with JSON only: {"headline": "...", "body": "..."}'
)
VOICE_HINT = {
    "broadcast": "neutral, precise, broadcast tone",
    "fan_for": "excited, speaking to a supporter of the team that benefits",
    "fan_against": "sympathetic, speaking to a supporter of the team that suffers",
    "fan_neutral": "friendly neutral fan tone",
}


def voices_for(p: FactPacket) -> tuple[str, ...]:
    return ("broadcast", "fan_for", "fan_against", "fan_neutral") if p.beneficiary else ("broadcast", "fan_neutral")


def _pick(options: list[str], key: str) -> str:
    return options[zlib.crc32(key.encode()) % len(options)]


def _nf(T: dict, key: str, n: int) -> str:
    """Number-aware template: some languages (Arabic: 3 to 10) need a different form after the number."""
    return T[key + "_few"] if key + "_few" in T and 3 <= int(n) <= 10 else T[key]


def _nm(p: FactPacket, pid: str, lang: str) -> str:
    return p.names[pid][lang]


_AR_VENUE_KIND = {"Park": "بارك", "Arena": "أرينا", "Ground": "غراوند", "Field": "فيلد"}


def localize_venue(venue: str, lang: str, names: dict) -> str:
    """The stadium is "<place> <Park|Arena|Ground|Field>". Arabic text must not carry Latin letters, so the place
    comes from the home team's Arabic name (clubs are named after their place) and the word is mapped."""
    if lang != "ar" or not venue:
        return venue
    place, _, kind = venue.rpartition(" ")
    ar_kind = _AR_VENUE_KIND.get(kind)
    if not place or not ar_kind:
        return "الملعب"
    for d in names.values():
        en, ar = d.get("en", ""), d.get("ar", "")
        if en.startswith(place + " ") and " " in ar:
            return f"{ar.rsplit(' ', 1)[0]} {ar_kind}"
    return "الملعب"


def render(p: FactPacket, lang: str, voice: str, venue: str = "") -> tuple[str, str]:
    T = LANG[lang].T
    f = p.facts
    n = lambda k: _nm(p, f[k], lang)  # noqa: E731
    home, away = _nm(p, f["home"], lang), _nm(p, f["away"], lang)
    score = f"{home} {f.get('home_goals', 0)}-{f.get('away_goals', 0)} {away}"
    common = {"minute": p.minute, "scoreline": score, "home": home, "away": away, "venue": localize_venue(venue or f.get("venue", ""), lang, p.names)}
    k = p.kind
    if k == "goal":
        fl = f["flags"]
        if fl["is_penalty"]:
            key = "penalty"
        elif fl["winner"] and fl["late"]:
            key = "winner"
        elif fl["equaliser"]:
            key = "equaliser"
        elif fl["go_ahead"]:
            key = "go_ahead"
        else:
            key = "base"
        d = {**common, "scorer": n("scorer"), "team": n("team")}
        head = T["goal_head"][key].format(**d)
        body = T["goal_body"].format(**d)
        parts = []
        if "assist" in f:
            parts.append(T["c_assist"].format(assist=n("assist")))
        for c in p.causes:
            tag = {"counter_attack": "c_counter", "high_press_win": "c_press", "long_build_up": "c_build",
                   "set_piece": "c_setpiece", "header": "c_header", "long_range": "c_long"}.get(c)
            if tag:
                num = f.get("buildup_seconds", 0) if tag == "c_counter" else f.get("buildup_passes", 0)
                parts.append(_nf(T, tag, num).format(secs=f.get("buildup_seconds", 0), passes=f.get("buildup_passes", 0), dist=f["shot_distance_m"]))
                break
        if f.get("attackers_in_box", 0) >= 3:
            parts.append(T["c_box"].format(n=f["attackers_in_box"], team=n("team")))
        body = " ".join([body] + parts)
    elif k == "comeback":
        d = {**common, "scorer": n("scorer"), "team": n("team"), "behind_minute": f["behind_minute"]}
        head = T["comeback_head"].format(**d)
        level = f["home_goals"] == f["away_goals"]
        body = T["comeback_body_level" if level else "comeback_body_ahead"].format(**d)
    elif k == "red_card":
        d = {**common, "player": n("player"), "team": n("team"), "men": f["men_left"]}
        head, body = T["red_head"].format(**d), T["red_body"].format(**d)
    elif k == "big_save":
        d = {**common, "keeper": n("keeper"), "shooter": n("shooter"), "team": n("team"), "dist": f["shot_distance_m"]}
        head, body = T["save_head"].format(**d), T["save_body"].format(**d)
    elif k == "penalty_miss":
        d = {**common, "shooter": n("shooter"), "team": n("team")}
        head, body = T["pen_head"].format(**d), T["pen_body"].format(**d)
    elif k == "pressing_spell":
        d = {**common, "team": n("team"), "start": f["start_label"], "end": f["end_label"], "n": f["turnovers"]}
        head, body = T["press_head"].format(**d), _nf(T, "press_body", f["turnovers"]).format(**d)
    elif k == "star_performance":
        d = {**common, "player": n("player"), "team": n("team"), "share": f["shot_share_pct"], "shots": f["shots"], "touches": f["touches"]}
        head, body = T["star_head"].format(**d), T["star_body"].format(**d)
        if f["goals"] > 0:
            body += " " + T["star_goals"].format(goals=f["goals"])
    elif k == "super_sub":
        d = {**common, "player": n("player"), "team": n("team"), "sub": f["sub_label"]}
        head, body = T["super_head"].format(**d), T["super_body"].format(**d)
    elif k == "full_time":
        d = {**common, "shots_home": f["shots_home"], "shots_away": f["shots_away"]}
        head = T["ft_head"].format(**d)
        if f["winner"]:
            body = T["ft_body_win"].format(winner=n("winner"), loser=n("loser"), **d)
        else:
            body = T["ft_body_draw"].format(**d)
    else:
        raise ValueError(k)
    if voice in ("fan_for", "fan_against") and p.beneficiary:
        fan_team = p.beneficiary if voice == "fan_for" else (f["away"] if p.beneficiary == f["home"] else f["home"])
        line = _pick(T["voice_for" if voice == "fan_for" else "voice_against"], f"{p.moment_id}:{lang}:{voice}")
        body = f"{body} {line.format(ft=_nm(p, fan_team, lang))}"
    return head, body


def narrate(mv: MatchView, packets: list[FactPacket], model=None, style_min_importance: float = 0.6,
            importance: dict[str, float] | None = None, style_voices: tuple[str, ...] = ("broadcast", "fan_for")) -> tuple[list[Narration], list[str]]:
    from .verify import verify_narration
    out: list[Narration] = []
    notes: list[str] = []
    all_names = mv.all_names()
    stats = {"llm_used": 0, "llm_rejected": 0, "llm_unavailable": 0}
    for p in packets:
        for lang in LANG:
            for voice in voices_for(p):
                head, body = render(p, lang, voice, mv.meta.get("venue", ""))
                ok, why = verify_narration(p, head, body, lang, all_names)
                nar = Narration(p.moment_id, lang, voice, head, body, "template", verified=ok, rejected_llm="" if ok else f"template failed: {why}")
                out.append(nar)
                if model is not None and voice in style_voices and (importance or {}).get(p.moment_id, 1.0) >= style_min_importance:
                    draft = _style(model, p, nar, stats)
                    if draft is not None:
                        out.append(draft)
    if model is not None:
        notes.append(f"model {getattr(model, 'name', '?')}: drafts {stats['llm_used']}, no answer {stats['llm_unavailable']}, unusable {stats['llm_rejected']}")
    return out, notes


def _style(model, p: FactPacket, base: Narration, stats: dict[str, int]) -> Narration | None:
    """Ask the model for a restyled draft. The draft is NOT trusted: the Verify agent decides."""
    names = {k: v[base.lang] for k, v in p.names.items()}
    payload = {"language": base.lang, "voice": VOICE_HINT[base.voice], "minute": p.minute,
               "draft_headline": base.headline, "draft_body": base.body, "names": names,
               "facts": {k: (localize_venue(v, base.lang, p.names) if k == "venue" else v) for k, v in p.facts.items() if k not in ("home", "away")},
               "causes": p.causes}
    try:
        raw = model.complete(STYLE_SYSTEM, json.dumps(payload, ensure_ascii=False))
        raw = re.sub(r"<think>[\s\S]*?</think>", "", raw)   # reasoning models print their thinking first
        s, e = raw.find("{"), raw.rfind("}")
        data = json.loads(raw[s:e + 1])
        head, body = str(data["headline"]).strip(), str(data["body"]).strip()
    except LookupError:
        stats["llm_unavailable"] += 1
        return None
    except Exception:  # noqa: BLE001  (network, JSON or key errors all mean "keep the template")
        stats["llm_rejected"] += 1
        return None
    stats["llm_used"] += 1
    return Narration(p.moment_id, base.lang, base.voice, head, body, "llm_draft", verified=False)
