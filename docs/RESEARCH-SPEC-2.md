# Spec 2: Research for solutions (open problems + the full five-stage pipeline)

Audience: research agent. Status: v2, 2026-10-19. Replaces the open items of `RESEARCH-SPEC.md`.
Inputs you should read first: `docs/CALIBRATION-REPORT.md`, `docs/TUNING.md`, `docs/UNCALIBRATED.md`,
`docs/README.md`, `synthetic-event-generator-spec.md`, `schema/*.json`.

## 0. Settled facts and rules of work

- **Settled:** calibrating the generator to published aggregate statistics is allowed. Do not research
  or re-open that question. Raw event or tracking data from real matches is still never stored in the repo.
- Cite every claim (source, URL, date, season, licence). No invented numbers; "not found" is a valid answer.
- This spec asks for **solutions**, not only facts. For every item deliver: the options (2 to 3), a
  recommendation, the effort (hours, S/M/L), the risk, and the exact change it implies (file, field, config key).
- Keep real club, player and league names out of code, config and the app UI. They may appear in your report.
- Output: `docs/RESEARCH-REPORT-2.md` (decision-ready) and, where a solution is a design, a short design
  note per item in `docs/design/`. No production code beyond small scripts under `tools/`.

## 1. The product we are building (verbatim requirements, do not reinterpret)

**(i) One pipeline with five stages.** The project should:
- (a) **Ingest** synthetic match events as they happen (passes, shots, tackles, possession changes,
  pressure events, match metadata, etc.).
- (b) **Interpret** them into meaningful football statistics, patterns, and the context behind them.
- (c) **Explain** why a moment matters rather than only reporting that it happened.
- (d) **Render** that insight into something that can sit on screen alongside the match.
- (e) **Personalize** it so the same intelligence reaches a data-hungry analyst and a casual fan as two
  genuinely different experiences: customized modes, favorite club(s), favorite player(s), a player-focused
  mode that follows one player throughout the match, and many more ideas. The project may focus on
  on-screen storytelling (clean outputs, timed and machine-readable enough to be rendered as synchronized
  graphical overlays on a live match feed, the way the platform's rendering partner handles overlays in the
  production path), or on personalized audience experiences (viewing modes shaped by language preference,
  favorite club, favorite player, or a single performance metric a viewer cares about), or both. A project
  that only generates metrics has no audience; a solution that only personalizes has nothing to personalize.

**(ii) Real-time match intelligence:** aggregate events into football states and statistics. Consider:
player identification (real-time name tagging, with optional speed and distance indicators triggered at
predefined thresholds); pass quality (distance, accuracy, a pass difficulty rating); speed metrics (ball
speed, shot speed); auto-eventing (a model over an incoming video feed generating the pass and speed
metrics automatically).
**(iii) Narrative generation:** key narratives, player-performance context, notable milestones, match recaps.
**(iv) Explainability:** why moments matter, such as control vs. chaos, tactical pressure changes, game
rhythm patterns.
**(v) Data innovation:** create or extend synthetic football-realistic datasets (passes, shots, tackles,
possession changes, pressure events, match metadata).
**(vi) Multi-language storytelling:** clear natural-language output for global studio and streaming
scenarios in multiple languages.

Where we are: stage (a)'s data source (the generator) is built. The later stages are not. The point of this
research is to make sure the generator, and every decision from here, serves the stages that earn the score.

## 2. Part A: Open problems from the generator (find solutions)

Current state is in `docs/TUNING.md`. For each item: options, recommendation, effort, exact change.

| # | Problem | What to find |
|---|---|---|
| A1 | **No `goal_kick` or `save` events.** Goal kicks are a possession change plus a goalkeeper pass; saves are only a shot outcome. Sourced goal kicks: 15.5 per match (2025-26). | Minimal faithful event design: fields for `goal_kick` and `save` (goalkeeper id, link to the shot, save type if a public definition exists), where they fit in the possession and validator rules, and how the comparison script should count them. |
| A2 | **No home advantage.** Generator home goal share 0.49; sourced 0.516 to 0.556 (home win share and home possession figures are in the report). | A single, defensible mechanism (for example a small multiplier on home attack intensity and on the home completion edge) with a first value range, and the test that proves it lands in the sourced range. |
| A3 | **Teams do not react to the score or the clock** outside planted stories. Sourced direction: trailing teams hold more possession and shoot less; late goals are more frequent (stoppage-time goal share 8.4% in 2024-25, about 13% early 2025-26); 16.6% of matches had a team win after being behind (2024-25). | A small score-and-time-dependent adjustment, with sourced direction and magnitude where they exist, and the base rates the generator should reproduce for comebacks and late goals. Make sure planted stories still add on top without double counting. |
| A4 | **Tackle count is untuned** (generator about 89 per match; only source: 31.1, 2020-21, unknown definition). Pressure counts have no public source. | Find a recent, defined tackle statistic (attempted vs won, per team or per match) or conclude none exists. If none, propose a defensible way to define our "tackle" and "pressure" events (so the Interpret stage can state its definition honestly) and what to keep as design parameters. |
| A5 | **Shots on target, corners, free kicks, goals by half, shots by distance band** have no solid target. | Best available sourced values, or a decision to leave as design parameters. |
| A6 | **Season to imitate for restart timing** (2025-26 full season vs 2026-27 with the throw-in and goal-kick directive and only about 50 matches). | Recommendation with reasons and the exact `timing.dead_ball_ms` values implied (mean and spread). |
| A7 | **Team colours:** some pairs (red/green, blue/purple) are indistinguishable by luminance and for red-green colour blindness. | A palette rule or an `away` colour pair field, tested with contrast ratios and a colour-blind simulation, small enough to implement in a day. |
| A8 | **Name audit (H1).** Names are procedural. | A method and a run result: generate 2,000+ players and all clubs and check against public lists of club names, towns used as club names and famous people (you may use public lists in your own tooling; do not commit real names). List collisions and the syllable changes that remove them. |
| A9 | **Arabic and Spanish names and club suffixes (H2).** | Review criteria and a sample of 50 generated entries for a native reviewer; known pitfalls (transliteration conventions, unfortunate words). |
| A10 | **Cross-platform byte determinism (H4).** | Method and a result table for Python 3.10 to 3.13 on Linux, macOS, Windows (or a CI recipe). Known risks: float formatting, `random.Random(str)` seeding, line endings. |
| A11 | **Licence (H3).** | Recommendation (MIT was suggested). Check the hackathon licence clause in the rules and any conflict. |
| A12 | **Azure stretch sink (G1 to G3).** Event Hubs was recommended. | Confirm current official Python SDK versions, partition-key usage when batching, auth without secrets, cost or free tier, and whether the rules reward using Azure here. A short design note for an optional `eventgen_azure` package. |
| A13 | **Spread, not only means.** The comparison script judges means. | Sourced per-match spreads (standard deviation or percentile bands) for goals, cards, shots, fouls, possession, or a statement that none exist; then extend `tools/compare_to_targets.py` to test spread where a source exists. |
| A14 | **Home-side shots on target and possession spread.** | Sourced values or "not found". |

## 3. Part B: What the later stages need from the data (find solutions)

The generator is the data source; the score comes from (b) to (e). For each stage, work out what
inputs it needs, which of them the generator must emit, and which belong to the stage itself (the generator
must emit raw facts only; derived statistics such as difficulty or pressure index belong to Interpret).

### B1. Ingest (a)
- Streaming contract: ordering, late or duplicate events, `seq` as the canonical order, match metadata at
  start, how a consumer detects the end of a period and the match. Propose the minimal envelope the replay
  should emit (for example a `match_start` header, heartbeat/clock ticks, `match_end`), and whether the
  current `period_start`/`period_end` events suffice.
- Replay speed and clock semantics for demos (speed controls, pause, seek, start at minute N).
- Output: a one-page ingest contract and a list of generator changes (if any).

### B2. Interpret (b)
- A catalogue of football states and statistics computable from events alone, with sourced definitions
  where they exist: possession (time and pass based), territory, field tilt, passing networks, progressive
  passes, passes into the final third, pressure and counter-pressure, turnover location, shot quality
  proxies, momentum, control vs chaos, game rhythm (event rate, tempo, ball-in-play share).
- For each: the formula, the inputs, the minimum window (rolling 5 or 10 minutes), the update rate, and
  whether it needs positions beyond the event coordinates.
- **Pass quality (required by the rules):** pass distance and accuracy are direct; a **pass difficulty rating**
  needs a defensible event-only definition (length, direction, zone, pressure at start, receiver pressure,
  line-breaking). Find published approaches and propose one explainable formula that uses only fields we
  emit. List any extra raw field the generator would need.
- **Speed metrics:** ball speed and shot speed exist as raw fields. Find what viewers expect to see (units,
  thresholds, "fastest shot of the match").
- **Player identification with speed and distance indicators:** events carry no player running speed or
  distance. Evaluate the options: (1) a separate optional `tracking.jsonl` (player x, y per second or per
  event window) generated consistently with events, (2) distance derived from event positions only (coarse),
  (3) skip. Recommend one, with the file format, rate, size per match, how the generator would produce it
  cheaply and plausibly, and the thresholds that trigger an indicator (sourced sprint and high-intensity
  speed definitions).
- **Auto-eventing (video model):** the rules list it as a feature to consider. Research feasible scope for a
  hackathon: what a video-to-events model would output, which open or Microsoft/Azure vision services could
  do pass and ball-speed estimation, what synthetic video would be needed, and whether to demonstrate it as
  a clearly labelled mock/adapter (events produced from a synthetic feed) instead of real video. Recommend
  scope and a risk note (the rules say entrants must hold every licence for footage).
- Output: a metric catalogue table and the one chosen formula for pass difficulty, momentum and control vs chaos.

### B3. Explain (c) and Explainability (iv)
- What makes a moment matter: score state and time left, win-probability swing (find a simple, explainable
  method; a lookup or logistic model fitted to sourced aggregates is acceptable, nothing opaque), turning
  points, momentum shifts, pressing spells, red cards, comebacks, milestones (first goal, 100th pass,
  fastest shot, streaks).
- A template for an explanation (claim, evidence, context, so-what) so every explanation names the
  statistics behind it, and the rule for when **not** to explain (noise).
- How to evaluate explanations against `ground_truth.json` (detection precision and recall of planted
  stories, timing error in seq and seconds, correctness of the stated reason). Propose the metric and a
  pass bar. Remember the explain stage must not read ground truth at runtime.
- **What the generator should plant additionally** so that explanations have something real to find (for
  example, stories that produce a visible tempo change, a pressing trigger, a substitution impact, a
  tactical switch). List the story types worth adding, with the parameter changes each implies and the
  realization check.
- Output: an explanation template, an evaluation protocol, and a prioritized list of extra stories.

### B4. Narrative generation (iii) and multi-language storytelling (vi)
- Approach options: templates, LLM generation with grounded facts, hybrid. Recommend a hybrid in which every
  sentence is generated from structured facts (so numbers are never invented) and an evaluation that
  checks every number in the text against the facts.
- Output types: live captions (short, timed), milestone alerts, half-time summary, full-time recap, player
  report, analyst deep dive. Length and tone for each.
- Languages: which to ship first (the generator has `en`, `ar`, `es`) and why; how right-to-left (Arabic)
  affects overlay layout; football terminology glossaries per language; how to keep names consistent with
  `name_i18n`; number and date formatting by locale; how to evaluate translation quality (back-translation
  checks, glossary checks, native-reader sample). Cost and latency of generating per language live vs
  generating facts once and rendering text per language.
- `description_i18n` for ground truth (the current ground-truth text is English only): design and effort.
- Output: a narrative architecture note, a glossary format and a language rollout plan.

### B5. Render (d)
- What "machine-readable and timed enough to render as synchronized overlays" means in practice. Find public
  information about how broadcast graphics and overlay partners consume data (timing model, data formats,
  latency, safe areas, aspect ratios) without relying on private information. Propose our **overlay
  message schema**: `overlay_id`, `start_ms`/`end_ms` or `start_seq`/`end_seq`, `type` (lower third, stat
  card, momentum bar, player tag, pitch map, alert), `priority`, `payload`, `i18n` text map, `style` hints,
  `audience` tags, `source_event_ids` for traceability.
- Output formats to evaluate: JSON stream, WebSocket, Server-Sent Events, a simple HTML/Canvas overlay
  player for the demo, and what is needed for a recorded demo video (the rules want a demo video without
  third-party trademarks).
- Visual design rules for readability on a moving feed (duration on screen, frequency cap, collision rules,
  accessibility: contrast, colour-blind safe palettes, text size, RTL).
- Output: overlay schema draft, a rendering recommendation for the hackathon, and a frequency/priority rule.

### B6. Personalize (e)  (the main differentiator, treat as the core of the research)
Deliver a concrete personalization design, not a list of ideas.
- **Personas** (research, then pick 4 to 6 with evidence): data-hungry analyst, casual fan, club
  superfan, fantasy/betting-style stat watcher, player-focused follower, newcomer or learner, accessibility
  needs (screen reader, low vision, colour blind), language-first viewer, second-screen vs main-screen viewer.
- **Dimensions** a viewer can control: language, expertise level (verbosity and jargon), favorite club(s),
  favorite player(s), single metric focus (for example ball speed, pass difficulty, pressure), notification
  intensity, spoiler sensitivity, tone (neutral, excited, analytical), overlay density.
- **Player-focused mode:** what to show for one player throughout the match (live involvement, heat map,
  key passes, duels, running load if tracking exists, milestones, a personal recap), what events to
  attach, how to handle substitutions and off-ball minutes.
- **Favorite-club mode:** how the same moment is framed for each side (a goal means different things to
  each fan), neutral vs partisan framing, and the rules to avoid misleading output.
- **Ranking:** how to choose what to show now. Propose a relevance score (importance of the moment times
  profile match times novelty times recency) and the rate limits per persona. Evaluate how to test that two
  personas get genuinely different output from the same events (a difference metric) and a protocol for a
  small user test or a heuristic review.
- **Profile format:** a small JSON profile and the defaults per persona, so the demo can switch persona live.
- **Cold start and privacy:** no personal data stored; profile kept locally or in the session.
- **Further ideas** worth the effort, ranked by judge impact and effort (for example: "explain it to me"
  button, glossary tooltips for newcomers, "what changed since I looked away" catch-up, multi-view split of
  the same match, watch-party shared overlays, voice or audio-description scripts, a challenge mode that
  asks the fan to predict the next event).
- Output: persona table, profile schema, relevance-scoring formula, player-focus spec, and a ranked idea list.

### B7. Data innovation (v)
- Which extra synthetic data would make the project stand out and is credible: tracking file (B2), richer
  set of events (A1), second competition or season, multiple matches with league table context, injuries,
  VAR checks, weather or crowd metadata. For each: value for the demo, effort, risk of unrealistic output.
- Provenance: how to document that the dataset is synthetic and how it was calibrated (sources, tuning log),
  as something judges can read.
- Output: a ranked list with a recommendation of what to build next.

## 4. Part C: Judging and submission (find and plan)

- Extract from the official rules everything about scoring: criteria, weights, stages, pass/fail items,
  what the demo video and pitch must contain, required technology mentions, team and licence terms.
  Translate them into a **scoring checklist** and map every item to a feature in this project.
- Identify which Microsoft and Azure technologies the rules reward, and which are realistic here (the
  earlier report listed Foundry, Agent Framework, Azure MCP, GitHub Copilot Agent Mode, Fabric, GitHub
  SDK/CLI, Azure apps, AI services, databases). For each: what role it could play in the five stages,
  effort, and the demo risk. Recommend a minimal credible stack.
- Propose the demo story: a 3 to 5 minute walkthrough of one generated match with two personas side by side
  and one language switch, and the exact planted stories it should contain so the explanation moments land.
- Risks and a cut list: what to drop first if time runs out.

## 5. Part D: Build order recommendation

Using the findings, propose the build order for the rest of the project for a team with limited time:
which generator changes first (A1 to A3 and B-items that change the data), then Interpret, Explain, Render,
Personalize, Narrative. Give a milestone plan with a definition of done per milestone and the evaluation
used to accept it. Flag decisions the owner must make and the date they block.

## 6. Deliverables and definition of done

- [ ] `docs/RESEARCH-REPORT-2.md` with sections A, B1 to B7, C, D; every claim cited; every problem has
      options, a recommendation, effort and the exact repo change.
- [ ] Design notes in `docs/design/` for: ingest contract, metric catalogue (with the pass difficulty
      formula), explanation template and evaluation protocol, narrative and language architecture, overlay
      schema, personalization profile and relevance scoring, tracking file (if recommended).
- [ ] Updated `tools/targets.json` and `tools/compare_to_targets.py` for new sourced targets or spread tests.
- [ ] A one-page decision list for the owner (open decisions, options, recommendation, deadline).
- [ ] A ranked backlog (must, should, could) with effort, tied to the judging checklist.
- [ ] No raw real data, no real names in code or config, no secrets.
