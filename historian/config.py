"""Config, paths, and state for the historian. All state lives under
.historian/ in the project root. stdlib only."""

import json
import os
from pathlib import Path
from types import SimpleNamespace

_DENY_TOOLS = '{"edit":"deny","bash":"deny","webfetch":"deny"}'

DEFAULTS = {
    "provider": "cli",                       # cli | api | stub | <custom module>
    "command": "opencode",                   # cli providers
    "args": ["run", "-m", "opencode/nemotron-3-ultra-free"],
    "model": "opencode/nemotron-3-ultra-free",
    "timeout_sec": 180,
    "stream": True,                          # show model output live while it runs
    "env": {"OPENCODE_PERMISSION": _DENY_TOOLS},
    "api": {"base_url": "https://api.openai.com/v1", "api_key_env": "OPENAI_API_KEY"},
    "prompt_template": "iteration.md",
    "docs_dir": "historian-docs",
    "implementation_file": "implementation.md",
    "diff_cap_bytes": 200000,
    "retry_cap": 3,
    "skip_empty_iterations": True,
    "exclude_globs": [
        ".historian/", ".git/", "node_modules/", "dist/", "build/",
        "*.env", ".env*", "*.pem", "*.key", "*.pfx", "*.log",
    ],
}


def _apply_legacy(filecfg):
    """Map pre-R1 (OpenCode-specific) config keys onto the generic schema so an
    existing .historian/config.json keeps working. ponytail: shim, not a migration."""
    if filecfg.get("provider") == "opencode":
        filecfg["provider"] = "cli"
        filecfg.setdefault("command", filecfg.get("opencode_command", "opencode"))
        if not filecfg.get("args"):
            model = filecfg.get("model", "opencode/nemotron-3-ultra-free")
            filecfg["args"] = ["run", "-m", model]
        if filecfg.get("opencode_deny_tools", True):
            filecfg.setdefault("env", {}).setdefault("OPENCODE_PERMISSION", _DENY_TOOLS)
    if "provider_timeout_sec" in filecfg and "timeout_sec" not in filecfg:
        filecfg["timeout_sec"] = filecfg["provider_timeout_sec"]
    return filecfg


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
        session=h / "session",
        prompts=h / "session" / "prompts.jsonl",
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
    """Effective config: DEFAULTS overlaid with config.json (missing keys default),
    with legacy key shims applied to the file config first."""
    return {**DEFAULTS, **_apply_legacy(_read_json(paths.config, {}))}


def global_config_path():
    """Machine-wide default config chosen at `historian install` time. Kept under
    ~/.claude/historian/ (NOT a .historian dir, so it can't confuse find_root)."""
    base = os.environ.get("HISTORIAN_HOME")
    root = Path(base) if base else (Path.home() / ".claude" / "historian")
    return root / "config.json"


def load_global():
    """The install-time default, or DEFAULTS if the user never ran install."""
    return {**DEFAULTS, **_read_json(global_config_path(), {})}


def write_global(cfg):
    p = global_config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    _write_json(p, cfg)


def ensure_layout(paths, base=None):
    """Create dirs and write config.json / state.json if absent. Idempotent.
    `base` is the config to seed a new repo with (defaults to DEFAULTS; init
    passes the install-time global default)."""
    for d in (paths.historian, paths.session):
        d.mkdir(parents=True, exist_ok=True)
    if not paths.config.exists():
        _write_json(paths.config, base or DEFAULTS)
    if not paths.state.exists():
        _write_json(paths.state, {"iteration": 0, "last_shadow_commit": None,
                                  "last_documented": 0, "last_error": None, "paused": False})


def effective_excludes(cfg):
    """exclude_globs plus the docs output dir — the historian must never track or
    document its own generated docs (that would self-document forever)."""
    return list(cfg.get("exclude_globs", [])) + [cfg.get("docs_dir", "docs").rstrip("/") + "/"]


def write_excludes(paths, globs):
    paths.shadow_excludes.write_text("\n".join(globs) + "\n", encoding="utf-8")


def read_state(paths):
    return _read_json(paths.state, {"iteration": 0, "last_shadow_commit": None, "last_error": None})


def update_state(paths, **fields):
    state = read_state(paths)
    state.update(fields)
    _write_json(paths.state, state)
    return state
