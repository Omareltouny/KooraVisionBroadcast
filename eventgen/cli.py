"""Command line: generate | validate | replay | schema."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config
from .io import MATCH_FILE, write_match
from .replay import CallableSink, FileSink, StdoutSink, load_callable, replay
from .schema import export_json_schema
from .simulate import generate_league
from .tracking import generate_tracking
from .io import read_match, read_tracking, write_tracking, TRACKING_FILE
from .validate import validate_dir


def _match_dirs(path: Path) -> list[Path]:
    if (path / MATCH_FILE).exists():
        return [path]
    return sorted(p.parent for p in path.glob(f"*/{MATCH_FILE}"))


def cmd_generate(a: argparse.Namespace) -> int:
    cfg = load_config(a.config)
    matches = generate_league(a.seed, a.matches, a.stories, cfg)
    out = Path(a.out)
    for i, m in enumerate(matches, start=1):
        d = out if a.matches == 1 else out / f"match_{i:03d}"
        if not a.no_tracking:
            m.extras["tracking"] = generate_tracking(m, cfg)
        write_match(m, d)
        s = m.meta.final_score
        print(f"{d}: {m.meta.match_id} score {s.home}-{s.away}, {len(m.events)} events, "
              f"{len(m.ground_truth.stories)} stories planted")
        for st in m.ground_truth.stories:
            print(f"  [{st.story_id}] {st.type}: {st.description}")
        for u in m.ground_truth.unrealized_stories:
            print(f"  WARNING: story {u['story_id']} ({u['type']}) not realized")
    return 0


def cmd_track(a: argparse.Namespace) -> int:
    cfg = load_config(a.config)
    dirs = _match_dirs(Path(a.path))
    if not dirs:
        print(f"no {MATCH_FILE} found under {a.path}", file=sys.stderr)
        return 2
    for d in dirs:
        data = generate_tracking(read_match(d), cfg)
        write_tracking(data, d / TRACKING_FILE)
        print(f"{d / TRACKING_FILE}: {len(data.frames)} frames at {data.hz} Hz, "
              f"{data.header['fidelity']['pin_within_1_5m']:.1%} of event moments within 1.5 m")
    return 0


def cmd_autoevent(a: argparse.Namespace) -> int:
    import json

    from .adapters import detect_passes, evaluate_round_trip
    d = Path(a.path)
    match, data = read_match(d), read_tracking(d / TRACKING_FILE)
    det = detect_passes(data)
    with open(d / "autoevents.jsonl", "w", encoding="utf-8", newline="\n") as fh:
        for e in det:
            fh.write(json.dumps(e, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"{d / 'autoevents.jsonl'}: {len(det)} detected events (mock auto-eventing from tracking, not video)")
    for k, v in evaluate_round_trip(match, det).items():
        print(f"  {k}: {v}")
    return 0


def cmd_validate(a: argparse.Namespace) -> int:
    dirs = _match_dirs(Path(a.path))
    if not dirs:
        print(f"no {MATCH_FILE} found under {a.path}", file=sys.stderr)
        return 2
    cfg = load_config(a.config)
    bad = 0
    for d in dirs:
        violations = validate_dir(d, cfg)
        if violations:
            bad += 1
            print(f"FAIL {d}: {len(violations)} violation(s)")
            for v in violations[:50]:
                print(f"  {v}")
        else:
            print(f"OK   {d}")
    return 1 if bad else 0


def cmd_replay(a: argparse.Namespace) -> int:
    path = Path(a.path)
    if a.sink == "stdout":
        sink = StdoutSink()
    elif a.sink == "file":
        sink = FileSink(a.sink_path or path / "replay_out.jsonl")
    else:
        if not a.callable:
            print("--sink callable needs --callable package.module:function", file=sys.stderr)
            return 2
        sink = CallableSink(load_callable(a.callable))
    n = sum(1 for _ in replay(path, speed=a.speed, sink=sink))
    if hasattr(sink, "close"):
        sink.close()
    print(f"replayed {n} events at speed {a.speed}", file=sys.stderr)
    return 0


def cmd_schema(a: argparse.Namespace) -> int:
    for p in export_json_schema(a.out):
        print(p)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="eventgen", description="Synthetic football event generator")
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate", help="generate match files")
    g.add_argument("--seed", type=int, default=42)
    g.add_argument("--out", required=True)
    g.add_argument("--stories", default="random", help="random | none | path/to/stories.yaml")
    g.add_argument("--matches", type=int, default=1)
    g.add_argument("--config", default=None)
    g.add_argument("--no-tracking", action="store_true", help="skip tracking.jsonl (faster, smaller)")
    g.set_defaults(fn=cmd_generate)
    ae = sub.add_parser("autoevent", help="detect passes from tracking.jsonl and score them against the events")
    ae.add_argument("path")
    ae.set_defaults(fn=cmd_autoevent)
    tr = sub.add_parser("track", help="add tracking.jsonl to an existing match folder")
    tr.add_argument("path")
    tr.add_argument("--config", default=None)
    tr.set_defaults(fn=cmd_track)
    v = sub.add_parser("validate", help="check invariants of a generated match (or a folder of matches)")
    v.add_argument("path")
    v.add_argument("--config", default=None)
    v.set_defaults(fn=cmd_validate)
    r = sub.add_parser("replay", help="stream a generated match in scaled real time")
    r.add_argument("path")
    r.add_argument("--speed", type=float, default=20.0, help="0 = as fast as possible")
    r.add_argument("--sink", choices=["stdout", "file", "callable"], default="stdout")
    r.add_argument("--sink-path", default=None)
    r.add_argument("--callable", default=None, help="package.module:function for --sink callable")
    r.set_defaults(fn=cmd_replay)
    s = sub.add_parser("schema", help="export JSON Schema files")
    s.add_argument("--out", default="schema")
    s.set_defaults(fn=cmd_schema)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except BrokenPipeError:  # e.g. `| head`: the reader left, not an error
        sys.stderr.close()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
