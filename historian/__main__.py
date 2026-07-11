"""CLI entry point.  python -m historian <command>

Commands: init | hook <event> | worker | finalize | status
Only `init` and a no-op `hook` are implemented in Phase 1."""

import json
import sys
from pathlib import Path

from . import config, shadowgit

HOOKS = {"UserPromptSubmit": "prompt", "Stop": "stop"}


def _ensure_claude_hooks(root):
    """Idempotently wire the two Claude Code hooks into .claude/settings.json."""
    settings = root / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if settings.exists():
        try:
            data = json.loads(settings.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    hooks = data.setdefault("hooks", {})
    for event, sub in HOOKS.items():
        cmd = f"python -m historian hook {sub}"
        entries = hooks.setdefault(event, [])
        if not any(cmd in json.dumps(e) for e in entries):
            entries.append({"hooks": [{"type": "command", "command": cmd}]})
    settings.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _ensure_gitignore(root):
    gi = root / ".gitignore"
    lines = gi.read_text(encoding="utf-8").splitlines() if gi.exists() else []
    if ".historian/" not in lines:
        lines.append(".historian/")
        gi.write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_init():
    root = Path.cwd()
    p = config.paths(root)
    config.ensure_layout(p)
    cfg = config.load(p)
    config.write_excludes(p, cfg["exclude_globs"])
    _ensure_claude_hooks(root)
    _ensure_gitignore(root)
    if not shadowgit.is_initialized(p):
        shadowgit.init(p)
    # snapshot last so the baseline captures the fully-initialized project
    sha = shadowgit.snapshot(p, "historian: init baseline")
    config.update_state(p, last_shadow_commit=sha)
    print(f"historian initialized at {p.historian}")
    print(f"shadow baseline commit: {sha[:10]}")
    return 0


def cmd_hook(event):
    from . import hooks
    if event == "prompt":
        return hooks.prompt()
    if event == "stop":
        return hooks.stop()
    try:  # unknown event: drain stdin, exit 0
        sys.stdin.read()
    except Exception:
        pass
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else ""
    if cmd == "init":
        return cmd_init()
    if cmd == "hook":
        return cmd_hook(argv[1] if len(argv) > 1 else "")
    if cmd == "worker":
        from . import worker
        return worker.run()
    if cmd in ("finalize", "status"):
        print(f"historian: '{cmd}' not implemented yet", file=sys.stderr)
        return 0
    print("usage: python -m historian {init|hook <event>|worker|finalize|status}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    # hook must never break Claude: swallow errors and exit 0 for hook subcommand.
    try:
        sys.exit(main())
    except Exception as e:
        if len(sys.argv) > 1 and sys.argv[1] == "hook":
            sys.exit(0)
        print(f"historian error: {e}", file=sys.stderr)
        sys.exit(1)
