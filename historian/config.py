"""Config, paths, and state for the historian. All state lives under
.historian/ in the project root. stdlib only."""

import json
from pathlib import Path
from types import SimpleNamespace

DEFAULTS = {
    "provider": "opencode",
    "model": "opencode/nemotron-3-ultra-free",
    "opencode_command": "opencode",
    "opencode_deny_tools": True,
    "docs_dir": "docs",
    "implementation_file": "implementation.md",
    "diff_cap_bytes": 200000,
    "provider_timeout_sec": 180,
    "retry_cap": 3,
    "skip_empty_iterations": True,
    "exclude_globs": [
        ".historian/", ".git/", "node_modules/", "dist/", "build/",
        "*.env", ".env*", "*.pem", "*.key", "*.pfx", "*.log",
    ],
}


def find_root(start=None):
    """Project root = nearest ancestor containing .historian/, else cwd."""
    start = Path(start or Path.cwd()).resolve()
    for d in (start, *start.parents):
        if (d / ".historian").is_dir():
            return d
    return start


def paths(root):
    root = Path(root).resolve()
    h = root / ".historian"
    return SimpleNamespace(
        root=root,
        historian=h,
        config=h / "config.json",
        state=h / "state.json",
        shadow_git=h / "shadow.git",
        shadow_excludes=h / "shadow.excludes",
        queue=h / "queue",
        dead=h / "dead",
        session=h / "session",
        prompts=h / "session" / "prompts.jsonl",
        lock=h / "worker.lock",
        log=h / "historian.log",
    )


def _read_json(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write_json(p, obj):
    Path(p).write_text(json.dumps(obj, indent=2), encoding="utf-8")


def load(paths):
    """Effective config: DEFAULTS overlaid with config.json (missing keys default)."""
    return {**DEFAULTS, **_read_json(paths.config, {})}


def ensure_layout(paths):
    """Create dirs and write config.json / state.json if absent. Idempotent."""
    for d in (paths.historian, paths.queue, paths.dead, paths.session):
        d.mkdir(parents=True, exist_ok=True)
    if not paths.config.exists():
        _write_json(paths.config, DEFAULTS)
    if not paths.state.exists():
        _write_json(paths.state, {"iteration": 0, "last_shadow_commit": None, "last_error": None})


def write_excludes(paths, globs):
    paths.shadow_excludes.write_text("\n".join(globs) + "\n", encoding="utf-8")


def read_state(paths):
    return _read_json(paths.state, {"iteration": 0, "last_shadow_commit": None, "last_error": None})


def update_state(paths, **fields):
    state = read_state(paths)
    state.update(fields)
    _write_json(paths.state, state)
    return state
