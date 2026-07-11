"""Turn one iteration event into a documented section: render the template,
call the provider (with retry/backoff), append to implementation.md. Used
synchronously by the `save` command — no queue, no worker, no lock."""

import time
from pathlib import Path

from . import collector
from .providers import get_provider

_PROMPTS = Path(__file__).parent / "prompts"
_BACKOFF = [2, 8, 30]  # seconds between provider retries


def _format_files(files):
    out = []
    for label, key in (("Created", "created"), ("Modified", "modified"),
                       ("Deleted", "deleted"), ("Renamed", "renamed")):
        items = files.get(key) or []
        out.append(f"{label}: " + (", ".join(items) if items else "none"))
    return "\n".join(out)


def _render_prompt(cfg, payload):
    """Fill the iteration template. str.replace (not .format) because diffs
    contain braces. Template name is configurable (prompt_template)."""
    tpl = (_PROMPTS / cfg.get("prompt_template", "iteration.md")).read_text(encoding="utf-8")
    prompts = "\n".join(f"- {p}" for p in payload["prompts"]) or "- (none)"
    note = ("\n(NOTE: diff truncated due to size — rely on the diffstat and file "
            "lists for the rest.)") if payload["truncated"] else ""
    repl = {
        "[[ITERATION]]": str(payload["iteration"]),
        "[[TIMESTAMP]]": str(payload["ts"]),
        "[[TITLE]]": payload.get("title") or "(none given)",
        "[[PROMPTS]]": prompts,
        "[[FILES]]": _format_files(payload["files"]),
        "[[DIFFSTAT]]": payload["diffstat"] or "(none)",
        "[[DIFF]]": payload["diff"] or "(no diff)",
        "[[TRUNCATED_NOTE]]": note,
    }
    for k, v in repl.items():
        tpl = tpl.replace(k, v)
    return tpl


def analyze_with_retry(provider, prompt, cfg, log, label):
    attempts = max(1, cfg.get("retry_cap", 3))
    for i in range(attempts):
        try:
            return provider.analyze(prompt, cfg)
        except Exception as e:
            log.error(f"{label} provider attempt {i + 1}/{attempts} failed: {e}")
            if i + 1 >= attempts:
                raise
            time.sleep(_BACKOFF[min(i, len(_BACKOFF) - 1)])


def _append_section(paths, cfg, payload, analysis):
    docs = paths.root / cfg["docs_dir"]
    docs.mkdir(parents=True, exist_ok=True)
    impl = docs / cfg["implementation_file"]
    title = payload.get("title")
    head = f"Iteration {payload['iteration']}: {title}" if title else f"Iteration {payload['iteration']} - {payload['ts']}"
    header = f"## {head}\n\n"
    with impl.open("a", encoding="utf-8") as f:
        f.write(header + analysis.strip() + "\n\n---\n\n")


def generate(paths, cfg, event, log):
    """Document one iteration. Returns True if a section was written, False if
    the iteration had no changes and was skipped."""
    payload = collector.build_payload(paths, event, cfg)
    empty = not any(payload["files"].values()) and not payload["diff"].strip()
    if cfg.get("skip_empty_iterations") and empty:
        return False
    provider = get_provider(cfg["provider"])
    analysis = analyze_with_retry(provider, _render_prompt(cfg, payload), cfg, log, event["iteration"])
    _append_section(paths, cfg, payload, analysis)
    return True
