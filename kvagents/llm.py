"""Optional language model for the Narrate agent ("stylist"). Free options: a local OpenAI-compatible server such as
Ollama (http://localhost:11434/v1). Nothing here is required: with no model the agents use templates.

Every model answer is cached on disk, so a demo can be replayed with no model and no network (offline=True).
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.request
from pathlib import Path
from typing import Protocol


class TextModel(Protocol):
    name: str

    def complete(self, system: str, user: str) -> str: ...


class OpenAICompat:
    def __init__(self, base_url: str, model: str, api_key: str | None = None, timeout: float = 90.0, temperature: float = 0.4):
        self.base_url, self.model, self.timeout, self.temperature = base_url.rstrip("/"), model, timeout, temperature
        self.api_key = (api_key or os.environ.get("KV_LLM_KEY", "none")).strip()
        self.name = f"openai-compatible:{model}"

    def complete(self, system: str, user: str) -> str:
        body = json.dumps({"model": self.model, "temperature": self.temperature,
                           "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
        req = urllib.request.Request(f"{self.base_url}/chat/completions", data=body,
                                     headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}",
                                              "User-Agent": "kooravision/1.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:  # noqa: S310 (user-configured endpoint)
            return json.loads(r.read())["choices"][0]["message"]["content"]


class AgentFrameworkModel:
    """The writer as a real Microsoft Agent Framework `Agent`: a chat client plus instructions, run with `agent.run`.

    Backends (set KV_LLM_BACKEND): "openai" (default) = any OpenAI-compatible server through
    `OpenAIChatCompletionClient(base_url=...)`, which covers Foundry Local's local server and Ollama;
    "foundry_local" = `FoundryLocalClient(model)` from agent-framework-foundry-local (starts the local runtime itself).
    """

    def __init__(self, model: str, base_url: str | None = None, backend: str = "openai", api_key: str | None = None):
        self.model, self.base_url, self.backend = model, base_url, backend
        self.api_key = (api_key or os.environ.get("KV_LLM_KEY", "none")).strip()
        self.name = f"agent-framework:{backend}:{model}"
        self._client = None
        self._agents: dict[str, object] = {}

    def _make_client(self):
        if self.backend == "foundry_local":
            from agent_framework_foundry_local import FoundryLocalClient
            return FoundryLocalClient(self.model)
        from agent_framework.openai import OpenAIChatCompletionClient
        return OpenAIChatCompletionClient(model=self.model, api_key=self.api_key, base_url=self.base_url)

    def _agent(self, system: str):
        from agent_framework import Agent
        if self._client is None:
            self._client = self._make_client()
        if system not in self._agents:
            self._agents[system] = Agent(self._client, instructions=system, name="narrator")
        return self._agents[system]

    def _run(self, coro):
        """Run a coroutine on ONE long-lived event loop (in a helper thread). The chat client keeps HTTP connections
        that belong to the loop that opened them, so a fresh `asyncio.run` per call fails with 'Event loop is closed'."""
        import asyncio
        import threading
        if getattr(self, "_loop", None) is None:
            self._loop = asyncio.new_event_loop()
            threading.Thread(target=self._loop.run_forever, daemon=True, name="kv-model-loop").start()
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    def complete(self, system: str, user: str) -> str:
        agent = self._agent(system)
        return self._run(agent.run(user)).text


class CachedModel:
    """Wraps a model with an on-disk cache. `inner=None` + a cache file = offline replay of saved answers.

    Free hosted tiers have rate limits, so a call can wait (`min_interval` seconds between real calls) and is retried
    with a growing pause when the service answers with an error (for example HTTP 429).
    """

    def __init__(self, inner: TextModel | None, cache_path: str | Path, offline: bool = False,
                 min_interval: float = 0.0, retries: int = 3, retry_pause: float = 15.0):
        self.inner, self.path, self.offline = inner, Path(cache_path), offline
        self.min_interval, self.retries, self.retry_pause = min_interval, retries, retry_pause
        self.name = f"cached:{inner.name}" if inner else "cached:replay"
        self.cache: dict[str, str] = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        self.hits = self.misses = self.failures = 0
        self._last = 0.0

    def complete(self, system: str, user: str) -> str:
        key = hashlib.sha256((system + "\n" + user).encode()).hexdigest()
        if key in self.cache:
            self.hits += 1
            return self.cache[key]
        if self.offline or self.inner is None:
            raise LookupError("no cached answer")
        out = None
        for attempt in range(self.retries + 1):
            wait = self.min_interval - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            try:
                out = self.inner.complete(system, user)
                break
            except Exception:  # noqa: BLE001  (rate limit, network, server error: pause and try again)
                self.failures += 1
                if attempt == self.retries:
                    raise
                time.sleep(self.retry_pause * (attempt + 1))
        self.misses += 1
        self.cache[key] = out
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.cache, ensure_ascii=False, indent=1), encoding="utf-8")
        return out


class ByLanguage:
    """Routes each request to a model chosen by the note's language (the request is JSON with a "language" field).
    Use it to give Arabic a model that is better at Arabic, while the other languages keep the main model."""

    def __init__(self, default: TextModel, per_language: dict[str, TextModel]):
        self.default, self.per_language = default, per_language
        self.name = default.name + "".join(f" + {k}:{m.name}" for k, m in per_language.items())

    def complete(self, system: str, user: str) -> str:
        try:
            lang = json.loads(user).get("language", "")
        except (ValueError, AttributeError):
            lang = ""
        return self.per_language.get(lang, self.default).complete(system, user)


def build_model(url: str | None, model: str, backend: str = "openai", model_ar: str | None = None) -> TextModel | None:
    def one(name: str) -> TextModel | None:
        if backend == "plain":
            return OpenAICompat(url, name) if url else None
        if backend == "foundry_local":
            return AgentFrameworkModel(name, backend="foundry_local")
        return AgentFrameworkModel(name, url, "openai") if url else None

    main = one(model)
    if main is None:
        return None
    if model_ar and model_ar != model:
        ar = one(model_ar)
        if ar is not None:
            return ByLanguage(main, {"ar": ar})
    return main


def model_from_env() -> TextModel | None:
    """KV_LLM_MODEL (+ KV_LLM_URL for an OpenAI-compatible server). KV_LLM_BACKEND: openai (default), foundry_local, plain.
    Optional KV_LLM_MODEL_AR: a different model for Arabic only."""
    model = os.environ.get("KV_LLM_MODEL")
    if not model:
        return None
    return build_model(os.environ.get("KV_LLM_URL"), model, os.environ.get("KV_LLM_BACKEND", "openai"),
                       (os.environ.get("KV_LLM_MODEL_AR") or "").strip() or None)
