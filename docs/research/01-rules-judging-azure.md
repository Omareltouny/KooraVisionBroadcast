# KooraVision: rules, judging, Azure stack, demo (research strand 1)

Accessed 2026-10-19. Method: WebFetch only. Every WebFetch returns a model-written summary, not raw text, so section numbers and quoted fragments are second-hand. **Re-read the rules page once by eye before submitting.** Nothing was blocked.

Sources:
- R = https://raw.githubusercontent.com/microsoft/insidethegamehackathon/main/OFFICIAL%20RULES.md (repo https://github.com/microsoft/insidethegamehackathon, MIT-licensed, files: CODE OF CONDUCT, LICENSE, OFFICIAL RULES, RESOURCE PLAYLISTS, SECURITY)
- P = https://raw.githubusercontent.com/microsoft/insidethegamehackathon/main/RESOURCE%20PLAYLISTS.md

## 1. Urgent facts (R s.1)

| Item | Value |
|---|---|
| Registration | 2026-09-29 09:00 PT to **2026-10-20 12:00 PT (tomorrow, noon)** |
| Submission period | 2026-10-06 to **2026-10-27 23:59 PT** (8 days left) |
| Judging | 2026-10-27 to 2026-11-10 |
| Winners | by 2026-11-20 |

Registration closes first. **Register before noon PT on Oct 20.** The project must be "newly created after the Registration Period starts" (s.4.3, paraphrase), so the generator must have been written after 2026-09-29. Confirm its commit dates.

## 2. Scoring extracted from R

**Stage One (s.6.1), pass/fail:** project must reasonably fit the theme and reasonably apply the required technologies.

**Stage Two (s.6.2), five criteria, 20% each:**
1. Technological Implementation
2. Agentic Design & Innovation
3. Real-World Impact & Applicability
4. User Experience & Presentation
5. Adherence to Hackathon Category

Tie-break (s.6.3): higher score on the first criterion in the list above, then down the list; then a judge vote. So Technological Implementation breaks ties.

**Hero technologies named (s.6.2):** Microsoft Foundry, Agent Framework, Azure MCP, GitHub Copilot Agent Mode, Fabric, GitHub SDK, GitHub CLI, Azure Apps and AI Services, Azure databases.

**Pipeline (s.4.1):** ingest, interpret, explain, render, personalize, "synthetic football events into explainable match intelligence". This matches KooraVision.

**Prizes (s.4.2, s.8):**
- Grand Prize 1st: ticket, store voucher, about $4,000 cash per member.
- Grand Prize 2nd: about $2,500 cash per member.
- Category prizes (about $1,500 per member, no ticket): Best Use of Microsoft Foundry Project, Best Enterprise Solution, Best Multi-Agent System (called "Best Multi-Agent Orchestration" in s.8), Best Azure Cloud Native Integration.
- A project can win one Grand Prize and up to one Category Prize. Judges may move a project between categories (s.4.3).
- Multi-Agent prize names GitHub Copilot, Microsoft Agent Framework, A2A "or another supported orchestration approach". Cloud Native prize names AKS, Container Apps, Functions, Logic Apps and "AI-optimized data platforms".

**Submission (s.4.4):**
- New project meeting the challenge requirements.
- Short pitch: what was built, which Microsoft and Azure technologies were used, what it does, what problem it solves.
- **Demo video under 2 minutes.** Judges need not watch beyond that. It must show the project running on its intended device and platform. Host on YouTube, Vimeo, Facebook Video or Youku, and link it on the project page.
- No third-party trademarks or copyrighted music or material in the video without permission.
- **Public GitHub repo URL** (private repos are not considered).
- Content must not be offensive, promote alcohol, drugs, tobacco or a political agenda, or harm Microsoft's goodwill.
- Entry must not have won another contest.
- English required, or provide translations of all materials (s.4.9). Arabic UI is fine if the pitch, README and video are English or subtitled.
- Working link, demo or test build free until judging ends, with login details if private (s.4.8). Judges may decide from text and video alone.
- Team: up to 4 people, one Representative (s.3).
- Post-deadline changes only at Sponsor discretion (s.5).

**Data (s.4.7):** "synthetic, football-realistic data". Organisers do not supply footage. Entrants hold any rights they use. We use our own generator, which fits. Do not use real Premier League event feeds or footage. Avoid real player or club names in the demo (trademark rule for the video, and a safe fit with "synthetic").

**IP (s.4.6, s.7, s.10, s.11.8):**
- Entrant keeps ownership; the work must be original and non-infringing.
- Entrant grants Promotion Entities a "worldwide, perpetual, irrevocable, royalty-free, non-exclusive" licence for any non-commercial or commercial purpose.
- Names, likenesses and voices may be used for promotion for the hackathon period plus 3 years. Anyone voicing the demo is consenting to this.
- Open source is allowed if you follow the upstream licences and add meaningful functionality (s.4.11).
- Tools must be used within their licence terms.

**Third-party code and AI use:** no separate AI rule found beyond the above (the fetch summary stated this; I did not search the full text myself). Licence-compliant use of libraries and models is the only constraint. Credit Copilot-assisted work in the README, which also helps the Copilot hero-tech point.

**Not found in R:** a minimum number of technologies, a word limit for the pitch, a video resolution rule, and a bonus for open-sourcing.

## 3. Scoring checklist

| Criterion (20% each) | KooraVision feature | What to show on screen |
|---|---|---|
| Technological Implementation | Event Hubs ordered stream, Foundry model calls, Agent Framework workflow, DefaultAzureCredential with no secrets, tests, CI | Events arriving live in the UI; architecture slide; repo with `azd`/Bicep or a one-command run |
| Agentic Design & Innovation | Interpret, Explain and Personalize as separate agents with typed hand-offs; an explain step that cites event IDs | Trace or log showing agents hand off; each claim linking back to source events (explainability) |
| Real-World Impact & Applicability | Same match told differently for a casual fan and an analyst; Arabic for underserved audiences; accessibility | Two personas side by side; one language switch |
| User Experience & Presentation | Match timeline, plain-language "why it matters", clean render | Under-2-minute video with captions; polished UI |
| Adherence to Category | State the target category and map each stage to a technology | Closing slide: stage to Azure service table |

## 4. Technology options (stack effort and risk are my judgement; docs facts are cited)

Hero tech list: R s.6.2. Playlists in P: GitHub Copilot https://aka.ms/asn/ghcopilot, Foundry https://aka.ms/asn/foundry, Foundry Agents https://aka.ms/asn/foundryagents, Agentic Workflows https://aka.ms/asn/agenticworkflows, Data https://aka.ms/asn/data.

| Tech | Role in our stages | Effort | Demo risk | Docs |
|---|---|---|---|---|
| Azure Event Hubs | **Ingest**: replay a generated match as an ordered stream | S | Low to medium (role assignment can take minutes) | https://learn.microsoft.com/en-us/azure/event-hubs/event-hubs-python-get-started-send |
| Microsoft Foundry (models, `azure-ai-projects` 2.x) | **Explain** and **Personalize**: LLM narration | S to M | Medium (quota, latency); cache outputs | https://learn.microsoft.com/en-us/azure/ai-foundry/what-is-foundry |
| Microsoft Agent Framework (`agent-framework` 1.22.0, 2026-10-15, Production/Stable, Python >=3.10; Foundry via `agent-framework-foundry`) | **Interpret, Explain, Personalize** as agents in a graph workflow | M | Medium (young API; pin the version) | https://learn.microsoft.com/en-us/agent-framework/overview/ ; https://pypi.org/project/agent-framework/ |
| GitHub Copilot agent mode | Build tool; show it in README and video | S | Low | P playlist |
| Azure MCP Server | Dev-time (it targets developers in an org, not external apps): Copilot queries and deploys Azure resources | S | Low | https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/overview |
| Azure Container Apps or Functions | Host the API and UI (also wins "Cloud Native" fit and satisfies the working-link rule) | M | Medium | named in R s.4.2 |
| Azure Translator / Azure AI Speech | **Personalize**: Arabic text and voice. Arabic coverage, free-tier limits and Python package names are **not confirmed** on the pages I read; the Speech SDK name is from the fetch tool's general knowledge, unverified | S to M | Medium | https://learn.microsoft.com/en-us/azure/ai-services/translator/overview ; https://learn.microsoft.com/en-us/azure/ai-services/speech-service/text-to-speech |
| Azure database (Cosmos DB or Postgres) | Store interpreted events and explanations | M | Low | not fetched |
| Fabric | Analytics layer | L | High | not fetched; cut |

### Recommended minimal credible stack (hits Stage One and the Foundry, Multi-Agent and Cloud Native prize angles)

1. Event Hubs for Ingest. Use the Standard tier if Capture or Kafka is wanted; either way the generator publishes events keyed by `match_id`.
2. Agent Framework workflow with 3 agents (Interpret, Explain, Personalize) on a Foundry-hosted model.
3. Render: static or small web UI served from Container Apps (or locally if time runs out, noting s.4.8 wants a working link).
4. Language switch via the Foundry model, with Translator only if time permits.
5. Copilot agent mode used for development, with a note in the README.

Options for the model call:
- (a) Foundry model through Agent Framework: recommended, S to M.
- (b) Raw `azure-ai-projects`: S, less "agentic" credit.
- (c) Third-party model API: faster to hack, poor Stage One fit. Avoid.

### Event Hubs details (all from the docs above)

- Package: `pip install azure-eventhub azure-identity aiohttp`. PyPI shows **5.15.1 (2025-10-30), Python >=3.9** at https://pypi.org/project/azure-eventhub/. That is a year old and the page may be cached; run `pip index versions azure-eventhub` to confirm.
- Auth: `DefaultAzureCredential` (async clients use `azure.identity.aio`; close the credential), passing `fully_qualified_namespace`, `eventhub_name` and `credential`. No connection string is needed, so there are no secrets in the repo. Local dev uses `az login`. Roles: Data Sender to send, Data Receiver to read; the quickstart uses Data Owner. Receivers with a checkpoint store also need Storage Blob Data Contributor.
- Partition key: signature is `create_batch(*, partition_id=None, partition_key=None, max_size_in_bytes=None)`, per https://learn.microsoft.com/en-us/python/api/azure-eventhub/azure.eventhub.eventhubproducerclient?view=azure-python . The SDK page says `send_batch(..., partition_key=...)` raises `TypeError` if given an `EventDataBatch`, because the batch carries its own key. So: **`producer.create_batch(partition_key=match_id)`, then `send_batch(batch)`** (no key on send). Use a string key; non-string keys are ignored and sent round-robin. Create a new batch per match. The create_batch docs gave no prose description of the parameter, so confirm with a quick test that all events for a match land in one partition.
- Event Hubs vs Service Bus (https://learn.microsoft.com/en-us/azure/event-grid/compare-messaging-services): Event Hubs guarantees order per partition and supports replay via Capture. Service Bus gives FIFO only with sessions and lists no replay. **Recommendation: Event Hubs, key by match_id.** Option 2 is Service Bus sessions (strict per-match FIFO but no replay), option 3 is skip the broker and replay from a file (zero risk, weak Azure score). Event Hubs retention is 1 day on Basic and 7 days on Standard, so replay beyond that needs Capture, which is Standard only.
- Cost: pricing page shows no prices and no free tier (https://azure.microsoft.com/en-us/pricing/details/event-hubs/). Cost: **not found**. Use the Azure calculator. A throughput unit is 1 MB/s in, 2 MB/s out, which is far above what one synthetic match needs.
- Local fallback: the Event Hubs emulator runs in Docker, with 32 partitions max and 1 MB events, and does not persist data (https://learn.microsoft.com/en-us/azure/event-hubs/overview-emulator). It does **not** support Entra ID, so `DefaultAzureCredential` will not work against it; use its local connection string through an env var (not committed). Also no Capture. It has no official support.

## 5. Demo script

**Hard constraint: R s.4.4 says the video is under 2 minutes.** The 3 to 5 minute request cannot be the submitted video. Plan a 1:45 video and a longer live or pitch version.

### Submitted video (1:45)

| Time | Content |
|---|---|
| 0:00-0:12 | Problem: raw match events are unreadable for most fans |
| 0:12-0:30 | One generated match streams into Event Hubs; UI timeline fills live |
| 0:30-1:05 | Two personas side by side (casual fan, analyst): same moment, different explanation, each citing event IDs |
| 1:05-1:25 | Language switch to Arabic (one click) |
| 1:25-1:40 | Architecture slide: Ingest, Interpret, Explain, Render, Personalize mapped to Azure services; agent trace |
| 1:40-1:45 | Repo URL and close |

### Longer version (3:30, for a live pitch or judges who ask)

Add: 45 s on agent hand-offs and the explainability trace, 30 s on a deployed link and the no-secrets auth story, 30 s on Copilot agent mode and the repo.

### Cut list (cut in this order)
1. Fabric, databases, Translator or Speech (use Foundry model for the language switch).
2. Live Event Hubs in video: pre-run the stream and show the real send logs.
3. Container Apps deployment: run locally, state it clearly.
4. Live LLM calls: use cached outputs generated by the real pipeline.
5. Last to cut: two personas and one language switch (they carry the Impact and UX scores).

Video must not use music, club crests, or real names (s.4.4, s.11.8).

## 6. Licence

| Option | Fit with rules | Effort | Risk |
|---|---|---|---|
| **MIT (recommended)** | The organisers' own repo is MIT. The s.7 grant is non-exclusive, so it does not conflict. MIT is more permissive than the grant. Open source is allowed (s.4.11). | S | Low. Check that dependencies' licences allow it, and that no third-party text or assets are copied in. |
| Apache-2.0 | Also compatible; adds a patent grant | S | Low |
| Proprietary, public repo | Allowed by the grant | S | Weaker with reviewers; the repo must be public anyway |

Not found in R: any requirement to open-source or to pick a licence. The repo only has to be public. Name and likeness clause (s.7, s.10) applies to team members regardless of licence.

## 7. Open items
- Verify R wording on s.4.4 video length and s.6.2 by eye.
- Confirm Arabic availability in Translator and Speech and the free-tier limits (pages did not state them).
- Confirm the generator's first-commit date is after 2026-09-29.
- Confirm Foundry model quota in the team subscription today.
