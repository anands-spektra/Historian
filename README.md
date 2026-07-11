# AI Development Historian

Automatically documents every Claude Code iteration so you can see **what
changed, why, and how the architecture evolved** — without spending Claude's
tokens on explanations. Each iteration is analyzed by a separate model
(OpenCode + free Nemotron) and appended to `docs/implementation.md`. When the
project is done, `finalize` generates architecture / knowledge-base / workflow
docs.

See `DESIGN.md` for the full architecture and rationale.

## How it works

```
UserPromptSubmit hook  -> record the prompt
Claude edits files
Stop hook              -> snapshot changes (shadow git) + enqueue + spawn worker
Worker (background)    -> diff -> model -> append "Iteration N" to implementation.md
```

Change capture uses a **shadow git repo** (`.historian/shadow.git`) separate
from your real repo, so it works whether or not you commit. The worker runs
detached, so Claude is never blocked; a broken historian never breaks Claude
(hooks always exit 0).

## Requirements

- Python 3.8+ and `git` on PATH
- [OpenCode](https://opencode.ai) authenticated with a provider that offers
  `opencode/nemotron-3-ultra-free` (verify with `opencode models`). Swap the
  model/provider in config if you prefer another.

## Setup

```
python -m historian init
```

This creates `.historian/` (config, state, shadow repo), wires the hooks into
`.claude/settings.json`, and adds `.historian/` to `.gitignore`. It is
idempotent — safe to re-run.

> **Note:** Claude Code reads hook config at **session startup**. After the
> first `init`, restart your Claude Code session so the hooks go live.

## Commands

| Command | What it does |
|---|---|
| `python -m historian init` | Set up (or re-sync) the historian in this project |
| `python -m historian status` | Iterations captured, queue depth, dead-letters, last error |
| `python -m historian finalize` | Generate PROJECT_ARCHITECTURE / KNOWLEDGE_BASE / WORKFLOW docs |
| `/historian-finalize` | Same as `finalize`, from inside Claude Code |

`hook` and `worker` are invoked automatically by the hooks; you don't run them.

## Configuration

`.historian/config.json` (missing keys fall back to defaults):

| Key | Default | Purpose |
|---|---|---|
| `provider` | `opencode` | Provider module in `historian/providers/` |
| `model` | `opencode/nemotron-3-ultra-free` | Model passed to `opencode run -m` |
| `opencode_deny_tools` | `true` | Deny agent tools so the model is a pure text transform |
| `docs_dir` / `implementation_file` | `docs` / `implementation.md` | Output location |
| `diff_cap_bytes` | `200000` | Diff size before truncation |
| `provider_timeout_sec` | `180` | Per-call timeout |
| `retry_cap` | `3` | Provider attempts before dead-lettering |
| `skip_empty_iterations` | `true` | Skip iterations with no file changes |
| `exclude_globs` | secrets + build dirs | Never captured or sent (see below) |

## Data residency & secrets

Only the **prompt and diff** leave your machine (to the model provider);
everything else stays local. `exclude_globs` (default includes `.env*`,
`*.pem`, `*.key`, `*.pfx`) keeps matching files out of the shadow repo entirely,
so they never appear in a diff or reach the provider. Add patterns for anything
sensitive in your project. For a fully offline setup, point `provider` at a
local model — no other changes needed.

## Extending

- **New model provider:** add `historian/providers/<name>.py` exposing
  `analyze(prompt, cfg) -> str`, then set `"provider": "<name>"`.
- **Change per-iteration content:** edit `historian/prompts/iteration.md`.
- **Change final docs:** edit the templates in `historian/prompts/`.

## Cross-platform

Windows-first, but cross-platform: the detached worker uses
`DETACHED_PROCESS` on Windows and `start_new_session=True` on POSIX; queue
writes are atomic via temp+rename on both. stdin is decoded as `utf-8-sig` to
tolerate a BOM from some shells.

## Test

```
python test_historian.py
```

Offline end-to-end smoke test (stub provider, no network).
