## Iteration 1 - 2026-07-11T17:26:03+05:30

### User Prompt
Refactor the AI Development Historian project to make it provider-agnostic and workflow-oriented. Key requirements: remove automatic iteration generation (make it manual via `/historian-save`), make initialization a one-time global install with per-repo init, create a provider interface supporting OpenCode, Gemini CLI, Codex, Ollama, OpenRouter, custom providers, add flexible configuration (provider, command, model, timeout, prompt template, CLI args), implement manual commands (`/historian`, `/historian-save`, `/historian-status`, `/historian-finalize`, `/historian-pause`, `/historian-resume`), keep the shadow git repository, and enrich iteration documentation with 17 specific sections.

### Summary of Changes
This iteration establishes the complete refactored architecture for the AI Development Historian. It introduces a provider-agnostic abstraction layer with a generic `analyze(prompt, cfg) -> str` interface, replaces automatic per-response iteration generation with a manual queue-based workflow triggered by Claude Code hooks, adds a detached background worker for async documentation generation, and creates all supporting infrastructure: configuration system, shadow git integration, atomic file queue, prompt templates, and end-to-end test. The codebase grows from a minimal skeleton to a functional pipeline with 19 files.

### Files Created / Modified / Deleted

**Created:**
- `.claude/commands/historian-finalize.md` — slash command to generate final architecture/knowledge/workflow docs
- `README.md` — comprehensive project documentation with setup, commands, config, extending guide
- `REFACTOR_PLAN.md` — detailed 10-phase implementation plan for the provider-agnostic refactor
- `historian/collector.py` — builds model-ready payload from queued events (prompts, diff, file buckets, diffstat)
- `historian/finalize.py` — generates PROJECT_ARCHITECTURE.md, KNOWLEDGE_BASE.md, WORKFLOW.md via provider
- `historian/hooks.py` — fast-path hook handlers: `prompt` logs user prompts, `stop` snapshots shadow repo + enqueues
- `historian/prompts/architecture.md` — template for PROJECT_ARCHITECTURE.md generation
- `historian/prompts/iteration.md` — template for per-iteration documentation (17 required sections)
- `historian/prompts/knowledge_base.md` — template for KNOWLEDGE_BASE.md generation
- `historian/prompts/workflow.md` — template for WORKFLOW.md generation
- `historian/providers/__init__.py` — provider registry via `get_provider(name)` using importlib
- `historian/providers/opencode.py` — OpenCode provider using `opencode run -m` with stdin prompt, tools denied
- `historian/providers/stub.py` — deterministic offline provider for testing
- `historian/queue.py` — atomic file-based iteration queue (temp+rename)
- `historian/spawn.py` — cross-platform detached subprocess launch (DETACHED_PROCESS on Windows, start_new_session on POSIX)
- `historian/worker.py` — detached drain loop: lock, retry/backoff, dead-letter, append to implementation.md
- `test_historian.py` — offline e2e smoke test using stub provider

**Modified:**
- `historian/__main__.py` — added `cmd_status`, `cmd_hook` dispatch for prompt/stop, wired worker/finalize commands
- `historian/shadowgit.py` — added `EMPTY_TREE` constant, `diff`, `name_status`, `diffstat` helpers

**Deleted:** None
**Renamed:** None

### What Was Implemented
The iteration builds a complete async documentation pipeline:

1. **Hook layer** (`hooks.py`): `prompt` appends user prompts to `session/prompts.jsonl`; `stop` snapshots the shadow git repo, drains prompts, creates an iteration event with prev/new commit SHAs, enqueues it atomically via `queue.py`, updates state, and spawns a detached worker via `spawn.py`.

2. **Queue** (`queue.py`): Single JSON file per iteration named `event-{iteration:06d}.json`; writes use temp+rename for atomicity on Windows/POSIX.

3. **Worker** (`worker.py`): Single-instance via lockfile with TTL-based stale reclaim (no `os.kill`). Drains queue oldest-first: builds payload via `collector.build_payload()` (categorizes files via `git diff --name-status`, computes diffstat, truncates diff at configurable byte cap), renders the iteration template, calls provider with retry/backoff (3 attempts, 2/8/30s), appends to `docs/implementation.md`, marks `last_documented` in state, acknowledges by deleting queue file. On exhausted retries, moves event to `dead/` and stops drain.

4. **Collector** (`collector.py`): `build_payload()` computes unified diff between commits, parses `--name-status` into created/modified/deleted/renamed/copied buckets, returns structured dict with iteration, timestamp, prompts, files, diffstat, diff (truncated if >200KB), and truncation flag.

5. **Provider abstraction** (`providers/__init__.py` + `opencode.py` + `stub.py`): `get_provider(name)` dynamically imports `historian.providers.{name}`; each provider exposes `analyze(prompt: str, cfg: dict) -> str`. OpenCode provider runs `opencode run -m <model>` with prompt on stdin, denies agent tools via `OPENCODE_PERMISSION` env, 180s timeout. Stub returns fixed message for offline testing.

6. **Finalize** (`finalize.py`): Reads full iteration log + source tree (filtered by exclude_globs), builds context (file tree + iteration log + source excerpts capped at 400KB), makes one provider call per template (architecture/knowledge_base/workflow), writes three output files.

7. **CLI** (`__main__.py`): Dispatch for `init`, `hook prompt|stop`, `worker`, `status`, `finalize`. `init` creates `.historian/` layout, writes excludes, installs Claude hooks, initializes shadow repo, snapshots baseline. `status` reports iterations, queue depth, dead letters, worker lock, last error.

8. **Shadow git** (`shadowgit.py`): Added `diff`, `name_status`, `diffstat` wrappers; `EMPTY_TREE` constant for first-iteration base.

9. **Templates** (`prompts/*.md`): Structured prompts for iteration documentation (17 sections) and three final summary docs.

10. **Test** (`test_historian.py`): Creates temp repo, runs `init`, forces stub provider, creates/modifies files, snapshots, enqueues, runs worker, verifies iteration appended, queue drained, idempotent re-run.

### Why It Was Needed
The original design generated an iteration automatically after every Claude response, creating noise instead of meaningful milestone documentation. The tool was coupled to OpenCode and lacked a provider interface. Configuration was rigid. No manual commands existed for user-controlled documentation. The refactor addresses all nine design goals from the prompt: manual iterations, one-time install, provider-agnostic architecture, flexible config, manual commands, shadow repo retention, richer iteration content, and maintainable loose coupling.

### Important Classes / Functions Introduced

- `historian/providers/__init__.py:get_provider(name)` — dynamic provider registry, returns module with `analyze(prompt, cfg)`
- `historian/providers/opencode.py:analyze(prompt, cfg)` — OpenCode provider, stdin prompt, tools denied
- `historian/providers/stub.py:analyze(prompt, cfg)` — deterministic offline provider
- `historian/collector.py:build_payload(paths, event, cfg)` — constructs model-ready payload from shadow git diff
- `historian/queue.py:enqueue(paths, event)` — atomic queue write (temp+rename)
- `historian/worker.py:run()` — detached drain loop with lock, retry, dead-letter, append
- `historian/worker.py:_analyze_with_retry(provider, prompt, cfg, log, iteration)` — retry/backoff wrapper
- `historian/hooks.py:prompt()` — logs user prompt to session/prompts.jsonl
- `historian/hooks.py:stop()` — snapshots shadow repo, enqueues iteration, spawns worker
- `historian/spawn.py:spawn_detached(argv, cwd)` — cross-platform fire-and-forget subprocess
- `historian/finalize.py:run()` — generates three summary docs from iteration log + source
- `historian/__main__.py:cmd_init()` — per-repo initialization (config, hooks, shadow repo, baseline snapshot)
- `historian/__main__.py:cmd_status()` — reports iterations, queue, dead letters, worker state, last error
- `historian/shadowgit.py:EMPTY_TREE` — Git empty tree hash for first-iteration diff base
- `historian/shadowgit.py:diff/name_status/diffstat(paths, a, b)` — git diff wrappers

### Important Design Decisions

1. **Provider interface = single function `analyze(prompt, cfg) -> str`** — no DI container, no base class, just importlib + convention. Adding a provider = drop a `.py` in `providers/`. This matches the "one interface" requirement and keeps extension trivial.

2. **Shadow git as source of truth** — decouples historian from user's git workflow. User never forced to commit. Diff always between historian snapshots.

3. **Async via detached worker + file queue** — hooks exit 0 instantly (never block Claude). Worker runs in background, survives hook process death. Lockfile with TTL reclaim avoids stale locks without `os.kill` (Windows-incompatible).

4. **Atomic queue writes via temp+rename** — works on Windows and POSIX; no partial reads.

5. **Append-only documentation** — iterations appended to `implementation.md`; never rewritten. Crash between append and state mark can duplicate a section (preferred over losing one).

6. **Prompt logging via passive `UserPromptSubmit` hook** — captures "prompts since last iteration" without generating iterations. `stop` hook drains and rolls the file.

7. **Diff truncation at byte cap + diffstat fallback** — keeps provider input bounded; diffstat preserves structural summary.

8. **Configuration via JSON with fallbacks** — missing keys fall back to defaults; old configs keep working.

9. **Stub provider for offline testing** — entire pipeline testable without network/API keys.

10. **Cross-platform detached spawn** — `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` on Windows, `start_new_session=True` on POSIX; stdin/stdout/stderr to DEVNULL.

### Before vs After Behavior

| Aspect | Before | After |
|--------|--------|-------|
| Iteration trigger | Automatic after every Claude response | Manual via `/historian-save` (queued by `Stop` hook) |
| Provider | Hardcoded to OpenCode | Pluggable via `providers/<name>.py` + config `provider` key |
| Configuration | Fixed keys, OpenCode-specific | Flexible: provider, command, args, model, timeout, env, api, prompt_template |
| Commands | None (auto-only) | `init`, `hook`, `worker`, `status`, `finalize` + slash commands |
| Installation | Per-project | Global `historian install` (planned), per-repo `init` |
| Documentation content | Minimal | 17-section senior-engineer template |
| Async processing | None | Detached worker + atomic queue + retry/dead-letter |
| Change capture | Unknown | Shadow git snapshot-to-snapshot diff |
| Testing | None | Offline e2e smoke test with stub provider |

### Possible Risks

1. **Worker lock stale reclaim race** — TTL-based reclaim assumes worker heartbeat updates lock mtime; if worker crashes mid-iteration, next worker may reclaim lock and process same event (append-only mitigates duplication, but state `last_documented` prevents double-mark).

2. **Dead-letter stops entire drain** — On provider failure after retries, worker moves event to `dead/` and exits. Subsequent queue events stall until manual intervention. Could process remaining events instead.

3. **Prompt hook only captures `UserPromptSubmit`** — Misses prompts from other sources (e.g., slash commands, inline edits). May need broader capture.

4. **Diff truncation loses detail** — 200KB cap may cut critical changes; diffstat helps but not a full substitute. Configurable but default may surprise.

5. **Shadow git excludes via `core.excludesFile`** — Relies on git respecting the excludes file; patterns must match gitignore syntax exactly.

6. **No iteration title/objective capture** — Current `stop` hook doesn't accept a title; `save` command (planned) will add this. Iterations currently timestamp-only.

7. **Provider timeout hardcoded in retry logic** — `_lock_ttl` uses `provider_timeout_sec * 2`; if provider hangs beyond timeout, lock may be reclaimed mid-call.

8. **State file corruption risk** — `config.update_state` writes JSON; concurrent worker + hook could race (though hook only updates `iteration`/`last_shadow_commit`, worker updates `last_documented`/`last_error`).

### What You Should Understand as the Developer

1. **The provider seam is the extension point** — `get_provider(name)` + `analyze(prompt, cfg)` is the entire interface. To add Gemini CLI, create `providers/gemini.py` with `analyze()` running `gemini -p` or similar. No other code changes.

2. **Manual iterations = `Stop` hook enqueues, worker documents** — The `Stop` hook does the heavy lifting (snapshot, enqueue, spawn). The worker is a separate process. If worker fails, events pile in queue; `status` shows depth. Run `worker` manually to drain.

3. **Shadow git is the source of truth for diffs** — `shadowgit.snapshot()` commits everything (minus excludes). `collector.build_payload()` diffs against `prev_commit`. The user's actual git history is irrelevant.

4. **Templates drive output** — Edit `prompts/iteration.md` to change per-iteration sections; edit `prompts/architecture.md` etc. for finalize output. The `[[PLACEHOLDER]]` replacement in `worker.py:_render_prompt()` and `finalize.py` is simple string replace (not templating engine) — diffs with braces are safe.

---

## Iteration 2 - 2026-07-11T17:35:49+05:30

### User Prompt
"ok lets start R1 phase" — begin the first refactor phase (R1) of the provider-agnostic refactor initiated in Iteration 1.

### Summary of Changes
This iteration replaces the hardcoded OpenCode provider with a generic provider abstraction layer. The OpenCode-specific provider (`providers/opencode.py`) is removed and replaced by two generic providers: `cli.py` (runs any command that reads prompt from stdin, writes response to stdout) and `api.py` (OpenAI-compatible HTTP endpoint). Configuration is migrated to a generic schema (`provider`, `command`, `args`, `model`, `timeout_sec`, `env`, `api`, `prompt_template`) with a backward-compatibility shim that maps legacy OpenCode-specific keys (`opencode_command`, `opencode_deny_tools`, `provider_timeout_sec`) onto the new schema. The worker's lock TTL calculation is updated to use the new `timeout_sec` config key with a fallback to the legacy `provider_timeout_sec`.

### Files Created / Modified / Deleted

**Created:**
- `docs/implementation.md` — Iteration 1 documentation (146 lines)
- `historian/providers/api.py` — OpenAI-compatible HTTP provider using stdlib `urllib`
- `historian/providers/cli.py` — Generic CLI provider (stdin/stdout, configurable command/args/env)

**Modified:**
- `historian/config.py` — New generic config schema with legacy key migration shim (`_apply_legacy`)
- `historian/worker.py` — Lock TTL now reads `timeout_sec` (with legacy fallback)

**Deleted:**
- `historian/providers/opencode.py` — OpenCode-specific provider (replaced by generic `cli` provider)

### What Was Implemented

1. **Provider abstraction layer** (`providers/__init__.py` unchanged, but registry pattern established in Iteration 1): two new provider modules implement the `analyze(prompt, cfg) -> str` interface:
   - `cli.py`: Runs `command + args` with prompt on stdin, captures stdout. Config-driven: `command`, `args`, `env`, `timeout_sec`. Covers OpenCode, Gemini CLI, Codex, Ollama CLI, custom scripts.
   - `api.py`: POSTs to OpenAI-compatible `/chat/completions` endpoint using stdlib `urllib`. Config-driven: `api.base_url`, `api.api_key_env`, `model`, `timeout_sec`. Covers OpenAI, OpenRouter, Ollama `/v1`, any compatible endpoint.

2. **Config migration shim** (`config.py:_apply_legacy`): Detects legacy `provider: "opencode"` and maps:
   - `opencode_command` → `command`
   - `model` + `opencode_command` → `args: ["run", "-m", <model>]`
   - `opencode_deny_tools: true` → `env.OPENCODE_PERMISSION = '{"edit":"deny","bash":"deny","webfetch":"deny"}'`
   - `provider_timeout_sec` → `timeout_sec`
   This allows existing `.historian/config.json` files to work unchanged.

3. **Worker lock TTL update** (`worker.py:_lock_ttl`): Reads `cfg.get("timeout_sec", cfg.get("provider_timeout_sec", 180)) * 2` with 300s minimum, aligning with new config key.

### Why It Was Needed
Iteration 1 established the provider-agnostic architecture but left the OpenCode provider as the sole implementation. R1 phase delivers the actual provider implementations that make the abstraction real: a generic CLI provider covering all CLI-based tools and an OpenAI-compatible HTTP provider covering all API-based providers. The config migration shim ensures zero-downtime upgrade for existing users.

### Important Classes / Functions Introduced
- `historian/providers/cli.py:analyze(prompt, cfg)` — Generic CLI provider, runs configured command with stdin/stdout
- `historian/providers/api.py:analyze(prompt, cfg)` — OpenAI-compatible HTTP provider using stdlib `urllib`
- `historian/config.py:_apply_legacy(filecfg)` — Legacy config key migration shim (non-migrating, applied at load time)

### Important Design Decisions
1. **Provider interface remains a single function** — `analyze(prompt, cfg) -> str` keeps extension trivial (drop a `.py` in `providers/`).
2. **CLI provider uses stdin for prompt** — Avoids command-line length limits; works for any tool accepting stdin.
3. **API provider uses stdlib only** — Zero dependencies; works with OpenAI, OpenRouter, Ollama, local LLMs.
4. **Legacy config shim at load time, not migration** — `_apply_legacy` runs inside `load()` each time; original `config.json` never rewritten. Zero risk of corrupting user config.
5. **Lock TTL derives from provider timeout** — Worker lock outlives a single provider call (2x timeout, min 5min) so crash mid-call doesn't trigger premature lock steal.

### Before vs After Behavior

| Aspect | Before (Iteration 1) | After (Iteration 2) |
|--------|---------------------|---------------------|
| Provider | Hardcoded `opencode.py` only | Pluggable: `cli`, `api`, `stub`, or custom |
| Config keys | `provider`, `model`, `opencode_command`, `opencode_deny_tools`, `provider_timeout_sec` | Generic: `provider`, `command`, `args`, `model`, `timeout_sec`, `env`, `api`, `prompt_template` |
| OpenCode usage | Hardcoded `opencode run -m <model>` with `OPENCODE_PERMISSION` | Config-driven: `provider: "cli"`, `command: "opencode"`, `args: ["run", "-m", "model"]`, `env.OPENCODE_PERMISSION` |
| HTTP API providers | Not supported | Supported via `provider: "api"` + `api.base_url`, `api.api_key_env`, `model` |
| Config migration | Manual (user edits config.json) | Automatic at load time via `_apply_legacy` |

### Possible Risks
1. **Legacy shim only handles `provider: "opencode"`** — If a user had custom provider name but used OpenCode keys, migration won't trigger. Low risk (Iteration 1 only shipped OpenCode).
2. **CLI provider assumes stdin/stdout protocol** — Tools requiring prompt as CLI arg (not stdin) won't work without wrapper script. Mitigation: user can write a thin wrapper.
3. **API provider requires `model` in config** — No default; will raise `RuntimeError` if missing. Fail-fast is intentional.
4. **Lock TTL uses `timeout_sec * 2`** — If provider hangs beyond timeout but process doesn't exit, lock may be reclaimed mid-call. Worker refreshes lock mtime after each event as heartbeat.

### What You Should Understand as the Developer
1. **Adding a new provider = one file in `providers/`** — Implement `analyze(prompt, cfg)`, register nothing else. The registry uses `importlib.import_module(f"historian.providers.{name}")`.
2. **Config is the contract** — Provider behavior is entirely config-driven. `cli` provider runs whatever `command + args` you give it. `api` provider hits whatever `base_url` you configure.
3. **Legacy configs just work** — `_apply_legacy` runs on every load. Users upgrading from Iteration 1 don't touch their config.

---

