"""Generic CLI provider: run any command that reads a prompt on stdin and
writes the analysis to stdout. Covers OpenCode, Gemini CLI, Codex, Ollama, and
any custom script — the specific tool is entirely config (command/args/env)."""

import os
import subprocess


def analyze(prompt, cfg):
    command = cfg.get("command")
    if not command:
        raise RuntimeError("cli provider: 'command' is not set in config")
    cmd = [command] + list(cfg.get("args") or [])
    env = dict(os.environ)
    env.update(cfg.get("env") or {})
    timeout = cfg.get("timeout_sec", cfg.get("provider_timeout_sec", 180))
    r = subprocess.run(
        cmd, input=prompt, capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=env, timeout=timeout,
    )
    if r.returncode != 0:
        raise RuntimeError(f"{command} failed ({r.returncode}): {r.stderr.strip()[:500]}")
    out = r.stdout.strip()
    if not out:
        raise RuntimeError(f"{command} returned empty output")
    return out
