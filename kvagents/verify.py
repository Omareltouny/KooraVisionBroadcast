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


# ---- extra guards: what the model may NOT do even when every digit and name is right
_LATIN = re.compile(r"[A-Za-z]{2,}")
_ARABIC = re.compile(r"[\u0600-\u06FF]")

_EN_UNITS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
             "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
             "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
             "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100}
_ES_UNITS = {"dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
             "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15, "dieciséis": 16, "diecisiete": 17,
             "dieciocho": 18, "diecinueve": 19, "veinte": 20, "treinta": 30, "cuarenta": 40, "cincuenta": 50,
             "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90, "cien": 100}
_ES_TENS = {"veinti": 20}
# 'one'/'uno' are left out on purpose: they are ordinary words ("one of the", "no one").


def _spelled_numbers(text: str, lang: str) -> list[int]:
    """Numbers written as words ("fifteen", "thirty-six", "veintitrés"), so they cannot dodge the digit check."""
    out: list[int] = []
    low = text.lower()
    if lang == "en":
        for m in re.finditer(r"\b([a-z]+)(?:[\-\u2010-\u2015\s]([a-z]+))?\b", low):
            a, b = m.group(1), m.group(2)
            if a in _EN_UNITS and a not in ("hundred",):
                if b in ("one", "two", "three", "four", "five", "six", "seven", "eight", "nine") and _EN_UNITS[a] >= 20:
                    out.append(_EN_UNITS[a] + (1 if b == "one" else _EN_UNITS[b]))
                else:
                    out.append(_EN_UNITS[a])
            elif b in _EN_UNITS and b != "hundred":
                out.append(_EN_UNITS[b])
    elif lang == "es":
        for w in re.findall(r"[a-záéíóúñ]+", low):
            if w in _ES_UNITS:
                out.append(_ES_UNITS[w])
            elif w.startswith("veinti") and len(w) > 6:
                out.append(20)
    return out


_AR_L = "\u0621-\u064A"


def _ar_word(words: str) -> "re.Pattern[str]":
    """Arabic words take prefixes (و ب ل ف ك, ال) and suffixes; a plain substring test would also hit names
    (دافوزول contains فوز), so a match must start at a word boundary, after an optional prefix."""
    return re.compile(rf"(?<![{_AR_L}])[وبلفك]?(?:ال)?(?:{words})[{_AR_L}]{{0,2}}(?![{_AR_L}])")


_OUTCOME = {
    "en": re.compile(r"\b(victory|triumph|winner|clinch\w*|sealed|sealing|consolation|\d+\W{0,2}\d+ win|win over|win against)\b", re.I),
    "es": re.compile(r"\b(victoria|triunfo|ganador|consuelo|se impuso|se impone|se lleva|sella|asegura)\b", re.I),
    "ar": _ar_word("فوز|فاز|انتصار|انتصر|فائز"),
}
_ENDED = {
    "en": re.compile(r"\b(ended|finished|final whistle|full[- ]time|final score)\b", re.I),
    "es": re.compile(r"\b(terminó|finalizó|final del partido|marcador final|pitido final)\b", re.I),
    "ar": _ar_word("انتهى|انتهت|ينتهي|ينتهى|نهاية المباراة|النتيجة النهائية"),
}


def _allows_outcome(p: FactPacket) -> bool:
    """A result may only be called a win/victory when the facts say so: full time, or a winning goal."""
    f = p.facts
    return p.kind == "full_time" or bool(isinstance(f.get("flags"), dict) and f["flags"].get("winner"))


def _extra_checks(p: FactPacket, text: str, lang: str) -> tuple[bool, str]:
    if lang == "ar" and _LATIN.search(text):
        return False, f"Latin letters in Arabic text: {_LATIN.search(text).group(0)}"
    if lang in ("en", "es") and _ARABIC.search(text):
        return False, "Arabic letters in a Latin-script text"
    allowed = {int(x) for x in allowed_numbers(p) if x.isdigit()}
    for n in _spelled_numbers(text, lang):
        if n not in allowed:
            return False, f"spelled-out number not in facts: {n}"
    if p.kind != "full_time" and _ENDED.get(lang) and _ENDED[lang].search(text):
        return False, "claims the match ended"
    if not _allows_outcome(p) and _OUTCOME.get(lang) and _OUTCOME[lang].search(text):
        return False, "claims a win the facts do not support"
    return True, ""


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
    return _extra_checks(p, text, lang)


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


def held_languages() -> set[str]:
    """Languages whose model text is NOT published until a native reader approves it: those whose template file says
    STATUS = "needs_native_review". Approve one by listing it in KV_TRUST_LANGS (for example KV_TRUST_LANGS=ar)."""
    import os
    from .lang import LANG
    trust = set(os.environ.get("KV_TRUST_LANGS", "").replace(",", " ").split())
    return {code for code, mod in LANG.items() if getattr(mod, "STATUS", "") == "needs_native_review" and code not in trust}


def verify_all(narrations, packets: dict[str, FactPacket], all_names: set[str], approvals: set[str] | None = None):
    """Settle every LLM draft: it replaces its template only if it passes. Returns (final narrations, stats, rejections).
    `approvals` holds "moment|lang|voice" keys a native reader approved: such a held draft is published (it still had to pass)."""
    approvals = approvals or set()
    from .models import Narration  # local import: models has no dependency on this module
    final: dict[tuple[str, str, str], Narration] = {}
    stats = {"templates_ok": 0, "templates_failed": 0, "llm_accepted": 0, "llm_rejected": 0, "llm_held_for_review": 0}
    hold = held_languages()
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
            if ok and n.lang in hold and key in final and f"{n.moment_id}|{n.lang}|{n.voice}" not in approvals:
                final[key].held_headline, final[key].held_body = n.headline, n.body   # the template stays published
                stats["llm_held_for_review"] += 1
            elif ok:
                n.source, n.verified = "llm", True
                final[key] = n
                stats["llm_accepted"] += 1
            else:
                if key in final:
                    final[key].rejected_llm = why
                stats["llm_rejected"] += 1
                rejections.append(f"{n.moment_id}/{n.lang}/{n.voice}: {why}")
    return list(final.values()), stats, rejections
