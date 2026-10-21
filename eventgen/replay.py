"""Replay engine and sinks.

Why: the rest of the pipeline must be developed against a *stream*, not a
file, so replay emits events in `seq` order paced to (scaled) match time.
The core has no cloud dependency; an Azure sink would implement `EventSink`
in its own optional module.
"""
from __future__ import annotations

import asyncio
import importlib
import sys
import time
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Iterable, Iterator, Protocol

from .io import EVENTS_FILE, event_to_line, read_events
from .schema import Match


class EventSink(Protocol):
    def send(self, event: Any) -> None: ...


class StdoutSink:
    """Print each event as one JSON line."""

    def send(self, event: Any) -> None:
        sys.stdout.write(event_to_line(event) + "\n")
        sys.stdout.flush()


class FileSink:
    """Append each event as one JSON line to a file."""

    def __init__(self, path: str | Path) -> None:
        self._fh = open(path, "w", encoding="utf-8", newline="\n")

    def send(self, event: Any) -> None:
        self._fh.write(event_to_line(event) + "\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()

    def __enter__(self) -> "FileSink":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


class CallableSink:
    def __init__(self, fn: Callable[[Any], None]) -> None:
        self._fn = fn

    def send(self, event: Any) -> None:
        self._fn(event)


def load_callable(spec: str) -> Callable[[Any], None]:
    """Resolve 'package.module:function' for `--sink callable`."""
    mod, _, name = spec.partition(":")
    if not mod or not name:
        raise ValueError("callable must look like 'package.module:function'")
    return getattr(importlib.import_module(mod), name)


def _events_of(source: Match | str | Path | Iterable[Any]) -> list[Any]:
    if isinstance(source, Match):
        return list(source.events)
    if isinstance(source, (str, Path)):
        p = Path(source)
        return read_events(p / EVENTS_FILE if p.is_dir() else p)
    return list(source)


def _delay(events: list[Any], i: int, speed: float, elapsed: float) -> float:
    if speed <= 0:
        return 0.0
    due = (events[i].match_clock_ms - events[0].match_clock_ms) / 1000.0 / speed
    return due - elapsed


def replay(source: Match | str | Path | Iterable[Any], speed: float = 1.0, sink: EventSink | None = None,
           sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic) -> Iterator[Any]:
    """Yield (and optionally sink) events in seq order; speed=0 means no sleeping."""
    events = _events_of(source)
    start = clock()
    for i, ev in enumerate(events):
        wait = _delay(events, i, speed, clock() - start)
        if wait > 0:
            sleep(wait)
        if sink is not None:
            sink.send(ev)
        yield ev


async def areplay(source: Match | str | Path | Iterable[Any], speed: float = 1.0,
                  sink: EventSink | None = None) -> AsyncIterator[Any]:
    """Async variant of `replay` using asyncio.sleep."""
    events = _events_of(source)
    loop = asyncio.get_running_loop()
    start = loop.time()
    for i, ev in enumerate(events):
        wait = _delay(events, i, speed, loop.time() - start)
        if wait > 0:
            await asyncio.sleep(wait)
        if sink is not None:
            sink.send(ev)
        yield ev
