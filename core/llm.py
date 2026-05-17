"""LLM wrapper: Mistral primary, Groq fallback, on-disk JSON cache."""
from __future__ import annotations
import hashlib
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

load_dotenv()

CACHE_DIR = Path(os.getenv("LLM_CACHE_DIR", ".llm_cache"))
CACHE_DIR.mkdir(exist_ok=True)

MISTRAL_KEY = os.getenv("MISTRAL_API_KEY", "").strip()
GROQ_KEY = os.getenv("GROQ_API_KEY", "").strip()
DEFAULT_MODEL = os.getenv("LLM_MODEL", "mistral-small-latest")


def _cache_key(provider: str, model: str, system: str, user: str, temperature: float) -> str:
    payload = f"{provider}|{model}|{temperature}|{system}|||{user}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_get(key: str):
    path = CACHE_DIR / f"{key}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))["response"]
        except Exception:
            return None
    return None


def _cache_set(key: str, response: str, meta: dict) -> None:
    path = CACHE_DIR / f"{key}.json"
    path.write_text(
        json.dumps({"response": response, "meta": meta}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


class LLMError(Exception):
    pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=20),
    retry=retry_if_exception_type(LLMError),
    reraise=True,
)
def _call_mistral(model: str, system: str, user: str, temperature: float, max_tokens: int) -> str:
    if not MISTRAL_KEY:
        raise LLMError("MISTRAL_API_KEY missing")
    import requests

    r = requests.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {MISTRAL_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=60,
    )
    if r.status_code == 429:
        raise LLMError(f"Mistral rate-limited: {r.text[:200]}")
    if r.status_code >= 500:
        raise LLMError(f"Mistral 5xx: {r.status_code} {r.text[:200]}")
    if r.status_code >= 400:
        raise RuntimeError(f"Mistral {r.status_code}: {r.text[:500]}")
    data = r.json()
    return data["choices"][0]["message"]["content"]


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=20),
    retry=retry_if_exception_type(LLMError),
    reraise=True,
)
def _call_groq(model: str, system: str, user: str, temperature: float, max_tokens: int) -> str:
    if not GROQ_KEY:
        raise LLMError("GROQ_API_KEY missing")
    import requests

    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=60,
    )
    if r.status_code == 429:
        raise LLMError(f"Groq rate-limited: {r.text[:200]}")
    if r.status_code >= 500:
        raise LLMError(f"Groq 5xx: {r.status_code} {r.text[:200]}")
    if r.status_code >= 400:
        raise RuntimeError(f"Groq {r.status_code}: {r.text[:500]}")
    return r.json()["choices"][0]["message"]["content"]


def chat(
    system: str,
    user: str,
    *,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 1500,
    cache: bool = True,
    provider: str | None = None,
) -> str:
    provider = (provider or os.getenv("LLM_PROVIDER", "mistral")).lower()
    model = model or DEFAULT_MODEL
    key = _cache_key(provider, model, system, user, temperature)
    if cache:
        cached = _cache_get(key)
        if cached is not None:
            return cached
    started = time.time()
    try:
        if provider == "mistral":
            out = _call_mistral(model, system, user, temperature, max_tokens)
        else:
            out = _call_groq(model, system, user, temperature, max_tokens)
    except LLMError:
        # try fallback once
        if provider == "mistral":
            out = _call_groq("llama-3.3-70b-versatile", system, user, temperature, max_tokens)
            provider = "groq-fallback"
        else:
            out = _call_mistral("mistral-small-latest", system, user, temperature, max_tokens)
            provider = "mistral-fallback"
    if cache:
        _cache_set(
            key,
            out,
            {"provider": provider, "model": model, "elapsed_s": round(time.time() - started, 2)},
        )
    return out


def parse_json(text: str):
    """Pull first JSON object/array out of LLM response. Picks whichever appears earliest."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(l for l in lines if not l.startswith("```"))
    # pick the opener that appears first in the text
    candidates = []
    for opener, closer in (("{", "}"), ("[", "]")):
        i = text.find(opener)
        if i != -1:
            candidates.append((i, opener, closer))
    if not candidates:
        raise ValueError(f"no JSON found in: {text[:200]!r}")
    candidates.sort()
    i, opener, closer = candidates[0]
    depth = 0
    for j in range(i, len(text)):
        if text[j] == opener:
            depth += 1
        elif text[j] == closer:
            depth -= 1
            if depth == 0:
                return json.loads(text[i : j + 1])
    raise ValueError(f"unterminated JSON starting at {i}: {text[i : i + 200]!r}")
