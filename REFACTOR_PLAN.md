# Historian Refactor Plan — Provider-Agnostic & Manual/Milestone-Oriented

**Status:** Plan only (no implementation). Purpose unchanged: observe milestones,
capture changes, generate developer docs, build understanding over time.

The headline: this refactor **removes more than it adds**. Manual iterations make
most of the async machinery unnecessary, and "provider-agnostic" is achieved by
*generalizing* the seam that already exists — not by adding a provider module per
vendor. Net result is a smaller, simpler codebase.

---

## 1. Current architecture (what exists today)

| Module | Role |
|---|---|
| `__main__.py` | CLI dispatch: `init`, `hook`, `worker`, `finalize`, `status` |
| `config.py` | defaults, path resolution, state (JSON files) |
| `hooks.py` | `prompt` (log prompt) + `stop` (snapshot → enqueue → spawn worker) — **automatic per Claude response** |
| `shadowgit.py` | shadow git repo: init/snapshot/diff/name-status/diffstat |
| `collector.py` | `build_payload()` — prompts + diff + file buckets + diffstat, with size cap |
| `queue.py` | atomic file queue of iteration events |
| `worker.py` | detached drain loop, lock, retry/backoff, dead-letter, append section |
| `spawn.py` | cross-platform detached process launch |
| `providers/opencode.py`, `stub.py`, `__init__.py` | `analyze(prompt,cfg)->str`; `get_provider(name)` |
| `prompts/*.md` | iteration + 3 finalize templates |
| `finalize.py` | build context → 3 provider calls → 3 summary docs |
| `.claude/settings.json` | auto hooks (UserPromptSubmit, Stop) |

The provider seam (`get_provider(name)` + a module exposing `analyze(prompt, cfg)`)
is **already the "one interface" the new design asks for.** It just needs
generalizing and the async/auto layer around it removed.

---

## 2. Keep / Remove / Redesign

### KEEP (unchanged or near-unchanged)
- **Shadow git repo** (`shadowgit.py`) — the strongest decision; keep exactly. Snapshot-to-snapshot diff stays the capture mechanism.
- **`config.py` structure** — JSON config + `state.json` + path resolution. Generalize keys (below).
- **`collector.build_payload()`** — reused by manual save; keep the cap/truncation.
- **`log.py`** — rotating log, unchanged.
- **Provider contract** — a module exposing `analyze(prompt: str, cfg: dict) -> str`, resolved by `get_provider(name)`. This IS the interface; keep it. **No DI framework** — a function contract + importlib is the right amount of abstraction.
- **`prompts/` isolation** — templates already live in files; keep, expand content.
- **`.historian/` layout** — compatible; add a couple of state fields.

### REMOVE (deletion is the point)
- **Automatic iteration generation** — the `Stop` hook and everything it triggers.
- **`queue.py`** — with manual, synchronous save there is nothing to queue.
- **`spawn.py`** — no detached background worker needed.
- **`worker.py` drain loop / lock / dead-letter** — collapses into a synchronous `document.py` (retry/backoff logic can be salvaged and reused).
- **`providers/opencode.py`** — becomes a **config preset** of the generic `cli` provider, not code.
- **Per-project `.claude/settings.json` auto hooks** and per-project command files — replaced by global commands.

### REDESIGN
- **Provider layer → two generic providers** (see §3).
- **Config → flexible, provider-neutral** (see §4).
- **Auto hooks → manual slash commands** (see §5).
- **install (once, global) vs init (per repo)** (see §6).
- **Richer iteration template** (see §7).

---

## 3. Provider-agnostic architecture (the key simplification)

The vendor list (OpenCode, Gemini CLI, Codex, Ollama, Cursor, OpenRouter, OpenAI,
Anthropic, custom) collapses to **two built-in providers plus stub** — because
most of them are just "run a command, pipe text, read text":

| Provider module | Covers | How |
|---|---|---|
| `providers/cli.py` (generic) | OpenCode, Gemini CLI, Codex CLI, Ollama, Cursor-CLI, any custom script | Runs `config.command` + `config.args`, prompt on **stdin**, returns **stdout**; optional `config.env`, `config.timeout_sec` |
| `providers/api.py` | OpenAI, OpenRouter, Ollama `/v1`, any OpenAI-compatible endpoint | HTTP POST via stdlib `urllib`; `base_url`, `model`, key from an env var |
| `providers/stub.py` | tests / offline | deterministic, unchanged |

- Adding OpenCode/Gemini/Ollama = **config only**, zero new code (they're all `cli`).
- Anthropic native API (different shape) = a small future `providers/anthropic.py` if wanted — one file, proves the interface.
- The contract stays `analyze(prompt, cfg) -> str`. "Custom provider" = drop a `.py` in `providers/` and name it in config. That is the whole extension story — **resist a plugin registry / DI container.**

---

## 4. Flexible configuration

`.historian/config.json` — provider-neutral keys:

```jsonc
{
  "provider": "cli",                    // cli | api | stub | <custom module>
  "command": "opencode",                // cli providers
  "args": ["run", "-m", "opencode/nemotron-3-ultra-free"],
  "model": "opencode/nemotron-3-ultra-free",  // informational / used by api
  "timeout_sec": 180,
  "env": { "OPENCODE_PERMISSION": "{\"edit\":\"deny\",\"bash\":\"deny\"}" },
  "api": { "base_url": "https://openrouter.ai/api/v1", "api_key_env": "OPENROUTER_API_KEY" },
  "prompt_template": "iteration.md",    // overridable path
  "docs_dir": "docs",
  "diff_cap_bytes": 200000,
  "exclude_globs": ["...secrets/build..."],
  "paused": false
}
```

Presets documented in README (gemini-cli, ollama, opencode, openrouter) — copy/paste,
no code. Defaults in `config.py`; missing keys fall back so old configs keep working.

---

## 5. Manual commands (replace hooks)

All synchronous — the user triggers them and can wait a few seconds.

| Command | CLI | Action |
|---|---|---|
| `/historian` | `historian init` | Create `.historian/` in this repo (shadow, config, docs) |
| `/historian-save [title]` | `historian save` | **One** iteration: diff since last snapshot → provider → append → advance snapshot |
| `/historian-status` | `historian status` | repo, provider/model, iterations, last iteration, **pending changes** (live shadow diff), paused? |
| `/historian-finalize` | `historian finalize` | Generate the 3 summary docs |
| `/historian-pause` | `historian pause` | set `paused=true`; `save` refuses while paused |
| `/historian-resume` | `historian resume` | set `paused=false` |

**Prompts-since-last (recommended hybrid):** keep ONE passive, non-blocking
`UserPromptSubmit` hook that only appends prompts to `session/prompts.jsonl` — it
does **not** generate iterations. `save` bundles and rolls it. This preserves the
"prompts since previous iteration" section. If the user prefers zero hooks, drop it
and rely on the `[title]` argument + provider inferring intent from the diff. Make
it a config/init toggle; default = passive hook on.

---

## 6. Install once (global) vs init (per repo)

Mirror Ponytail/Graphify: install is global and one-time; repos only init.

- **`historian install`** (one-time): make the `historian` CLI available on PATH
  (`pipx install .` — isolated, recommended; `pip install .` fallback) and provision
  the global slash commands into `~/.claude/commands/historian*.md` (each wraps
  `historian <subcommand>`). Optionally register as a Claude Code plugin.
- **`historian init` / `/historian`** (per repo): create `.historian/` + config +
  shadow repo + `docs/` only. **Never reinstalls.**
- Package needs a minimal `pyproject.toml` with a `historian` console entry point.
- Removes reliance on the project-local `historian/` package + PYTHONPATH.

---

## 7. Richer iteration content

Expand `prompts/iteration.md` to require, in order: **Feature Title**, Timestamp,
User Objective, Prompts Since Previous Iteration, Files Created/Modified/Deleted,
Summary of Implementation, Why It Was Required, Important Classes, Important Methods,
Important Architectural Changes, Design Decisions, Before vs After, Risks, Testing
Performed (if detectable from diff — test files touched, assertions added),
Suggested Future Improvements, Learning Notes. Feed title/objective from the
`/historian-save [title]` argument; keep the senior-engineer voice.

---

## 8. Target module layout (after refactor)

```
historian/
  __main__.py         # thin dispatch table -> commands
  commands.py         # init, save, status, finalize, pause, resume (isolated fns)
  config.py           # generalized config + state (storage)
  storage.py          # (optional) state/paths helpers split from config if it grows
  shadowgit.py        # unchanged
  collector.py        # build_payload (reused by save)
  document.py         # render template + call provider + append section (ex-worker)
  finalize.py         # uses generic provider
  log.py
  providers/
    __init__.py       # get_provider(name)
    cli.py            # generic command+args+stdin
    api.py            # OpenAI-compatible HTTP
    stub.py
  prompts/            # iteration + 3 finalize templates (expanded)
pyproject.toml        # console entry point: historian
```
Deleted: `queue.py`, `spawn.py`, `worker.py`, `providers/opencode.py`, per-repo hooks.
`commands.py` is a flat module of functions — **no command-class hierarchy.**

---

## 9. Phased implementation plan

Each phase is independently implementable, testable, committable. Order favors the
core intent (provider-agnostic + manual) first; global install later.

**Phase R1 — Generic provider layer**
- Add `providers/cli.py` (command+args+stdin, env, timeout) and `providers/api.py`
  (OpenAI-compatible via urllib). Generalize config keys (command/args/model/
  timeout_sec/env/api/prompt_template). Keep `get_provider` + `stub`. Delete
  `opencode.py` (document it as a `cli` preset).
- Test: `cli` against `python -c` echo; `api` against a tiny local mock or skip if
  no key; stub. Verify config presets resolve.

**Phase R2 — Synchronous manual `save` (remove async)**
- Add `document.py` (render + provider call + append, with salvaged retry/backoff)
  and a `save` command: snapshot → diff vs `last_shadow_commit` → build payload →
  document → advance snapshot → roll prompts. Synchronous, single-shot.
- Delete `queue.py`, `spawn.py`, `worker.py`; drop `worker` from dispatch.
- Test: edit files → `save` → one section; `save` again with no changes → no-op
  (respect `skip_empty`). Offline via stub.

**Phase R3 — Remove auto hooks; wire manual commands**
- Remove the `Stop` hook. Keep optional passive `UserPromptSubmit` prompt-log hook
  (init toggle, default on). `init` writes only that (or nothing if disabled).
- Test: Claude responses no longer auto-document; only `save` does.

**Phase R4 — Pause/resume + richer status**
- `state.paused`; `save` refuses when paused. `pause`/`resume` commands. `status`
  shows pending shadow diff (files changed since last snapshot), provider/model,
  iteration count, last iteration, paused.
- Test: pause → save refuses; resume → save works; status fields correct.

**Phase R5 — Richer iteration template**
- Expand `iteration.md` per §7; `save [title]` passes title/objective.
- Test: a real save has every required subsection; title flows through.

**Phase R6 — Global install / init split**
- `pyproject.toml` + `historian install` (pipx + provision global `~/.claude/commands/historian*.md`). `init` becomes per-repo only. Remove project-local command files.
- Test: install once; `init` two separate repos; both drive the CLI with no PYTHONPATH.

**Phase R7 — Maintainability + docs**
- Extract `commands.py` dispatch; split `storage.py` only if `config.py` grows.
  Update README/DESIGN, update `test_historian.py` to the synchronous `save` path.
- Test: `python test_historian.py` green.

---

## 10. Backward compatibility & simplicity guardrails

- `.historian/` layout, shadow repo, and `docs/implementation.md` append format are
  **preserved** — existing logs stay valid.
- Old opencode-named config keys can be read as fallbacks during R1 so an existing
  `config.json` still works; new keys take precedence.
- **Anti-over-engineering:** no DI container, no plugin registry, no command classes,
  no message queue, no daemon. The abstractions are: one provider function, one
  config file, flat command functions. If a phase seems to need more, re-read this line.
