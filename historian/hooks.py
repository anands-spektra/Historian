"""Fast-path hook handlers. Run in-process with Claude Code, so they do the
minimum and always exit 0 (the outer wrapper in __main__ guarantees that).
No Gemini/OpenCode calls here — heavy work is the worker's job (Phase 4)."""

import json
import sys
from datetime import datetime, timezone

from . import config, queue, shadowgit
from .log import get_logger


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


def _drain_prompts(paths):
    """Read accumulated prompts and roll the file so the next iteration starts clean."""
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


def stop():
    """Stop: snapshot the shadow repo and enqueue an iteration event.
    No worker spawn yet (Phase 4)."""
    data = _stdin_json()
    p = config.paths(config.find_root())
    log = get_logger(p)
    state = config.read_state(p)
    iteration = state.get("iteration", 0) + 1
    prev = state.get("last_shadow_commit")
    new = shadowgit.snapshot(p, f"historian: iteration {iteration}")
    prompts = _drain_prompts(p)
    event = {
        "iteration": iteration,
        "ts": _now(),
        "session_id": data.get("session_id"),
        "prompts": prompts,
        "prev_commit": prev,
        "new_commit": new,
    }
    queue.enqueue(p, event)
    config.update_state(p, iteration=iteration, last_shadow_commit=new)
    log.info(f"iteration {iteration} enqueued: {prev} -> {new}, {len(prompts)} prompt(s)")
    return 0
