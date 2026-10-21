# Tracking data (`tracking.jsonl`)

Events say **what happened**. Tracking says **where everybody was**, 5 times a second. It is what
makes speed, distance, spacing and sprint numbers possible, and it feeds the Interpret stage
(player identification with speed and distance indicators) and the auto-eventing adapter.

**It is synthetic.** It is built from the events of the same match, not recorded from real games.

## Format

Line 1 is a header, every later line is one frame.

```
{"type":"header","match_id":"m00042-fel-gus","hz":5,"pitch_length_m":105.0,"pitch_width_m":68.0,
 "coordinates":"...","provenance":"synthetic_tracking_from_events","generator_version":"1.0.0","seed":42,
 "players":[{"index":0,"player_id":"T01-P01","team_id":"T01","jersey_number":1}, ...36 players...],
 "fidelity":{"pins_checked":2626.0,"pin_within_1_5m":0.95,"pin_within_3m":0.97}}
{"type":"frame","t":0,"period":1,"ball":[52.5,34.0],"p":[[0,5.31,33.1],[1,36.2,8.55], ...]}
```

`t` is the match clock in ms (same clock as `match_clock_ms` in events). `p` lists only the players
on the pitch, as `[index into header.players, x, y]`. Substituted-off and sent-off players disappear;
a substitute appears on the touchline at the halfway line. Coordinates use the same absolute pitch
frame as the events. About 30,000 frames and 12 MB per match. JSON Schema: `schema/tracking_*.schema.json`.

## How it is made

1. Every event pins the ball and the acting players to a place and time (passer, receiver at arrival,
   tackler and opponent, presser at `distance_m` from the pressed player, fouler and fouled player).
2. Between pins, each player drifts to a formation slot that follows the ball up and down the pitch
   (more forward when the team has the ball, deeper when it does not) with a small random drift.
3. Players start moving towards their next pin early enough to arrive on time, within a speed and
   acceleration limit. Events are never changed; the output is deterministic from the match seed.

## Checks (validator rules 11 to 15)

Frame grid complete; positions inside the pitch and at most 11 per team; no frame step faster than
the speed limit; sent-off and substituted players never reappear; the ball is at the event position
and the acting player is near it for nearly every event.

## Honest limits

- Everything in `tracking:` in `config/default.yaml` is **UNCALIBRATED** (see `UNCALIBRATED.md`): hand-set values
  that give a football-like shape (speeds, distances, team spacing). The output is synthetic and has **not** been
  validated against real match data; do not present it as realistic or as a model of real football.
- The ball is 2D (no height). Off-ball movement is a simple model (formation slots, forward runs), not tactics.
- `python -m eventgen autoevent` finds kicks from the ball trajectory and scores them against the true events
  (about 0.80 F1 on test matches). It is a **mock** of the positions-to-events step. **It does not process video.**
