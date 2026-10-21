# Calibration report for `eventgen`

Written 2026-10-18. Date accessed for every source: 2026-10-18.
League described: the English top flight (men), seasons stated per row. "Both teams" = per match, both sides added together. "Per team" = that number halved by me (marked "derived").

## 0. Read this first

**What this report is.** Sourced *targets* for what the generator's output should look like. It is not a list of config values. Config values are rates and probabilities; they must be tuned until the generated output hits these targets. That is what `tools/compare_to_targets.py` is for. Remove an `# UNCALIBRATED` marker only after the tuned output lands inside the target.

**What I could not do (and why).**
- The repo is not in this workspace, only the two spec files. So I could **not** run H1 (name audit), H4 (cross-platform byte check), H5 (colour pairs), or write a literal patch to `config/default.yaml`. They are marked "not done" below with the method.
- The hackathon site (aka.ms/insidethegame) blocks automated reading. I used the two GitHub files only.
- `tools/compare_to_targets.py` was tested on a tiny stub (2 fake matches) to check it runs. **It has not been run on real generator output**, and it assumes the field names in the generator spec. If the built schema differs, edit only the constants and `match_metrics`.

**Biggest mismatches (generator baseline vs sourced), all per match unless stated:**

| Quantity | Generator (spec baseline) | Sourced | Verdict |
|---|---|---|---|
| Goals, both teams | mean 3.5, range 0–11 | 2.75–3.28 full seasons 2022-23 to 2025-26 | too high |
| Penalties awarded | 0.72 | 0.17–0.33 | ~2–4x too high |
| Shots, both teams | 31.0 (15.5 per team) | 24.2–27.6 | too high |
| Shots on target | 7.9 per team | away sides 4.4 per game (one source) | too high |
| Throw-ins, both teams | 11.6 (5.8 per team, if per team) | 35.8 | ~3x too low |
| Fouls, both teams | 15.6 (7.8 per team) | at least 20.4; 21.8 in 2020-21 | too low |
| Yellow cards | 2.25 | 2.88–4.2 (full seasons) | too low |
| Red cards | 0.25 | 0.126–0.16 | ~2x too high |
| Tackles, both teams | 43.7 (unclear if per team) | 31.1 (2020-21 only) | too high either way |
| Possession gap | mean 2.8 pts, max 11 | top sides average above 60% over a season | too even |
| Passes, per team | 415 | ~425–473 (derived) | slightly low |
| Pass completion | 0.83 | 0.815–0.837 | OK |

---

## 1. Gate: rules and licensing

### A1. May we calibrate from published aggregate statistics?
Source: Official Rules, [github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL RULES.md](https://github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL%20RULES.md).

- §4.7 says: "Projects must use synthetic, football-realistic data." It adds that entrants source their own footage and must hold every licence and consent needed.
- §4.1(v) asks entrants to "create or extend" synthetic datasets that are football-realistic.
- §4.3 says third-party data must be used within its terms; §4.6 says the Submission must be solely the entrant's work.

**Verdict: unclear, leaning allowed.** Nothing forbids using published summary numbers as parameters, and "football-realistic" suggests realism is expected. But the rules never say it. Use only cited summary numbers; never raw event or tracking data.

**Question for the organizers** (§11.6 says clarification requests must be written and sent before the deadline; I could not find where on the site to send it):
> "May a synthetic generator be tuned to published aggregate league statistics (season averages from public articles), as long as no real event-level data is used or stored?"

### A2. Who allows reuse of aggregate numbers?
I found **no source with an explicit open licence for Premier League aggregates.** Verdict for each is a risk view, not legal advice.

| Source | Offers | Terms found | Verdict |
|---|---|---|---|
| premierleague.com articles ("Talking Tactics", Opta-based) | season averages, formation counts | Site terms say the site is covered by copyright and database rights; no reuse licence ([terms](https://www.premierleague.com/ar/terms-and-conditions)) | Cite single figures as facts with link. Do not copy tables or charts. |
| Football DataCo | manages rights to official event data | Asserts database rights in official data ([site](https://www.football-dataco.com/)) | This is why raw event data stays out. |
| Opta Analyst (theanalyst.com, Stats Perform) | season averages, ball-in-play, restarts | Terms at statsperform.com/terms-of-use: **not opened** | Same as above. Check terms before the final README. |
| Academic papers (JSSM, PMC, journals) | kick speeds, match-status studies | Per paper; one seen was CC BY-NC-SA 4.0 | Cite results with the paper link. |
| Fantasy and betting sites (Fantasy Football Scout, FISO, allaboutfpl, Racing Post) | home advantage, penalties, substitution counts | Not checked | Cross-check only. Medium to low confidence. |

Attribution text for the README: "Calibration targets are summary statistics from the sources listed in docs/CALIBRATION-REPORT.md. No third-party event data is included."

### A3. League naming, trademarks, crests
No rule on fictional league naming or colours. Related rules: §4.4 (demo video must not include third-party trademarks or copyrighted material without permission) and §11.8 (the Premier League and Microsoft marks stay theirs). **My inference:** keep all crests, logos and club or league marks out of the app, repo and video. Describing the event in a README is a different matter, but do not use "Premier League" as a product or league name.

### A4. Azure rules
No rule requires, forbids, or funds a specific Azure service, and no credits are mentioned in the rules. What exists: the pitch must say which Microsoft and Azure technologies were used (§4.4); Stage One is pass/fail on "reasonably applies to the required technologies" (§6.1); criterion 1 lists hero technologies (Foundry, Agent Framework, Azure MCP, GitHub Copilot Agent Mode, Fabric, GitHub SDK/CLI, Azure apps, AI services, databases, "etc."). Event Hubs and Service Bus are not named. The Azure Cloud Native category names AKS, Container Apps, Functions and Logic Apps. Credits: **not found** (site unreadable).

---

## 2. Calibration targets

Confidence: **High** = league or Opta analysis published on the league site or Opta Analyst. **Medium** = fantasy or stats sites. **Low** = SEO pages, old data, or one small study.
Recommendation: **replace** / **keep placeholder** / **owner**.

### 2.1 Match volume and outcome

| # | Value or range | Source and season | Conf. | Recommendation |
|---|---|---|---|---|
| B1 | Passes per match, both teams: 941.0 (2023-24), 893.4 (2024-25), 849.1 (2025-26, partial season), 945.2 (2020-21). Per team (derived): ~425–473. Generator 415 is slightly under. | [PL.com / Opta Analyst](https://www.premierleague.com/en/news/4426039/opta-analyst-on-long-balls-long-throws-key-tactical-trends-spotted-in-2025-26-season) | High | replace (raise a little) |
| B2 | Pass completion 83.7% (2024-25); 81.5% (2020-21, then a record). Completed passes 748 per match in 2024-25, about 4.7% fewer early 2025-26. By length: **not found** at league level. One World Cup 2014 paper gives 76.4% short, 56.5% long, different definitions, treat as low confidence ([paper](https://journals.uran.ua/sport_herald/article/view/67656/62892)). | [PL.com](https://www.premierleague.com/en/news/4461793/what-are-the-biggest-trends-from-202526-so-far); [Stadium Astro, citing PL 2020-21 review](https://english.stadiumastro.com/football/was-premier-league-season-no-other-really-no-other-194957) | High overall, low by length | overall: generator 0.83 already inside; by length: keep placeholder |
| B3 | Shots per match, both teams: 24.2 (2020-21, incl. blocked), 25.7, 25.3, 27.6, 26.1 (2021-22 to 2024-25; last is partial). Per team (derived): 12.1–13.8. Shots on target: only found away teams at 4.4 per game (2024-25 to January) and 4.45 (2023-24). Share blocked or off target: **not found**. | [PL.com Talking Tactics](https://www.premierleague.com/news/4271974); [Opta Analyst](https://theanalyst.com/articles/premier-league-home-wins-covid-levels) | High (shots), medium (SoT: partial) | replace shots; SoT: owner needs home-side figure; block and off-target shares: keep placeholder |
| B4 | Goals per match, both teams: 2.85 (2022-23), 3.28 (2023-24), 2.93 (2024-25), 2.75 (2025-26: 1,045 in 380). Early 2025-26 ran at 2.6. Share of matches with 4+ goals: 34.2% (2024-25), 29.2% (2025-26 to round 25). Shares of 0, 1, 2, 3 goal matches: **not found**. | [Opta Analyst](https://theanalyst.com/2024/11/premier-league-2024-25-data-trends-stats); [tournamentfootball.co.uk](https://www.tournamentfootball.co.uk/en-gb/fantasy-football-premier-league/2025-2026/statistics); [FISO](https://www.fiso.co.uk/premier-league-scoring-trends-2024-25-season-vs-2025-26-gw25-whats-changed/) | High (means), medium (4+ share) | replace. Generator mean 3.5 is above every recent full season. Tail question confirmed worth checking: run the script and histogram goals. |
| B5 | Conversion by distance band: **not found** in usable form. Weak reference points only: average shot distance in the top five leagues fell from 18.5 m to 17.7 m ([Driblab](https://www.driblab.com/blog/how-are-the-shots-in-the-big-leagues-evolution-of-distance-and-xg-per-shot), date not stated); long-range central shots about 3% ([StatsBomb, 2014](https://blogarchive.statsbomb.com/articles/soccer/mythbusting-is-long-range-shooting-a-bad-option/), old). | | Low | keep placeholder |
| B6 | Home advantage. Home win %: 47.6 (2018-19), 45.3, 37.9 (2020-21, no crowds), 42.9, 48.4, 46.1, 40.8 (2024-25), 42.6 (2025-26). Away win %: 33.7, 30.5, 40.3, 34.0, 28.7, 32.4, 34.7, 30.0. Home share of goals 51.6% (2024-25) up to 55.6% (2018-19). Away possession 49.6% in 2024-25 (a record high), so home about 50.4%. | [Fantasy Football Scout, Aug 2026](https://www.fantasyfootballscout.co.uk/2026/08/19/how-important-is-home-advantage-in-fpl); [Opta Analyst](https://theanalyst.com/articles/premier-league-home-wins-covid-levels) | Medium / High | owner: add a small home effect (none today). Target home goal share 0.516–0.556. |
| B7 | Penalties awarded per match: 0.24 (2019-20), 0.33 (2020-21), 0.27, 0.26, 0.28 (2023-24), 0.23 (2024-25 to MD20); 92 attempts in 2025-26 = 0.24 (derived). Generator 0.72 is 2–4x too high. | [Opta Analyst](https://theanalyst.com/articles/football-newsletter-penalties-bruno-fernandes); [fpl.team](https://fpl.team/blog/2026-27-premier-league-set-piece-battles-pre-season-guide/) | High | replace |
| B8 | Penalty conversion: 89.7% (96/107, 2023-24), 82.6% (38/46, 2024-25 to MD20), 83.7% (77/92, 2025-26). Opta xG for a penalty is 0.79 ([Squawka](https://www.squawka.com/en/?p=1410915)). Generator placeholder 0.76 is below the observed range. | as listed | High / medium | replace with 0.826–0.897 range |

### 2.2 Defensive and discipline

| # | Value or range | Source and season | Conf. | Recommendation |
|---|---|---|---|---|
| C1 | Tackles per match, both teams: 31.1 (11,800 in 380). **2020-21 only.** Tackle success rate: **not found**. The baseline 43.7 is above this whether it is per team or per match. | [Stadium Astro](https://english.stadiumastro.com/football/was-premier-league-season-no-other-really-no-other-194957) | Low (old) | owner: find a recent figure; until then keep placeholder |
| C2 | Pressures per match, success, presser distance and duration: **not found.** No public league total or definition. Related only: high turnovers 14.9 per match (2024-25, early). | [PL.com](https://premierleague.com/news/4171114) | n/a | keep placeholder; document these as design parameters, not real-world fits |
| C3 | Fouls per match, both teams: 21.8 (8,283 in 380, 2020-21). In 2025-26 the quietest matchday so far had 204 fouls in 10 matches = 20.4 per match. Generator 15.6 (if 7.8 per team) is low. | Stadium Astro (above); [Opta Analyst](https://theanalyst.com/articles/premier-league-md6-stats-off-the-charts-cards-fouls-referees) | Medium | replace: target at least 20.4 |
| C4 | Yellows per match: 2.88 (2020-21), 4.2 (2023-24), 5.1 (2024-25 first 100 matches), 3.96 (2025-26: 1,506 in 380). Reds per match: 0.126 (2020-21: 48), 0.16 (2024-25 early), 0.13 (2025-26: 48). Cards are strongly season-dependent (rule and referee emphasis). | [Opta Analyst](https://theanalyst.com/articles/do-premier-league-suspension-rules-need-changing); tournamentfootball.co.uk; Stadium Astro | High / medium | replace: yellow target 2.88–4.2, red 0.126–0.16 |
| C5 | Fouls by the team in possession vs defending: **not found.** | | n/a | keep placeholder |

### 2.3 Restarts, time and substitutions

| # | Value or range | Source and season | Conf. | Recommendation |
|---|---|---|---|---|
| D2 | **Throw-ins:** 13,615 in 2025-26 = 35.8 per match, both teams (derived). **Goal kicks:** 5,901 = 15.5 per match (derived). **Corners:** only weak figures, about 10.3–10.7 per match from older aggregator pages; no reliable league total found. **Free kicks:** **not found.** The generator's 5.8 throw-ins is about 3–6x too low. | [Opta Analyst, 8 Oct 2026](https://theanalyst.com/articles/premier-league-rules-throw-ins-goal-kicks-ball-in-play) | High (throw-ins, goal kicks); low (corners) | replace throw-ins; corners and free kicks: owner (find a reliable source) |
| D3 | Ball in play: 54:49 (2022-23), 58:11 (2023-24), 56:59 (2024-25), 55:23 (2025-26); 56:35 in the first 5 matchdays of 2026-27. Restart delays, 2025-26 → start of 2026-27: throw-in 17.8 → 15.3 s; goal kick 30.4 → 27.7 s; corner 36.1 → 33.9 s; penalty 164.7 → 117.4 s; substitution break 76.1 → 64.3 s; free kick 33.3 s (2026-27). **Rule change in 2026-27** (five-second throw-in and goal-kick directive), so pick one season to imitate. | [Opta Analyst](https://theanalyst.com/articles/premier-league-rules-throw-ins-goal-kicks-ball-in-play); [Opta Analyst](https://theanalyst.com/articles/premier-league-ball-in-play-are-we-seeing-less-football-2025-26) | High | owner: choose 2025-26 (full season, safer) or 2026-27 (50 matches only) |
| D4 | Added time, both halves: 8:04 per match early 2026-27 (lowest since 2021-22 at 7:29); 2024-25 was 1:51 shorter than 2023-24; average match length 98:07 in 2022-23 and over 100 min in 2025-26. Split between halves: **not found** (one match had 13:43 in a second half). Generator total 7.5 min is near the low end. | Opta Analyst (above); [PL.com](https://www.premierleague.com/news/4322877); [PL.com](https://www.premierleague.com/en/news/4437338/opta-analysis-of-why-more-late-goals-are-being-scored-in-2025-26-premier-league-season); [90min](https://www.90min.com/posts/how-long-is-an-average-premier-league-match) | High (total) | total: replace; half split: keep placeholder. "Second half longer" is **not confirmed** by a good source. |
| D5 | Five substitutions per team allowed since 2022-23. Average about 4.0 per team in 2023-24; 42.5% of matches used all five. Timing: in early 2022-23 samples about 38% of changes came at minute 80 or later and about 10% in the 90th minute or added time (small samples). Generator caps at minute 85, so it misses late subs. | [Kwest Thoughts (Substack)](https://kwestthoughts.substack.com/p/data-dump-2023-24-substitution-trends); [FourFourTwo](https://www.fourfourtwo.com/news/how-premier-league-teams-have-used-their-substitutes-so-far-this-season-1661272652000) | Medium (small samples) | owner: raise the count (about 4) and allow late subs |
| D6 | **No match-level shot or pass speed distribution found.** Maximum-effort instep kicks in studies: 104.4 km/h (29.0 m/s, elite players, radar), 108.8 ± 7.5 km/h (30.2 m/s, U19), 94.7–96 km/h (26.3–26.7 m/s, older studies), professional instep swerve 23.5 m/s. These are **upper bounds for tests, not match averages.** | [JSSM abstract](https://jssm.org/suppls/10/Suppl.10.26-29.php); [study](https://nomos.is.cuni.cz/publication/525207?query=NART); [Taylor & Francis](https://www.taylorfrancis.com/books/9781134317356/chapters/10.4324/9780203412992-9) | Medium (bounds only) | bounds: may use ~30 m/s as a ceiling for `bounds.shot_speed`; typical values: keep placeholder |
| D7 | Long pass = at least 32 m (Opta). Long share of passes: 12.2% (2021-22), 11.5%, 10.8%, 10.4% (2024-25), 11.5% (2025-26 early). Long balls per match 93.4 (2024-25), 99.7 (2025-26 early). League average pass length: **not found** (club range in another dataset: 15.9–23.4 m, 2018-19). | [PL.com](https://www.premierleague.com/news/4271974); [PL.com](https://www.premierleague.com/en/news/4426039/opta-analyst-on-long-balls-long-throws-key-tactical-trends-spotted-in-2025-26-season); [CIES](https://football-observatory.com/IMG/sites/b5wp/2018/263/en/) | High (share) | replace long-pass share and the 32 m cut; average length keep placeholder |

### 2.4 Structure and style

| # | Value or range | Source | Conf. | Recommendation |
|---|---|---|---|---|
| E1 | Partial only: one club's long-pass share was 8.8% (2024-25) while the league was 10.5%; team corner averages ranged 3.6–8.2 per game (2021-22). No clean spread for possession, pressing, directness. | [PL.com](https://www.premierleague.com/en/news/4461793/what-are-the-biggest-trends-from-202526-so-far); [Planet Sport](https://www.planetsport.com/soccer/feature/the-analyst-premier-league-corner-kings-betting-stats) | Low | keep placeholder |
| E2 | Direction only, no shares. Central midfielders had the most passes in one tournament study ([Kubayi 2021](https://tutvital.tut.ac.za/items/6051bb66-195f-45bb-bde9-ec8c885a76c1), CC BY-NC-SA 4.0); another study ranks centre-backs highest. Sources disagree. | | Low | keep placeholder |
| E3 | Shot share by role: **not found.** | | n/a | keep placeholder |
| E4 | Formation use (760 team-matches per season): 4-2-3-1 used 296 times (38.9%) in 2023-24 and 408 (53.7%) in 2024-25; 4-3-3: 172 (22.6%) then 114 (15.0%); 3-4-2-1: 71 then 117 (15.4%). Shares checked by my own arithmetic against the 760 total. | [PL.com 2024/25](https://www.premierleague.com/news/4323030); [PL.com 2023/24](https://www.premierleague.com/news/4030093) | High | replace `match.formations` weights (use 2024-25 or an average) |
| E5 | Per-match possession spread: **not found.** Season averages: only two sides were above 60% early in 2018-19 ([Sporting Life](https://www.sportinglife.com/football/news/premier-league-stats-and-rankings/153425), old). My inference: the generator's maximum gap of 11 points (55.5%/44.5%) cannot produce a 60%+ side, so it looks too even. | | Low | owner: add stronger team-strength spread, then re-measure |
| E6 | Direction supported: teams hold more possession when losing than when winning or drawing, and shoot less when losing (studies cited in [Sampaio et al. 2013](https://www.scitepress.org/Papers/2013/46787/); four-team sample for the passing result). Effect sizes **not found.** Useful base rates for the late-comeback story: 16.6% of matches (63 of 380) had a team win after being behind in 2024-25, a record; 8.4% of goals came in stoppage time in 2024-25, about 13% early in 2025-26. | [PL.com](https://www.premierleague.com/news/4322877); [PL.com](https://www.premierleague.com/en/news/4437338/opta-analysis-of-why-more-late-goals-are-being-scored-in-2025-26-premier-league-season) | Medium | `stories.effects.*` magnitudes: keep placeholder; use base rates to judge how often the comeback story should fire |

---

## 3. Missing features (F1–F9)

Priority is for the hackathon demo, judged against the challenge text (§4.1 in the rules).

| # | Needed? | Minimum faithful design |
|---|---|---|
| F1 | **Medium.** Recaps lean on big saves; throw-ins and goal kicks are now frequent (35.8 and 15.5 per match). | Add `save` (goalkeeper id, linked to the shot) and `goal_kick`. Skip dribble, offside, clearance for now. |
| F2 | Low. | Skip. |
| F3 | Low. | Skip. |
| F4 | **High, cheap.** Home share of goals 0.516–0.556. | One config value: a small home multiplier on attack intensity. Add a per-club strength tier so league-level stories exist. |
| F5 | **Medium-high if you keep the "speed and distance indicators" feature** from §4.1(ii) of the rules. Events alone cannot give player speed or distance. | Optional low-rate `tracking.jsonl` (player x, y per second, or per event window). Keep it a separate file. |
| F6 | Low-medium (drama). | `var_check` event with an outcome that can cancel a goal. Only after the core is tuned. |
| F7 | **High.** Supported by the possession-when-losing evidence. | Make attack intensity depend on score and time left, small effect; story windows then add on top. |
| F8 | Low. | Keep assists derived from `assist_event_id`. Add own goals only if a recap needs one. |
| F9 | **High.** Multi-language storytelling is in the challenge. | `description_i18n` in ground truth, same language set as `name_i18n`. |

---

## 4. Plausibility checks

Script: `tools/compare_to_targets.py`, with `tools/targets.json` (sourced ranges only).

```
python tools/compare_to_targets.py out/            # parent folder of match folders
python tools/compare_to_targets.py out/ --strict   # exit 1 if any FAIL
```

**Status: tested on a 2-match stub only** (to check it runs; every "FAIL" in that run was expected because the stub is tiny). **No real generator output has been compared.** Paste the real output into this section after running it on 40 seeds.

What the script covers: check 1 (means vs sourced ranges). It does **not** judge spread, because no source gave a real per-match spread. Checks 2–5 (correlations, time sanity, distribution shapes, style diversity) still need to be done by the agent that has the repo: histograms of goals, cards and shots; possession vs shots; fouls vs cards. The "second-half added time longer than first" check cannot be done until a good source exists (see D4).

---

## 5. Azure stretch sink

**G1. Recommendation: Event Hubs**, partition key = `match_id`.
- Event Hubs is the streaming and ingestion service, with each partition an ordered sequence; related events go to one partition by giving a partition key ([Azure messaging comparison](https://docs.azure.cn/en-us/service-bus-messaging/compare-messaging-services)).
- Service Bus fits queues with sessions and dead-lettering; useful for agent hand-offs, not needed to replay one ordered match.
- Throughput, cost, free tier: **not found.** Check the pricing page before relying on it.
- For the owner: Event Hubs, unless you also want agent-to-agent queues.

**G2. SDK.** Packages: `azure-eventhub`, `azure-identity` (passwordless sign-in with `DefaultAzureCredential`). Receiving with checkpoints needs `azure-eventhub-checkpointstoreblob-aio`. Sending needs the "Azure Event Hubs Data Owner" role. **Python version conflict between doc versions** (3.8+ vs 3.9+): check the current English page. **Versions: not found.** Source: [Microsoft Learn quickstart](https://learn.microsoft.com/ms-my/azure/event-hubs/event-hubs-python-get-started-send). The doc's async pattern: create an `EventHubProducerClient` with namespace, hub name and credential, create a batch, `add(EventData(...))`, send the batch. Passing a partition key when creating a batch exists in the SDK as far as I know, but I did **not** see it in the page I read: confirm in the SDK reference.

**G3. Design note.** Put the sink in an optional package (for example `eventgen_azure/`) implementing `EventSink.send(event)`. Buffer events, send in batches, one batch per match key, flush on `close()`. Use the SDK's own retries; add an async variant for `areplay`. Namespace and hub name come from environment variables; no secrets in the repo. The core must import nothing from Azure.

---

## 6. Repo safety and quality

| # | Status | Notes |
|---|---|---|
| H1 | **Not done** (no repo here). | Method: generate 2,000 players and all clubs; compare against a list you compile of real club and town names. I did not compile such a list from memory, to avoid false confidence. |
| H2 | **Not done.** | Needs a native reader. Have an Arabic reader skim the `ar` names; the `es` pattern needs a Spanish reader. |
| H3 | **Partly.** No licence file exists. Rules §7 already give Microsoft and the Premier League a broad licence to your Submission whatever you pick. **Recommendation: MIT** (simple, permissive). Owner decision. Still to do on the repo: scan for secrets, confirm no copied code. |
| H4 | **Not done.** | Risk areas for byte differences: float formatting (round before writing), dict or set ordering, locale, line endings (write `\n` explicitly, open files with `newline="\n"`). |
| H5 | **Not done.** | Method: take both team colours, compute WCAG contrast, check both under colour-blind simulation. Prefer pairs that differ in brightness, not only hue. |

---

## 7. Decisions for the owner

1. **Sources.** Use single cited figures from league and Opta articles plus papers; no copied tables. Send the A1 question to the organizers. *Recommendation: yes.*
2. **Number of clubs.** Not researched. A league-level story needs enough clubs to show a table, but I have no evidence for a number. *Owner call.*
3. **Azure service.** Event Hubs (G1).
4. **Add F1 events before Interpret starts?** Add only `save` and `goal_kick`. Add F4, F7, F9 too; they are cheap and matter more.
5. **Which season to imitate.** 2025-26 (full season) or 2026-27 (rule change, 50 matches).

## 8. Definition of done

- [x] Section 1 answered (quotes short; full text at the link).
- [x] Rows in 2.1–2.4 answered or marked "not found".
- [x] This report written; numbers cited by link.
- [ ] Config patch: **not done**, needs the repo. Replace values only after tuned output matches the targets.
- [ ] `compare_to_targets.py` run on real output: **not done** (stub test only).
- [x] Sections 3, 5 written; section 6 partly (H1, H2, H4, H5 need the repo or a reader).
- [x] Decisions listed.
- [x] No raw real data, no real club or player names in the files I wrote, no secrets.

Note: this report names the real league and cites real articles, so keep it outside `config/`, code and the app's UI. The spec's rule "no real names in docs" would otherwise be broken.
