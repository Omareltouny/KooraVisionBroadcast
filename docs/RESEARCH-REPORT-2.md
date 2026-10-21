# KooraVision: Research Report 2 (decision-ready)

Prepared 2026-10-19. Answers `RESEARCH-SPEC-2.md`. Detail and sources live in `docs/research/01` to `05`; this file is the synthesis. Anything marked **(design)** is our proposal, not a sourced fact. Anything marked **(unverified)** came through fetch-tool summaries or could not be checked, and must be re-read before it goes into the demo.

---

## 0. Read this first (urgent)

| Item | Value |
|---|---|
| Registration closes | **2026-10-20 12:00 PM PT** (tomorrow; roughly 22:00 Cairo, verify the conversion) |
| Submission closes | **2026-10-27 11:59 PM PT** (8 days) |
| Demo video | **under 2 minutes** (rules s.4.4). Plan a 1:45 cut |
| Repo | public GitHub, MIT recommended |
| Newness | project must be created after 2026-09-29. Check the first-commit date |

Re-read the official rules page once by eye before submitting; section numbers came second-hand.

### Owner decisions needed (answer these and I can build immediately)

1. Season basis for restart timings and targets: **2025-26 (recommended)** or 2026-27 (only 50 matches of data).
2. Optional 5 Hz tracking file: **stretch only (recommended)**, or build now.
3. Languages at launch: **en, ar, es (recommended)**.
4. Use a live Azure OpenAI/Foundry model for the "stylist", or ship templates plus cached LLM output only. Recommended: templates live, LLM cached.
5. Who does the native-speaker review for Arabic and Spanish (glossary and about 30 sample sentences)?
6. Team has registered? Foundry quota confirmed?

---

## A. Open generator problems

Measured against the 22 new sourced targets over 300 matches (`tools/targets.json`).

| # | Problem | Options | Recommendation | Effort | Repo change |
|---|---|---|---|---|---|
| A1 | No `goal_kick`, no `save` events (goal_kicks 0; shots saved are implicit) | (a) leave; (b) add `goal_kick` (pass-like, GK as passer) and `save` (defending GK, links `shot_event_id`, outcome caught/parried/tipped) | **(b).** Both feed Interpret/Explain and the player-focus mode (keepers have no involvement otherwise) | M | `schema.py` new classes in the union and `PASS_LIKE`; `simulate.py` emit on `saved` and on out-of-play goal-kick restarts; validator rules for GK identity and shot link; regenerate JSON Schema; tests |
| A2 | Home advantage absent (home goal share 0.48, target 0.502 to 0.573, aim 0.545; home/draw/away 0.317/0.27/0.413 vs 0.41-0.48 / 0.22-0.27 / 0.29-0.35) | (a) none; (b) small multiplier on home attack and completion; (c) separate home profile | **(b).** One config key `home_advantage.attack_mult` (about 1.05 to 1.08) plus `completion_bonus`; tune to goal share 0.545 | S | `config/default.yaml` + `config.py`, applied in `MatchSimulator` step; UNCALIBRATED marker kept; rerun `gen_batch.sh 300` |
| A3 | Score-state and time shape (second-half goal share 0.494 vs 0.55 to 0.60; first-15 share 0.165 vs about 0.13; 90+ share target 0.056 to 0.09) | (a) none; (b) intensity ramp by minute plus trailing-team push, leading-team sit-back | **(b)**, small, config-driven. Fatigue ramp raises second-half shot rate; trailing team gets attack multiplier by goal deficit | M | `simulate.py` step reads minute and score diff; config block `game_state`; targets re-check |
| A4 | Substitutions: 3.48 per team vs 3.95 to 4.15; sub goal share 0.10 vs 0.126 to 0.133 | Raise range and give subs a tiny attack bonus | `sub_count_range` to [3,5], mean about 4; `sub_minute_range` skew 55 to 80 | S | config only |
| A5 | Comeback-win share 0.123 vs 0.166 | Falls out of A2 + A3; retest before touching | Do A2/A3 first | S | none |
| A6 | Restart timings use old values | Adopt 2025-26 means: throw-in 17.8 s, goal kick 30.4 s, corner 36.1 s, penalty 164.7 s, substitution 76.1 s; ball in play 55:23. 2026-27 values are 15.3/27.7/33.9/117.4/64.3 | **2025-26** (full season) | S | `stoppage` and restart config; add targets |
| A7 | Kit colour pairs hard to tell apart (red/green, blue/purple). About 8% of men have red-green deficiency; WCAG 1.4.1 says colour must not be the only cue | Contrast-aware away-kit pick; add pattern/outline as second cue in render | Choose away primary by luminance and hue distance from home; render adds a shape or number badge | S | `league.py` palette selection; a small test asserting minimum contrast ratio |
| A8 | Names: no audit against real-name lists | Programmatic uniqueness checks (done: unique within league); real-name collision check; native review for ar/es | Run a collision check against a public given-name/surname list, then native review. Video must contain no real names (s.4.4, s.11.8) | S + human | `tools/name_audit.py` |
| A9 | Tackles untuned (88.9 vs about 31) | No recent source found; cut tackle attempts by about 2/3 to a plausible level and keep UNCALIBRATED | Retune to about 31 and say so | S | config |
| A10 | Determinism across platforms | Tested: byte-identical on Python 3.11, 3.12, 3.13 (Linux), different PYTHONHASHSEED | Document; macOS/Windows/3.10 untested; say so in README | done | README note |
| A11 | Licence | MIT (organisers' repo is MIT; grant is non-exclusive) | MIT | S | `LICENSE` file |
| A12 | Pipeline transport | See B1 | Event Hubs | M | `eventgen/replay.py` EventHub sink |
| A13 | Speed/distance indicators | Event-derived only (no tracking) | See B2 | M | `interpret/` |
| A14 | Events missing for richer analytics (offside, shot assist type, body part) | `body_part` on pass/shot is the cheapest; matters for headed goal share (target 0.156 to 0.213) and pass difficulty | Add optional `body_part` | S | schema + simulate |

Not found in any source: SoT home split, corners, free kicks, offsides, recent tackles, pressures, per-match spreads, cards by minute, sprint thresholds, score-state magnitudes, sub timing bands. These stay UNCALIBRATED and are documented as such.

---

## B. Pipeline stages and hackathon requirements

### B1. Ingest (stage a)

Options: Event Hubs (recommended), Service Bus sessions (strict FIFO, no replay), file replay only (zero risk, weak Azure score).

Design: `pip install azure-eventhub azure-identity aiohttp`; `DefaultAzureCredential` (no secrets in repo; `az login` locally); `producer.create_batch(partition_key=match_id)` then `send_batch(batch)` (do not pass a key on send; the SDK raises `TypeError`). One batch per match so order is preserved within a partition. Standard tier gives 7-day retention and Capture; Basic only 1 day. Price: not found, use the Azure calculator. Local fallback: Event Hubs emulator in Docker (no Entra ID there, use env-var connection string, never commit it).
Effort M. Risk Low-Med. Verify with a quick test that all events of a match land in one partition.

### B2. Interpret (stage b) and real-time intelligence

- **Player ID with speed/distance indicators.** Without tracking, derive from events: pass length, time between events, carry distance. Speed per player = distance between consecutive owned events / elapsed match clock (the validator already bounds this). Clearly label as event-derived estimates. Optional 5 Hz tracking file is a stretch.
- **Pass quality and difficulty (design, UNCALIBRATED).** `p = sigmoid(3.0 - 0.05*L - 0.010*max(fwd,0) - 0.015*|dy| - 0.8*[final third] - 0.8*[box] - 0.9*pressed - 0.8*head)`; difficulty = round(100*(1-p)). Bands: Easy p>=0.85, Medium 0.6 to 0.85, Hard <0.6 (anchored to the 0.8/0.2 convention in Opta xP). Passes-above-expected = outcome minus p. Calibration against our own generator tests internal consistency, not realism.
- **Ball/shot speed.** Not in events. Options: add generator-side `ball_speed_kmh` on shots and long passes drawn from plausible ranges (labelled synthetic), or derive from pass length / action_ms. Recommend derived value plus label; stretch is the tracking file.
- **Momentum / control vs chaos.** xT-lite grid (16x12) with an EMA over the last 3 to 4 minutes (Stats Perform: only the last 3-4 minutes matter); a three-state control/balanced/chaos classifier by shots and turnover rate (HMM literature supports three states). Poisson win probability from remaining time and score.
- **Auto-eventing from video.** Not feasible in 8 days (SoccerNet best Team-mAP@1 about 60; no licensed footage; Video Indexer is not documented as an event detector). **Recommend a labelled adapter** (`adapters/tracking_to_events.py`, provenance `auto_eventing_mock`) from the optional tracking file, round-trip scored (pass F1 within +-1 s). Say plainly on screen that it does not process video.

Effort M (metrics) plus S (adapter stub). Repo: `interpret/` package, `config/interpret.yaml`.

### B3. Explain (stage c) and explainability

Every claim is a **fact packet** with `source_event_ids` and the numbers that justify it. Explanations render as "Because ..." with clickable event IDs, plus a per-claim trace of which agent produced it. Evaluate against the generator's `ground_truth.json` (six stories plus extra story types worth planting: injury-time winner, goalkeeper heroics once saves exist, penalty drama). Score: story recall, false-positive rate, and timing error against ground-truth sequence numbers.
Effort M. Risk Med (causal claims must stay in fact packets).

### B4. Narrative generation

Recommended **hybrid slot-locked generation**:

1. Interpret emits fact packets `{fact_id, kind, slots, source_event_ids, importance}`.
2. Template realiser per language (always on, no LLM, exact numbers).
3. Optional LLM stylist returns sentences with `{slot}` placeholders and `cites`; code fills slots, the model never writes digits or names.
4. Mandatory verifier checks every number, name and club against the cited facts; any failure falls back to the template and is logged.

Neural data-to-text research finds weak content selection and templated baselines beating neural models on some metrics, so this is the safe route. Effort M-L. Risk Low-Med.

### B5. Multi-language storytelling

Ship **en, ar (Modern Standard), es**. Generate **per language from the same fact packets** (not English then translate). Arabic has six CLDR plural categories; Spanish decimal comma varies by region (use neutral `es`). Azure Translator (free tier 2M chars/hour, 15 s latency) is for **back-translation tests only**, not the live path. Glossary of about 40 football terms x 3 languages needs native review (no open licensed glossary exists). Add `description_i18n` to ground truth. RTL render rules: mirror layout, keep numerals and club badges consistent, test with long names.
Effort M. Risk Med (native review). Arabic coverage in Azure Speech/Translator: **(unverified)**.

### B6. Render

Open question: no public detail on the rendering partner's format, so we assume nothing. We define our own **overlay message schema v0** (JSON): `{id, t_match_ms, ttl_ms, priority, lang, text, style, cites}` with match-clock timing, JSONL output plus SSE for the demo, and an **HTML overlay page replaying the JSONL** (RTL aware, `role=status` / polite announcements, pausable per WCAG 2.2.2, colour never the only cue). Scheduler handles priority, collisions, and a minimum on-screen time.
Effort M. Risk Low. Questions for the partner are listed in `docs/research/04` C3.

### B7. Personalize (stage e)

The piece judges will remember. Design:

- **Six personas (design):** Casual Cara, Analyst Amir, Club Loyalist Lina, Player-Follower Pablo, Language-first Layla, Access-first Sam; Spoiler-safe as a modifier.
- **Controls:** presets plus quick dials (language, depth/jargon, notification level, favourite club/player, spoiler mode, accessibility mode). Profile is JSON, stored **client-side** (privacy, no accounts).
- **Ranking:** multiplicative relevance score = importance x persona weight x favourite-team factor x player factor x novelty decay, with a per-persona cap on items per minute.
- **Partisan framing:** template wrappers for the favourite team's wins and losses; same facts, honest framing, verifier-checked.
- **Player-focus mode:** whole-match view of one player (involvements, passes with difficulty, key moments, personal recap). Defenders and keepers are thin until A1 events exist.
- **Proof of difference:** automated Persona Distance test over output streams (item overlap, mean length, jargon rate, stats per minute, language) plus a 30-45 minute blind A/B with 5 to 8 people.

Evidence: Deloitte 2018 (over 25% want customization, about 18-24s want interaction); RNIB (blind fans want real-time description and no dead silence); competitors offer toggles and stat dumps, not per-persona narration. Football-specific fan-segment shares were **not found**, so personas are hypotheses.
Effort S-M. Risk: canned feel (mitigate by showing two personas side by side on the same event).

### B8. Data innovation

Ranked: (1) new events (goal_kick, save, body_part) and lineups first; (2) fact-packet provenance in ground truth; (3) optional 5 Hz tracking file as stretch; (4) provenance block on every artifact (generator version, seed, config hash, UNCALIBRATED list) for judges.

---

## C. Judging and submission

Stage 1 is pass/fail (Azure and agent requirements, public repo, working link, video under 2 min). Stage 2 scores five equal 20% criteria. Recommended minimal credible stack:

1. Event Hubs for Ingest, events keyed by `match_id`.
2. Microsoft Agent Framework (1.22.0) workflow with three agents (Interpret, Explain, Personalize) on a Foundry-hosted model.
3. Render: small web UI on Container Apps (locally if time runs out; rules want a working link).
4. Language switch via the Foundry model.
5. Copilot agent mode used in development, noted in README.
Fabric, databases, Speech: cut.

Cut order if time runs short: Fabric/Translator/Speech, live Event Hubs in the video (show real send logs), Container Apps deployment, live LLM calls (use cached output from the real pipeline). **Last to cut: two personas plus one language switch.**

---

## D. Build order (8 days, ranked)

| Day | Work | Why |
|---|---|---|
| 0 (today) | Register. Confirm Foundry quota. Add LICENSE. Check first-commit date | Registration closes tomorrow noon PT |
| 1 | A2 home advantage, A6 restart timings, A4 subs, A3 time shape, A9 tackles; re-run 300-match calibration | Generator credibility, all config-only |
| 2 | A1 `goal_kick` + `save` + `body_part`, validator rules, schema regen, tests | Unlocks keepers and richer facts |
| 3 | Interpret: metrics, pass difficulty, momentum, fact packets (with event IDs) | Core of the pipeline |
| 4 | Explain + template narrative en/ar/es + verifier + glossary | Explainability and multilingual |
| 5 | Personalize: profiles, ranking, partisan wrappers, player-focus | Differentiator |
| 6 | Event Hubs ingest, agents on Foundry, overlay schema + HTML page, A7 colours | Stage 1 requirements and demo |
| 7 | Persona Distance test, native review, README, architecture diagram, record video (1:45) | Evidence and polish |
| 8 | Buffer; re-read rules; submit before the deadline, not at it | Risk |

## E. Demo script (1:45)

0:00-0:12 problem; 0:12-0:30 one generated match streams into Event Hubs, timeline fills; 0:30-1:05 two personas side by side on the same moment, each citing event IDs; 1:05-1:25 language switch to Arabic; 1:25-1:40 architecture slide mapping the five stages to Azure services plus agent trace; 1:40-1:45 repo URL. No music, no real club crests or names.

## F. Unverified or still needing a human

- Rules wording (s.4.4 video length, s.6.2), re-read by eye.
- Azure free-tier limits, pricing, Arabic coverage in Translator/Speech, Foundry quota.
- Many numbers came via fetch-tool summaries; re-check any you will cite on screen (especially the 2025-26 restart timings and goal-timing shares, rated medium).
- Native-speaker review of Arabic and Spanish names, glossary, templates.
- Determinism on macOS, Windows, Python 3.10.
- Fan-segment sizes for football specifically (not found).
- Home/draw/away result targets need the generator to emit `home_team` and a match result before `compare_to_targets.py` can check them.
