# Run the agents with a free hosted model (GitHub Actions)

No model runs on your computer. GitHub Actions starts a Linux machine, runs the agents, calls a free hosted model with
your API key, and saves the answers into `demo/llm_cache.json` so the demo replays offline afterwards.

1. **Repository.** Sign in to GitHub, create a **public** repository (add the MIT licence), upload the project files
   (including the hidden-looking `.github` folder).
2. **API key.** Create a free key with a provider that needs no credit card (for example Groq: console.groq.com, API Keys).
3. **Secret.** Repository Settings > Secrets and variables > Actions > New repository secret, name `LLM_API_KEY`,
   value = the key. Never put the key in a file.
4. **Run.** Actions tab > "Narrate with a free model" > Run workflow. The defaults use Groq and `openai/gpt-oss-120b`;
   change `base_url` and `model` to try another provider or model.
5. Read the log of the step "Check the model on one goal note": it shows, per language, whether the model's rewrite
   passed the fact-check.

Free tiers have limits (Groq's published free limits at the time of writing: 30 requests a minute, 1,000 a day,
200,000 tokens a day per model, and about 8,000 tokens a minute), so calls are spaced `min_interval` seconds apart and
retried when the service says "too many requests". Prompts and answers contain only synthetic match data.

## The match desk page and the Arabic review

`python tools/build_site.py` builds `site/index.html` from `demo/out`: one file, data inside, no server and no live model.
The `pages.yml` workflow publishes it with GitHub Pages (Settings > Pages > Source: GitHub Actions).

The page has an **Arabic review** tab. A native reader approves or rejects each held Arabic draft, copies the decisions, and saves
them as `demo/approvals-ar.json`. The next run of the Narrate workflow publishes the approved drafts and keeps the template for the rest.
