# 03 - Interpret + Explain research strand

Scope: stages Interpret and Explain over our synthetic events. All web sources accessed **2026-10-19**; IDs like [S3] are in section 9. "DESIGN" marks our own choices, not published facts. "UNCALIBRATED" marks coefficients that are guesses. Several fetched pages were summarised by the fetch tool, so numbers should be re-checked against the primary page before they appear in a demo. Two pages (PMC9173601 momentum paper, PMC11474994 EPL distances) returned a bot check and were not worked around.

Facts about our data used below (checked on a seed-42 match): ~1,560 events, ~16 events/min; pass length median ~13 m, ball speed median ~11 m/s; `pressure` is emitted by the *pressing* team with `pressed_player_id` = carrier, median distance 3.2 m, duration 1.4-3.2 s; a `pressure` on the passer is directly followed by that passer's pass in 176 of 291 cases. Receiver is null on non-complete passes.

**Common preprocessing (DESIGN).** `ax = x` if the team attacks left-to-right in that period else `105 - x` (from `match.json periods[].attacking_direction`); same for `end_x`. Final third: `ax >= 70`. Box: `ax >= 88.5` and `13.84 <= y <= 54.16` (standard 16.5 m box; Laws-of-the-Game dimensions, not re-fetched). Time = `match_clock_ms`.

## 1. Metric catalogue

All metrics are event-only unless marked "positions". Update rate = recompute on every event of that team/type, publish at most every 15 s of match clock.

| Metric | Definition (source) | Formula from our fields | Window | Extra data |
|---|---|---|---|---|
| Possession | Share of match time a team has the ball [S1] | Time per `possession_id` = last event clock minus first; team share = sum / total | 10 min rolling + match | No. Pass-count share as fallback |
| Field tilt | Share of attacking-third passes [S1]; Driblab also uses touches and the last 35 m, averaged per match [S2] | `N_A/(N_A+N_B)`, `N_X` = passes (type pass, any outcome) by X with `ax>=70` | 10 min | No |
| PPDA | Opponent passes allowed per defensive action in the opponent's 60% of pitch; actions = tackles, interceptions, challenges incl. failed, fouls [S3]; Wyscout lists fouls, interceptions, won duels, sliding tackles [S4] | opp passes starting where the presser's `ax>=42` / (own `tackle` any outcome + `possession_change` reason interception won + `foul` committed, same zone). Caveat: can be low from possession dominance [S3] | 10 min | No |
| Pressing intensity | Pressures; counter-press = pressure within 2 s of losing the ball [S5] | pressures/min by team in opp half + counter-press count (pressure within 2000 ms after own `possession_change`) + mean `distance_m` | 5 min | No (uses `pressure`) |
| Progressive pass | At least 10 yards toward goal line, stricter in attacking thirds [S1] | complete pass, `end_ax - ax >= 9.14`; DESIGN stricter rule: if start `ax>=70` require `>=5` m | match, 10 min | No |
| Progressive carry | Same 10-yard idea [S1] | Not directly observable (no carry events). Skip (S) | - | positions |
| Passes into final third / box | Standard count (no sourced definition found) | complete pass, start `ax<70`, end `ax>=70` (box: end in box, start outside) | 10 min | No |
| Pass network | Nodes = players, directed edges = successful passes A_ij; centrality (closeness, betweenness, PageRank), clustering [S6] | edges from complete passes `player_id -> receiver_id`; node position = mean start x,y of own passes; draw edges with >= 3 passes | 15 min and match | No |
| Turnover / high turnover | High turnover = possession starting in open play at 40 m or less from the opponent goal [S5]; Driblab: losing ball under 40 m from own goal [S7] | `possession_change` reason in {tackle, interception, miscontrol}, new owner's `ax>=65`. "Dangerous turnover" (DESIGN) = turnover followed by own shot within 15 s | 10 min | No |
| Shot quality (xG-style) | Core features distance and angle [S8]; xT iteration 1 is essentially an xG model [S9] | Section 1b | per shot | No |
| Momentum | Section 3 | EMA of event threat difference | 5 min | No |
| Control vs chaos | Section 3 | state machine | 3 min | No |
| Rhythm / tempo | Premier League ball-in-play averaged 54:45-58:11 per match, 54.7-55.7% share [S10] | events/min; passes per minute of possession; median gap between consecutive passes; verticality = sum(ax gain)/possession seconds; ball-in-play share = 1 - stoppage/elapsed, stoppage = from `possession_change` reason out_of_play/foul, or a goal, until next restart event (throw_in, corner, free_kick, penalty, period_start) | 5 min | No |
| Line height proxy | No published event-only definition found | DESIGN: mean `ax` of own tackles + pressures + interception wins, last 10 min. With positions: mean x of outfield players | 10 min | optional tracking |

**1b. xG-style shot quality (DESIGN, UNCALIBRATED).** `angle` = angle subtended by the posts (7.32 m goal) from shot `x,y`; `d` = distance to goal centre.
`logit = -1.6 - 0.14*(d-11) + 0.8*(angle-0.6) - 0.7*head - 0.3*pressed`, `pressed` = a `pressure` on the shooter in the same possession in the last 3 s. Penalty = fixed 0.76 design constant (must be sourced before shown as fact). Values: 11 m central 0.17; 11 m header 0.09; 17 m central 0.07; 8 m wide angle 0.02-0.03. Calibrate by logistic regression of `outcome=="goal"` on these features over a generated batch (`tools/gen_batch.sh out/calib 200`): circular, tests consistency only, so label every xG on screen "model estimate (synthetic)". Post-shot view: goalkeeper "saves above expected" = post-shot xG faced minus goals conceded, built from shot speed and goal-mouth point [S11]; we have `shot_speed_ms`, `end_y` only (no height), so use a reduced form.

**Options per choice (S/M/L = effort).**

| Choice | Options | Recommend | Risk | Repo change |
|---|---|---|---|---|
| Possession measure | time per possession_id (S); pass share (S); positions-based (L) | time per possession_id | possession_id spans include dead time | `interpret/metrics/possession.py` |
| Pressing | PPDA only (S); PPDA + counter-press + pressure rate (M) | the M option | PPDA misleading [S3] | `interpret/metrics/pressing.py` |
| Carries / line breaks | skip (S); implied carry from consecutive events (M); needs tracking (L) | skip; line-breaking needs every player's position [S12] | judges may ask | docs only |
| Shot quality | hand formula (S); fit logistic on batch (M) | hand formula now, fit if time | circularity | `interpret/xg.py`, `config/interpret.yaml` |

## 2. Pass difficulty rating

**Published approaches.** (1) Opta expected pass completion: inputs include start x, mirrored y, angle, distance, foot/head, cross, set piece, ground/air, passes so far in possession, carry before, previous action; xP 0.2 = high-risk, 0.8 = low-risk [S13]. (2) StatsBomb xPass: start location, target distance, angle, passer under pressure, body part, pattern of play; backward unpressured defensive-third pass ~99%, switch to far flank final third ~40% or lower [S14]. (3) StatsBomb pressure-disruption model: start/end, length, angle, header; random forest AUC 87% vs logistic 81% [S15]. (4) Line-breaking passes: need positions [S12]. Options for us: A) logistic on pass geometry + pressure (explainable, event-only), B) tree model (more accurate, less explainable), C) add line-breaking via tracking. **Recommend A.**

**Formula (DESIGN, UNCALIBRATED).** `p = sigmoid(3.0 - 0.05*L - 0.010*max(fwd,0) - 0.015*|dy| - 0.8*[end in final third] - 0.8*[end in box] - 0.9*pressed - 0.8*head)`
`L` = `pass_length_m`; `fwd` = `end_ax - ax`; `dy` = `end_y - y`; `pressed` = a `pressure` event with `pressed_player_id == passer` earlier in the same possession within 3 s; optional continuous variant `pressed = clamp(1 - distance_m/6, 0, 1)`. Difficulty = `round(100*(1-p))`. Not usable: receiver pressure and opponent line positions (not in our fields). Corners, free kicks, throw-ins use the same model plus a `set_piece` term of 0 until calibrated.

Banding (anchored to the 0.8 / 0.2 convention in [S13]): **Easy** p >= 0.85 (difficulty <= 15); **Medium** 0.6 <= p < 0.85; **Hard** p < 0.6. Worked values: 8 m back pass 0.93 (easy); 15 m forward in midfield 0.89 (easy); 40 m switch 0.61 (medium, borderline); 35 m long ball into final third 0.50 (hard); 22 m cross into box 0.49 (hard); 14 m pass into box under pressure 0.41 (hard).
Calibration: fit logistic regression, target `outcome=="complete"`, features above; accept when mean p matches observed completion within 2 pp and each band's observed completion falls in its band (reliability plot, Brier score). Passes-above-expected = outcome minus p [S13]. Honest note: fitting to our own generator measures internal consistency, not football realism.

| Choice | Options | Recommend | Effort / risk | Repo change |
|---|---|---|---|---|
| Model | logistic (S); gradient boosting (M); + tracking line-breaks (L) | logistic | S / low | `interpret/pass_difficulty.py`, coefficients in `config/interpret.yaml` |
| Calibration source | generator batch (S); real open data (M, licence check needed) | generator batch | S / circular | `tools/fit_pass_model.py` |

## 3. Momentum, control vs chaos, win probability

**Published.** Stats Perform match momentum = likelihood the team in possession scores in next 10 s, from possession value; per minute takes each team's maximum possession value capped 0-0.1, recent minutes weighted, only the last 3-4 minutes matter significantly, momentum = difference between teams; weights not published [S16]. Possession-value family: xT uses a 16x12 grid, `xT(x,y) = s*g + m*sum T*xT`, 4-5 iterations suffice [S9]; xT only values ball-moving actions, VAEP values P(score) minus P(concede) over the next 10 actions using last 3 actions [S17][S18]. HMM paper (Dortmund, minute counts of shots and touches): no formal momentum definition; best model has 3 states = low control with quick counter-attacks, balanced, high control; cannot separate momentum from tactics [S19].

**Momentum Index (DESIGN).** Per-event threat `v`: completed pass or throw/corner/free kick `max(0, V(end) - V(start))` with `V(x,y)` = location xG from section 1b (xT iteration 1 idea [S9]); shot = its xG; pressure/tackle won in opp half = 0.01. Bucket per 30 s, cap at 0.15 per bucket, team EMA with half-life 120 s (matches the "3-4 minutes" finding [S16]). `MI = (EMA_A - EMA_B) / P90` where P90 = running 90th percentile of |difference| (from minute 10, clamp to +-1). Needs no positions.
**Swing detected** (DESIGN, UNCALIBRATED): MI crosses from <= -0.25 to >= +0.25 (or reverse) within 6 min and stays beyond +-0.25 for >= 2 min; suppress further swings for 5 min. Tune thresholds by ROC against planted `momentum_swing`.

**Control vs chaos (DESIGN).** In 3-min windows stepped every 30 s compute turnover rate `tr` (possession_change per min), median possession length in passes, team possession share and pass completion. State: **CHAOS** if `tr >= 1.5 x` match median and median possession <= 2 passes for >= 2 windows; **CONTROL_A** if A possession >= 60%, A completion >= match average, and `tr` <= match median; else **CONTESTED**. Maps to the HMM's three control levels [S19]. Effort M, risk: thresholds depend on baseline needing ~10 min of data.

**Win probability (DESIGN, sourced approach).** Published: per-minute Poisson model of each team's remaining goals, inputs score difference, time remaining, Elo difference, home advantage, red cards, plus xT, attacking passes, duels; fit on 12,758 matches (2011/12-2017/18) from five leagues with ClubElo ratings; ECE 0.011 [S20][S21]. Simple version: `lambda_team = base * (T_rem/90) * exp(+-0.5*s*dStrength) * state`, `base` ~ goals per team per match from batch; red-card state multipliers own x0.53, opponent x2.2 (a World Cup study found about -47% and +120% scoring rates [S22], UNCALIBRATED here); trailing teams get a small rate boost (DESIGN). Remaining goals ~ independent Poisson, add current score, sum scoreline probabilities for W/D/L. `dStrength` = pre-match rating from a static league table in `teams.json` (to be added; do not read `ground_truth.json`). Data to fit properly: a multi-season event dataset with ratings; we have none, so fit `base` and the home term on 200 generated matches and say so. Swing = |WP change| >= 0.10 within 5 min.

| Choice | Options | Recommend | Effort / risk |
|---|---|---|---|
| Momentum | rolling xT-lite EMA (M); HMM on minute counts (L); raw shot difference (S) | xT-lite EMA | M / thresholds uncalibrated |
| Win prob | Poisson closed form (M); logistic on score x time (S); Bayesian model [S20] (L) | Poisson closed form | M / strength prior is a guess |
Repo change: `interpret/momentum.py`, `interpret/state.py`, `interpret/winprob.py`; optional `strength` field per team in `teams.json` (generator change in `league.py`).

## 4. Speed and distance indicators

**Thresholds.** A review: no consensus; men's high-speed running most often 19.8 km/h, sprint 25.2; UEFA/FIFA references 20/25 km/h (men), 19/23 (women); reported men's HSR 618-1,001 m and sprint 153-295 m per match [S23]. Euro 2024 reference values: HSR 20.0-24.9, sprint >= 25.0 km/h; midfielders ~11.4-11.9 km total distance, centre backs ~9.7-10.1 km, top speeds 34.8-35.7 km/h [S24] (ranges may span Euro 2024 and the 2022 World Cup; verify). Position pattern: central midfielders highest total distance; wide midfielders highest sprint distance in a Bundesliga sample; centre backs lowest [S23][S24].

| Option | What it gives | Effort / risk |
|---|---|---|
| (a) Optional tracking file | real speeds, distance, sprints, line height, pass receiver pressure, and an input for the auto-eventing mock | M-L / consistency with events |
| (b) Distance from event positions | player distance between own consecutive events is a lower bound; ball speed is already in fields | S / misleading as "running speed" |
| (c) Skip | nothing | S / misses a stated requirement |

**Recommend (a), generated from events, off by default.** File `tracking.csv.gz` per match: columns `period,t_ms,entity,x,y` in long form or wide `t_ms,period,ball_x,ball_y,p1_x,...` (wide is smaller). **5 Hz**, 105x68 m frame, 1 decimal: ~29,500 frames, ~8 MB raw CSV, ~2 MB gzipped (2 Hz: ~3.3 MB raw; 1 Hz ~1.6 MB; estimates). Cheap, plausible generation: each player has a formation anchor (from `teams.json` formation) shifted toward ball and team line by ~20-30%; between event waypoints (actor at event `x,y` at `clock_ms`) move with acceleration cap ~3 m/s^2 and speed cap 9.7 m/s (35 km/h); per-position budgets scaled to the figures above; low-pass noise. Indicators at thresholds `hsr_kmh: 20`, `sprint_kmh: 25` in `config/interpret.yaml`; speed from 5 Hz positions smoothed over 1 s. Label all as synthetic.
Repo change: `eventgen/tracking.py`, CLI flag `--tracking`, `validate` check that actor position at event time is within 1.5 m, update README and UNCALIBRATED.md.

## 5. Auto-eventing from video

Facts: SoccerNet 2025 Team Ball Action Spotting has 12 classes including Pass and Drive, 1 s tolerance, best Team-mAP@1 60.03 and team-agnostic mAP@1 68.92, 7 annotated games (2 more held out) [S25]. Azure AI Video Indexer detects ~80 classes including "sports ball"; limits quoted: 20 detections per frame, small or blurry objects missed, uploaded files only; it is not documented as an event or ball-speed detector in the pages read [S26]. Azure AI Vision custom models were not verified (not fetched). Open-source route: Roboflow tutorial uses YOLOv8 keypoints (32 pitch landmarks) plus OpenCV homography to put players in pitch coordinates; no accuracy numbers given, YOLOv8 is AGPL-3.0, RF-DETR is Apache 2.0 [S27]; PassNet-style video classifiers exist but report no usable numbers in the abstract [S28].
Options: (1) real video model (L, high risk, no licensed footage, no ground truth); (2) Video Indexer ball detections plus own heuristics (M-L, weak); (3) **labelled adapter**: tracking file (section 4) -> events: nearest-player-to-ball possession, pass = change of ball owner, ball speed = displacement/time. **Recommend (3)**, provenance `auto_eventing_mock`, and say plainly that it does not process video. Round-trip test: regenerate events from tracking and score against the original (pass F1 within +-1 s, matching SoccerNet tolerance; ball speed MAE). Risks: judges read it as real CV; mitigate with on-screen label. Repo change: `adapters/tracking_to_events.py`; schema addition needs a new optional field (`additionalProperties: false`), so add `provenance` to all events or emit a side file.

## 6. Explain

**What makes a moment matter** (score: take the max, then rank): goal or red card (1.0); win-probability swing |dWP| >= 0.10 within 5 min; lead change or equaliser; momentum/control-state change (section 3); milestone within the match (first shot, 10th pass in a possession, player reaches own highest involvement count); streak (3 consecutive dangerous turnovers, 5 corners in 10 min); extreme vs own match baseline (z >= 2). No external "records" exist for synthetic leagues; do not invent any.

**Template.** `claim` (one sentence, plain words) -> `evidence` (2-3 numbers, each tagged with metric and window, recomputable from events) -> `context` (score, minute, baseline comparison) -> `so what` (consequence: threat, WP change, what to watch). Output as JSON with `evidence[]` `{metric, value, window_s, seqs}` so Render shows it and evaluation can verify it.

**Do NOT explain** when: fewer than 8 events of the relevant type in the window; before minute 10 for baseline-relative claims; WP already > 0.97 or < 0.03; same story type for same team within 90 s; evidence contradicts the claim (e.g. high tilt but zero shots: say so or stay silent); causal wording not supported (use "coincided with", never "because"); anything needing positions when tracking is absent; when two metrics disagree and no tie-break exists.

**Worked examples** (numbers illustrative; "(a)"/"(b)" are team labels):
1. Momentum swing: "Team B take control (62'). They had 71% of attacking-third passes in the last 6 minutes vs 38% before, and 3 shots against 0 (`shot` x3, `pass` ax>=70). Score still 1-0 to A, but B's win probability rose 14 points to 33%."
2. Pressing spell: "A are winning it back high (21'-34'). 13 turnovers in B's half (`possession_change` reason tackle/interception) at 0.93/min vs 0.36 match average; PPDA fell from 11.2 to 6.1; 4 of them came within 2 s of A losing the ball (counter-press)."
3. Late comeback: "From 0-2 to 2-2 (71'-86'). Both goals followed pressure phases; A had 8 shots (xG 1.4) in 15 min vs 1 for B; win probability moved from 4% to 41%."
4. Red card: "Red card for B's `player_id` (54') changes the match. B's shots: 0.3 xG per 10 min before, 0.1 after; A's territory (field tilt) 48% -> 71%."
5. Star player: "P09 is the hub: 31 of A's 212 passes involve him (15%, next highest 8%), 3 shots, 2 progressive passes into the box."
6. Quiet then chaos: "A calm 12 minutes (7.9 events/min vs 15.9 average, one shot) then four shots in 8 minutes from A (xG 0.9). Turnovers doubled once B started pressing."
7. xG vs score mismatch: "A trail 0-1 despite 2.1 xG to 0.4. They are creating most of the danger, but B's keeper has saved 4 of 5 on-target shots."
8. Hard pass completed: "A 38 m switch (difficulty 61/100, medium-hard) found P07 and led to a shot 9 seconds later."
9. Chaos state: "Scrappy spell (35'-38'): 9 possession changes in 3 minutes, no possession longer than 2 passes. Neither team has control."
10. Substitution impact: "P14 on at 60'. In the 15 minutes since, A's passes into the final third doubled (6 -> 12) and tilt moved from 44% to 58%." (Say "since", not "because".)
Do-not-explain example: A 22% to 31% tilt rise over 4 minutes with 5 attacking-third passes in total: below the evidence floor, stay silent.

| Choice | Options | Recommend | Effort / risk | Repo change |
|---|---|---|---|---|
| Text generation | fixed templates (S); LLM from structured evidence (M); LLM free (S, risky) | templates, optional LLM rewrite constrained to given numbers | S-M / number hallucination | `explain/templates/`, `explain/rank.py`, `explain/guard.py` (check every number appears in evidence) |

## 7. Evaluation against ground truth

Use `ground_truth.json` only in the evaluation harness (README forbids runtime use). Run on a batch of 40 matches with stories plus 20 `--stories none` controls (`tools/gen_batch.sh`).
- **Matching:** detection matches a story if team matches and the detection interval overlaps `[start_seq, end_seq]` by temporal IoU >= 0.3, or its midpoint is within +-120 s of the story midpoint (also accept +-150 seqs). One-to-one matching.
- **Metrics per story type:** precision, recall, F1; time-to-detect (start error in seconds); false alerts per match on controls.
- **Reason correctness:** the explanation must cite the type-specific evidence: momentum_swing -> tilt or MI shift; pressing_spell -> PPDA drop or high-turnover/counter-press count; late_comeback -> deficit overturned plus minute >= 70 plus WP swing; red_card_turning_point -> the red `card` seq and before/after contrast; star_player_match -> the named player share; quiet_then_chaos -> low event rate then shot burst. Score = fraction of matched detections with a correct reason tag.
- **Faithfulness (hard gate):** every number in an explanation recomputes from events within rounding; 0 failures.
- **Pass bars (DESIGN, adjust after first run):** recall >= 0.80 for stories with `strength >= 0.6` (>= 0.6 all); precision >= 0.70; reason correctness >= 0.90; <= 2 non-story alerts per match on controls; faithfulness 100%; red card detection recall 1.0. Report `unrealized_stories` separately and exclude them.

## 8. Extra story types worth planting

Each only changes parameters in a window (no event writing), then a realization check; repo change = add type to `eventgen/stories.py`, a check in `groundtruth.py`, params in `config/default.yaml` (mark `# UNCALIBRATED`), example in `config/stories.example.yaml`, tests, README/UNCALIBRATED.

| Story | Parameter change | Realization check (events) | Effort |
|---|---|---|---|
| tempo_change | scale event spacing x0.6 for 8 min | events/min >= 1.4x match median; pass interval shorter | S |
| tactical_switch | team formation/`buildup_directness` and `attack_intensity` shift at minute N | verticality and mean `ax` of defensive actions change >= 15% either side | M |
| substitution_impact | on-player quality boost, more touches | his involvements per min >= 2x team median after `substitution` | S |
| set_piece_spell | raise out-of-play/corner/foul probability near opp box | >= 4 corners or free kicks in 8 min for one team | S |
| goalkeeper_heroics | lower goal probability for on-target shots | >= 4 `saved` and 0 conceded while design xG faced >= 1.0 | S |
| xg_vs_score_mismatch | high chance volume, low conversion for one team | design xG diff >= 1.0 while score is level or reversed | M |
| defensive_collapse | defensive quality down after a goal/red | >= 3 shots against and own-third turnovers 2x within 8 min | M |
| park_the_bus (game state) | leader drops line, lowers attack | leader's possession <= 40% and tilt <= 35% for 10 min while leading | M |
| discipline_spiral | foul rate up | >= 3 fouls and >= 1 card for one team in 10 min | S |

Recommendation: plant tempo_change, goalkeeper_heroics, xg_vs_score_mismatch, substitution_impact first (S effort each, they test the Explain evidence rules most). Risk: realization checks use the same xG proxy as Interpret, so keep the generator check independent (simple counts) to avoid circularity.

## 9. Sources (all accessed 2026-10-19)

- [S1] Guide to Football glossary https://guidetofootball.com/glossary/statistical-terms/
- [S2] Driblab field tilt https://www.driblab.com/blog/field-tilt-percentage-of-passes-and-touches-in-the-final-third
- [S3] Premier League PPDA explained https://www.premierleague.com/en/news/4250153
- [S4] Wyscout PPDA https://dataglossary.wyscout.com/ppda/
- [S5] Premier League pressing terms https://premierleague.com/news/4183646
- [S6] Network theory analysis of football strategies https://arxiv.org/pdf/1206.6904
- [S7] Driblab high turnovers https://www.driblab.com/blog/italy-and-denmarks-key-to-euro-2020-high-turnovers-a-look-at-the-high-pressing-efficiency
- [S8] MetricGate xG model https://metricgate.com/docs/expected-goals-model/
- [S9] Karun Singh xT https://karun.in/blog/expected-threat.html
- [S10] Opta Analyst ball in play https://theanalyst.com/articles/premier-league-ball-in-play-are-we-seeing-less-football-2025-26
- [S11] Hudl post-shot xG https://www.hudl.com/blog/a-new-way-to-measure-keepers-shot-stopping-post-shot-expected-goals
- [S12] Stats Perform line-breaking passes https://www.statsperform.com/insights/how-impactful-are-line-breaking-passes/
- [S13] Opta expected pass completion https://theanalyst.com/articles/expected-pass-completion-explained
- [S14] StatsBomb xPass https://www.hudl.com/blog/statsbomb-models-expected-pass-xpass-and-pass-clustering
- [S15] StatsBomb Under Pressure https://blogarchive.statsbomb.com/articles/soccer/under-pressure/
- [S16] Opta match momentum https://theanalyst.com/articles/what-is-match-momentum
- [S17] socceraction VAEP https://socceraction.readthedocs.io/en/latest/documentation/valuing_actions/vaep.html
- [S18] KU Leuven xT vs VAEP https://dtai.cs.kuleuven.be/sports/blog/valuing-on-the-ball-actions-in-soccer-a-critical-comparison-of-xt-and-vaep
- [S19] Copula HMM momentum https://arxiv.org/pdf/2002.01193
- [S20] KU Leuven in-game win probability https://dtai.cs.kuleuven.be/sports/blog/a-bayesian-approach-to-in-game-win-probability
- [S21] Who will win it? https://arxiv.org/pdf/1906.05029
- [S22] Red cards and goal rates (IZA DP 10174) https://docs.iza.org/dp10174.pdf
- [S23] Sprint/HSR thresholds review https://pmc.ncbi.nlm.nih.gov/articles/PMC9968809
- [S24] Euro 2024 running reference values https://www.termedia.pl/Establishing-reference-values-for-the-match-running-performances-r-nof-thirteen-specific-positional-roles-at-UEFA-Euro-2024,78,55765,1,0.html
- [S25] SoccerNet 2025 challenges https://arxiv.org/html/2508.19182v1
- [S26] Azure AI Video Indexer object detection https://learn.microsoft.com/en-us/azure/azure-video-indexer/object-detection-insight
- [S27] Roboflow pitch calibration https://roboflow.com/blog/camera-calibration-sports-computer-vision
- [S28] PassNet pass detection https://mlanthology.org/ecmlpkdd/2020/sorano2020ecmlpkdd-automatic

Unverified, left out on purpose: Azure AI Vision custom-model capabilities, UEFA/FIFA primary threshold documents, Metrica tracking sample rate (README did not state it), real-data xG and pass-completion benchmarks.
