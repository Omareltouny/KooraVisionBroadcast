# 04. Narrative, multi-language, render (strand report)

Date 2026-10-19. All web sources accessed 2026-10-19; cited as [Sn] (list at the end). "Not found" means I looked and the page did not say. Names and numbers in examples are invented (fictional league). Arabic and Spanish example strings are drafts and need native review. Design values marked **(design)** are my proposals, not sourced facts.

Inputs read: `docs/README.md`, `schema/*.json`. Relevant facts: events carry `seq`, `match_clock_ms`, `period`, running `score_home/away`, `player_id`, `outcome`, `body_part`, `shot_speed_ms`, `assist_event_id`; `teams.json` has `name_i18n` (en, ar, es); `ground_truth.stories[].description` is English only. The Microsoft/Premier League announcement mentions "real-time data overlays" and answers "in fans' native languages through text and audio translation" [S9]. It says nothing about broadcast graphics tooling or a rendering partner. The hackathon page [S10] does not mention one either. **I make no claim about the unnamed rendering partner**; section C lists what to ask.

---

## A. Narrative architecture

### A1. Template vs LLM vs hybrid

| Option | Strength | Weakness | Effort | Risk |
|---|---|---|---|---|
| Templates/grammar only | Deterministic, offline, ms latency, numbers exact | Repetitive; per-language grammar work | M | Low; looks robotic |
| LLM free text from stats | Fluent, varied | Invents or mis-copies numbers; research on neural data-to-text finds weak content selection and templated baselines beating neural models on some metrics [S40] | S | High for a "numbers never invented" rule |
| **Hybrid (recommended)** | Fluent where it is safe, exact where it matters, offline fallback | Two code paths, a verifier to build | M-L | Low-Med |

**Recommended hybrid ("slot-locked generation"):**
1. Interpret emits **fact packets**: `{fact_id, kind, slots:{...typed values...}, source_event_ids, importance}`. Example: `F7 kind=goal slots={scorer:p_09, team:t_02, minute:67, score:[1,1], body_part:"head", assist:p_14}`.
2. **Realiser A (always on, no LLM):** per-language template per `kind` with plural/gender variants. Numbers and names come only from slots, formatted by the locale layer.
3. **Realiser B (optional LLM "stylist"):** receives only the fact packets plus a glossary and tone card. It returns sentences as **text with slot placeholders**, e.g. `"{scorer} levels it with a header on {minute}'."` plus `cites:["F7"]`. Code substitutes slot values. The model never writes a digit or a name. With strict structured outputs, Azure enforces the JSON shape [S1].
4. **Verifier (mandatory, both realisers):** extract every number, name and club from the final string and check each against the allowed set built from the cited facts (all locale renderings of each value, including Arabic-Indic digits if enabled). Also check: every `cite` exists, no placeholder is left unfilled, the length budget holds. Any failure falls back to Realiser A for that item and is logged.
5. Claims about *why* (explain stage) must also be fact packets (`kind=momentum_shift`, with its supporting numbers). The LLM may not add causal claims that are not a fact packet.

### A2. Output types

| Output | Length | Tone | Timing / trigger | Path |
|---|---|---|---|---|
| Live caption | 6-14 words, one line, at most 42 chars/line, 2 lines max (subtitle norms [S23][S26]) | Neutral, present tense | Event `seq` + 0-1 s | Templates only |
| Milestone alert | Headline of at most 5 words plus one 10-word line | Punchy | On triggering event | Templates |
| Half-time summary | 3-5 sentences, ~70-90 words | Studio, balanced | At `period_end` of period 1, pre-composed 30 s earlier | Hybrid |
| Full-time recap | 120-180 words, 5-7 sentences | Report style, score first | At final `period_end` | Hybrid |
| Player report | 40-60 words plus a stat strip | Fan-friendly, favourite-player aware | On demand or at the sub / half / full | Hybrid |
| Analyst deep dive | 150-250 words, bullets with numbers | Dry, definitional | On demand | Hybrid, definitions from Interpret |

(Word and sentence counts are **(design)**.)

Examples against our vocabulary (invented names):
- Caption (`shot`, outcome `goal`, `body_part=head`, clock 4032000 ms, scores 1-1): "67' GOAL. Amir Haddad heads it in. 1-1."
- Alert (`card`, red): "RED CARD. Luis Ferrer sent off, 10 v 11." (10 v 11 is a count derived by Interpret from cards, listed as a fact.)
- Milestone: "Haddad's second shot on target tonight." The count is a fact computed from events; the template only prints it.
- Half-time: "Harbour United lead 1-0 at the break. They had 58% of the ball (possession_pct from stats) but Dunes FC had more shots on target, 3 to 2. The pressing spell from the 31st minute is why." The last clause appears only if a `pressing_spell` fact exists.
- Full-time: score, scorers with minutes, the key swing, one team stat contrast, one standout player.
- Player report: "Haddad: 41 touches, 2 shots, 1 goal, 84% pass completion."
- Analyst: "Pressures in the 55-70' window: 14 vs 6 earlier. Pass completion fell from 86% to 71% under pressure (events with `pressure` on the ball carrier)." Definitions are stated in a footnote because the generator's tackle and pressure definitions are open design parameters.

Clock text: format `match_clock_ms` using `periods[].scheduled_duration_ms` to produce "45+2'" for stoppage (**design**).

### A3. Azure OpenAI / Foundry fit (from current docs)
- **Structured outputs:** `response_format: json_schema` with `strict: true`. All properties required, `additionalProperties:false` on every object, at most 100 properties and 5 nesting levels. `minLength`, `maxLength`, `pattern`, `minItems`, `maxItems` and `minimum/maximum` are **not** supported, so length limits must be checked in code. The page lists models up to gpt-4.1, o3 and o4-mini and GA API `2024-10-21` [S1]. The current model list on Azure is much longer, including GPT-5.x and later families [S5]. **Per-model structured-output support for newer models: not confirmed; verify when deploying.**
- **Deployments:** Global Standard has the highest default quota but "greater latency variability" under high consistent volume. Provisioned types give "lower and more consistent latency". Batch has a 24 h target and no real-time SLA, with a 50% discount. Data Zone types keep processing inside US/EU/APAC [S2]. For a hackathon, Global Standard or Standard is enough; Batch suits pre-generating recaps for many matches.
- **Latency model:** `TTLT = TTFT + TBT x tokens generated`. Output tokens dominate, so set `max_tokens` low and keep outputs short. Streaming helps chat more than bulk generation [S4]. No absolute latency figures are published there (not found).
- **Content safety:** all four harm categories default to Medium threshold; blocked requests return HTTP 400 with `content_filter`. Classifiers are trained and tested in English, German, Japanese, Spanish, French, Italian, Portuguese and Chinese, and **Arabic is not in that list**, so test Arabic yourselves [S3]. Filtering adds latency [S4]. Handle the 400 as a fallback trigger, not an error.
- **No-LLM fallback:** Realiser A + verifier. A `--narrative-mode templates|hybrid` flag. A cache of LLM outputs keyed by hash of (fact packets, glossary version, prompt version) lets the recorded demo replay offline.
- **Live latency/cost:** keep the LLM out of the per-event path. Captions and alerts are templates (microseconds). LLM calls happen at four moments per match (half-time, full-time, plus player/analyst on demand) and run async with a template result shown first and replaced if the LLM version passes the verifier. Cost: per-token prices not fetched (not found); estimate by (tokens in + out) x calls, and cache.

Decision table: A-generation = {templates / LLM / hybrid} -> hybrid, L effort for full, M for first cut, risk Med. A-hosting = {Azure OpenAI Global Standard / Provisioned / local small model} -> Global Standard, S, risk Low-Med (quota variability).

---

## B. Multi-language

### B1. Which languages
| Option | Languages | Rationale | Effort | Risk |
|---|---|---|---|---|
| **Ship now (recommended)** | en, ar (Modern Standard), es | Already in `name_i18n`; covers LTR+RTL and two plural systems; Microsoft says fans get answers "in native languages" [S9] | M | Low |
| Tier 2 | fr, pt-BR, then zh-Hans / ja / ru / id / ko | The IFAB publishes the Laws in 13 languages, a usable proxy for football-relevant locales [S36]; each needs names added to `name_i18n` | M each | Med |
| Many via MT | 20+ | Breadth, poor control of numbers | S | High |

Regional variants: Spanish decimal comma (Spain) vs point (Latin America) [S25]; Netflix Arabic guidance is Modern Standard only, no dialect [S24]. Use `es` neutral with an `es-ES` / `es-MX` override and `ar` MSA.

### B2. Generate per language vs translate
| Option | Notes | Effort | Risk |
|---|---|---|---|
| **Generate per language from the same fact packets (recommended)** | Numbers/names are slots, so the verifier is identical across languages; plural/gender handled per language. Arabic has six CLDR plural categories (zero, one, two, few, many, other) [S33] | M | Med (needs per-language templates) |
| Generate English then machine-translate | Cheap; Translator has 50,000 chars per request, 2M chars/hour on the free tier, 15 s max latency (standard models) [S6]; unsuitable for the live path | S | High: digits, names, terminology drift |
| LLM writes each language directly | Good fluency; verifier and glossary catch errors | S | Med; Arabic filter coverage unknown [S3] |

Recommendation: templates (live items) and slot-locked LLM (long-form) directly per language; use Azure Translator only as a **back-translation test tool**. The dynamic dictionary is documented as "safe only for compound nouns like proper names and product names", requires an English pair and an explicit `from` language [S7], so it is not a football-glossary solution.

### B3. Glossary (no ready open glossary found)
Found, with constraints:
- IFAB Laws of the Game exist in Arabic and Spanish [S36][S37]. The Arabic edition forbids reissue or translation without permission and states English prevails [S37]. Use it **only to verify terms internally**, never copy it into the repo.
- A 2012 Arabic-Spanish football lexicon article (CC BY-NC-ND 3.0) [S38]; ND means do not derive a glossary from it, only consult.
- A 297-term multilingual soccer list exists for South African languages [S39]. Not relevant to en/ar/es, but it shows a term-list format.
- A published open en/ar/es football glossary with a usable licence: **not found**.

Proposed format, `i18n/glossary/football.tsv` (one row per term x language):
`term_id | lang | surface | pos | gender | plural_forms | register(live|studio|analyst) | definition_ref | source_url | licence | reviewer | status(draft|verified)`
`term_id` examples: `shot.on_target`, `card.red`, `pressure.event`, `possession.pct`, `substitution`. Build: (1) derive the term list from the event types and outcome enums in `event.schema.json` (about 40 terms); (2) a native-speaker author writes entries; (3) verify against IFAB text and two public sources; (4) a CI test fails if a template uses a term_id missing or `draft` for a shipped language.

### B4. Right-to-left (Arabic) implications
- Numbers still run left-to-right inside RTL text; European digits and Eastern Arabic-Indic digits are bidi class EN, Arabic-Indic digits AN, so ordering can differ by digit type [S31]. Digit forms vary by region (European digits in Maghreb; Arabic-Indic in Egypt, Saudi, Iraq) [S31]. Recommendation: default to Latin digits for the demo with a `digits` style flag; check resolved digits with `resolvedOptions().numberingSystem` [S34].
- Neutrals (spaces, punctuation) and numbers next to a Latin name can jump sides; the fix is to set base direction and isolate adjacent runs [S32]. Wrap every inserted name and number in an isolate (`<bdi>` or `dir` with `unicode-bidi: isolate`; the W3C article cited does not itself describe `bdi`, so confirm in a second source).
- Layout: mirror lower thirds (logo/flag side, text alignment) using CSS logical properties; clock and score digits stay LTR. Arabic line breaks must not split verb from subject or noun from modifier [S24].

### B5. Locale formatting
Use `Intl.NumberFormat`, `Intl.PluralRules`, `Intl.DateTimeFormat` in the browser and Babel (Python) server-side. `ar-EG` yields Arabic-Indic digits by default; `-u-nu-latn` forces Latin digits [S34]. Arabic in Netflix guidance: percent spelled out, thousands comma, 12-hour time [S24] (that is subtitle style, not a rule for overlays). Clock text ("67'") is a symbol, not a localized number; keep Latin digits there (design).

### B6. Name handling
Resolve with `name_i18n[locale] -> name_i18n[lang] -> name`. Never machine-translate names. Verifier compares against the whole `name_i18n` set. Short forms (surname only for captions): add `short_i18n` optional field to the data (proposal; not in the current schema).

### B7. Evaluation
(1) Number/name consistency check (automatic, 100% of outputs). (2) Glossary compliance (term_id surface present, no banned variants). (3) Back-translation by Azure Translator, then compare numbers, names and fact_ids (informational). (4) Length/CPS check (D). (5) Native-reader sample: 30 sentences per language, two raters, 1-5 on accuracy/fluency/register, gate at mean >= 4 **(design)**. (6) Content-filter smoke test in Arabic.

### B8. Azure options and limits
Translator limits as above [S6]; custom models 3,600 chars/sec/model, 120 s max latency [S6]. Speech-to-text lists 18 Arabic and 22 Spanish locales [S8]. Text-to-speech voice availability for ar/es: **not found** on the page I could read. LLM speech translation lists Spanish but not Arabic [S8]. Treat speech as a stretch goal.

### B9. `description_i18n` in ground truth
Add optional `description_i18n: {"en":..., "ar":..., "es":...}` to `StoryTruth`; keep `description` as the English alias and validate `description_i18n.en == description`. Generate from the same fact templates as the narrative (story `type` + `details`), reviewed once by native speakers (6 story types x 3 languages = 18 strings; effort S). Add `facts` ids so number checks can reuse `details`. Use it for evaluation only (as today).

---

## C. Render / overlays

### C1. What public sources say
- **CasparCG HTML templates:** page calls `play()`, `stop()`, `next()`, `update(data)`; JSON data supported in server 2.1.0b1+ [S11]. The HTML producer loads a hosted page that "can't be controlled by CasparCG" [S12]. Key/fill, frame rate and alpha behaviour for CasparCG: not found on those pages.
- **Singular Data Stream API:** websocket, "latency below 300 ms", for updates at 1 Hz or faster; payload persists until replaced; new clients receive the latest payload; payloads carry a UTC timestamp; the REST API takes about a second [S13]. Payload schema: not found.
- **Viz (Trio Datacenter):** key/value data from files (JSON among them), live scoreboard feeds, or other Datacenters, pushed to Viz Engine receivers over UDP shared memory; monitored files update graphics on save [S18]. Flowics is described as cloud HTML5 graphics fed by sports-data connectors [S19]; its transport and latency are not stated.
- **Key and fill:** SDI cannot carry alpha, so key and fill go on separate channels and are recombined [S17].
- **SMPTE ST 2110-40:** ancillary data (captions, timecode, metadata) as RTP, timestamps derived from video fields, all streams on a common reference clock [S14]. This is the layer where frame-accurate metadata lives; an overlay data feed in a hackathon cannot assume it.
- **OBS Browser Source:** CEF-based, transparent background by default, custom FPS default 30 [S16]; hence an HTML overlay page can be captured or keyed over a feed.
- **Safe areas:** EBU R 95 sets action safe at 3.5% and graphics safe at 5% per side (7% and 10% of the full image) [S15].
- **Latency context:** typical TV broadcast latency 10-30 s; HLS 9+ s; WebRTC sub-second (vendor figures) [S20]. So overlay timing must be tied to the *video's* timeline, not to wall-clock arrival.

### C2. Timing model options
| Option | Description | Effort | Risk |
|---|---|---|---|
| **Match-clock based (recommended)** | Messages stamped with `start_ms`/`end_ms` on the match clock plus `seq`; renderer maps to the feed through a `sync_offset_ms` | S | Low; offset needed for real feeds |
| Wall-clock (UTC) | Like Singular's UTC timestamps [S13] | S | Med; breaks with stream delay |
| Frame/timecode accurate | ST 2110-40 style [S14] | L | High; needs partner infrastructure |

### C3. Questions to ask the platform/rendering partner (assume nothing)
1. Accepted input: HTML5 template, JSON over WebSocket/REST, or a proprietary format? 2. Trigger model: frame-accurate/timecode or time-based? What reference clock? 3. Allowed end-to-end latency and who owns feed delay compensation? 4. Key and fill vs HTML composite; resolution and frame rate (1080p/25-50?). 5. Safe-area policy; font and brand rules; i18n/RTL support. 6. Max concurrent graphics, layers/channels, and who arbitrates collisions. 7. Message acknowledgement/retry and whether state is persistent (Singular-style) or one-shot. 8. Are Arabic and Spanish fonts licensed for their pipeline? 9. Do they cap payload size?

### C4. Overlay message schema (v0, JSON)
```json
{
  "schema": "kv.overlay/0.1",
  "overlay_id": "ov_000231",
  "rev": 1,
  "op": "show",
  "type": "lower_third",
  "start_ms": 4032000, "end_ms": 4040000,
  "start_seq": 981, "end_seq": 981,
  "min_on_screen_ms": 3500, "ttl_ms": 8000,
  "priority": 90,
  "collision_group": "lower_third_main",
  "audience": ["all", "analyst", "fav_team:t_02"],
  "payload": {"headline_key": "goal", "player_id": "p_09", "team_id": "t_02", "score": [1,1], "clock": "67'"},
  "text": {"en": {"headline": "GOAL", "line": "Amir Haddad heads it in. 1-1."},
           "ar": {"headline": "هدف", "line": "..."},
           "es": {"headline": "GOL", "line": "..."}},
  "style": {"theme": "team", "accent": "#D55E00", "anim_in": "slide", "anim_out": "fade", "safe_area": "graphics"},
  "source_event_ids": ["e_000981"],
  "fact_ids": ["F7"]
}
```
- `type` enum: `lower_third`, `stat_card`, `momentum_bar`, `player_tag`, `pitch_map`, `alert`, `ticker`, `score_bug`.
- `op`: `show` | `update` (same `overlay_id`, higher `rev`) | `hide`.
- A separate `{"type":"clock_sync","match_clock_ms":...,"seq":...}` message gives the renderer an anchor.
- Text per language is pre-rendered (the renderer never formats numbers), with `dir` implied by language; `fact_ids` link to the verifier.

### C5. Example: 10 seconds (match clock 66:56 to 67:06), JSONL, abridged
```
{"t":4016000,"type":"clock_sync","seq":975,"match_clock_ms":4016000}
{"t":4016400,"overlay_id":"ov_229","op":"show","type":"player_tag","start_ms":4016400,"end_ms":4020400,"priority":30,"collision_group":"tag","payload":{"player_id":"p_14"},"text":{"en":{"line":"Noor Karim, 8"}}}
{"t":4025000,"overlay_id":"ov_230","op":"show","type":"momentum_bar","start_ms":4025000,"end_ms":4040000,"priority":20,"collision_group":"momentum","payload":{"home":0.38,"away":0.62}}
{"t":4032000,"overlay_id":"ov_231","op":"show","type":"alert","start_ms":4032000,"end_ms":4040000,"priority":90,"collision_group":"lower_third_main","text":{"en":{"headline":"GOAL","line":"Amir Haddad heads it in. 1-1."}}}
{"t":4032000,"overlay_id":"ov_232","op":"update","type":"score_bug","rev":2,"payload":{"score":[1,1],"clock":"67'"}}
{"t":4033200,"overlay_id":"ov_229","op":"hide"}
{"t":4036000,"overlay_id":"ov_233","op":"show","type":"stat_card","start_ms":4040000,"end_ms":4048000,"priority":50,"collision_group":"lower_third_main","text":{"en":{"line":"Haddad: 2nd shot on target"}}}
```
`ov_233` is deferred to 4040000 so it queues behind the higher-priority alert in the same collision group instead of replacing it.

### C6. Output transports for the demo
| Option | Pros | Cons | Effort | Risk |
|---|---|---|---|---|
| JSON file stream (JSONL) | Simplest, deterministic, diffable | Not "live" by itself | S | Low |
| WebSocket | Bidirectional; matches Singular-style [S13] | Classic API lacks backpressure [S22]; more moving parts | M | Med |
| SSE | One-way push, auto-reconnect with `Last-Event-ID` and `id` field [S21] | Needs small server | S-M | Low |
| **HTML/Canvas overlay page replaying the JSONL (recommended)** | Looks broadcast-like, records cleanly via OBS Browser Source (transparent) or screen capture [S16], same JSON later swapped to WebSocket/SSE/CasparCG `update()` [S11] | Needs a video or synthetic pitch under it | M | Low |

Recommendation: one static page `overlay_web/` that reads `overlay.jsonl` (or an SSE URL) and drives a local clock, with a synthetic pitch animation behind it to look like a feed. The file path is the always-works demo path; SSE is the optional "live" path; WebSocket only if the partner asks.

---

## D. Visual rules for a moving feed

Sourced numbers:
- Reading speed ceilings, adult programmes: English 20 cps (children 17); Spanish 17 cps; Arabic 20 cps (SDH 23); 42 characters/line, 2 lines max [S24][S25][S26]. Subtitle event duration: min 5/6 s, max 7 s [S23]. BBC guidance (secondary summary): 160-180 wpm, roughly 0.3 s per word minimum, min gap between captions 1.5 s [S27].
- WCAG: text contrast at least 4.5:1; large text (18 pt or 14 pt bold) 3:1 [S28]. No more than three flashes in any one second [S29].
- Graphics-safe area: 5% each side [S15].
- Colour-blind-safe palette: Okabe-Ito colours (orange E69F00, sky blue 56B4E9, bluish green 009E73, yellow F0E442, blue 0072B2, vermilion D55E00, reddish purple CC79A7) [S30, secondary hex source; palette attributed to Okabe and Ito].

Rules I propose **(design, unsourced thresholds)**:
| Rule | Value | Alternatives | Rec |
|---|---|---|---|
| Min on-screen time | `max(2500 ms, chars / 17 cps + 800 ms)`, cap 7 s | lower cps for ar | Use 17 cps for all languages (the lowest sourced) |
| Frequency cap | At most 1 new lower-third / 8 s, at most 3 overlays visible at once | none sourced | Adopt, make configurable |
| Priority | alert 90 > milestone 70 > stat card 50 > tag 30 > ticker 10; a higher priority preempts only after `min_on_screen_ms` of the shown one, except red card and goal | strict FIFO | Adopt |
| Collision | One item per `collision_group`; others queue, expire after `ttl_ms` | stack | Adopt |
| Motion | Entry/exit 250-400 ms, no flashing | none | Adopt; obey <=3 flashes/s |
| Contrast | Text 4.5:1 against its own plate, never directly over video | none | Adopt; test with team colours |
| Colour use | Pair colour with icon/label; use Okabe-Ito accents | team colours only | Adopt |
| Text size | Do not publish a pixel size; test legibility at 1080p and at a phone-width crop | none sourced (not found) | Test, then fix |
| RTL | Mirror layout; Latin names isolated | none | Adopt |

---

## E. Effort and layout

| Work item | Effort | Risk |
|---|---|---|
| Fact packets + Interpret hooks (shared with other strands) | M | Med |
| Template realiser en/ar/es + plural/gender | M | Med |
| Verifier (numbers/names/cites) | S | Low |
| LLM stylist via Azure (slot-locked, cached) | M | Med |
| Glossary (TSV, about 40 terms x 3 languages, native review) | M | Med |
| `description_i18n` in ground truth | S | Low |
| Overlay scheduler (priority, collision, TTL) | M | Med |
| HTML overlay page + RTL + recording | M | Low |
| SSE/WebSocket server | S/M | Low |
| Native-reader evaluation | S | Low |

Recommended layout (new top-level packages beside `eventgen/`):
```
narrative/
  facts.py            # FactPacket dataclasses, kinds enum
  templates/{en,ar,es}.yaml
  realise.py          # template realiser
  llm_stylist.py      # Azure client, strict JSON schema, cache
  verify.py           # number/name/cite checker
  clock.py            # 67' / 45+2' formatting
i18n/
  glossary/football.tsv
  names.py            # name_i18n resolution
  fmt.py              # Babel/Intl-equivalent number/plural/date helpers
  checks/             # glossary compliance, CPS checks
overlay/
  schema/overlay.schema.json
  scheduler.py        # priority, collisions, ttl, min on-screen
  emit.py             # JSONL, SSE
overlay_web/          # static page: overlay.html, overlay.js, themes, fonts (RTL)
docs/design/ narrative.md  overlay-schema.md
tests/ narrative/ i18n/ overlay/
```

## Not found
Open en/ar/es football glossary with usable licence; rendering-partner details; Azure per-token prices; Azure absolute latency figures; Speech TTS voice availability for ar/es; CasparCG key/fill details; Singular payload schema; per-model structured-output support for the newest Azure models; sourced broadcast text-size minima; sourced frequency caps; CLDR Spanish plural rule text (page was truncated).

## Sources (all accessed 2026-10-19)
- S1 https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/structured-outputs
- S2 https://learn.microsoft.com/azure/foundry/foundry-models/concepts/deployment-types
- S3 https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/default-safety-policies
- S4 https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/latency
- S5 https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure
- S6 https://learn.microsoft.com/en-us/azure/ai-services/translator/service-limits
- S7 https://learn.microsoft.com/sk-sk/azure/ai-services/translator/text-translation/how-to/use-dynamic-dictionary
- S8 https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support
- S9 https://news.microsoft.com/source/2025/07/01/premier-league-and-microsoft-announce-five-year-strategic-partnership-to-personalize-the-fan-experience-with-ai-for-1-8-billion-people/
- S10 https://developer.microsoft.com/en-us/reactor/events/27536/
- S11 https://casparcg.com/docs/wiki/media/html-templates
- S12 https://casparcg.com/docs/wiki/server/producers/html-producer
- S13 https://developer.singular.live/data-stream-api/introduction
- S14 https://www.thebroadcastbridge.com/content/entry/20879/standards-part-20-st-2110-4x-metadata-standards
- S15 https://tech.ebu.ch/publications/r095
- S16 https://obsproject.com/kb/browser-source
- S17 https://mimolive.com/user-manual/sources-input/key-fill-source/
- S18 https://docs.vizrt.com/viz-trio-guide/4.1/Datacenter.html
- S19 https://www.vizrt.com/news-articles/sports/betql-viz-flowics-sports-betting-data-integration
- S20 https://optiview.dolby.com/resources/blog/sports/low-latency-sports-streaming/ (vendor)
- S21 https://html.spec.whatwg.org/multipage/server-sent-events.html
- S22 https://developer.mozilla.org/en-US/docs/Web/API/WebSocket
- S23 https://partnerhelp.netflixstudios.com/hc/en-us/articles/215758617-Timed-Text-Style-Guide-General-Requirements
- S24 https://partnerhelp.netflixstudios.com/hc/en-us/articles/215517947-Arabic-Timed-Text-Style-Guide
- S25 https://partnerhelp.netflixstudios.com/hc/en-us/articles/217349997-Spanish-Latin-America-Spain-Timed-Text-Style-Guide
- S26 https://partnerhelp.netflixstudios.com/hc/en-us/articles/217350977-English-Timed-Text-Style-Guide
- S27 https://clevercast.com/bbc-subtitling-guidelines (secondary summary of BBC guidelines)
- S28 https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
- S29 https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html
- S30 https://conceptviz.app/blog/okabe-ito-palette-hex-codes-complete-reference (hex, secondary); https://jfly.uni-koeln.de/color/ (original palette)
- S31 https://www.w3.org/TR/alreq/
- S32 https://www.w3.org/International/articles/inline-bidi-markup/uba-basics
- S33 https://unicode.org/cldr/charts/44/supplemental/language_plural_rules.html
- S34 https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/NumberFormat
- S36 https://theifab.com/documents
- S37 https://downloads.theifab.com/downloads/laws-of-the-game-202627-arabic-double-pages?l=en
- S38 https://rodin.uca.es/handle/10498/15489
- S39 https://repo.sadilar.org/items/29ed91c9-bf2b-4d40-9ade-73c8f9dbc5ce/full
- S40 https://ar5iv.labs.arxiv.org/html/1707.08052
