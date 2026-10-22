# KooraVision agents

Turns a match's events (and tracking, when present) into short, fact-checked stories in English, Arabic and
Spanish, for two audiences: **broadcast** (producers, highlights editors, lower-thirds) and **fans** (a push
and feed per fan, voiced for or against their club, in their language).

## The workflow (Microsoft Agent Framework)

```
Interpret -> Explain -> Narrate -> Verify -+-> Broadcast desk -+-> Publish
                                           +-> Fan desk -------+
```

Built with `agent-framework-core` (Microsoft Agent Framework, open source, free): each agent is an `Executor`
with one handler, wired with `WorkflowBuilder` (chain, fan-out, fan-in). Every handoff is written to
`trace.json` together with the framework's own executor events. Without the package the same agents run in a
plain loop; a test checks both engines give identical output.

| Agent | Job | Uses a model? |
|---|---|---|
| Interpret | Finds moments in the events: goals (with equaliser, go-ahead, winner flags), comebacks, red cards, big saves, missed penalties, pressing spells, star performances, super-subs, full time. Scores importance 0..1. | No (explicit rules) |
| Explain | Works out *why*: counter-attack, set piece, high press win, long build-up, header, long range, penalty. Collects the only numbers and names the writers may use (a closed fact packet). With tracking: how many of the scorer's team were in the box. | No |
| Narrate | Writes each moment in en/ar/es and four voices (broadcast, fan_for, fan_against, fan_neutral) from templates. Optionally asks a model to restyle the important ones. | Optional |
| Verify | Fact-checks every text: each number must be in the packet, no player or club name outside the packet, main actor named, length bounded. A model draft that fails is dropped and the template stays. | No |
| Broadcast desk | Neutral voice, a lower-third line (70 characters), tier A/B/C. | No |
| Fan desk | Per profile: language, voice for/against by club, feed vs push (at most 6 pushes). | No |

Why more than one agent: the writer cannot grade its own work. Verify is a separate agent with a veto, and the
Explain agent hands Narrate a closed list of facts, so a model can restyle but cannot invent.

## Which parts are Microsoft Agent Framework agents

- The **workflow** (executors, chain, fan-out, fan-in, events) is Agent Framework and is always used.
- The **writer** is an Agent Framework `Agent` (chat client plus instructions) when a model is configured:
  `OpenAIChatCompletionClient(base_url=...)` reaches any OpenAI-compatible server. Microsoft's **Foundry Local**
  runs models on your own computer (its docs: no Azure subscription, no per-token cost, OpenAI-compatible server)
  and works this way; `KV_LLM_BACKEND=foundry_local` uses the `FoundryLocalClient` connector instead (beta package).
  Ollama works the same way through its OpenAI-compatible URL.
- Interpret, Explain, Verify and the desks are deliberately rule-based: they must be exact and repeatable.
  Verify is the guardrail that makes a model safe to use.

## Honest limits

- Without a model the writer is template-based. The model path is tested against a fake model and a fake
  OpenAI-compatible server (including answers that invent a number, and garbage); it has **not** yet been run
  with a real model, and Foundry Local itself has not been run by us.
- Arabic is `needs_native_review`, Spanish is `machine_assisted_needs_review`. Venue names are not translated.
  Arabic uses separate singular and plural forms for 3 to 10 versus 11 and above in a few phrases only.
- Thresholds (late goal from minute 75, pressing spell needs 6 turnovers at 1.8 times the match average, star
  performance needs 60 percent of the team's shots and at least 10) are hand-set, not fitted to real matches.
- The data is synthetic (fictional league). Nothing here says anything about real football.

## Measured on 24 generated matches with planted stories (`python -m kvagents evaluate <match dirs>`)

Goals found 81 of 81, late comebacks 9 of 9, red cards 4 of 4, pressing spells 6 of 7 (only spells with at least
6 turnovers are scored: weaker planted ones are not visible in the data). Not scored: planted star-player,
quiet-then-chaos and momentum-swing stories (no rule yet, or the star story does not show in touch counts).
The Interpret and Explain agents never read `ground_truth.json`; only `evaluate.py` does, and a test enforces it.

## Run it

```
pip install -e ".[agents]"     # add ".[foundry]" for the Foundry Local connector
python -m eventgen generate --seed 7 --stories config/stories.example.yaml --out out/demo
python -m kvagents run out/demo --out demo/out
# optional model, with every answer cached so the demo replays offline:
KV_LLM_URL=<local OpenAI-compatible URL> KV_LLM_MODEL=<model> python -m kvagents run out/demo --out demo/out --model-cache demo/llm_cache.json
python -m kvagents run out/demo --out demo/out --model-cache demo/llm_cache.json --offline
```

Outputs per match in `demo/out/<match_id>/`: `moments.json`, `packets.json`, `narrations.json`, `broadcast.json`,
`fan_<profile>.json`, `trace.json`, `manifest.json`. `demo/` ships two example matches already processed.

## What the Verify agent checks, and what it cannot (updated after the first real-model run)

The first run against a real model (Groq, `openai/gpt-oss-120b`) showed that digits and names are not enough. Verify now also rejects a draft that:

- has a number written as a word (en/es) that is not in the facts ("one"/"uno" are skipped: too common as ordinary words);
- calls a result a win or victory, or says the match ended, when the facts do not say so (a winning goal or full time);
- puts Latin letters in Arabic text (the venue is shown in Arabic through `localize_venue`), or Arabic letters in en/es text;
- uses only a surname that belongs to a player who is not in the facts (a surname alone is accepted for the main actor).

Known limits: the check is rule based. It cannot tell grammar mistakes, garbled words, or a wrong claim it has no rule for
(for example saying a team "won" in words the lists do not contain). Arabic model text is therefore only a draft until a native
reader approves it; the Arabic templates are the safe default. Arabic can use its own model (`KV_LLM_MODEL_AR`, for example `allam-2-7b` on Groq).

Arabic hold: Arabic model text that passes Verify is kept in `held_headline` / `held_body` and the template stays published,
because the Arabic is not yet approved by a native reader (`STATUS = "needs_native_review"`). After a native reader has approved
the model's Arabic, set `KV_TRUST_LANGS=ar` to publish it. English is the source language and Spanish is published after Verify.
