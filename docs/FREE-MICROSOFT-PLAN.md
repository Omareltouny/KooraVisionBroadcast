# Free-only plan: Microsoft tools mapped to the judging rubric

Rule for this project: **nothing costs money.** Every Azure piece below is either on a free tier, or
optional with a free local fallback. Written 2026-10-19. Items marked (unverified) came from
fetch-tool summaries; check the live page before relying on them.

## What changed in the research

- **GitHub Models was retired on 2026-07-30** (GitHub's REST docs say so; its older billing pages are stale).
  There is no free hosted model from GitHub any more.
- Azure for Students: $100 credit, no credit card, for full-time university students; a school email is
  used to sign up. Whether the credit covers AI models is not stated on the page. Check at
  azure.microsoft.com/free/students.
- Event Hubs still has no free tier.

## Free pieces (all unverified until you check the live pricing pages)

| Need | Microsoft tool | Free allowance found |
|---|---|---|
| Code, repo, CI | GitHub (public repo), GitHub Actions, VS Code | free for public repos |
| Agents | Microsoft Agent Framework (open source) | free, runs anywhere |
| Model for agents | Foundry Local or an OpenAI-compatible local model, **or** Azure AI Foundry on student credit | local is free; Foundry needs credit |
| Live push to the UI | Azure Web PubSub, Free tier | 20 connections, 20,000 messages/day |
| Web UI hosting | Azure Static Web Apps, Free plan | 100 GB bandwidth, 2 custom domains |
| API / orchestration | Azure Functions (Consumption) or Container Apps | 1M executions/month; 2M requests/month |
| Translation checks | Azure Translator F0 | 2 million characters (per month or per hour; sources disagree) |
| Video editing | Clipchamp (free tier) | free export |

Event Hubs: the code keeps an Event Hubs sink, but the default demo path is file replay plus Web PubSub
(or plain server-sent events locally). If student credit turns out to cover Event Hubs, switch it on.

## Architecture (free path)

```
tracking.jsonl + events.jsonl   (generator, local)
        |  replay at match speed (file sink, or Event Hubs / Web PubSub if free)
        v
 Interpret agent  -- tools: speed/distance from tracking, pass difficulty, momentum, xT-lite
 Explain agent    -- tools: fact packets with event IDs, "because ..." traces
 Narrator agent   -- templates + optional model, en / ar / es, verifier checks every number and name
 Personalize agent-- reads profile (6 personas + dials), ranks and rewrites for the viewer
 Verifier         -- rejects any sentence whose numbers or names are not in the cited facts, asks for a repair
        v
 Web UI on Static Web Apps (or local): timeline, pitch view from tracking, persona A/B, language switch
```

The model is pluggable: Foundry (if credit) -> local model -> pure templates. The demo always works
offline. Model output for the demo is generated once and cached, with the real agent trace shown.

## Rubric mapping (each criterion is 20%)

| Criterion | What we show | Free tool carrying it |
|---|---|---|
| Technological implementation | validator rules 1-15, 47 tests, CI on every push, schemas, determinism, docs | GitHub Actions, Agent Framework, Azure services in the free tier |
| Agentic design | four agents plus a verifier loop (generate, check, repair); tools are deterministic code; every claim cites event IDs | Microsoft Agent Framework |
| Real-world impact | casual fans, Arabic and Spanish speakers, blind and low-vision fans (live description), personalised depth | free Azure hosting; accessible UI |
| UX and presentation | two personas side by side on the same moment, one-click Arabic, pitch view driven by tracking, under-2-minute video | Static Web Apps, Clipchamp |
| Category adherence | pick one category when registering. Recommended: **Multi-Agent**. Read its description on the hackathon page and match the demo to it | n/a |

## Risks to watch

- Student credit may not cover AI models, so keep the local and template fallbacks working first.
- Web PubSub's 20,000 messages/day is too small for 30,000 tracking frames. Send events live and
  tracking at 1 Hz or only around key moments (unverified count rules).
- A "production-ready" claim needs a Dockerfile, CI and a deployed link. Keep the deployed link on a free plan.
- No music, no real club names or crests, no third-party trademarks in the video.
