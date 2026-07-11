"""Detached worker: drains the queue oldest-first, documents each iteration
via the provider, appends to docs/implementation.md. Single-instance via a
lockfile. Append-only; never rewrites prior sections."""

import json
import os

from . import collector, config
from .log import get_logger
from .providers import get_provider


def _acquire(paths):
    """Minimal single-instance lock. (Stale-lock reclaim is Phase 6.)"""
    try:
        fd = os.open(str(paths.lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        return False


def _release(paths):
    try:
        paths.lock.unlink()
    except FileNotFoundError:
        pass


def _build_prompt(payload):
    """Serialize the payload for the provider. Phase 5 replaces this with a
    real template render."""
    lines = [f"Iteration {payload['iteration']} at {payload['ts']}", "",
             "User prompt(s):"]
    lines += [f"- {p}" for p in payload["prompts"]] or ["- (none)"]
    for label, key in (("Created", "created"), ("Modified", "modified"),
                       ("Deleted", "deleted"), ("Renamed", "renamed")):
        items = payload["files"].get(key) or []
        if items:
            lines.append(f"\n{label}: " + ", ".join(items))
    lines += ["", "Diffstat:", payload["diffstat"], "", "Diff:", payload["diff"]]
    return "\n".join(lines)


def _append_section(paths, cfg, payload, analysis):
    docs = paths.root / cfg["docs_dir"]
    docs.mkdir(parents=True, exist_ok=True)
    impl = docs / cfg["implementation_file"]
    header = f"## Iteration {payload['iteration']} - {payload['ts']}\n\n"
    with impl.open("a", encoding="utf-8") as f:
        f.write(header + analysis.strip() + "\n\n---\n\n")


def _process(paths, cfg, provider, ev_path, log):
    event = json.loads(ev_path.read_text(encoding="utf-8"))
    iteration = event["iteration"]
    if iteration <= config.read_state(paths).get("last_documented", 0):
        ev_path.unlink()  # already documented (crash after append, before ack)
        return
    payload = collector.build_payload(paths, event, cfg)
    empty = not any(payload["files"].values()) and not payload["diff"].strip()
    if cfg.get("skip_empty_iterations") and empty:
        log.info(f"iteration {iteration} has no changes; skipping")
        ev_path.unlink()
        return
    analysis = provider.analyze(_build_prompt(payload), cfg)
    # ponytail: append -> mark -> ack. A crash between append and mark can dup
    # a section; preferred over the alternative (marking first) which could drop one.
    _append_section(paths, cfg, payload, analysis)
    config.update_state(paths, last_documented=iteration, last_error=None)
    ev_path.unlink()
    log.info(f"iteration {iteration} documented")


def _handle_failure(paths, cfg, ev_path, err, log):
    try:
        event = json.loads(ev_path.read_text(encoding="utf-8"))
    except Exception:
        event = {}
    retries = event.get("_retries", 0) + 1
    log.error(f"iteration {event.get('iteration', '?')} failed (attempt {retries}): {err}")
    config.update_state(paths, last_error=str(err))
    if retries >= cfg.get("retry_cap", 3):
        paths.dead.mkdir(parents=True, exist_ok=True)
        ev_path.rename(paths.dead / ev_path.name)
        log.error(f"iteration {event.get('iteration', '?')} dead-lettered after {retries} attempts")
        return "dead"
    event["_retries"] = retries
    ev_path.write_text(json.dumps(event, indent=2), encoding="utf-8")
    return "retry"


def _drain(paths, log):
    cfg = config.load(paths)
    provider = get_provider(cfg["provider"])
    while True:
        events = sorted(p for p in paths.queue.glob("event-*.json") if p.suffix == ".json")
        if not events:
            break
        ev_path = events[0]
        try:
            _process(paths, cfg, provider, ev_path, log)
        except Exception as e:
            if _handle_failure(paths, cfg, ev_path, e, log) == "retry":
                break  # keep order; next spawn retries this event


def run():
    paths = config.paths(config.find_root())
    log = get_logger(paths)
    if not _acquire(paths):
        log.info("worker already running; exiting")
        return 0
    try:
        _drain(paths, log)
    finally:
        _release(paths)
    return 0
