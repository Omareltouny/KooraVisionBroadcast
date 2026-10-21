"""Verify agent: fact-check every narration against its FactPacket.

Rules: every number in the text must be one the packet allows; no name of a player or club that is not in the packet;
the main actor must be named; lengths are bounded. A narration that fails is replaced by the template version.
"""
from __future__ import annotations

import re
from typing import Any

from .models import FactPacket

_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
MAX_HEAD, MAX_BODY = 110, 420
_NUM = re.compile(r"\d+")


_LABEL_KEYS = ("start_label", "end_label", "behind_minute", "sub_label")


def _tokens(name: str) -> set[str]:
    """The words of a name that can stand for it on their own (surname, club word); very short words are ignored."""
    return {w for w in re.split(r"[\s\-]+", name) if len(w) >= 4}


def _has_word(text: str, tok: str) -> bool:
    if tok.isascii():
        return re.search(r"(?<!\w)" + re.escape(tok) + r"(?!\w)", text) is not None
    return tok in text  # Arabic and other scripts glue prefixes onto words, so a plain substring test


def _mentions(text: str, name: str) -> bool:
    """The full name, or its last word (a writer may say just 'Vokafet' after the headline used the full name)."""
    if name in text:
        return True
    last = re.split(r"[\s\-]+", name.strip())[-1]
    return len(last) >= 4 and _has_word(text, last)


def _ints(obj: Any, out: set[str]) -> None:
    """Collect the numbers a text may state. Only numeric facts and minute labels count: ids such as T06-P11
    contain digits that are not facts, so strings are ignored except the known minute-label keys."""
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        out.add(str(int(obj)))
        if isinstance(obj, float):
            out.update(re.findall(r"\d+", f"{obj}"))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k in _LABEL_KEYS and isinstance(v, str):
                out.update(_NUM.findall(v))
            elif k not in ("home", "away", "team", "opp"):
                _ints(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _ints(v, out)


def allowed_numbers(p: FactPacket) -> set[str]:
    out: set[str] = set()
    _ints(p.facts, out)
    out.update(_NUM.findall(p.minute))
    return out


def main_actor_ids(p: FactPacket) -> list[str]:
    f = p.facts
    for k in ("scorer", "player", "keeper", "shooter"):
        if k in f:
            return [f[k]]
    return []


def verify_text(p: FactPacket, text: str, lang: str, all_names: set[str], headline: bool = False) -> tuple[bool, str]:
    t = text.translate(_ARABIC_DIGITS)
    bad = sorted(set(_NUM.findall(t)) - allowed_numbers(p))
    if bad:
        return False, f"number not in facts: {bad[0]}"
    allowed_names = {n for d in p.names.values() for n in d.values()}
    allowed_tokens = {t for n in allowed_names for t in _tokens(n)}
    for n in all_names - allowed_names:
        if n and n in text:
            return False, f"name not in facts: {n}"
        for tok in _tokens(n) - allowed_tokens:  # a surname alone must not smuggle in someone who is not in the facts
            if _has_word(text, tok):
                return False, f"name not in facts: {n}"
    if len(text) > (MAX_HEAD if headline else MAX_BODY):
        return False, "too long"
    return True, ""


def verify_narration(p: FactPacket, head: str, body: str, lang: str, all_names: set[str]) -> tuple[bool, str]:
    ok, why = verify_text(p, head, lang, all_names, headline=True)
    if not ok:
        return ok, why
    ok, why = verify_text(p, body, lang, all_names)
    if not ok:
        return ok, why
    for pid in main_actor_ids(p):
        nm = p.names.get(pid, {}).get(lang)
        if nm and not _mentions(head + " " + body, nm):
            return False, f"main actor missing: {nm}"
    return True, ""


def verify_all(narrations, packets: dict[str, FactPacket], all_names: set[str]):
    """Settle every LLM draft: it replaces its template only if it passes. Returns (final narrations, stats, rejections)."""
    from .models import Narration  # local import: models has no dependency on this module
    final: dict[tuple[str, str, str], Narration] = {}
    stats = {"templates_ok": 0, "templates_failed": 0, "llm_accepted": 0, "llm_rejected": 0}
    rejections: list[str] = []
    for n in narrations:
        if n.source != "llm_draft":
            ok, why = verify_narration(packets[n.moment_id], n.headline, n.body, n.lang, all_names)
            n.verified = ok
            n.rejected_llm = "" if ok else f"template failed: {why}"
            stats["templates_ok" if ok else "templates_failed"] += 1
            final[(n.moment_id, n.lang, n.voice)] = n
    for n in narrations:
        if n.source == "llm_draft":
            ok, why = verify_narration(packets[n.moment_id], n.headline, n.body, n.lang, all_names)
            key = (n.moment_id, n.lang, n.voice)
            if ok:
                n.source, n.verified = "llm", True
                final[key] = n
                stats["llm_accepted"] += 1
            else:
                if key in final:
                    final[key].rejected_llm = why
                stats["llm_rejected"] += 1
                rejections.append(f"{n.moment_id}/{n.lang}/{n.voice}: {why}")
    return list(final.values()), stats, rejections
