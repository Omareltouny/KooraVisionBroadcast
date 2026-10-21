# Tuning record: generator output vs sourced targets

Targets: `tools/targets.json` (from `docs/CALIBRATION-REPORT.md`, English top flight, per match, both
teams combined). Measured with `tools/gen_batch.sh out/calib 300` (300 plain matches, `--stories none`,
seeds 1000 to 1299, config as committed). Re-run it after any config change.

```
tools/gen_batch.sh out/calib 300
```

## Result (300 matches)

| Metric | Generator | Sourced range | Verdict |
|---|---|---|---|
| Passes | 877.9 | 849.1 to 945.2 | PASS |
| Pass completion | 0.818 | 0.815 to 0.837 | PASS |
| Long pass share (>= 32 m) | 0.112 | 0.104 to 0.122 | PASS |
| Shots | 24.6 | 24.2 to 27.6 | PASS |
| Goals | 2.85 | 2.75 to 3.28 | PASS |
| Share of matches with 4+ goals | 0.33 | 0.292 to 0.342 | PASS |
| Penalties awarded | 0.24 | 0.17 to 0.33 | PASS |
| Penalty conversion | 0.836 | 0.826 to 0.897 | PASS |
| Fouls | 21.2 | at least 20.4 | PASS |
| Yellow cards | 2.94 | 2.88 to 4.2 | PASS (low end) |
| Red cards | 0.15 | 0.126 to 0.16 | PASS |
| Throw-ins | 35.3 | 35.8 (one season) | x0.98 |
| Match length (min) | 98.1 | at least 98.0 | PASS |
| Tackles | 88.9 | 31.1 (2020-21 only, old) | **not tuned**: x2.9 |
| Goal kicks | 0 | 15.5 (one season) | **no event yet** |

## What changed from the first build
- Config knobs retuned (all still marked `# UNCALIBRATED`, because they are knobs tuned to hit an
  aggregate, not measured values): shot appetite, goal chance, foul / card / penalty rates, pass
  type mix and lengths, action durations, failure split, penalty outcome weights.
- New knob `foul.second_yellow_mult` (referees are slower to book a player already on a yellow);
  without it second yellows pushed red cards to about 3x the sourced rate.
- Code: a misplayed pass that would stay inside the pitch now runs on and leaves over the nearer
  touchline (the old behaviour fell back to "incomplete" and produced only about 12 throw-ins per match).
- `stories.max_attempts` raised from 60 to 150: two-story random combinations such as
  late comeback + star player sometimes need about 90 attempts (about 6 s worst case per match).

## Round 2 (generator 1.1.0, 1,000 matches, seeds 1000 to 1999)

Run `tools/gen_batch.sh out/calib 1000` to reproduce (about 40 seconds). Targets follow the 2025-26 season.

| Metric | Generator | Sourced target | Verdict |
|---|---|---|---|
| passes per match | 864.5 | 849 to 945 | PASS |
| shots | 24.3 | 24.2 to 27.6 | PASS |
| goals | 2.99 | 2.75 to 3.28 | PASS |
| pass completion | 0.822 | in range | PASS |
| home goal share | 0.534 | 0.502 to 0.573 | PASS |
| home / draw / away share | 0.416 / 0.263 / 0.321 | 0.41-0.48 / 0.22-0.27 / 0.29-0.35 | PASS |
| goals in second half | 0.561 | 0.55 to 0.60 (point 0.601, partial season) | inside the recommended band |
| goals at 90+ | 0.092 | 0.056 to 0.133 (2025-26 early 0.113 to 0.133) | PASS |
| subs per team | 4.00 | 3.95 to 4.15 | PASS |
| tackles | 31.2 | 31.1 (2020-21, old) | matches the only source |
| goal kicks | 16.6 | 15.5 | 1.07x |
| throw-in / goal-kick / corner / penalty / substitution seconds | 17.8 / 30.4 / 36.0 / 164.9 / 75.9 | 17.8 / 30.4 / 36.1 / 164.7 / 76.1 | match |
| match length (min) | 100.8 | at least 98 (2025-26 above 100) | PASS |

Still just outside a range (all within sampling noise of the bound, 1,000 matches):
red cards 0.16 (limit 0.16), matches with 4+ goals 0.35 (limit 0.342), goals after minute 75 0.273
(limit 0.263), substitute goal share 0.125 (limit 0.126). Comeback-win share is 0.134 vs 0.166.

### What changed in round 2
- **Home advantage** (`game.home_shot_mult`, `game.home_completion_bonus`).
- **Time and score shape** (`game.*`): cautious first 15 minutes, a stronger second half, trailing teams attack more,
  leading teams ease off. Longer added time (`stoppage_per_sub_ms` 30 s) so substitutions cost clock time.
- **Substitutions**: 3 to 5 per team (mean 4); substitutes shoot slightly less (`game.sub_shot_mult`) to hit the sourced goal share.
- **Restart dead time** set to the 2025-26 league means. Passes fell as a result, so action times were shortened by about 15%.
- **Tackles** cut to about 31 per match; fouls were kept constant by raising the foul chance per attempt.
- **New events**: `goal_kick` (goalkeeper, short or long) and `save` (links to the saved shot, outcome caught, parried or tipped).
  Validator rule 16 checks them. Ground-truth stats now include `goal_kicks` and `saves`.
- **Header share** of goals raised (`shot.header_prob`), **kit colours** made distinct (away kit when two shirts are too close).

## Open (needs the owner or better sources)
- **Tackles** still have a single old source (2020-21) with an unknown definition. Pressure counts, shots on target,
  corners and free kicks have no reliable target (generator: about 244 pressures, 13 on target, 5.3 corners, 20 free kicks).
- **Kit colours** now differ in every fixture, but no test covers colour-blind-safe palettes beyond the distance rule.
- Every value in `config/default.yaml` marked UNCALIBRATED is still a guess (`docs/UNCALIBRATED.md`).
- The comparison script does not judge spread. Per-match spreads are the generator's own.

## Round 3: pass direction mix

Pass direction mix changed (short passes go in any direction; forward weight 0.9 to 0.45, lateral 0.5 to 0.75,
passes 8 percent longer). Shots fell to about 18 per match, so `shot.weight_scale` went 0.240 to 0.435 and
`goal_near` 0.435 to 0.455 (400 matches: 24.96 shots, 2.91 goals, 891 passes). Small remaining misses (draw share,
goals_4plus_share, penalty conversion) are within sampling noise of the targets. These are event-count targets
from public season statistics only; nothing here claims the data matches real matches in detail.
