"""Check that a local model (a hosted free tier, Foundry Local, Ollama, or any OpenAI-compatible server; the key, if any, goes in KV_LLM_KEY) works for KooraVision.

    python tools/foundry_check.py --url http://localhost:PORT/v1            # lists models, tries the first
    python tools/foundry_check.py --url http://localhost:PORT/v1 --model <id>

It asks the model to restyle one goal note in English, Arabic and Spanish, then runs the same fact-check the Verify
agent uses, so you can see whether the model is good enough. Nothing is written except what it prints.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kvagents.explain import explain          # noqa: E402
from kvagents.interpret import interpret      # noqa: E402
from kvagents.llm import AgentFrameworkModel, OpenAICompat  # noqa: E402
from kvagents.match_view import MatchView     # noqa: E402
from kvagents.narrate import STYLE_SYSTEM, VOICE_HINT, render  # noqa: E402
from kvagents.verify import verify_narration  # noqa: E402

DEMO = Path(__file__).resolve().parents[1] / "demo" / "matches"


def list_models(url: str) -> list[str]:
    import os
    req = urllib.request.Request(url.rstrip("/") + "/models", headers={"Authorization": f"Bearer {os.environ.get('KV_LLM_KEY', 'none')}"})
    with urllib.request.urlopen(req, timeout=20) as r:  # noqa: S310
        return [m["id"] for m in json.loads(r.read())["data"]]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="OpenAI-compatible base URL, e.g. https://api.groq.com/openai/v1")
    ap.add_argument("--model")
    ap.add_argument("--backend", choices=["openai", "plain"], default="openai", help="openai = Agent Framework agent; plain = bare HTTP client")
    a = ap.parse_args()
    try:
        models = list_models(a.url)
    except Exception as e:  # noqa: BLE001
        print(f"Cannot reach {a.url}/models: {e}\nIs the server running? (foundry server status)")
        return 1
    print("Models the server offers:")
    for m in models:
        print("  ", m)
    model_id = a.model or (models[0] if models else None)
    if not model_id:
        print("The server lists no models. Load one first (foundry model load <alias>).")
        return 1
    print(f"\nTesting model: {model_id}\n")
    mv = MatchView(next(DEMO.iterdir()))
    packets = explain(mv, interpret(mv))
    p = next(x for x in packets if x.kind == "goal" and x.beneficiary)
    names = mv.all_names()
    llm = AgentFrameworkModel(model_id, a.url) if a.backend == "openai" else OpenAICompat(a.url, model_id)
    ok_count = 0
    for lang in ("en", "ar", "es"):
        head, body = render(p, lang, "fan_for", mv.meta["venue"])
        payload = {"language": lang, "voice": VOICE_HINT["fan_for"], "minute": p.minute, "draft_headline": head,
                   "draft_body": body, "names": {k: v[lang] for k, v in p.names.items()},
                   "facts": {k: v for k, v in p.facts.items() if k not in ("home", "away")}, "causes": p.causes}
        t0 = time.time()
        try:
            raw = llm.complete(STYLE_SYSTEM, json.dumps(payload, ensure_ascii=False))
            data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
            h2, b2 = str(data["headline"]), str(data["body"])
            ok, why = verify_narration(p, h2, b2, lang, names)
        except Exception as e:  # noqa: BLE001
            print(f"[{lang}] FAILED: {type(e).__name__}: {e}\n")
            continue
        ok_count += ok
        print(f"[{lang}] {time.time() - t0:.1f}s  fact-check: {'PASS' if ok else 'REJECTED (' + why + ')'}")
        print("   template:", head, "|", body)
        print("   model:   ", h2, "|", b2, "\n")
    print(f"{ok_count}/3 languages passed the fact-check.")
    return 0 if ok_count else 2


if __name__ == "__main__":
    sys.exit(main())
