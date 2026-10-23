"""Build the KooraVision Match Desk page from the pipeline output (demo/out) and the demo matches (demo/matches).

    python tools/build_site.py                 # writes site/index.html (a full page) and site/viewer-fragment.html
    python tools/build_site.py --demo demo --site site

The page is one self-contained file: the data is inlined, so it works from any static host (GitHub Pages, Azure Static Web
Apps) and needs no server and no live model. Only the pipeline's own output files are read; never ground_truth.json.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE_ORDER = ["fan_en", "fan_ar", "fan_es"]
PATH_KINDS = {"goal", "comeback", "big_save", "penalty_miss"}
SHORT = {"fan_en": "Neutral · English", "fan_ar": "Arabic · home fan", "fan_es": "Spanish · away fan"}


def _load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def _attack_path(events: list[dict], moment: dict, directions: dict[int, dict[str, str]]) -> list[list[float]]:
    """The last few touches of the possession that ended in the shot, drawn so that the attack always goes to the right."""
    by_seq = {e["seq"]: e for e in events}
    shot = None
    for s in range(moment["seq"], moment["seq"] - 4, -1):
        e = by_seq.get(s)
        if e and e["type"] in ("shot", "penalty"):
            shot = e
            break
    if shot is None:
        return []
    chain = [e for e in events if e["possession_id"] == shot["possession_id"] and e["seq"] <= shot["seq"]
             and e["team_id"] == shot["team_id"] and e["type"] in ("pass", "shot", "penalty")][-6:]
    flip = directions.get(shot["period"], {}).get(shot["team_id"], "left_to_right") == "right_to_left"
    pts = [[e["x"], e["y"]] for e in chain]
    if "end_x" in shot:
        pts.append([shot["end_x"], shot["end_y"]])
    if flip:
        pts = [[105 - x, 68 - y] for x, y in pts]
    return [[round(x, 1), round(y, 1)] for x, y in pts]


def _match(out: Path, mdir: Path) -> dict:
    man, moments, packets = _load(out / "manifest.json"), _load(out / "moments.json"), _load(out / "packets.json")
    narr, bcast, trace = _load(out / "narrations.json"), _load(out / "broadcast.json"), _load(out / "trace.json")
    meta, teams = _load(mdir / "match.json"), _load(mdir / "teams.json")
    events = [json.loads(line) for line in (mdir / "events.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    directions = {p["period"]: p["attacking_direction"] for p in meta["periods"]}
    tinfo = {t["team_id"]: t for t in teams["teams"]}
    home, away = tinfo[meta["home_team_id"]], tinfo[meta["away_team_id"]]
    names: dict[str, dict] = {}
    for p in packets:
        names.update(p["names"])
    pk = {p["moment_id"]: p for p in packets}
    mom_out = []
    for m in moments:
        p = pk[m["moment_id"]]
        facts = {k: v for k, v in p["facts"].items() if k not in ("home", "away", "venue")}
        path = _attack_path(events, m, directions) if m["kind"] in PATH_KINDS else []
        mom_out.append({"id": m["moment_id"], "kind": m["kind"], "minute": p["minute"], "importance": m["importance"],
                        "team": m["team_id"], "facts": facts, "causes": p["causes"], "path": path})
    texts: dict[str, dict] = {}
    for n in narr:
        slot = texts.setdefault(n["moment_id"], {}).setdefault(n["lang"], {})
        slot[n["voice"]] = {"h": n["headline"], "b": n["body"], "src": n["source"], "hh": n.get("held_headline", ""), "hb": n.get("held_body", "")}
    fans = {}
    for prof in man["profiles"]:
        cards = _load(out / f"fan_{prof['id']}.json")
        fans[prof["id"]] = {"id": prof["id"], "lang": prof["lang"], "label": prof["label"], "short": SHORT.get(prof["id"], prof["id"]),
                            "cards": [{"moment_id": c["moment_id"], "voice": c["voice"], "push": c["push"], "headline": c["headline"],
                                       "body": c["body"], "source": c["source"]} for c in cards]}
    verify_agent = next(a for a in trace["agents"] if a["agent"] == "Verify")
    verify = json.loads(verify_agent["outputs"])
    verify.setdefault("llm_held_for_review", 0)
    rejections = [x for x in verify_agent["notes"] if ": " in x]
    h, a = man["score"].split("-")
    return {"id": man["match_id"], "competition": meta["competition"], "season": meta["season"], "matchday": meta["matchday"],
            "venue": meta["venue"], "home_goals": int(h), "away_goals": int(a), "engine": man["engine"],
            "model_short": man["model"].split(":")[-1].split("/")[-1] if man.get("model") else "templates only",
            "language_status": man["language_status"],
            "home": {"names": home["name_i18n"], "color": home["primary_color"]}, "away": {"names": away["name_i18n"], "color": away["primary_color"]},
            "names": names, "moments": mom_out, "texts": texts, "fans": fans,
            "broadcast": [{"moment_id": c["moment_id"], "tier": c["tier"], "importance": c["importance"]} for c in bcast],
            "verify": verify, "trace": {"agents": trace["agents"], "rejections": rejections}}


def build(demo: Path, site: Path) -> None:
    matches = []
    for out in sorted((demo / "out").iterdir()):
        if (out / "manifest.json").exists():
            matches.append(_match(out, demo / "matches" / out.name))
    scenes: dict[str, list] = {}
    for f in sorted((demo / "scenes").glob("*.json")) if (demo / "scenes").is_dir() else []:
        sc = json.loads(f.read_text(encoding="utf-8"))
        scenes.setdefault(sc["match_id"], []).append(sc)
    data = json.dumps({"profileOrder": PROFILE_ORDER, "matches": matches, "scenes": scenes}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    bundle_path = site / "vendor" / "scene3d.js"
    bundle = bundle_path.read_text(encoding="utf-8").replace("</script", "<\\/script") if bundle_path.exists() else ""
    fragment = (site / "viewer.fragment.html").read_text(encoding="utf-8").replace("/*__KV3D__*/", bundle).replace("/*__DATA__*/null", data)
    (site / "viewer-fragment.html").write_text(fragment, encoding="utf-8")
    title_end = fragment.index("</title>") + len("</title>")
    page = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
            + fragment[:title_end] + "\n<style>html,body{margin:0}</style>\n</head>\n<body>\n" + fragment[title_end:] + "\n</body>\n</html>\n")
    (site / "index.html").write_text(page, encoding="utf-8")
    print(f"{len(matches)} matches, index.html {len(page)//1024} KB")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", default=str(ROOT / "demo"))
    ap.add_argument("--site", default=str(ROOT / "site"))
    a = ap.parse_args()
    build(Path(a.demo), Path(a.site))
