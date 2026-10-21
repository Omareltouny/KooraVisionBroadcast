"""Write and read the four match files.

Why: one module owns the on-disk format so output is byte-stable (compact
JSON lines, fixed key order from the schema, trailing newline) and can be
round-tripped without loss.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Iterator

from .schema import EVENT_ADAPTER, GroundTruth, Match, MatchMeta, TeamsFile
from .tracking import TrackingData

MATCH_FILE, TEAMS_FILE, EVENTS_FILE, TRUTH_FILE = "match.json", "teams.json", "events.jsonl", "ground_truth.json"
TRACKING_FILE = "tracking.jsonl"


def event_to_line(event: Any) -> str:
    return event.model_dump_json()


def write_events(events: Iterable[Any], path: str | Path) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for e in events:
            fh.write(event_to_line(e) + "\n")


def iter_events(path: str | Path) -> Iterator[Any]:
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield EVENT_ADAPTER.validate_json(line)


def read_events(path: str | Path) -> list[Any]:
    return list(iter_events(path))


def write_tracking(data: TrackingData, path: str | Path) -> None:
    """One header line, then one compact line per frame (fixed key order, byte-stable)."""
    dump = json.dumps
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(dump(data.header, ensure_ascii=False, separators=(",", ":")) + "\n")
        for t, per, bx, by, row in data.frames:
            p = ",".join(f"[{i},{x},{y}]" for i, x, y in row)
            fh.write(f'{{"type":"frame","t":{t},"period":{per},"ball":[{bx},{by}],"p":[{p}]}}\n')


def read_tracking(path: str | Path) -> TrackingData:
    with open(path, encoding="utf-8") as fh:
        header = json.loads(fh.readline())
        frames = []
        for line in fh:
            if not line.strip():
                continue
            d = json.loads(line)
            frames.append((d["t"], d["period"], d["ball"][0], d["ball"][1], [(int(i), x, y) for i, x, y in d["p"]]))
    idx = {p["player_id"]: p["index"] for p in header["players"]}
    return TrackingData(header=header, frames=frames, player_index=idx)


def _dump(model: Any, path: Path) -> None:
    path.write_text(json.dumps(model.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_match(match: Match, out_dir: str | Path) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    _dump(match.meta, out / MATCH_FILE)
    _dump(TeamsFile(match_id=match.meta.match_id, teams=match.teams), out / TEAMS_FILE)
    write_events(match.events, out / EVENTS_FILE)
    _dump(match.ground_truth, out / TRUTH_FILE)
    if match.extras.get("tracking") is not None:
        write_tracking(match.extras["tracking"], out / TRACKING_FILE)
    return out


def read_match(directory: str | Path) -> Match:
    d = Path(directory)
    meta = MatchMeta.model_validate_json((d / MATCH_FILE).read_text(encoding="utf-8"))
    teams = TeamsFile.model_validate_json((d / TEAMS_FILE).read_text(encoding="utf-8")).teams
    truth = GroundTruth.model_validate_json((d / TRUTH_FILE).read_text(encoding="utf-8"))
    return Match(meta=meta, teams=teams, events=read_events(d / EVENTS_FILE), ground_truth=truth)
