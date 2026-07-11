"""Primary provider: OpenCode headless (`opencode run`) with the free Nemotron
model. Prompt goes on stdin (no command-line length limit); agent tools are
denied so it's a pure text-in/text-out transform, not a coding agent."""

import os
import subprocess

DENY = '{"edit":"deny","bash":"deny","webfetch":"deny"}'


def analyze(prompt, cfg):
    cmd = [cfg.get("opencode_command", "opencode"), "run"]
    model = cfg.get("model")
    if model:
        cmd += ["-m", model]

    env = dict(os.environ)
    if cfg.get("opencode_deny_tools", True):
        env["OPENCODE_PERMISSION"] = DENY

    r = subprocess.run(
        cmd, input=prompt, capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=env,
        timeout=cfg.get("provider_timeout_sec", 180),
    )
    if r.returncode != 0:
        raise RuntimeError(f"opencode run failed ({r.returncode}): {r.stderr.strip()[:500]}")
    out = r.stdout.strip()
    if not out:
        raise RuntimeError("opencode run returned empty output")
    return out
