# Research 02: open calibration items

Accessed 2026-10-19. English top flight (men). All numbers are published summaries; none are raw event data. "Both" = both teams combined per match. "Derived" = my arithmetic, shown. Confidence: H = league or Opta Analyst page, M = fantasy/stats site, L = single small study or not stated.
Inability notes: pmc.ncbi.nlm.nih.gov showed a browser check, so I did not use it (not worked around). Several pages were read through a summariser, so figures were taken as given and a few inconsistencies are flagged.

## 1. Home advantage

| Quantity | Value | Season | Source | Conf. |
|---|---|---|---|---|
| Home / away win % | 46.1 / 32.4; 40.8 / 34.7; 42.6 / 30.0 | 2023-24; 2024-25; 2025-26 | [Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/2026/08/19/how-important-is-home-advantage-in-fpl) | M |
| Also | 48.4 / 28.7 (2022-23); 37.9 / 40.3 (2020-21, no fans) | | same | M |
| Draw % (derived) | 21.5; 24.5; 27.4 (100 - home - away) | 2023-24; 2024-25; 2025-26 | same | M |
| Cross-check 2025-26 draws | Final table sums to 104 draws = 104 / 380 = 27.4% (derived), 276 wins. Matches the above | 2025-26 | [NBC Sports table](https://www.nbcsports.com/premier-league-table-2025-26-season-standings) | M |
| Home share of goals | 54.9; 51.6; 55.5 % (2023-24, 2024-25, 2025-26); 57.3 (2022-23); 50.2 (2020-21) | | Fantasy Football Scout | M |
| Away possession | 49.6% in 2024-25, a record high. Home about 50.4% (derived: 100 - 49.6) | 2024-25 | [Opta Analyst](https://theanalyst.com/articles/premier-league-home-wins-covid-levels) | H |
| Away goals / xG / SoT / box touches | 1.5 goals, 1.4 xG, 4.4 SoT (4.45 in 2023-24), 25.5 box touches per game | 2024-25 to Jan | same | H |
| All-era home win | 45.8% (5,779 of 12,624) | to Jan 2025 | same | H |

Not found: home vs away shots, pass completion, fouls (FFS section paywalled). The Opta page gives 39.0% home wins "so far" in 2024-25 versus 40.8% final, so partial-season values drift by about 2 points.

Recommendation: home goal share target 0.50 to 0.573 (use central 0.545, mean of 2022-23 to 2025-26: (57.3+54.9+51.6+55.5)/4 = 54.8, derived). Home win about 43% to 46%, draw 22% to 27%, away 29% to 34%. Home possession about 50.4%: a small effect. Do not model home-shot or home-foul asymmetry; no source.

## 2. Score state and time

Sourced:
- Late goals: 26.3% of goals came after minute 75 (2023-24, to before matchweek 22), above 61-75 at 17.3%. 60.1% of goals in the second half; next highest 55.6% (2018-19). [PL.com](https://www.premierleague.com/en/news/3871035). H.
- Share of goals after 75: 20.0% (2022-23), 24.6% (2023-24), 22.0% (2024-25 to MD22). Substitutes scored 39.2%, 39.4%, 44.9% of those. [Opta Analyst](https://theanalyst.com/2025/01/premier-league-substitutes-increasingly-important-stats). H.
- Goals in the opening 15 min: 13.5%, 13.8%, 11.5%, 14.4% (2021-22 to 2024-25, last partial, 289 matches). [PL.com](https://www.premierleague.com/news/4271974). H.
- Goals at 90+: 7.9% (2021-22), 5.6%, 9.0%, 8.4% (2024-25), 13.3% (2025-26, early). The 2024-25 full figure is 94 goals = 8.4%; 2023-24 was 112. [PL.com](https://www.premierleague.com/en/news/4322877), [PL.com](https://www.premierleague.com/news/4271974). Through MW24 of 2025-26: 76 of 666 = 11.4%; 2024-25 at same point 9.3%. [PL.com](https://www.premierleague.com/en/news/4580269/why-more-late-goals-are-being-scored-in-2025-26-premier-league-season). H.
- Comebacks (win after trailing): 63 of 380 = 16.6% in 2024-25, joint record with 2023-24. 7 wins from two goals down in 2024-25. [PL.com](https://www.premierleague.com/en/news/4322877); [Opta Analyst](https://theanalyst.com/articles/premier-league-2024-25-data-trends-stats). H. Draw-after-trailing share: not found.
- 2025-26 90th-minute winners decided 14.3% of games (previous high 7.1%); 41.7% of late goals (10 of 24) turned a draw into a win, early season. [PL.com](https://www.premierleague.com/en/news/4437338/opta-analysis-of-why-more-late-goals-are-being-scored-in-2025-26-premier-league-season). H (partial season, treat as tail not mean).
- Winning margin average 1.34 (2025-26), 2.02 for decisive games in 2023-24 (same page). H.

Missing: full 0-15, 16-30, 31-45, 46-60 shares for a whole league (only team splits); effect magnitudes of score state on possession, shots, tempo, pressing, fouls. The only paper found ([Sampaio et al. 2013](https://www.scitepress.org/Papers/2013/46787/), 20 Champions League matches, 4 teams) is qualitative: losing and drawing teams use longer passing sequences; winning teams more short ones. No numbers. Confidence L.

Recommendation: time shape of goals, as shares: 0-15 about 0.12 to 0.14; 76-90 plus stoppage about 0.22 to 0.26 (2022-23 to 2024-25); second half 0.55 to 0.60; 90+ share 0.056 to 0.09 (aim 0.085 in a "2024-25" style, 0.11 to 0.13 for a late-drama story). Story base rates: comeback win 0.166 of matches. Keep `stories.effects.*` magnitudes as placeholders and label them design parameters.

## 3. Tackles, interceptions, pressure

- Tackles: only 31.1 both (2020-21) in the existing report. This session found no newer league total. Definitions only: Opta "successful tackle" = defending team wins possession or ball goes out of play; "true tackle" counts a touch on the ball even if the opponent keeps possession, penalises tackle fouls. [Opta Analyst MD5](https://theanalyst.com/articles/premier-league-stats-defending-off-the-charts-md5). H on definitions, nothing on rates. Example single-match player lines (7 attempts, 3 successful) are illustrative only, not averages.
- Interceptions, clearances, blocks, duels per match: not found.
- High turnovers per game: 16.7 (2023-24), 14.6 (2024-25), 11.5 (2025-26, early). 14.9% of high turnovers ended in a shot in 2025-26 (17% in 2023-24). [PL.com](https://www.premierleague.com/en/news/4426039/opta-analyst-on-long-balls-long-throws-key-tactical-trends-spotted-in-2025-26-season). H.
- PPDA: "opponent passes allowed per defensive action, in the opponent's defensive 3/5ths of the pitch" ([Stats Perform](https://www.statsperform.com/resource/how-we-measure-pressure/)); defensive-action event types not specified. Values: lowest PL side 8.62, European lowest 7.26 (2021-22, Wyscout); highest 16.93 ([PL.com](https://www.premierleague.com/en/news/4250153)). League average: not found. No public definition of an Opta "pressure" event found.

Recommendation: keep tackles untuned; define the event as "tackle attempt" with `won` boolean. If forced to pick: target the old 31.1 as successful tackles both and treat attempts as unsourced. PPDA 8.6 to 17 is a plausible spread across clubs (two seasons mixed; use as a club-tier range only, medium-low).

## 4. Shots, set pieces

- Shots both: 25.7, 25.3, 27.6, 26.1 (2021-22 to 2024-25) [PL.com](https://www.premierleague.com/news/4271974). Conversion 10.99%, 11.28%, 11.88%, 11% (same). Goals/shots check: 27.6 x 0.1188 = 3.28 (derived) agrees with 3.28.
- SoT: away 4.4 (2024-25), 4.45 (2023-24); home not found. Do not infer.
- Headers: share of goals from headers 15.6% (2024-25), 21.3% (2025-26 early; prior high 19.3%, 2010-11). Headed goals per 90: 0.43, 0.44, 0.53, 0.46 (2021-22 to 2024-25). [PL.com](https://www.premierleague.com/en/news/4461793/what-are-the-biggest-trends-from-202526-so-far). Headers share of shots: not found.
- Goals by type: non-penalty set-piece goals 19.2% to 25.0% of goals (2016-17 to 2025-26; 25.0% in 2025-26 early; 20.6% in 2024-25) [PL.com](https://www.premierleague.com/en/news/4426039/opta-analyst-on-long-balls-long-throws-key-tactical-trends-spotted-in-2025-26-season). Open play 74.7% in 2024-25 [Opta Analyst](https://theanalyst.com/articles/premier-league-2024-25-data-trends-stats). Goals from corners per game: 0.45, 0.35, 0.44 (2023-24, 2024-25, 2025-26). Short corners 18.0% (2024-25), 13.5% (2025-26). Corner goals 135 (2024-25) vs 171.
- Corners per match, free kicks, offsides, blocked/off-target shares, distance bands, big chances: not found in a citable league page this session (the existing 10.3 to 10.7 corners figure stays low confidence). Goal kicks 15.5 and throw-ins 35.8 already sourced. Long throws per match 0.89 (2020-21) to 1.52 (2024-25), 3.44 (2025-26 early).
- Penalties per 90: 0.27, 0.26, 0.28, 0.22 (2021-22 to 2024-25).
- Goalless draws: 24 (2024-25), 11 (2023-24). 24 / 380 = 6.3% of matches (derived), 11 / 380 = 2.9% (derived). Useful anchor for the 0-goal share.

Recommendation: keep SoT, corners, free kicks, offside, blocked shares as unsourced; if a number is needed, set shot-to-goal conversion to 0.11 (+/-0.01) and keep SoT free. Set share of goals from headers 0.16 to 0.21. 0-goal share about 0.03 to 0.06 as an anchor.

## 5. Restart timing, 2025-26 vs 2026-27

Source: [Opta Analyst, 8 Oct 2026](https://theanalyst.com/articles/premier-league-rules-throw-ins-goal-kicks-ball-in-play), 50 matches after MD5 of 2026-27 versus full 2025-26. H.

| Restart (seconds) | 2025-26 | 2026-27 (first 5 MD) |
|---|---|---|
| Throw-in | 17.8 | 15.3 |
| Goal kick | 30.4 | 27.7 |
| Corner | 36.1 | 33.9 |
| Free kick (all) | not in article | 33.3 |
| Direct free kick | about 85.9 (derived: 74.5 + "over 11") | 74.5 |
| Penalty | 164.7 | 117.4 (9 penalties) |
| Substitution break | 76.1 | 64.3 |
| Ball in play (min:s) | 55:23 | 56:35 |
| Added time per match | not given | 8:04 (7:29 in 2021-22) |

Earlier seasons for context: [Opta Analyst 2025-26 MD7](https://theanalyst.com/articles/premier-league-ball-in-play-are-we-seeing-less-football-2025-26) early 2025-26 throw-in 17.7, goal kick 30.3, corner 36.9; 2024-25 throw-in 15.6, goal kick 28.3, corner 33.6. Total match length 100:35 (early 2025-26), 99:44 (2024-25), 101:36 (2023-24). Ball in play 58:11 (2023-24), 56:59 (2024-25). Two Opta pages disagree slightly (2024-25 throw-in 15.6 vs 17.8 labelled "last season" is the 2025-26 value, fine). 2026 World Cup: throw-in 13.2, goal kick 23.7, substitution 65.5. Rule: five-second countdown for throw-ins and goal kicks; extra 60 s wait for a substitute if the outgoing player takes over 10 s to leave; adopted from 2026-27.

Not found: goal celebration or restart delay after goals, VAR check durations.

Recommendation: imitate **2026-27 rules** only if the product is meant to show current football; it has just 50 matches and fixed throw-in/goal-kick values already below prior years. For a defensible, full-season anchor, use 2025-26 (throw-in 17.8, goal kick 30.4, corner 36.1, penalty 164.7, substitution 76.1, ball in play 55:23). Pick one and record it in config as `timing.profile: 2025-26` or `2026-27`. My recommendation: **2025-26** for the core calibration (full-season, matches throw-in 35.8 and goal-kick 15.5 counts, which are from that season), with the 2026-27 column as an optional profile. Goal celebration delay: keep placeholder.

## 6. Spreads

- Matches with 4+ goals: 34.2% (2024-25), 29.2% (2025-26 to GW25). BTTS: 57.4% and 55.6%. Goals per match 2.93 and 2.79. [FISO](https://www.fiso.co.uk/premier-league-scoring-trends-2024-25-season-vs-2025-26-gw25-whats-changed/). M.
- Goalless draws 24 and 11 (above). Shares of 1, 2, 3 goals: not found.
- Per-match SD of goals, shots, cards, fouls, corners, possession: not found. Poisson check for goals is derived: variance = mean for a Poisson (mean 2.85, SD about 1.69); the 4+ share 0.33 in the TUNING report is consistent with a mean near 2.85 under a mixed distribution, so no change.
- Club spread, points 2025-26 ([NBC Sports](https://www.nbcsports.com/premier-league-table-2025-26-season-standings)): mean 51.8, SD 15.4 (population, derived from 20 values listed: 85, 78, 71, 65, 60, 57, 54, 53, 53, 52, 52, 49, 49, 47, 45, 44, 41, 39, 22, 20; sum 1036 = 20 x 51.8). Range 20 to 85. Source flagged a GD column mismatch, so I used points only. Quartiles (derived): top four 65 to 85, bottom two 20 and 22 with a large gap to 39. Medium.
- Possession: Nottingham Forest 39.6% lowest, the only side under 40% (2024-25); highest club value not stated. Direct speed 2.1 m/s (fastest) vs 1.4 m/s (least direct); City 5.1 passes per open-play sequence. [Opta Analyst](https://theanalyst.com/articles/analysing-premier-league-playing-styles-2024-25). H. Earlier report: top sides above 60% in 2018-19 (old, L).
- Goals-per-game extremes: whole-league average margin 1.34 (2025-26), 1.58 (2023-24). Late-game: 13:43 stoppage in one match.

Recommendation: club strength SD of 15 points is a clean tier target (about 1.2 to 1.4 ppg-scale; 15.4/38 = 0.41 ppg SD, derived). Possession tier range: 39.6% to about 60+%; set club possession mean spread to cover 40 to 62 (the 62 end unsourced, flagged). Per-match spreads stay unsourced; do not claim calibration.

## 7. Substitutions

- Subs per game, both: 7.9 (2022-23), 8.0 (2023-24), 8.3 (2024-25) = 3.95, 4.0, 4.15 per team (derived /2). Club range 3.1 to 4.8 per game (22 matches). [Opta Analyst](https://theanalyst.com/2025/01/premier-league-substitutes-increasingly-important-stats). H.
- Average sub time on pitch (incl. stoppage): 25:53 (2023-24), 25:16 (2024-25). Implied mean introduction minute about 101.6 - 25.9 = 75.7 for 2023-24 (derived: match length 101:36 less 25:53, approximate since "on pitch" runs to final whistle). For 2024-25: 99:50 - 25:16 = 74.6 (derived).
- Share of goals by subs: 13.3% (2023-24), 12.6% (2024-25 to MD22); subs scored 55.7% of second-half stoppage goals (2024-25).
- From earlier report: 42.5% of matches used all five (2023-24, M); about 38% of changes at 80+ in small 2022-23 samples (M).
- Timing bands before 60, 60-75, 75+: not found. First-half injury sub rate: not found.

Recommendation: 4.0 to 4.15 per team (range 3.1 to 4.8 across clubs); mean entry minute about 75 (derived); keep late subs allowed into stoppage; set sub-goal share 12 to 13%.

## 8. Cards

- Yellows both: 4.2 (2023-24, 1,602); 5.1 (first 100 of 2024-25); 4.36 reported for 2024-25 after 308 games, but that average was divided by 380 on the page (1,660 / 380), so the real rate is 1,660 / 308 = 5.39 (derived), caution. 2025-26: 1,539 / 380 = 4.05 (derived) on [Koppa Football](https://www.koppafootball.com/en-gb/fantasy-football-premier-league/2025-2026/statistics); the earlier report said 1,506 (3.96): sources disagree, use 3.96 to 4.05. Record before 2024-25 was 3.7 (1998-99). [Opta Analyst](https://theanalyst.com/articles/do-premier-league-suspension-rules-need-changing).
- Reds both: 0.16 (2024-25 early), 0.15 (56 reds to 308 games; 56/308 = 0.18 derived), 0.13 (48 / 380 = 0.126, 2025-26).
- Second yellows: 38% of 2024-25 red cards (early). H.
- MD6 2025-26: 50 yellows, 1 red in 10 games; 9 of the 50 for dissent; 3 for excessive celebration; fouls 204 in 10 games = 20.4 per game (existing); referee spread 5.8 to 6.4 cards per game for the two highest, 29.6 fouls per game for the highest. [Opta Analyst](https://theanalyst.com/articles/premier-league-md6-stats-off-the-charts-cards-fouls-referees). H (one matchday).
- By half, by minute band, share from fouls in the box: not found.

Recommendation: yellow 4.0 (range 3.96 to 4.2), red 0.13 to 0.16, second-yellow share of reds about 0.38. Referee card-rate multiplier: lognormal with mean 1 and spread such that top refs run about 1.4x the mean (derived: 6.4/4.5 average cards per game, where 4.5 is an assumed mean between two sources; label medium-low).

## 9. Speed and distance

- Top speeds recorded in 2025-26: 37.30, 36.97, 36.74, 36.62, 36.41 km/h; 15th place 36.09; fastest per club 35.95 down to 34.68 km/h. [PL.com](https://www.premierleague.com/en/news/4673057/who-ran-fastest-and-furthest-in-202526-premier-league). H. Source (tracking provider) not stated; no sprint threshold given. In m/s: 37.30 / 3.6 = 10.36 m/s (derived).
- Furthest in a single game: 13.24 km, 13.13, 13.11 (2025-26). Season leader 415.46 km in 3,414 minutes = 0.1217 km/min (derived) = 10.95 km per 90 min (derived). Same article.
- Shot speed: only upper bounds from the earlier report (about 30 m/s). Pass speed: no match-level average found.
- Sprint and high-intensity thresholds: no league or FIFA definition retrieved. The PMC World Cup benchmark paper was blocked by a browser check. Common literature values (about 19.8 km/h high-speed, 25.2 km/h sprint) turned up only as search terms, not read: **not sourced**.
- Distance by position: not found.
- Match-level 2025-26 sequence length 9.6 s and 12.1 m (10.4 s, 12.6 m in 2024-25). Direct speed 1.4 to 2.1 m/s across clubs (2024-25).

Recommendation: cap player speed at about 10.4 m/s with typical top speeds 9.6 to 10.4 (derived from 34.68 to 37.30 km/h); player mean distance about 10.9 km per 90 as a ceiling for outfield regulars (derived from a leader, so it is a top-end, not a mean). Do not label sprint threshold as sourced.

## Decisions summary

1. Home: add the effect; tune to goal share about 0.545.
2. Season for restarts: 2025-26.
3. Late goals: 90+ share 0.085; second-half share 0.55 to 0.60.
4. Club strength: points SD about 15 with a bottom-end gap.
5. Not found: SoT home, corners, free kicks, offsides, tackles recent, pressures, spreads per match, cards by minute, sprint thresholds, score-state magnitudes, sub timing bands.

## Targets to add to tools/targets.json

```json
  "home_goal_share":    {"low": 0.502, "high": 0.573, "basis": "share of goals scored by home side", "seasons": "2020-21 to 2025-26 (0.516 to 0.573 for the last 4 full seasons)", "source": "fantasyfootballscout.co.uk/2026/08/19/how-important-is-home-advantage-in-fpl (medium)"},
  "home_win_share":     {"low": 0.408, "high": 0.484, "basis": "share of matches won by home side", "seasons": "2022-23 to 2025-26", "source": "fantasyfootballscout.co.uk 2026/08/19 (medium)"},
  "away_win_share":     {"low": 0.287, "high": 0.347, "basis": "share of matches won by away side", "seasons": "2022-23 to 2025-26", "source": "fantasyfootballscout.co.uk 2026/08/19 (medium)"},
  "draw_share":         {"low": 0.215, "high": 0.274, "basis": "share of matches drawn (derived = 1 - home - away)", "seasons": "2022-23 to 2025-26", "source": "fantasyfootballscout.co.uk 2026/08/19; nbcsports.com PL table 2025-26 (104 draws / 380)"},
  "goals_90plus_share": {"low": 0.056, "high": 0.09, "basis": "share of goals scored at 90 min or later", "seasons": "2021-22 to 2024-25 full or near-full (2025-26 early 0.113 to 0.133)", "source": "premierleague.com/news/4271974; premierleague.com/en/news/4322877"},
  "goals_after75_share":{"low": 0.20, "high": 0.263, "basis": "share of goals after 75th minute", "seasons": "2022-23 to 2024-25 (partial) and 2023-24 (pre-MW22)", "source": "theanalyst.com/2025/01/premier-league-substitutes-increasingly-important-stats; premierleague.com/en/news/3871035"},
  "goals_second_half_share": {"point": 0.601, "basis": "share of goals scored in second half", "seasons": "2023-24 to before MW22", "source": "premierleague.com/en/news/3871035"},
  "comeback_win_share": {"point": 0.166, "basis": "share of matches won by a team that trailed (63 / 380)", "seasons": "2024-25 and 2023-24", "source": "premierleague.com/en/news/4322877"},
  "goalless_draw_share":{"low": 0.029, "high": 0.063, "basis": "share of matches 0-0 (derived: 11/380, 24/380)", "seasons": "2023-24, 2024-25", "source": "premierleague.com/news/4271974"},
  "shot_conversion":    {"low": 0.1099, "high": 0.1188, "basis": "goals per shot", "seasons": "2021-22 to 2024-25", "source": "premierleague.com/news/4271974"},
  "headed_goal_share":  {"low": 0.156, "high": 0.213, "basis": "share of goals from headers", "seasons": "2024-25 and 2025-26 early", "source": "premierleague.com/en/news/4461793"},
  "subs_per_team":      {"low": 3.95, "high": 4.15, "basis": "per team per match (derived: 7.9, 8.0, 8.3 both / 2)", "seasons": "2022-23 to 2024-25", "source": "theanalyst.com/2025/01/premier-league-substitutes-increasingly-important-stats"},
  "sub_goal_share":     {"low": 0.126, "high": 0.133, "basis": "share of goals (excl. own goals) scored by substitutes", "seasons": "2023-24, 2024-25 to MD22", "source": "same as subs_per_team"},
  "second_yellow_share_of_reds": {"point": 0.38, "basis": "share of red cards from two bookings", "seasons": "2024-25 early", "source": "theanalyst.com/articles/do-premier-league-suspension-rules-need-changing"},
  "club_points_sd":     {"point": 15.4, "basis": "population SD of 20 clubs' season points (derived)", "seasons": "2025-26", "source": "nbcsports.com/premier-league-table-2025-26-season-standings"},
  "player_top_speed_kmh": {"low": 34.68, "high": 37.30, "basis": "fastest recorded speed per club to league max, km/h", "seasons": "2025-26", "source": "premierleague.com/en/news/4673057"},
  "throw_in_s":         {"point": 17.8, "basis": "mean seconds, 2025-26 (15.3 in 2026-27 first 50 matches)", "source": "theanalyst.com/articles/premier-league-rules-throw-ins-goal-kicks-ball-in-play"},
  "goal_kick_s":        {"point": 30.4, "basis": "mean seconds, 2025-26 (27.7 in 2026-27)", "source": "same"},
  "corner_s":           {"point": 36.1, "basis": "mean seconds, 2025-26 (33.9 in 2026-27)", "source": "same"},
  "penalty_s":          {"point": 164.7, "basis": "mean seconds, 2025-26 (117.4 in 2026-27)", "source": "same"},
  "substitution_s":     {"point": 76.1, "basis": "mean seconds, 2025-26 (64.3 in 2026-27)", "source": "same"},
  "ball_in_play_s":     {"point": 3323, "basis": "55:23 mean ball in play, 2025-26 (derived 55 x 60 + 23)", "source": "same"}
```

Note: goals_after75_share and goals_second_half_share use partial-season data; mark them medium in any report. `home_win_share`, `away_win_share`, `draw_share` need the generator to emit `home_team` and a match result before the script can check them.
