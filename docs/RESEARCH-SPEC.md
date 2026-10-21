# Spec: Research tasks for the event generator (what is missing, what to check)

Audience: research agent. Status: v1, 2026-10-18.
Context: `eventgen` v1.0.0 (this repo) is built and passes its tests. Its realism numbers are
guesses (`docs/UNCALIBRATED.md`, 90 values). This spec says what the research agent must find out
so those guesses can be replaced by sourced values, and which open questions need evidence.

## 0. Ground rules for the research agent

1. **Cite everything.** Each value you propose needs: source name, URL, date accessed, the
   competition and season it describes, and the licence or terms of use.
2. **Do not invent numbers.** If no source is found, report "not found" and leave the value
   `UNCALIBRATED`. A range from a source beats a point guess. Say whether a number is a mean,
   median or per-team-per-match.
3. **Aggregates only.** Hackathon rule: synthetic data only, no real event data (Opta, StatsBomb,
   Hudl and similar). Research may use published *summary statistics* (articles, public reports,
   papers). Never download, copy or paste raw event feeds, player tracking, or per-match logs into
   this repo. Task A1 below asks the owner to confirm this reading of the rules before anything is used.
4. **No real names in the repo.** Findings go in a report; only numbers and citations may flow into
   `config/default.yaml` comments. No real club, player or league names in code, config or docs.
5. **Output:** a single report `docs/CALIBRATION-REPORT.md` plus a proposed patch to
   `config/default.yaml` (values and the `# UNCALIBRATED` markers removed only where sourced).
   Keep the "one setting per line" format; `docs/UNCALIBRATED.md` must stay in sync (a test enforces it).

## 1. Gate: rules and licensing (do first, blocks everything else)

| # | Question | Done when |
|---|---|---|
| A1 | Do the hackathon rules allow calibrating a synthetic generator from published aggregate statistics? Quote the exact rule text. | Quote + link + verdict (allowed / forbidden / unclear). If unclear, list the question for the organizers. |
| A2 | Which candidate sources allow reuse of their *aggregate* numbers, with what attribution? | Table: source, what it offers, licence, attribution text, verdict. |
| A3 | Do the hackathon rules require anything about fictional league naming, trademarks or crest-like colours? | Short note. Current names are procedural and fictional; confirm no accidental overlap (see D1). |
| A4 | Are there rules on use of Azure services for the stretch sink (required? forbidden? credits)? | Quote + link. |

## 2. Calibration targets (what is missing)

For each row find a sourced value or range, for a top-flight men's league across several recent
seasons (state which). Report per team per match unless noted. "Config key" is the placeholder to replace.

### 2.1 Match volume and outcome
| # | Quantity | Config key(s) it calibrates | Generator baseline (40 seeds, per team unless noted) |
|---|---|---|---|
| B1 | Passes attempted | `passing.*`, `timing.action_ms` | mean 415 (range 376-460) |
| B2 | Pass completion rate, overall and by zone/length (short, long, cross) | `passing.completion`, `passing.pressure_penalty` | mean 0.83 |
| B3 | Shots, shots on target, share blocked, share off target | `shot.weight_scale`, `shot.block_prob`, `shot.off_target_*` | 15.5 shots, 7.9 on target |
| B4 | Goals per match (total) and its spread (share of 0, 1, 2, 3, 4+ goal matches) | `shot.goal_*` | mean 3.5 total, range 0 to 11 (too wide a tail?) |
| B5 | Conversion by shot distance band | `shot.goal_near`, `shot.goal_decay_m` | not measured yet |
| B6 | Home advantage (points, goals, possession) | `team_style` (none today, no home effect modelled) | none |
| B7 | Penalties awarded per match | `foul.box_foul_mult` and in-box fouls | 0.72 per match (suspect: high) |
| B8 | Penalty conversion rate | `penalty.outcome_weights` | goal 0.76 (placeholder) |

### 2.2 Defensive and discipline
| # | Quantity | Config key(s) | Baseline |
|---|---|---|---|
| C1 | Tackles attempted and tackle success rate | `pressure.tackle_*` | 43.7 tackles |
| C2 | Pressures per match and pressure success; typical presser distance and duration (only if a public definition exists) | `pressure.*` | 138.5 pressures |
| C3 | Fouls per match | `foul.defender_foul_prob`, `foul.offensive_foul_prob` | 7.8 |
| C4 | Yellow and red cards per match | `foul.yellow_prob`, `foul.red_prob` | 2.25 yellow, 0.25 red per match |
| C5 | Share of fouls by the team in possession vs defending | `foul.offensive_foul_prob` | ~minor |

### 2.3 Restarts, time and substitutions
| # | Quantity | Config key(s) | Baseline |
|---|---|---|---|
| D2 | Corners, throw-ins, free kicks, goal kicks per match | `shot.after_*`, `passing.failure_split` | corners 3.4, throw-ins 5.8 (looks low), free kicks 7.4 |
| D3 | Ball-in-play time and typical dead-ball durations per restart type | `timing.dead_ball_ms` | placeholders |
| D4 | Added time per half (mean and spread) and what drives it | `match.stoppage_*` | half 1: 3.0 min, half 2: 4.5 min |
| D5 | Substitutions: number per team, timing distribution | `match.sub_*` | 2 to 5, minutes 46 to 85 |
| D6 | Ball speeds by pass type and shot speed ranges | `passing.speed_ms`, `shot.speed_ms`, `bounds.*` | placeholders |
| D7 | Pass lengths by type | `passing.length_m` | placeholders |

### 2.4 Structure and style
| # | Quantity | Config key(s) |
|---|---|---|
| E1 | Spread of team styles between clubs (possession, pressing, directness) so the style ranges are not arbitrary | `team_style.*` |
| E2 | Typical share of touches/passes by role (GK, CB, FB, DM, CM, AM, W, ST) | `roles.involvement`, `roles.anchor_x` |
| E3 | Shot share by role | `roles.shot_mult` |
| E4 | Common formations and their frequency | `match.formations` |
| E5 | Possession-time share distribution (how lopsided matches get) | baseline: mean absolute gap from 50% is 2.8 points, max 11 |
| E6 | How scoring and cards change behaviour (trailing teams push, ten-man teams) | `stories.effects.*` magnitudes, grounding for the story types |

Deliverable per row: value or range, source, confidence (high / medium / low), and a one-line
recommendation (replace / keep placeholder / needs the owner).

## 3. What the generator does not model yet (missing features, evaluate before building)

For each, the research agent answers: *does the Interpret/Explain stage or the demo need it, and
what is the minimum faithful design?* Do not propose code beyond a short design note.

| # | Gap | Why it may matter |
|---|---|---|
| F1 | No separate dribble/carry, clearance, goal-kick, offside, save or block events (goalkeeper actions are implicit in shot outcomes) | Story detection and explanations may expect these |
| F2 | No extra time or penalty shootout | Cup demos |
| F3 | No injuries, injury-time substitutions in the first half, or fatigue | Realism of late-game patterns |
| F4 | No home advantage, no team form, no rivalry/strength tiers across the league | League-level stories |
| F5 | No player positions over time (stretch: tracking snapshots) | Overlay/Render demos |
| F6 | No VAR or disallowed goals | Drama moments |
| F7 | No score-state behaviour outside planted stories (teams do not naturally push when behind) | Comebacks would emerge naturally |
| F8 | No own goals, no assists as separate events (key passes are derived from `assist_event_id`) | Stat completeness |
| F9 | Ground-truth `description` is English only | Multilingual demos need localized descriptions |

## 4. Plausibility checks (run against sourced values from section 2)

The research agent should write a small, dependency-free script `tools/compare_to_targets.py`
(new file, no real data inside) that generates N seeds with the CLI/API and prints, for each
sourced target, the generator mean, spread and a pass/fail against the sourced range. Check:

1. Means fall inside the sourced range; spreads are not wider than the real spread (B4 is the
   known worry: totals of 8 to 11 goals appear).
2. Correlations people expect: more shots with more possession; more pressure with more turnovers;
   fouls and cards positively related; second-half added time longer than first (check the source).
3. Time sanity: first events, half length, added time, no event after the final whistle.
4. Distribution shape, not only the mean (histograms of goals, cards, shots).
5. Style diversity: matches should differ by team, not only by seed.

## 5. Research on the stretch goal (Azure sink)

| # | Question | Done when |
|---|---|---|
| G1 | Event Hubs vs Service Bus for a replayed ordered event stream (ordering, partitioning by `match_id`, throughput, cost, free tier) | Recommendation with reasons; list the question for the owner (spec open item 2). |
| G2 | Current official Python SDK package names and versions, authentication options (no secrets in the repo) | Links to official docs, minimal send example reviewed against the docs. |
| G3 | Fit with `EventSink.send(event)` in `eventgen/replay.py` (batching, async, retries) | Short design note. Must live in an optional module so the core keeps no Azure dependency. |

## 6. Repo safety and quality checks

| # | Check | Done when |
|---|---|---|
| H1 | Fictional-name audit: club names, place names, player names (all procedural). Look for accidental matches with real clubs, towns used as club names, or famous people across a large sample (for example 2,000 generated players). | List of matches found, proposed syllable list changes. |
| H2 | Arabic and Spanish renderings: are the Arabic transliterations readable and not offensive, is the `es` team-name pattern acceptable? Native-speaker review is better than automated checks. | Issues list with fixes. |
| H3 | Public-repo audit: secrets, keys, personal data, licence file (none exists yet), third-party code (none copied, confirm). | Checklist plus recommended licence. |
| H4 | Reproducibility across Python versions and platforms (3.10 to 3.13, Linux/macOS/Windows): byte-identical `events.jsonl` for the same seed. | Table of results; note any float formatting differences. |
| H5 | Colour pairs: are default team colour pairs distinguishable (including colour-blind viewers) when a Render stage draws two teams? | Short note. |

## 7. Decisions needed from the owner (research agent prepares options, does not decide)

1. Which source(s) for calibration, given licensing (section 1).
2. Number of fictional clubs for the demo league (`competition.num_clubs`, default 6).
3. Azure service for the stretch sink.
4. Whether to add the missing event types in F1 before the Interpret stage starts.

## 8. Definition of done

- [ ] Section 1 answered first, with quotes and links.
- [ ] Every row in 2.1 to 2.4 answered or marked "not found".
- [ ] `docs/CALIBRATION-REPORT.md` written, every number cited.
- [ ] Proposed `config/default.yaml` patch: only sourced values lose the `UNCALIBRATED` marker.
- [ ] `tools/compare_to_targets.py` runs and its output is pasted in the report.
- [ ] Sections 3, 5, 6 each have written findings or recommendations.
- [ ] Open decisions in section 7 listed with options and a recommendation.
- [ ] No raw real data, no real names, no secrets added to the repo.
