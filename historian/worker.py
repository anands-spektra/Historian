"""Detached worker: drains the queue oldest-first, documents each iteration
via the provider, appends to docs/implementation.md. Single-instance via a
lockfile. Append-only; never rewrites prior sections."""

import json
import os
import time
from pathlib import Path

from . import collector, config
from .log import get_logger
from .providers import get_provider

_TEMPLATE = Path(__file__).parent / "prompts" / "iteration.md"
_BACKOFF = [2, 8, 30]  # seconds between provider retries


def _create_lock(paths):
    fd = os.open(str(paths.lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)


def _lock_ttl(cfg):
    # Must exceed one event's max provider time; the drain refreshes the lock's
    # mtime after each event as a heartbeat. ponytail: TTL-based staleness (no
    # os.kill liveness — signal 0 can terminate a process on Windows).
    return max(cfg.get("provider_timeout_sec", 180) * 2, 300)


def _acquire(paths, cfg):
    """Single-instance lock with stale reclaim: a lock whose mtime is older than
    the TTL belongs to a dead worker and is taken over."""
    try:
        _create_lock(paths)
        return True
    except FileExistsError:
        pass
    try:
        age = time.time() - paths.lock.stat().st_mtime
    except FileNotFoundError:
        age = None  # vanished between create and stat
    if age is None or age > _lock_ttl(cfg):
        try:
            paths.lock.unlink()
        except FileNotFoundError:
            pass
        try:
            _create_lock(paths)
            return True
        except FileExistsError:
            return False
    return False


def _release(paths):
    try:
        paths.lock.unlink()
    except FileNotFoundError:
        pass


def _heartbeat(paths):
    try:
        os.utime(paths.lock, None)
    except OSError:
        pass


def _format_files(files):
    out = []
    for label, key in (("Created", "created"), ("Modified", "modified"),
                       ("Deleted", "deleted"), ("Renamed", "renamed")):
        items = files.get(key) or []
        out.append(f"{label}: " + (", ".join(items) if items else "none"))
    return "\n".join(out)


def _render_prompt(payload):
    """Fill the iteration template. Uses str.replace (not .format) because
    diffs contain braces."""
    tpl = _TEMPLATE.read_text(encoding="utf-8")
    prompts = "\n".join(f"- {p}" for p in payload["prompts"]) or "- (none)"
    note = ("\n(NOTE: diff truncated due to size — rely on the diffstat and file "
            "lists for the rest.)") if payload["truncated"] else ""
    repl = {
        "[[ITERATION]]": str(payload["iteration"]),
        "[[TIMESTAMP]]": str(payload["ts"]),
        "[[PROMPTS]]": prompts,
        "[[FILES]]": _format_files(payload["files"]),
        "[[DIFFSTAT]]": payload["diffstat"] or "(none)",
        "[[DIFF]]": payload["diff"] or "(no diff)",
        "[[TRUNCATED_NOTE]]": note,
    }
    for k, v in repl.items():
        tpl = tpl.replace(k, v)
    return tpl


def _analyze_with_retry(provider, prompt, cfg, log, iteration):
    attempts = max(1, cfg.get("retry_cap", 3))
    for i in range(attempts):
        try:
            return provider.analyze(prompt, cfg)
        except Exception as e:
            log.error(f"iteration {iteration} provider attempt {i + 1}/{attempts} failed: {e}")
            if i + 1 >= attempts:
                raise
            time.sleep(_BACKOFF[min(i, len(_BACKOFF) - 1)])


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
    analysis = _analyze_with_retry(provider, _render_prompt(payload), cfg, log, iteration)
    # ponytail: append -> mark -> ack. A crash between append and mark can dup a
    # section; preferred over marking first, which could drop one.
    _append_section(paths, cfg, payload, analysis)
    config.update_state(paths, last_documented=iteration, last_error=None)
    ev_path.unlink()
    log.info(f"iteration {iteration} documented")


def _dead_letter(paths, ev_path, err, log):
    config.update_state(paths, last_error=str(err))
    paths.dead.mkdir(parents=True, exist_ok=True)
    try:
        ev_path.rename(paths.dead / ev_path.name)
    except FileNotFoundError:
        pass
    log.error(f"dead-lettered {ev_path.name}: {err}")


def _drain(paths, cfg, log):
    provider = get_provider(cfg["provider"])
    while True:
        events = sorted(p for p in paths.queue.glob("event-*.json") if p.suffix == ".json")
        if not events:
            break
        ev_path = events[0]
        try:
            _process(paths, cfg, provider, ev_path, log)
        except Exception as e:
            # retries are exhausted (in _analyze_with_retry) -> dead-letter and stop
            # this run so we don't churn the rest of the queue on a down provider.
            _dead_letter(paths, ev_path, e, log)
            break
        _heartbeat(paths)  # keep the lock fresh across a long drain


def run():
    paths = config.paths(config.find_root())
    log = get_logger(paths)
    cfg = config.load(paths)
    if not _acquire(paths, cfg):
        log.info("worker already running; exiting")
        return 0
    try:
        _drain(paths, cfg, log)
    finally:
        _release(paths)
    return 0
