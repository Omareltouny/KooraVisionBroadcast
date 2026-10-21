# 05 Personalization + Data Innovation (research strand)

Accessed 2026-10-19. Cite style: [S#] -> Sources list at the end. Anything marked **(design)** is our inference or proposal, not a sourced fact. "Not found" is stated where evidence was missing.

Our vocabulary (from README + schema): raw events `pass shot tackle possession_change pressure foul card substitution period_start period_end corner free_kick throw_in penalty`; every event carries `player_id`, `team_id`, `x/y`, `score_home/away`, `possession_id`, `match_clock_ms`; passes carry `receiver_id`, `outcome`; pressure carries `pressed_player_id`, `distance_m`; teams.json has `name_i18n` en/ar/es. Stories: momentum_swing, pressing_spell, late_comeback, red_card_turning_point, star_player_match, quiet_then_chaos.

---

## 1. Evidence on fan segments and needs

### 1.1 What the sources say

| Finding | Source |
|---|---|
| About half of surveyed sports fans used connected devices while watching sport on TV; 44% of those followed other games via live text and scores, 21% chatted with friends, 14% posted about the event. (US, 2014, old but the only second-screen split found) | [S1] |
| Deloitte 2018 survey (15,000+ respondents): fans self-place on five levels (fanatic, love-it, casual, knows sport, unfamiliar). Over 25% say **customization** (e.g. choosing announcers or camera angles) is what they most want improved; Deloitte says customization could help move casual fans toward fanatic status. Over 40% say real-time AR stats on screen would make them more likely to watch. Deloitte advises assuming fans use a second screen. | [S2] |
| 18-24s want digital interaction during games far more than Boomers (41% vs 14%). | [S2] |
| Casual fans are a large group: about 4 in 10 NFL fans are casual (under 5 h live sport per week); about a third for MLB/NBA/NHL (US only, S&P 2026). Football/Premier League split: **not found**. | [S3] |
| Spoilers: an Australian streaming case study shows replay viewers were spoiled by upcoming-fixture listings, highlight narration, runtime and email subjects; author recommends a hide-results toggle and combining location, viewing time, habits and favourite team. (Practitioner blog, one case, not a controlled study.) | [S4] |
| Colour vision: about 8% of men and 0.5% of women have red/green colour blindness; FA report covered kit clashes, pitch markings and TV coverage. | [S5] |
| Blind/partially sighted fans (RNIB, 10 interviews, 2022): TV football scored 6.1/15; wanted real-time description of build-up, shot type, player positions, ball location, switches of play, and a pace that is not overwhelming; disliked "dead silences" and commentators only naming the player; radio was preferred. | [S6] |
| WCAG: colour must not be the only visual cue (1.4.1) [S7]; status messages should be programmatically announced without moving focus (4.1.3; `role=status` is implicitly `aria-live=polite`) [S8]; auto-updating information must be pausable/stoppable/hideable or have frequency control (2.2.2) [S9]. | [S7][S8][S9] |
| Global reach: Premier League shown in 188 of 193 UN-recognised countries; 3.2 billion viewers 2018-19 (2019 Nielsen data via trade press; old). | [S10] |

Honest gaps: no source found that quantifies football-specific stat-appetite, notification tolerance, or language-first viewing share. Personas below combine these partial sources with **(design)** judgment; they are hypotheses to test in section 4, not findings.

### 1.2 Six personas **(design, grounded in the sources above)**

| # | Persona | Wants | Density / jargon | Notification tolerance | Spoiler sensitivity | Device context |
|---|---|---|---|---|---|---|
| P1 | **Casual Cara** (casual fan, TV on, half watching) [S2][S3] | "Is anything important happening? Why does it matter?" plain stories, who is winning and why | Low density (<=2 stats/min), grade 6-7 reading level, glossary on tap | Low: key moments only (goals, cards, big chances) | Low live; high for replays | Phone as second screen, glances |
| P2 | **Analyst Amir** (data-hungry) [S2] | Stat feed, xG-like and pressure context, tactical patterns, filter by metric | High (8+ stats/min), full jargon, numbers over adjectives | High: wants everything, tunable | Low | Laptop + large second screen, dense dashboard |
| P3 | **Club Loyalist Lina** (favourite-club fan) | Her team's story, partisan-flavoured but honest framing, own players | Medium | Medium-high for her club, low for others | Medium | Phone, notifications on |
| P4 | **Player-Follower Pablo** (fantasy/"my player") [S11] | One player's involvement all match, fantasy points impact, milestones | Medium, player stats heavy | High for his player only | Low | Phone; wants personal recap |
| P5 | **Language-first Layla** (Arabic or Spanish first language; league is global [S10]) | Everything natively in her language, football terms localised, RTL layout, short sentences | Low-medium; avoid idioms | Medium | Medium | Phone, mixed network quality |
| P6 | **Access-first Sam** (screen reader and/or low vision and/or colour blind [S5][S6][S7][S8]) | Play-by-play description in text/speech with pace control, no colour-only cues, no auto-spam | Description-heavy, position and action rich, low stat density | Controlled: polite announcements, pausable [S9] | Medium | Screen reader (phone/laptop), high contrast, large text |

Optional seventh for the demo story: **Spoiler-safe Sasha** (watching a delayed replay [S4]); implement as a modifier on any persona rather than a separate persona.

### 1.3 Existing products: what they offer and the gaps

| Product | What it offers (cited) | Gap we can fill |
|---|---|---|
| Premier League app / myPremierLeague | Favourite clubs and players, settings sync across devices, Matchday Stories, archive, Fantasy [S12]; app: line-ups 75 min pre-kick-off, Matchday Live blogs, stats on key performers, favourite club news [S13] | Personalisation described as content/news shortcuts; **no per-persona live narration or complexity control found** on those pages |
| Premier League Companion (Microsoft Copilot) | AI assistant over 30+ seasons of stats, ~300k articles, 9k videos; tailored if signed in; launched 1 July 2025 [S14] | Historical Q&A; live match tailoring and viewing modes **not stated** |
| FotMob | Per-event alerts (goals, lineups, cards, subs), follow teams/players, xG, shot maps, ratings, multi-language audio on major matches [S15] | Dense stats for experts; no reading-level or "why it matters" explanation found |
| Sofascore | 300+ stats, Attribute Overview, heatmaps, 35 languages, instant notifications [S16] | Same: stat access, not adaptive explanation |
| Flashscore | Per-team and per-match notification menus by event type [S17] | Controls are toggles, not relevance-ranked |
| Fantasy Premier League 2026/27 | Live points during matches, projected bonus points after 20 minutes, live mini-league standings [S18] | Points only; no narrative of why a player is scoring |
| Broadcast audio description | Describer in gaps, often after the event; RNIB participants found it disjointed [S6] | Real-time, text/speech descriptions generated from events, pace-controlled |

**Gaps (design):** (1) one intelligence layer, many voices (same moment, genuinely different framing); (2) explanation level as a first-class dial; (3) relevance ranking instead of toggles; (4) spoiler-safe and catch-up logic; (5) accessible live narration from events; (6) player-focused "whole match" narrative; (7) honest partisan framing with visible guardrails.

---

## 2. Personalization design

### 2.1 Viewer-controlled dimensions

| Dimension | Values | Default |
|---|---|---|
| `language` | en, ar, es | en |
| `expertise` | newcomer, fan, analyst | fan |
| `favorite_clubs` | 0-2 team_ids | [] |
| `favorite_players` | 0-3 player_ids | [] |
| `metric_focus` | none or one of: shots, pressing, possession, passing, duels, discipline | none |
| `tone` | neutral, enthusiastic, dry-stats | neutral |
| `overlay_density` | minimal, balanced, rich | balanced |
| `notification_intensity` | key_only, normal, everything | normal |
| `spoiler_mode` | off, hide_score, hide_all_until_revealed | off |
| `a11y` | screen_reader, high_contrast, colorblind_safe, large_text, reduce_motion, speech_pace | all off |
| `mode` | match, player_focus, tactical, catch_up | match |

Design options for how to hold these: (A) free-form settings screen (M effort, many knobs, demo is slow); (B) **persona presets plus 3 live "quick dials"** (expertise, favourite club/player, language) (S effort, best demo); (C) learn from behaviour (L, needs data, privacy risk). **Recommend B**, with A as an "advanced" drawer. Risk: preset feels canned; mitigate by letting the judge change one dial and see output change instantly.

### 2.2 Profile JSON with persona defaults

```json
{
  "profile_id": "p1_casual",
  "language": "en",
  "expertise": "newcomer",
  "favorite_clubs": [],
  "favorite_players": [],
  "metric_focus": "none",
  "tone": "enthusiastic",
  "overlay_density": "minimal",
  "notification_intensity": "key_only",
  "spoiler_mode": "off",
  "mode": "match",
  "a11y": {"screen_reader": false, "high_contrast": false, "colorblind_safe": true, "large_text": false, "reduce_motion": false, "speech_pace": 1.0},
  "limits": {"max_items_per_5min": 3, "max_stats_per_min": 2, "min_gap_s": 90, "reading_grade_max": 7}
}
```

| Persona | expertise | density | notifs | limits (items/5min, stats/min, min gap s) | grade cap | Other defaults |
|---|---|---|---|---|---|---|
| P1 Casual | newcomer | minimal | key_only | 3, 2, 90 | 7 | glossary on |
| P2 Analyst | analyst | rich | everything | 15, 10, 15 | none | tone dry-stats, metric_focus pressing |
| P3 Loyalist | fan | balanced | normal | 8 (club-weighted), 5, 30 | 9 | favorite_clubs=[home] |
| P4 Player | fan | balanced | normal | 8, 6, 20 | 9 | mode player_focus, favorite_players=[star] |
| P5 Language-first | newcomer | balanced | normal | 5, 3, 60 | 7 | language ar or es, RTL |
| P6 Access-first | fan | minimal visual, rich spoken | normal | 6 spoken lines/5min, 3, 45 | 8 | screen_reader, high_contrast, colorblind_safe, large_text, reduce_motion |

The demo can switch persona live by swapping the profile object; Personalize is a pure function `(moments[], profile, state) -> items[]` so a switch is instant and replayable.

### 2.3 Relevance scoring **(design)**

Per candidate moment `m` (output of Interpret/Explain, each with `importance` 0-1 and tags: teams, players, metric, story_id):

```
score(m, v) = I(m) * M(m, v) * N(m, v) * R(m, now) * A(m, v)
I = importance 0..1 (goal=1.0, red card=0.9, shot on target=0.5, story-detected spell=0.7, routine=0.1)
M = 1 + w_club*[m.team in fav_clubs] + w_player*[m.player in fav_players] + w_metric*[m.metric == focus]
    (weights: club 0.6, player 1.0, metric 0.8; cap M at 3.0)
N = novelty = exp(-count_same_pattern_recent / tau)   (suppress "another pressure event" repeats; tau=2)
R = recency = max(0, 1 - age_s / horizon_s)   (horizon 20 s live, 120 s for catch-up)
A = persona adjustment: expertise filter (analyst boosts metric/tactical tags x1.5, newcomer demotes
    jargon-only tags x0.4), spoiler gate (0 if reveals suppressed info)
```
Show `m` if `score >= threshold(profile)` AND the rate limits pass; thresholds by notification_intensity: key_only 0.7, normal 0.4, everything 0.15. Hard overrides: goals and red cards always pass for every persona (except spoiler mode, where they are queued) so no persona misses the game. Rate limits per persona are in 2.2; when a limit blocks an item, collapse into a digest ("last 3 minutes: 4 shots, 2 corners").

Options: (A) the multiplicative formula above (S, transparent, tunable); (B) additive weighted sum (S, easier but lets low-importance noise through); (C) learned ranker (L, no training data). **Recommend A**; risk: hand-tuned weights; mitigate by logging per-factor scores in a debug panel judges can open.

### 2.4 Partisan framing rules

Same moment, three framings (illustrated with a `shot` outcome `saved` by the home keeper):

| Viewer | Framing |
|---|---|
| Home fan | "Great save keeps us level: that was their best chance of the half." |
| Neutral | "Home keeper denies the away side's best chance of the half." |
| Away fan | "So close: our best chance of the half is saved." |

Rules (design): (1) facts, score, minute, outcome never change; only voice, pronoun and emphasis; (2) the explanation payload (the "why") is computed once, neutral, and each framing is a wrapper over it; (3) no invented praise or blame: partisan language must be traceable to an event field; (4) never claim a decision (e.g. foul) was "wrong" without VAR/referee data; (5) opponent credit is mandatory for opponent goals ("Away side score a well-worked goal"), a partisan flavour may add emotion but not hide the fact; (6) every item carries a `framing` tag and a "show neutral version" toggle. Options: (A) template wrappers (S, safe), (B) LLM rewrite with constraint checker (M, richer, risk of drift), (C) neutral only (S, loses the differentiator). **Recommend A for the demo, B optional behind a validator that checks numbers/entities match the neutral version.**

### 2.5 Cold start and privacy

Cold start: first screen asks 3 questions (language, "how much football do you know?", pick a club or skip); with no input use P1 or P3 defaults by expertise; no behavioural learning needed. Privacy: **profile lives in the browser (localStorage) or URL hash; server stores nothing; no accounts; no analytics on identity**; if shared via URL it contains only dial values. Options: server-side profiles (M, GDPR burden), client-only (S), anonymous server session (S-M). **Recommend client-only.** Risk: none for demo; limitation: no cross-device sync (the Premier League's registered-profile model [S12] offers that; we state we deliberately do not).

---

## 3. Player-focused mode spec

**Concept:** pick one `player_id`; the whole match is re-narrated around that player until the final whistle, with a personal recap.

### 3.1 What to show

| Element | Derivation from existing events | Notes |
|---|---|---|
| Live involvement ticker | any event where `player_id`, `receiver_id`, `pressed_player_id`, `opponent_id`, `fouled_player_id` or `player_on/off_id` matches | "Involvement" has two roles: actor and target |
| Touches (proxy) | passes made + passes received (`receiver_id`, outcome complete) + shots + tackles + set pieces taken | True touches need extra data; label as "recorded involvements" |
| Passes | made, completed %, progressive (end_x gain >= 10 m toward goal using `attacking_direction`), forward/back/sideways | |
| Key passes / assists | pass whose `possession_id` leads to a `shot` by teammate (via `assist_event_id` on shot) | |
| Duels / tackles | `tackle` outcome won/lost, `opponent_id` | |
| Shots | outcome, location, body part, speed | Shot map on pitch |
| Pressure received / applied | `pressure` events with `pressed_player_id` / `player_id`; avg `distance_m` | Pressure-on-pass link: pass accuracy under pressure vs not (Interpret) |
| Heat map | binned x/y of all involvements (normalise per period using `attacking_direction`) | Sparse with events only, say so on screen |
| Milestones | 25th touch, first completed pass in final third, first shot, 5 tackles, first card | Template triggers |
| Personal recap | at full time, 3 highlights chosen by the score formula restricted to the player, plus 3 numbers vs team average | Shareable card |

### 3.2 Hard cases

- **Substitutions:** before `player_on_id`, show "on the bench" state with team context; on entry, show a "comes on" card with minute and score; after `player_off_id`, freeze the ticker, show a recap-so-far, and offer "follow replacement / follow team / stay with player's team".
- **Off-ball minutes and quiet spells:** event data cannot see off-ball movement. When the player has no involvement for > N minutes (N=6 casual, 3 analyst), emit a low-key "quiet spell" line using what is known (team possession share, whether team is attacking his zone, whether he was pressed) and never invent movement. With tracking data (3.3) this becomes real.
- **Star story:** `star_player_match` is the default demo subject; also test a quiet player to prove the mode degrades gracefully.
- **Rate limit:** follow the persona limits; goals, cards and milestone events always pass.

Design options: (A) event filter only (S, now); (B) filter + explained stat sheet (S-M, **recommended**); (C) tracking-based (L). Risk: sparse for defenders/keepers (no save/clearance events yet; see section 6).

### 3.3 Extra raw data that would improve it

Tracking at 10 fps (as in public open data [S19]) gives distance covered, sprints, off-ball runs, true heatmaps and "where was he when the goal happened". Without it, claim only what events show. Even a lightweight `positions.jsonl` at 1 Hz for the focus player and ball would unlock heatmap and quiet-spell narration (M effort).

---

## 4. Testing that personas are genuinely different

### 4.1 Difference metrics over output streams (automated, S effort)

Run all personas on the same seeded match; each persona emits `items[]` with `{seq, text, stats_shown[], lang}`.

| Metric | Definition | Pass bar (design) |
|---|---|---|
| Moment overlap | Jaccard of selected `seq` sets between persona pairs | Pairwise Jaccard <= 0.5 for all pairs except where explicitly intended similar; goals/red cards form the shared core |
| Core coverage | share of top-10 importance moments that every persona shows | >= 90% (nobody misses the match's biggest moments) |
| Density | stats shown per minute | P2 >= 4x P1; ordered P1 < P5 < P3 < P4 < P2 |
| Reading level | Flesch-Kincaid grade, 0.39 x words/sentence + 11.8 x syllables/word - 15.59 [S20]; English only (formula limits noted by source: ignores prior knowledge, dialects) | P1 <= 7 and P2 >= 2 grades above P1; for ar/es use sentence length and rare-word rate instead |
| Vocabulary | jargon term rate (count of terms from a glossary list per 100 words) and type-token overlap | P2 jargon rate >= 3x P1; vocabulary Jaccard between P1 and P2 <= 0.6 |
| Entity focus | share of items mentioning fav club/player | Loyalist >= 50% club-mentions in non-neutral items; Player persona >= 70% about the focus player |
| Framing integrity | numbers, minute, score and outcome in every framing equal the neutral version | 100% (hard fail otherwise) |
| Accessibility | no item relies on colour only; every visual item has a text equivalent | 100%; automated lint plus manual screen reader pass |
| Rate-limit compliance | items per 5 min and min gap by persona | 100% |

A single **Persona Distance** score: mean of (1 - Jaccard), normalised density gap and reading-grade gap per persona pair; report as a matrix on a judge-visible "Personas Lab" panel. Bar: every pair >= 0.35.

### 4.2 Lightweight user test (hackathon, 30-45 min total)

Heuristic review + 5-8 participants (teammates, mentors, other teams; no personal data recorded):
1. Blind A/B: show two persona streams of the same 3 minutes (names hidden); ask "which was made for a beginner / a stats fan / a Club X fan?". Pass: >= 75% correct matching over trials (chance is 33-50%).
2. Comprehension: newcomer persona users answer 3 questions ("who is dominating and why?") with >= 2/3 correct.
3. Overload rating (1-5) per stream; analyst persona must score <= 3 for analysts and casual persona <= 2 for novices.
4. Accessibility walk-through: operate the demo with a screen reader (built-in OS reader) and with greyscale/colour-blind simulation; checklist against WCAG items cited [S7][S8][S9]. Pass: all 3 tasks completed without sight of colour.
5. Fairness check: show the home-fan and away-fan framing of one goal; reviewers must agree the facts are identical (framing integrity manually confirmed).

Caveat to report to judges: small n, informal, not statistically significant; it supports the demo, it is not a study.

---

## 5. Further ideas ranked

| Rank | Idea | Judge impact | Effort | Data dependencies |
|---|---|---|---|---|
| 1 | Persona switcher with live side-by-side (same moment, different voice) | H | S | none beyond Interpret/Explain output |
| 2 | "Explain it to me" button with glossary tooltips | H | S | glossary + Explain "why" payload |
| 3 | Player-focused mode + personal recap card | H | M | player ids on events (have) |
| 4 | Catch-up since I looked away (summary of N minutes) | H | S-M | time-windowed Interpret; uses same scorer with recency horizon 120 s |
| 5 | Spoiler-safe replay mode (hide score/outcome, staged reveal) [S4] | M-H | S | event stream with `score_*` hidden by renderer |
| 6 | Accessible voice/audio-description script (speech-ready text, pace control) [S6] | H (inclusion) | M | positions/pass direction fields; sentence templates; browser speech synthesis |
| 7 | Multi-view split of the same match (analyst + casual) | M | S | none |
| 8 | Shareable highlight cards (moment + framing, image) | M | S-M | importance scores |
| 9 | Challenge/prediction mode ("next goal?") | M | M | replay with hidden future; fairness since synthetic |
| 10 | Tactical lens (pressing and momentum overlays) | M | M | pressure events (have), more event types help |
| 11 | Fantasy lens (live points, bonus projection) [S18] | M | M | needs save/clearance/interception events for realistic scoring |
| 12 | Watch-party shared overlay | L-M | L | real-time sync/backend |
| 13 | "My player" notifications | M | S | extension of player mode |

Recommend building 1, 2, 3, 4 and 6-lite first (section 7).

---

## 6. Data innovation

### 6.1 Candidate additions

| Addition | Value for demo | Effort | Realism risk | Notes |
|---|---|---|---|---|
| `save` event (keeper, shot link) + `goal_kick` (README already mentions goal kicks as an outcome but schema has no event type) | H: keeper involvement, completes shot sequences | S | Low | Keepers are otherwise invisible in player mode |
| `clearance`, `interception`, `block` events | H: defender stories, fantasy lens | S | Low-Med (rate calibration) | Interception currently only a `possession_change.reason` |
| `dribble` / `carry` (start-end) | M-H: attacker stories | M | Med | Needed for realistic touches |
| `offside` | M | S | Low | |
| VAR check (`var_review`: reason, outcome, duration) | H: drama, framing-integrity demo | S-M | Low | Must be marked synthetic and fictional-referee |
| `injury` + stoppage | M: explains subs | S | Low | Link to `substitution` reason field |
| `formation` + lineups with positions, starters/bench, formation change events | H: tactical lens, player mode context | M | Med | |
| Tracking file `positions.jsonl` (1-10 Hz, 22 players + ball) | H but heavy [S19] | L | **High** (movement realism) | Do a 1 Hz focus-player version only if time allows |
| League table / multi-match context (`--matches N` exists) | H: "what this result means", rivalry, form | M | Low | Table derived from generated results, fictional |
| Crowd/weather/kickoff metadata (`match.json`) | L-M: colour for narration, accessibility descriptions | S | Low | Keep as metadata, never affect events unless modeled |
| xG-like fields | Keep **out** of generator (README rule: events are raw facts); computed in Interpret | n/a | n/a | Preserves the separation of facts vs interpretation |
| Fan-profile fixtures (the six persona JSONs + a "viewer log" replay file) | H for testing | S | none | Synthetic personas, no personal data |

### 6.2 Recommended build order

1. save + goal_kick + clearance + interception/block (S; unlocks player mode and fantasy lens)
2. lineups with positions + formation + starter/bench flag in `teams.json` (S-M)
3. VAR check + injury events (S-M; adds stories and framing tests)
4. dribble/carry (M)
5. multi-match league table + form context (M; already supported by `--matches`)
6. match metadata (weather, attendance, kickoff time) (S)
7. 1 Hz focus-player positions (L, stretch)

### 6.3 Documenting provenance for judges

Following the datasheet idea (why created, contents, collection, uses) [S21], ship `docs/DATASHEET.md` with: purpose (hackathon demo); fully synthetic, fictional league, no real players/clubs/trademarks; generator version + seed + config hash recorded in `match.json`; which parameters are calibrated against sourced targets vs `# UNCALIBRATED` (link to UNCALIBRATED.md, CALIBRATION-REPORT.md); known limitations (no tracking, simplified tactics); intended and non-intended uses (not for betting, not realistic player evaluation); determinism statement (same seed + config + version = identical bytes); evaluation-only status of `ground_truth.json`. Add a visible "SYNTHETIC DATA" badge in the UI. Public football datasets exist for comparison and calibration, with attribution expectations (Metrica: anonymised, acknowledge source [S22]; SkillCorner: 10 A-League matches, MIT label, credit requested [S19]; StatsBomb: follow user agreement and credit [S23]); we cite them only as calibration references, **do not copy data**, and check licence text before using any figure beyond published aggregates.

---

## 7. Modes to build first and a minimal plan

Build four modes: **(M1) Persona/Viewing Mode (casual vs analyst)**, **(M2) Player Focus**, **(M3) Catch-up + Spoiler-safe**, **(M4) Language + Accessible narration**. Club-fan framing is included in M1 as a toggle.

### 7.1 Day plan (assumes ~5 working days; compress as needed)

| Day | Work | Needs from generator |
|---|---|---|
| 1 | Generator additions (6.2 items 1-2): `save`, `goal_kick`, `clearance`, `interception`, `block` events; lineups/positions/formation + starters/bench in teams.json; one new story `star_quiet_spell` is optional | see 7.2 |
| 2 | Profile schema + six persona JSONs; relevance scorer; rate limiter; persona switcher UI | existing events; stories ground truth for tests only |
| 3 | M1 framing templates (neutral/home/away), glossary, "explain it to me"; M2 player ticker + stat sheet + recap | player ids, `assist_event_id` |
| 4 | M3 catch-up summary + spoiler gating; M4 ar/es strings, RTL, `role=status` live region, high-contrast/colour-blind-safe palette with shapes/labels, speech output | `name_i18n` (have) |
| 5 | Persona Distance matrix, blind A/B test, accessibility walk-through, datasheet, demo script (switch persona live on the `red_card_turning_point` and `star_player_match` stories) | VAR/injury events if time |

### 7.2 Exact generator changes

New event types (all keep the existing base fields):
- `save`: `keeper_id` (player_id), `shot_event_id`, `outcome` (caught|parried|tipped), `x,y`.
- `goal_kick`: pass-like (end_x, end_y, receiver_id, outcome, body_part).
- `clearance`: `outcome` (safe|out|intercepted), `body_part`.
- `interception` and `block`: `player_id`, `opponent_id`/`shot_event_id`.
- Optional: `dribble` (`end_x,end_y,outcome`), `offside` (`player_id`), `var_check` (`reason`, `outcome`, `duration_ms`, `reference_event_id`), `injury` (`player_id`, `substitution_event_id`).

New or extended fields:
- `substitution.reason` (tactical|injury|fatigue).
- `teams.json`: `starter` bool, `position`, `shirt_number`, `formation` per team; `formation_change` events optional.
- `match.json`: `kickoff_local`, `weather`, `attendance`, `competition_round`, `table_before` (fictional league).
- `ground_truth.json` additions for personalization testing: `persona_expected_moments` (top-N seq per persona derived from a reference scorer) kept evaluation-only.
- Story additions: `quiet_star_spell` (star player with a deliberate 10-minute quiet then a decisive moment) to test the "quiet spell" player-mode logic; `derby_tension` (cards cluster) to differentiate club-fan framing; `keeper_heroics` (3 saves in 10 minutes) to give keepers a story.

Cautions: new events change the output; bump `generator_version` and re-run calibration; keep probabilities in `config/default.yaml` marked `# UNCALIBRATED` until compared to sourced targets.

---

## Decision summary (options, recommendation, effort, risk)

| Decision | Options | Recommend | Effort | Risk |
|---|---|---|---|---|
| Profile control | free settings / presets + quick dials / behaviour learning | presets + quick dials | S | canned feel |
| Ranking | multiplicative / additive / learned | multiplicative | S | hand-tuned weights |
| Partisan framing | templates / LLM rewrite + validator / neutral only | templates (+ validator stretch) | S | LLM drift |
| Privacy | server profiles / client-only / anonymous session | client-only | S | no sync |
| Player data | events only / events + stat sheet / tracking | events + stat sheet | S-M | sparse for defenders until new events |
| Testing | metrics only / metrics + blind A/B / full study | metrics + blind A/B | S | small n |
| Data additions | events first / tracking first / metadata only | events and lineups first | S-M | calibration drift |

---

## Sources (all accessed 2026-10-19)

- [S1] Benton / Sporting News Media "Know the Fan 2014", 3 Jun 2014: https://www.benton.org/headlines/half-viewers-use-connected-devices-while-eyeing-sports-tv
- [S2] Deloitte, Enhancing digital fan engagement (2018 survey, 2019): https://www.deloitte.com/content/dam/Deloitte/us/Documents/technology-media-telecommunications/us-enhancing-digital-fan-engagement.pdf
- [S3] S&P Global Market Intelligence, 1 Jul 2026 (summary only; full text not retrieved): https://www.spglobal.com/market-intelligence/en/news-insights/research/2026/07/us-sports-viewing-casual-to-avid-sports-fans
- [S4] Fusion (practitioner blog, one case): https://fusion.com.au/thinking/how-optus-spoiled-the-world-cup
- [S5] City St George's, University of London, 2017: https://www.citystgeorges.ac.uk/news-and-events/news/2017/09/colour-blindness-statistically-affects-every-male-football-team
- [S6] RNIB, Accessibility of football broadcasts on TV, 25 Nov 2022 (10 interviews): https://media.rnib.org.uk/documents/RNIB_report_on_accessibility_of_TV_football_broadcasts.pdf
- [S7] W3C Understanding SC 1.4.1: https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html
- [S8] W3C Technique ARIA22 (role=status); SC 4.1.3 context: https://w3.org/WAI/WCAG22/Techniques/aria/ARIA22
- [S9] W3C Understanding SC 2.2.2: https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html
- [S10] Advanced Television on Nielsen, 16 Jul 2019: https://www.advanced-television.com/?p=141010
- [S11] Fantasy context via [S18]; persona P4 is a design inference.
- [S12] myPremierLeague, 1 Jul 2026: https://www.premierleague.com/en/news/4345793/sign-up-now-to-mypremier-league/
- [S13] Premier League app page: https://www.premierleague.com/en/pl-app
- [S14] Premier League Companion, 1 Jul 2025: https://www.premierleague.com/en/news/4345260/what-is-the-premier-league-companion
- [S15] FotMob overview (undated): https://en.androidayuda.com/fotmob-follows-football-matches-live/
- [S16] Sofascore App Store listing: https://apps.apple.com/app/sofascore-live-score-app/id1176147574
- [S17] Flashscore notifications article (undated): https://www.flashscore.com/news/personalised-notifications-set-up-unique-in-app-notifications-for-each-team-and-match/OSM00lBF/
- [S18] Flashscore on FPL 2026/27 (undated): https://www.flashscore.com/news/soccer-premier-league-fantasy-premier-league-2026-27-all-rule-changes-and-new-features/KGmq7ts1/
- [S19] SkillCorner open data: https://github.com/SkillCorner/opendata
- [S20] Flesch-Kincaid formula: https://readabilityformulas.com/learn-how-to-use-the-flesch-kincaid-grade-level/
- [S21] Gebru et al., Datasheets for Datasets: https://arxiv.org/abs/1803.09010v1
- [S22] Metrica Sports sample data: https://github.com/metrica-sports/sample-data
- [S23] StatsBomb free data announcement: https://blogarchive.statsbomb.com/news/statsbomb-release-free-2023-womens-world-cup-data/
