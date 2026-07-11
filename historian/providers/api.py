"""OpenAI-compatible HTTP provider (stdlib urllib, no dependencies). Covers
OpenAI, OpenRouter, Ollama's /v1, and any compatible endpoint. Auth key comes
from an env var named in config (never stored in config)."""

import json
import os
import urllib.error
import urllib.request


def analyze(prompt, cfg):
    api = cfg.get("api") or {}
    base = api.get("base_url", "https://api.openai.com/v1").rstrip("/")
    key_env = api.get("api_key_env", "OPENAI_API_KEY")
    key = os.environ.get(key_env)
    if not key:
        raise RuntimeError(f"api provider: env var {key_env} is not set")
    model = cfg.get("model")
    if not model:
        raise RuntimeError("api provider: 'model' is not set in config")

    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    timeout = cfg.get("timeout_sec", cfg.get("provider_timeout_sec", 180))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"api HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")
    out = (data["choices"][0]["message"]["content"] or "").strip()
    if not out:
        raise RuntimeError("api provider returned empty output")
    return out
