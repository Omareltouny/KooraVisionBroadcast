# eventgen: synthetic football event generator

KooraVision entry, Microsoft Premier League Hackathon. Generates **synthetic, seeded, football-shaped
match event streams** from a **fictional league** (invented clubs, players, stadiums; no real data,
names or trademarks). It is the data source for Ingest -> Interpret -> Explain -> Render -> Personalize.

## Install (from the repository root)

```
pip install -e ".[dev]"
```

Needs Python 3.10+, `pydantic` v2 and `pyyaml`. Nothing else, and no cloud dependency.

## Commands

```
python -m eventgen generate --seed 42 --out out/match_001
python -m eventgen generate --seed 42 --out out/match_001 --stories none
python -m eventgen generate --seed 42 --out out/demo --stories config/stories.example.yaml
python -m eventgen generate --seed 7 --out out/league --matches 3
python -m eventgen generate --seed 42 --out out/match_001 --no-tracking   # skip the 12 MB tracking file
python -m eventgen track out/match_001          # add or rebuild tracking.jsonl for an existing match
python -m eventgen autoevent out/match_001      # mock auto-eventing: tracking in, passes out, scored
python -m eventgen validate out/match_001
python -m eventgen validate out/league
python -m eventgen replay out/match_001 --speed 20
python -m eventgen replay out/match_001 --speed 0 --sink file --sink-path out/replayed.jsonl
python -m eventgen schema --out schema/
python -m pytest
```

`--stories` is `random` (default, picked from the seed), `none`, or a YAML path
(see `config/stories.example.yaml`). With `--matches N > 1` each match gets its own
`match_001/`, `match_002/` ... folder; match `i` uses seed `seed + i` and the next fixture of the
fictional league built from `--seed`. `replay --speed 0` streams as fast as possible; `--speed 20`
is 20x real time. `--sink callable --callable package.module:function` calls your function per event.

## Output files (per match folder)

| File | Content |
|---|---|
| `match.json` | metadata, periods (with `attacking_direction` per team), `final_score` derived from events |
| `teams.json` | both squads, `name_i18n` with `en`, `ar`, `es` (all invented) |
| `events.jsonl` | one event per line, canonical order = `seq` |
| `tracking.jsonl` | 5 Hz positions of the ball and every player on the pitch (see `docs/TRACKING.md`) |
| `ground_truth.json` | planted stories with real `seq` ranges + stats computed from events. **Evaluation only: Interpret/Explain must not read it at runtime.** |

Coordinates use a fixed pitch frame, 105 x 68 m, origin bottom-left, home attacks left to right
in period 1 and swaps at half time. Normalize with `periods[].attacking_direction`.
Event types: `pass shot save tackle possession_change pressure foul card substitution period_start period_end`
plus set pieces `corner free_kick throw_in goal_kick penalty`. A `save` is made by the defending goalkeeper and
points at the saved shot with `shot_event_id`. A goal is a `shot` (or `penalty`) with
`outcome = "goal"`. Corners, free kicks, throw-ins and goal kicks are the delivery itself (they carry pass fields).
Events are raw facts only: no xG, difficulty or pressure index (that is the Interpret stage's job).
JSON Schema is in `schema/`.

## Python API

```python
from eventgen import generate_match, replay, areplay
from eventgen.io import write_match
from eventgen.validate import validate_match

match = generate_match(seed=42, stories="random")   # Match(meta, teams, events, ground_truth)
write_match(match, "out/match_001")
assert validate_match(match) == []
for event in replay(match, speed=20.0):             # sync generator, seq order, paced to match clock
    ...
# async: async for event in areplay(match, speed=20.0)
```

Sinks implement `EventSink.send(event)`: `StdoutSink`, `FileSink`, `CallableSink` (in `eventgen.replay`).
An Azure Event Hubs / Service Bus sink is a stretch goal and would be a separate optional module
implementing the same interface; verify the current SDK in the official docs first.

## How it works

A match is a loop of possessions. Each step: maybe a `pressure` event on the ball carrier (more
pressure means worse pass accuracy and more turnovers), maybe a tackle or foul, otherwise a shot or
pass chosen by field zone, player role, team style and pressure. Failed passes become interceptions,
loose balls or out-of-play restarts (throw-in, corner, goal kick). Stoppage time accrues from fouls,
cards, substitutions and goals. No machine learning.

**Determinism:** one `random.Random` per simulation attempt, seeded from the seed; no global RNG and no
wall clock. Same seed + same config + same `generator_version` gives byte-identical files.

**Stories** (`momentum_swing`, `pressing_spell`, `late_comeback`, `red_card_turning_point`,
`star_player_match`, `quiet_then_chaos`) only change simulation parameters inside a window; they never
write events. After generation each story is checked against the real events (for example the star
player really has a standout share of touches). If a planted story is not visible, the generator
re-simulates with the next deterministic attempt (`generation_attempt` in the ground truth, limit
`stories.max_attempts`). Anything still unrealized is listed under `unrealized_stories`.
The real `start_seq`/`end_seq` are written to `ground_truth.json`.

## Calibration

All probabilities and rates live in `config/default.yaml`. Guesses are marked `# UNCALIBRATED` and
listed in [UNCALIBRATED.md](UNCALIBRATED.md). The agents that read this data are described in [AGENTS.md](AGENTS.md). Do not treat the output statistics as realistic numbers.

## Layout

```
eventgen/  schema config league simulate pressure stories groundtruth io replay validate cli
config/    default.yaml  stories.example.yaml
docs/      README.md  UNCALIBRATED.md
schema/    exported JSON Schema      tests/  pytest suite
```

## Calibration tools

```
tools/gen_batch.sh out/calib 40        # generate 40 plain matches and compare to sourced targets
python tools/compare_to_targets.py out/calib --strict
```

Sourced targets and licensing notes: `docs/CALIBRATION-REPORT.md`; what was tuned and what is still
open: `docs/TUNING.md`.
