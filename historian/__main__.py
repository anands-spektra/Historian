"""CLI entry point.  python -m historian <command>

Commands: init | save [title] | status | finalize | hook <event>
Iterations are manual: `save` documents everything since the last save.
The only hook installed is a passive prompt logger."""

import json
import sys
from pathlib import Path

from . import config, shadowgit
from .log import get_logger

# Only a passive prompt-capture hook is installed; iterations are manual.
HOOKS = {"UserPromptSubmit": "prompt"}


def _ensure_claude_hooks(root):
    """Idempotently wire the passive prompt hook into .claude/settings.json."""
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
    config.write_excludes(p, config.effective_excludes(cfg))
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


def cmd_save(title):
    from . import document, hooks
    p = config.paths(config.find_root())
    if not p.historian.exists():
        print("historian not initialized here (run: python -m historian init)")
        return 1
    cfg = config.load(p)
    log = get_logger(p)
    state = config.read_state(p)
    if state.get("paused"):
        print("historian is paused (run: python -m historian resume)")
        return 0

    iteration = state.get("iteration", 0) + 1
    prev = state.get("last_shadow_commit")
    new = shadowgit.snapshot(p, f"historian: save {iteration}")
    event = {"iteration": iteration, "ts": hooks._now(), "session_id": None,
             "title": title, "prompts": [r.get("prompt", "") for r in hooks.drain_prompts(p)],
             "prev_commit": prev, "new_commit": new}
    try:
        documented = document.generate(p, cfg, event, log)
    except Exception as e:
        config.update_state(p, last_error=str(e))
        print(f"save failed: {e}")
        return 1
    if not documented:
        config.update_state(p, last_shadow_commit=new)  # advance baseline; no iteration
        print("no changes since last save - nothing to document")
        return 0
    config.update_state(p, iteration=iteration, last_shadow_commit=new,
                        last_documented=iteration, last_error=None)
    print(f"saved iteration {iteration}")
    return 0


def cmd_pause():
    p = config.paths(config.find_root())
    if not p.historian.exists():
        print("historian not initialized here (run: python -m historian init)")
        return 1
    config.update_state(p, paused=True)
    print("historian paused - /historian-save will do nothing until resumed")
    return 0


def cmd_resume():
    p = config.paths(config.find_root())
    if not p.historian.exists():
        print("historian not initialized here (run: python -m historian init)")
        return 1
    config.update_state(p, paused=False)
    print("historian resumed")
    return 0


def cmd_status():
    p = config.paths(config.find_root())
    if not p.historian.exists():
        print("historian not initialized here (run: python -m historian init)")
        return 1
    cfg = config.load(p)
    state = config.read_state(p)
    print(f"repository        : {p.root}")
    print(f"provider          : {cfg.get('provider')} ({cfg.get('model')})")
    print(f"iterations saved  : {state.get('iteration', 0)}")
    print(f"last documented   : {state.get('last_documented', 0)}")
    print(f"paused            : {'yes' if state.get('paused') else 'no'}")
    print(f"last error        : {state.get('last_error') or 'none'}")
    if shadowgit.is_initialized(p):
        pending = [ln for ln in shadowgit.status(p).splitlines() if ln.strip()]
        print(f"pending changes   : {len(pending)} file(s) since last save")
        for ln in pending[:20]:
            print(f"    {ln}")
        if len(pending) > 20:
            print(f"    ... and {len(pending) - 20} more")
    return 0


def cmd_hook(event):
    from . import hooks
    if event == "prompt":
        return hooks.prompt()
    try:  # any other event (e.g. a leftover Stop hook): drain stdin, exit 0
        sys.stdin.read()
    except Exception:
        pass
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else ""
    if cmd == "init":
        return cmd_init()
    if cmd == "save":
        return cmd_save(" ".join(argv[1:]).strip() or None)
    if cmd == "status":
        return cmd_status()
    if cmd == "pause":
        return cmd_pause()
    if cmd == "resume":
        return cmd_resume()
    if cmd == "finalize":
        from . import finalize
        return finalize.run()
    if cmd == "hook":
        return cmd_hook(argv[1] if len(argv) > 1 else "")
    print("usage: python -m historian {init|save [title]|status|pause|resume|finalize|hook <event>}",
          file=sys.stderr)
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
