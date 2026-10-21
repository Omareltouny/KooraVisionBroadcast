# Uncalibrated placeholder values

Every value below is a **guess**, not a measurement. None of them is presented as a fact about
real football. They exist so the generator runs and produces data with a football-like *shape*
(about 800 to 900 passes, 25 to 35 shots, a few goals, a handful of fouls and cards per match),
but the absolute numbers must be calibrated later from sources and licences the owner chooses
(open item 14 of the spec).

How to calibrate: change the value in `config/default.yaml`, keep the `# UNCALIBRATED` marker
until the value is backed by a source, then remove the marker **and** the row here.
A test (`tests/test_core.py::test_uncalibrated_doc_lists_every_placeholder`) fails if a marked
config key is missing from this file. To regenerate the table after editing the config:

```
python -c "from eventgen.config import uncalibrated_markdown as m; print(m())"
```

Values that are *not* listed are facts of the game or structure, not guesses: pitch dimensions
(105 m x 68 m, goal 7.32 m, penalty area 16.5 m x 40.32 m, spot 11 m), 45 minute halves,
formations, squad size (11 starters + 7 on the bench) and the 5 substitution maximum.

Also unresolved (owner decisions, not guessed by the generator): which Azure messaging service
to use for the stretch sink, and how many fictional clubs the demo league needs
(`competition.num_clubs` is only a default).

| Config key | Placeholder value | Controls |
|---|---|---|
| `competition.num_clubs` | `6` | demo league size (owner decision pending) |
| `match.stoppage_min_ms` | `60000` | minimum added time per half |
| `match.stoppage_max_ms` | `480000` | maximum added time per half |
| `match.stoppage_per_foul_ms` | `8000` | added time accrued per foul |
| `match.stoppage_per_card_ms` | `20000` | added time accrued per card |
| `match.stoppage_per_sub_ms` | `30000` | added time accrued per substitution |
| `match.stoppage_per_goal_ms` | `25000` | added time accrued per goal |
| `match.sub_count_range` | `[3, 5]` | substitutions each team makes (research: about 4 per team) |
| `match.sub_minute_range` | `[46, 85]` | when substitutions are scheduled |
| `team_style.attack_intensity` | `[0.9, 1.1]` | multiplier on shot appetite |
| `team_style.pressing_intensity` | `[0.8, 1.2]` | multiplier on pressing frequency |
| `team_style.buildup_directness` | `[0.2, 0.7]` | 0 patient, 1 direct |
| `team_style.quality` | `[-0.02, 0.02]` | additive pass completion edge |
| `player.skill_range` | `[0.35, 0.95]` | hidden player skill range |
| `player.involvement_range` | `[0.8, 1.2]` | hidden ball involvement range |
| `player.skill_pass_weight` | `0.10` | pass completion per unit of skill above 0.65 |
| `player.skill_finish_weight` | `0.15` | goal probability per unit of skill above 0.65 |
| `roles.anchor_x` | `{GK: 5, CB: 24, FB: 30, DM: 38, CM: 50, AM: 62, W: 72, ST: 85}` | typical own-half-relative x of each role |
| `roles.involvement` | `{GK: 0.5, CB: 0.9, FB: 1.0, DM: 1.1, CM: 1.2, AM: 1.2, W: 1.0, ST: 0.9}` | ball involvement by role |
| `roles.shot_mult` | `{GK: 0.0, CB: 0.3, FB: 0.4, DM: 0.6, CM: 0.9, AM: 1.2, W: 1.2, ST: 1.6}` | shooting appetite by role |
| `roles.anchor_spread_x` | `18.0` | how strictly players hold their x zone |
| `roles.lane_spread_y` | `16.0` | how strictly players hold their lane |
| `passing.base_weights` | `{short: 1.2, forward: 0.45, lateral: 0.75, back: 0.30, long: 0.30}` | relative pass type frequency |
| `passing.cross_weight` | `1.0` | crossing weight when wide in the final third |
| `passing.cross_min_x` | `72.0` | x from which crosses are considered |
| `passing.cross_wide_band_m` | `14.0` | distance from touchline counted as wide |
| `passing.length_m` | `{short: [5, 17], forward: [11, 30], lateral: [6, 24], back: [5, 24], long: [32, 58], goal_kick_short: [12, 24]}` | pass length ranges |
| `passing.completion` | `{short: 0.91, forward: 0.80, lateral: 0.93, back: 0.95, long: 0.58, cross: 0.32, throw_in: 0.85, corner: 0.38, free_kick: 0.62, goal_kick: 0.55}` | base completion by type |
| `passing.pressure_penalty` | `0.14` | completion lost under maximum pressure |
| `passing.failure_split` | `{intercepted: 0.42, incomplete: 0.32, out: 0.26}` | how failed passes fail |
| `passing.speed_ms` | `{short: [6, 14], forward: [8, 17], lateral: [6, 13], back: [6, 13], long: [16, 28], cross: [14, 24], throw_in: [7, 14], corner: [14, 24], free_kick: [12, 26], goal_kick: [14, 27]}` | ball speed ranges |
| `passing.goalkeeper_long_mult` | `3.0` | goalkeeper preference for long distribution |
| `passing.goal_kick_short_prob` | `0.45` | share of goal kicks played short |
| `pressure.base_prob` | `0.30` | per action chance of a pressure event at pressing 1.0 |
| `pressure.max_prob` | `0.90` | cap on pressure probability |
| `pressure.zone_factor` | `{own_third: 0.7, middle: 1.0, final_third: 1.3}` | pressing by ball zone (attacker frame) |
| `pressure.distance_m` | `[1.0, 6.0]` | presser distance range |
| `pressure.duration_ms` | `[500, 4000]` | pressure duration range |
| `pressure.tackle_attempt_prob` | `0.165` | tackle attempt chance given pressure |
| `pressure.tackle_win_prob` | `0.45` | tackle success |
| `pressure.quality_weight` | `1.0` | weight of team quality in tackle success |
| `foul.defender_foul_prob` | `0.40` | foul chance on a tackle attempt |
| `foul.box_foul_mult` | `0.10` | defenders are careful in their own box |
| `foul.offensive_foul_prob` | `0.009` | ball carrier foul chance per action |
| `foul.yellow_prob` | `0.155` | yellow card chance per foul |
| `foul.second_yellow_mult` | `0.17` | referees are slower to book a player already on a yellow |
| `foul.red_prob` | `0.0042` | straight red chance per foul |
| `shot.max_distance_m` | `34.0` | furthest distance shots are considered |
| `shot.distance_exponent` | `2.0` | how fast shot appetite falls off with distance |
| `shot.weight_scale` | `0.435` | overall shot appetite |
| `shot.block_prob` | `0.22` | blocked share of shots |
| `shot.off_target_base` | `0.20` | off target share at point blank |
| `shot.off_target_per_m` | `0.006` | extra off target share per metre |
| `shot.post_prob` | `0.02` | hit the woodwork |
| `shot.goal_near` | `0.455` | goal chance of an on-target shot at zero distance |
| `shot.goal_decay_m` | `15.0` | distance decay of goal chance |
| `shot.goal_min` | `0.03` | floor on goal chance |
| `shot.goal_max` | `0.85` | cap on goal chance |
| `shot.speed_ms` | `[14, 34]` | shot speed range |
| `shot.assist_window_ms` | `8000` | max gap between key pass and shot |
| `shot.header_prob` | `0.22` | chance a shot near goal is a header |
| `shot.header_zone_m` | `12.0` | distance from the byline counted as header range |
| `shot.after_saved` | `{corner: 0.28, keeper: 0.55, rebound: 0.10, defender: 0.07}` | what follows a save |
| `shot.after_blocked` | `{corner: 0.40, defender: 0.60}` | what follows a block |
| `shot.after_post` | `{rebound: 0.25, corner: 0.20, defender: 0.55}` | what follows a post hit |
| `shot.after_off_target` | `{goal_kick: 0.80, corner: 0.20}` | what follows a shot that misses (deflected misses give corners) |
| `penalty.outcome_weights` | `{goal: 0.88, saved: 0.08, off_target: 0.02, post: 0.02}` | penalty outcomes |
| `timing.action_ms` | `{short: [1600, 4400], forward: [2100, 5200], lateral: [1600, 4400], back: [1400, 4000], long: [2900, 6600], cross: [2200, 4800], goal_kick: [3000, 7000], shot: [3000, 7000], tackle: [1500, 3500]}` | time consumed per action |
| `timing.dead_ball_ms` | `{throw_in: [10000, 25600], corner: [22000, 50200], free_kick: [12000, 35000], goal_kick: [18000, 42800], keeper_hold: [4000, 12000], kickoff: [8000, 16000], foul: [6000, 15000], card: [15000, 40000], penalty: [110000, 190000], substitution: [50000, 102000], goal: [20000, 45000]}` | dead time before restarts (throw-in, goal kick, corner, penalty, substitution means follow 2025-26 league figures) |
| `timing.event_gap_ms` | `[200, 900]` | gap between events of one action |
| `bounds.pass_speed_ms` | `[1.0, 40.0]` | allowed pass ball speed |
| `bounds.shot_speed_ms` | `[5.0, 45.0]` | allowed shot speed |
| `stories.max_attempts` | `150` | re-simulations allowed to realize planted stories |
| `stories.random_max_stories` | `2` | most stories picked by --stories random |
| `stories.random_jitter_minutes` | `6` | random shift of default windows |
| `stories.defaults.momentum_swing` | `{start_minute: 15, end_minute: 45, strength: 0.8}` | default window and strength |
| `stories.defaults.pressing_spell` | `{start_minute: 20, end_minute: 34, strength: 0.8}` | default window and strength |
| `stories.defaults.late_comeback` | `{start_minute: 10, end_minute: 90, strength: 0.8}` | default window and strength |
| `stories.defaults.red_card_turning_point` | `{start_minute: 30, end_minute: 90, strength: 0.8}` | default window and strength |
| `stories.defaults.star_player_match` | `{start_minute: 10, end_minute: 85, strength: 0.8}` | default window and strength |
| `stories.defaults.quiet_then_chaos` | `{start_minute: 55, end_minute: 75, strength: 0.8}` | default window and strength |
| `stories.effects.momentum_swing` | `{completion: 0.08, shot: 0.8, press: 0.5, forward: 0.4}` | modifier sizes |
| `stories.effects.pressing_spell` | `{press: 1.8, opp_completion: -0.10, tackle_boost: 0.3}` | modifier sizes |
| `stories.effects.late_comeback` | `{setup_shot: 0.8, setup_finish: 0.15, shot: 1.2, finish: 0.2, completion: 0.05, tempo: 0.25, setup_fraction: 0.35, comeback_fraction: 0.35}` | modifier sizes |
| `stories.effects.red_card_turning_point` | `{pre_foul: 6.0, completion: -0.06, shot: -0.4, press: -0.4, opp_shot: 0.5, opp_completion: 0.04, opp_press: 0.3}` | modifier sizes |
| `stories.effects.star_player_match` | `{involvement: 4.0, finish: 0.10, completion: 0.05}` | modifier sizes |
| `stories.effects.quiet_then_chaos` | `{quiet_tempo: 1.5, quiet_shot: -0.9, quiet_press: -0.5, quiet_forward: -0.4, burst_shot: 2.5, burst_tempo: 0.3, burst_completion: 0.06, burst_press: 0.3, quiet_fraction: 0.6}` | modifier sizes |
| `stories.realization.momentum_min_share_gap` | `0.10` | min possession share gap between the two spells |
| `stories.realization.pressing_min_turnovers` | `4` | min ball wins in the opponent half in the window |
| `stories.realization.quiet_max_shots` | `1` | max shots in the quiet stretch |
| `stories.realization.chaos_min_shots` | `4` | min shots by the team in the burst |
| `stories.realization.star_min_touch_share` | `0.20` | min share of team touches for the star |
| `stories.realization.star_min_goals_plus_key_passes` | `2` | min goals plus key passes for the star |
| `stories.realization.red_card_min_minutes_after` | `8` | min minutes played after the red card |
| `stories.realization.red_card_min_share_drop` | `0.03` | min drop in pass share after the red card |
| `tracking.max_speed_ms` | `10.0` | fastest speed a player can reach |
| `tracking.speed_factor_range` | `[0.86, 1.0]` | per-player share of max speed |
| `tracking.max_accel_ms2` | `3.5` | largest change of velocity per second |
| `tracking.slot_speed_ms` | `3.0` | top speed when just holding formation |
| `tracking.lead_ms` | `5500` | minimum time a player starts moving before an event |
| `tracking.hold_ms` | `700` | time a player stays at the spot after an event |
| `tracking.ball_shift` | `1.0` | how far the team line follows the ball up the pitch |
| `tracking.attack_push_m` | `9.0` | extra forward shift of the team in possession |
| `tracking.defend_drop_m` | `10.0` | backward shift of the team out of possession |
| `tracking.wander_m` | `1.9` | size of small random drift of each player |
| `tracking.wander_period_s` | `[9.0, 18.0]` | seconds per drift cycle (shorter = busier off-ball movement) |
| `tracking.compact_x` | `0.62` | squeeze of the formation along the pitch (1 = textbook spacing) |
| `tracking.compact_y` | `0.92` | squeeze of the formation across the pitch |
| `tracking.y_follow` | `0.38` | how far the team shifts sideways with the ball |
| `tracking.out_compact_y` | `0.62` | sideways squeeze of the team without the ball |
| `tracking.out_compact_x` | `0.44` | lengthways squeeze of the team without the ball |
| `tracking.runs_per_match` | `{W: 56, ST: 56, AM: 48, CM: 38, FB: 38, DM: 24, CB: 12, GK: 0}` | forward off-ball runs per player in possession |
| `tracking.run_gain_m` | `[12.0, 22.0]` | how far a forward run goes |
| `tracking.run_dur_s` | `[3.0, 4.5]` | how long a run takes |
| `tracking.carry_touch_m` | `2.5` | how far the ball drifts from its spot while a player holds it |
| `game.home_shot_mult` | `1.12` | shot appetite multiplier for the home side |
| `game.home_completion_bonus` | `0.012` | pass completion bonus for the home side |
| `game.early_minutes` | `15` | length of the cautious opening spell |
| `game.early_shot_mult` | `0.65` | shot appetite in the opening spell |
| `game.second_half_shot_mult` | `1.90` | shot appetite in the second half versus the first |
| `game.late_ramp` | `0.10` | extra shot appetite reached at the end of the second half |
| `game.trailing_boost` | `0.28` | extra shot appetite per goal behind (up to 2) |
| `game.leading_cut` | `0.10` | lost shot appetite per goal ahead (up to 2) |
| `game.sub_shot_mult` | `0.82` | shot appetite of a player who came on as a substitute |
| `game.sub_involvement_mult` | `1.00` | ball involvement of a player who came on |

Values that are *not* listed are facts of the game or structure, not guesses: pitch dimensions
(105 m x 68 m, goal 7.32 m, penalty area 16.5 m x 40.32 m, spot 11 m), 45 minute halves,
formations, squad size (11 starters + 7 on the bench) and the 5 substitution maximum.

Also unresolved (owner decisions, not guessed by the generator): which Azure messaging service
to use for the stretch sink, and how many fictional clubs the demo league needs
(`competition.num_clubs` is only a default).

| Config key | Placeholder value | Controls |
|---|---|---|
| `competition.num_clubs` | `6` | demo league size (owner decision pending) |
| `match.stoppage_min_ms` | `60000` | minimum added time per half |
| `match.stoppage_max_ms` | `480000` | maximum added time per half |
| `match.stoppage_per_foul_ms` | `8000` | added time accrued per foul |
| `match.stoppage_per_card_ms` | `20000` | added time accrued per card |
| `match.stoppage_per_sub_ms` | `30000` | added time accrued per substitution |
| `match.stoppage_per_goal_ms` | `25000` | added time accrued per goal |
| `match.sub_count_range` | `[3, 5]` | substitutions each team makes (research: about 4 per team) |
| `match.sub_minute_range` | `[46, 85]` | when substitutions are scheduled |
| `team_style.attack_intensity` | `[0.9, 1.1]` | multiplier on shot appetite |
| `team_style.pressing_intensity` | `[0.8, 1.2]` | multiplier on pressing frequency |
| `team_style.buildup_directness` | `[0.2, 0.7]` | 0 patient, 1 direct |
| `team_style.quality` | `[-0.02, 0.02]` | additive pass completion edge |
| `player.skill_range` | `[0.35, 0.95]` | hidden player skill range |
| `player.involvement_range` | `[0.8, 1.2]` | hidden ball involvement range |
| `player.skill_pass_weight` | `0.10` | pass completion per unit of skill above 0.65 |
| `player.skill_finish_weight` | `0.15` | goal probability per unit of skill above 0.65 |
| `roles.anchor_x` | `{GK: 5, CB: 24, FB: 30, DM: 38, CM: 50, AM: 62, W: 72, ST: 85}` | typical own-half-relative x of each role |
| `roles.involvement` | `{GK: 0.5, CB: 0.9, FB: 1.0, DM: 1.1, CM: 1.2, AM: 1.2, W: 1.0, ST: 0.9}` | ball involvement by role |
| `roles.shot_mult` | `{GK: 0.0, CB: 0.3, FB: 0.4, DM: 0.6, CM: 0.9, AM: 1.2, W: 1.2, ST: 1.6}` | shooting appetite by role |
| `roles.anchor_spread_x` | `18.0` | how strictly players hold their x zone |
| `roles.lane_spread_y` | `16.0` | how strictly players hold their lane |
| `passing.base_weights` | `{short: 1.0, forward: 0.9, lateral: 0.5, back: 0.35, long: 0.31}` | relative pass type frequency |
| `passing.cross_weight` | `1.0` | crossing weight when wide in the final third |
| `passing.cross_min_x` | `72.0` | x from which crosses are considered |
| `passing.cross_wide_band_m` | `14.0` | distance from touchline counted as wide |
| `passing.length_m` | `{short: [5, 16], forward: [10, 28], lateral: [6, 22], back: [5, 22], long: [32, 58], goal_kick_short: [12, 24]}` | pass length ranges |
| `passing.completion` | `{short: 0.92, forward: 0.80, lateral: 0.93, back: 0.95, long: 0.58, cross: 0.32, throw_in: 0.85, corner: 0.38, free_kick: 0.62, goal_kick: 0.55}` | base completion by type |
| `passing.pressure_penalty` | `0.14` | completion lost under maximum pressure |
| `passing.failure_split` | `{intercepted: 0.42, incomplete: 0.32, out: 0.26}` | how failed passes fail |
| `passing.speed_ms` | `{short: [6, 14], forward: [8, 17], lateral: [6, 13], back: [6, 13], long: [16, 28], cross: [14, 24], throw_in: [7, 14], corner: [14, 24], free_kick: [12, 26], goal_kick: [14, 27]}` | ball speed ranges |
| `passing.goalkeeper_long_mult` | `3.0` | goalkeeper preference for long distribution |
| `passing.goal_kick_short_prob` | `0.45` | share of goal kicks played short |
| `pressure.base_prob` | `0.30` | per action chance of a pressure event at pressing 1.0 |
| `pressure.max_prob` | `0.90` | cap on pressure probability |
| `pressure.zone_factor` | `{own_third: 0.7, middle: 1.0, final_third: 1.3}` | pressing by ball zone (attacker frame) |
| `pressure.distance_m` | `[1.0, 6.0]` | presser distance range |
| `pressure.duration_ms` | `[500, 4000]` | pressure duration range |
| `pressure.tackle_attempt_prob` | `0.165` | tackle attempt chance given pressure |
| `pressure.tackle_win_prob` | `0.45` | tackle success |
| `pressure.quality_weight` | `1.0` | weight of team quality in tackle success |
| `foul.defender_foul_prob` | `0.40` | foul chance on a tackle attempt |
| `foul.box_foul_mult` | `0.10` | defenders are careful in their own box |
| `foul.offensive_foul_prob` | `0.009` | ball carrier foul chance per action |
| `foul.yellow_prob` | `0.155` | yellow card chance per foul |
| `foul.second_yellow_mult` | `0.17` | referees are slower to book a player already on a yellow |
| `foul.red_prob` | `0.0042` | straight red chance per foul |
| `shot.max_distance_m` | `34.0` | furthest distance shots are considered |
| `shot.distance_exponent` | `2.0` | how fast shot appetite falls off with distance |
| `shot.weight_scale` | `0.240` | overall shot appetite |
| `shot.block_prob` | `0.22` | blocked share of shots |
| `shot.off_target_base` | `0.20` | off target share at point blank |
| `shot.off_target_per_m` | `0.006` | extra off target share per metre |
| `shot.post_prob` | `0.02` | hit the woodwork |
| `shot.goal_near` | `0.435` | goal chance of an on-target shot at zero distance |
| `shot.goal_decay_m` | `15.0` | distance decay of goal chance |
| `shot.goal_min` | `0.03` | floor on goal chance |
| `shot.goal_max` | `0.85` | cap on goal chance |
| `shot.speed_ms` | `[14, 34]` | shot speed range |
| `shot.assist_window_ms` | `8000` | max gap between key pass and shot |
| `shot.header_prob` | `0.22` | chance a shot near goal is a header |
| `shot.header_zone_m` | `12.0` | distance from the byline counted as header range |
| `shot.after_saved` | `{corner: 0.28, keeper: 0.55, rebound: 0.10, defender: 0.07}` | what follows a save |
| `shot.after_blocked` | `{corner: 0.40, defender: 0.60}` | what follows a block |
| `shot.after_post` | `{rebound: 0.25, corner: 0.20, defender: 0.55}` | what follows a post hit |
| `shot.after_off_target` | `{goal_kick: 0.80, corner: 0.20}` | what follows a shot that misses (deflected misses give corners) |
| `penalty.outcome_weights` | `{goal: 0.88, saved: 0.08, off_target: 0.02, post: 0.02}` | penalty outcomes |
| `timing.action_ms` | `{short: [1600, 4400], forward: [2100, 5200], lateral: [1600, 4400], back: [1400, 4000], long: [2900, 6600], cross: [2200, 4800], goal_kick: [3000, 7000], shot: [3000, 7000], tackle: [1500, 3500]}` | time consumed per action |
| `timing.dead_ball_ms` | `{throw_in: [10000, 25600], corner: [22000, 50200], free_kick: [12000, 35000], goal_kick: [18000, 42800], keeper_hold: [4000, 12000], kickoff: [8000, 16000], foul: [6000, 15000], card: [15000, 40000], penalty: [110000, 190000], substitution: [50000, 102000], goal: [20000, 45000]}` | dead time before restarts (throw-in, goal kick, corner, penalty, substitution means follow 2025-26 league figures) |
| `timing.event_gap_ms` | `[200, 900]` | gap between events of one action |
| `bounds.pass_speed_ms` | `[1.0, 40.0]` | allowed pass ball speed |
| `bounds.shot_speed_ms` | `[5.0, 45.0]` | allowed shot speed |
| `stories.max_attempts` | `150` | re-simulations allowed to realize planted stories |
| `stories.random_max_stories` | `2` | most stories picked by --stories random |
| `stories.random_jitter_minutes` | `6` | random shift of default windows |
| `stories.defaults.momentum_swing` | `{start_minute: 15, end_minute: 45, strength: 0.8}` | default window and strength |
| `stories.defaults.pressing_spell` | `{start_minute: 20, end_minute: 34, strength: 0.8}` | default window and strength |
| `stories.defaults.late_comeback` | `{start_minute: 10, end_minute: 90, strength: 0.8}` | default window and strength |
| `stories.defaults.red_card_turning_point` | `{start_minute: 30, end_minute: 90, strength: 0.8}` | default window and strength |
| `stories.defaults.star_player_match` | `{start_minute: 10, end_minute: 85, strength: 0.8}` | default window and strength |
| `stories.defaults.quiet_then_chaos` | `{start_minute: 55, end_minute: 75, strength: 0.8}` | default window and strength |
| `stories.effects.momentum_swing` | `{completion: 0.08, shot: 0.8, press: 0.5, forward: 0.4}` | modifier sizes |
| `stories.effects.pressing_spell` | `{press: 1.8, opp_completion: -0.10, tackle_boost: 0.3}` | modifier sizes |
| `stories.effects.late_comeback` | `{setup_shot: 0.8, setup_finish: 0.15, shot: 1.2, finish: 0.2, completion: 0.05, tempo: 0.25, setup_fraction: 0.35, comeback_fraction: 0.35}` | modifier sizes |
| `stories.effects.red_card_turning_point` | `{pre_foul: 6.0, completion: -0.06, shot: -0.4, press: -0.4, opp_shot: 0.5, opp_completion: 0.04, opp_press: 0.3}` | modifier sizes |
| `stories.effects.star_player_match` | `{involvement: 4.0, finish: 0.10, completion: 0.05}` | modifier sizes |
| `stories.effects.quiet_then_chaos` | `{quiet_tempo: 1.5, quiet_shot: -0.9, quiet_press: -0.5, quiet_forward: -0.4, burst_shot: 2.5, burst_tempo: 0.3, burst_completion: 0.06, burst_press: 0.3, quiet_fraction: 0.6}` | modifier sizes |
| `stories.realization.momentum_min_share_gap` | `0.10` | min possession share gap between the two spells |
| `stories.realization.pressing_min_turnovers` | `4` | min ball wins in the opponent half in the window |
| `stories.realization.quiet_max_shots` | `1` | max shots in the quiet stretch |
| `stories.realization.chaos_min_shots` | `4` | min shots by the team in the burst |
| `stories.realization.star_min_touch_share` | `0.20` | min share of team touches for the star |
| `stories.realization.star_min_goals_plus_key_passes` | `2` | min goals plus key passes for the star |
| `stories.realization.red_card_min_minutes_after` | `8` | min minutes played after the red card |
| `stories.realization.red_card_min_share_drop` | `0.03` | min drop in pass share after the red card |
| `tracking.max_speed_ms` | `10.0` | fastest speed a player can reach |
| `tracking.speed_factor_range` | `[0.86, 1.0]` | per-player share of max speed |
| `tracking.lead_ms` | `5500` | minimum time a player starts moving before an event |
| `tracking.hold_ms` | `700` | time a player stays at the spot after an event |
| `game.home_shot_mult` | `1.12` | shot appetite multiplier for the home side |
| `game.home_completion_bonus` | `0.012` | pass completion bonus for the home side |
| `game.early_minutes` | `15` | length of the cautious opening spell |
| `game.early_shot_mult` | `0.65` | shot appetite in the opening spell |
| `game.second_half_shot_mult` | `1.90` | shot appetite in the second half versus the first |
| `game.late_ramp` | `0.10` | extra shot appetite reached at the end of the second half |
| `game.trailing_boost` | `0.28` | extra shot appetite per goal behind (up to 2) |
| `game.leading_cut` | `0.10` | lost shot appetite per goal ahead (up to 2) |
| `game.sub_shot_mult` | `0.82` | shot appetite of a player who came on as a substitute |
| `game.sub_involvement_mult` | `1.00` | ball involvement of a player who came on |
