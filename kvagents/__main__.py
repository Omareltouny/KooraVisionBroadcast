"""python -m kvagents run <match_dir> --out demo/ [--model-cache cache.json] [--offline]"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .llm import CachedModel, model_from_env
from .personalize import profiles_from_json
from .pipeline import run_pipeline


def _approvals(path: str | None) -> dict[str, set[str]]:
    """The review page's JSON: one object per match, {"match_id": ..., "approved": ["moment|lang|voice", ...]}."""
    if not path:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out: dict[str, set[str]] = {}
    for d in (data if isinstance(data, list) else [data]):
        out.setdefault(d.get("match_id", ""), set()).update(d.get("approved", []))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="kvagents")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run the agents on one generated match")
    r.add_argument("match_dir")
    r.add_argument("--out", default="demo")
    r.add_argument("--profiles", help="JSON list of fan profiles")
    r.add_argument("--model-cache", help="cache file for model answers (enables model mode when KV_LLM_URL/KV_LLM_MODEL are set, or replays it offline)")
    r.add_argument("--min-interval", type=float, default=float(os.environ.get("KV_LLM_MIN_INTERVAL", "0")),
                   help="seconds between real model calls (free tiers have rate limits)")
    r.add_argument("--offline", action="store_true", help="replay cached model answers only; never call a model")
    r.add_argument("--approvals", help="JSON saved from the Arabic review page: held model drafts a native reader approved")
    r.add_argument("--no-tracking", action="store_true")
    r.add_argument("--engine", choices=["auto", "framework", "direct"], default="auto")
    e = sub.add_parser("evaluate", help="score the Interpret agent against the planted stories (evaluation only)")
    e.add_argument("match_dirs", nargs="+")
    a = ap.parse_args(argv)
    if a.cmd == "run":
        model = None
        if a.model_cache:
            model = CachedModel(None if a.offline else model_from_env(), a.model_cache, offline=a.offline, min_interval=a.min_interval)
        profiles = profiles_from_json(json.loads(Path(a.profiles).read_text())) if a.profiles else None
        state, d = run_pipeline(a.match_dir, a.out, model, profiles, not a.no_tracking, a.engine, _approvals(a.approvals))
        for t in state.trace:
            print(f"[{t.agent}] {t.outputs}  ({t.took_ms:.0f} ms)")
        print(f"wrote {d}")
        return 0
    from .evaluate import evaluate_dirs
    return evaluate_dirs(a.match_dirs)


if __name__ == "__main__":
    sys.exit(main())
