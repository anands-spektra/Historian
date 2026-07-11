"""Passive prompt capture. The only hook the historian installs: it appends
each user prompt to session/prompts.jsonl so `save` can bundle "prompts since
last iteration". It never generates iterations and always exits 0."""

import json
import sys
from datetime import datetime, timezone

from . import config


def _now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _stdin_json():
    try:
        raw = sys.stdin.buffer.read().decode("utf-8-sig")  # utf-8-sig strips any BOM
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def prompt():
    """UserPromptSubmit: append the user's prompt to session/prompts.jsonl."""
    data = _stdin_json()
    text = data.get("prompt", "")
    if not text:
        return 0
    p = config.paths(config.find_root())
    p.session.mkdir(parents=True, exist_ok=True)
    rec = {"ts": _now(), "session_id": data.get("session_id"), "prompt": text}
    with p.prompts.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    return 0


def drain_prompts(paths):
    """Return accumulated prompts and roll the file so the next iteration starts clean."""
    if not paths.prompts.exists():
        return []
    out = []
    for line in paths.prompts.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    paths.prompts.unlink()
    return out
