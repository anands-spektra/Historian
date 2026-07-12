# AI Development Historian

Documents your coding sessions as a series of **milestones you choose**. When
you finish a meaningful piece of work, you run one command and a separate model
(any CLI or API you configure) writes a senior-engineer-style entry into
`historian-docs/implementation.md`. When the project matures, `finalize` generates
architecture / knowledge-base / summary docs. The goal is to capture *what
changed and why* without spending your coding assistant's tokens explaining it.
You watch the model write each entry live in your terminal.

## The problem it solves

Documentation normally loses to whichever is true that day: it's written by
hand and goes stale, or it's written by the same coding assistant that just
wrote the code — which burns its context/tokens narrating instead of building,
and only happens if you remember to ask. Neither gives you a running, honest
log of *what changed and why* tied to milestones you actually care about
(not noisy per-commit chatter), and neither gives a newcomer a single
up-to-date architecture doc once the project has grown past the first sprint.

Historian offloads all of that to a **second, separately configured model**
(free/local by default), triggered **manually** — so it never taxes your
coding assistant's budget and never runs without you asking for it.

## How it works

1. `historian save "title"` snapshots your working tree into a private
   **shadow git repo** — independent of your real git, no commits required.
2. It diffs that snapshot against the previous save.
3. It bundles the diff, diffstat, changed-file list, and (if the passive
   prompt hook is active) your recent prompts into one payload.
4. That payload is sent to whichever model you configured (OpenCode, Gemini
   CLI, Ollama, OpenAI, OpenRouter, or a custom command) — you watch its
   output stream live in your terminal.
5. The model's write-up is appended as one `## Iteration N` section to
   `historian-docs/implementation.md`.
6. `historian finalize` re-reads the whole iteration log plus a capped
   source-file tree and makes three more model calls to produce
   `PROJECT_ARCHITECTURE.md`, `KNOWLEDGE_BASE.md`, and `SUMMARY.md`.

- **Manual, milestone-based** — you decide when an iteration is worth recording.
- **Provider-agnostic** — OpenCode, Gemini CLI, Ollama, OpenAI/OpenRouter, or any custom command. Configured, not hard-coded.
- **Local & git-independent** — a private *shadow* git repo captures changes; you never have to commit.

## Install once

```
pipx install <path-to-this-repo>     # puts the `historian` CLI on PATH
historian install                    # provisions the /historian* slash commands globally
```

`historian install` walks you through two prompts:

1. **Pick a provider/tool** — OpenCode, Gemini CLI, Ollama, OpenAI API,
   OpenRouter API, or configure-later.
2. **Enter the model name** to use with that tool — a suggested default is
   shown (e.g. `opencode/nemotron-3-ultra-free` for OpenCode); press Enter to
   accept it or type any other model that tool supports.

The result is saved as your machine-wide default (`~/.claude/historian/config.json`),
and the slash commands are written to `~/.claude/commands/` (override with
`HISTORIAN_COMMANDS_DIR`). You only do this once per machine. Every repo you
`init` inherits that default and can override it in its own `.historian/config.json`.

## Use in any repository

```
historian init          # or /historian — creates .historian/ here (once per repo)
# ... work with Claude Code for a while ...
historian save "Add OAuth login"     # or /historian-save Add OAuth login
```

`save` snapshots the shadow repo, diffs against the previous save, and appends
one "Iteration N" section to `historian-docs/implementation.md`.

> **Note:** Claude Code reads hook config at session startup. After the first
> `init` in a repo, restart the session so the passive prompt-capture hook goes
> live (it records your prompts so `save` can include them). `save` works either
> way — the hook only enriches the "prompts" section.

## Commands

| Slash | CLI | Action |
|---|---|---|
| `/historian` | `historian init` | Initialize the current repo |
| `/historian-save [title]` | `historian save [title]` | Document all changes since the last save as one iteration |
| `/historian-status` | `historian status` | Provider, iterations, last documented, pending changes, paused |
| `/historian-pause` | `historian pause` | Stop recording until resumed |
| `/historian-resume` | `historian resume` | Resume recording |
| `/historian-finalize` | `historian finalize` | Generate PROJECT_ARCHITECTURE / KNOWLEDGE_BASE / SUMMARY docs |

## Providers & configuration

`.historian/config.json` (missing keys fall back to defaults). Two built-in
providers cover almost everything:

**`cli`** — runs any command, prompt on stdin, answer on stdout:

```jsonc
{ "provider": "cli", "command": "opencode",
  "args": ["run", "-m", "opencode/nemotron-3-ultra-free"],
  "env": { "OPENCODE_PERMISSION": "{\"edit\":\"deny\",\"bash\":\"deny\"}" } }
```

Presets (`historian install` builds `args` from the model name you type; edit
`command`/`args`/`model` directly to change tool or model later):

| Tool | command | args |
|---|---|---|
| OpenCode | `opencode` | `["run","-m","<model>"]` |
| Gemini CLI | `gemini` | `["-m","<model>"]` |
| Ollama | `ollama` | `["run","<model>"]` |

**`api`** — OpenAI-compatible HTTP (OpenAI, OpenRouter, Ollama `/v1`):

```jsonc
{ "provider": "api", "model": "gpt-4o-mini",
  "api": { "base_url": "https://api.openai.com/v1", "api_key_env": "OPENAI_API_KEY" } }
```

Other keys: `timeout_sec`, `retry_cap`, `diff_cap_bytes`, `skip_empty_iterations`,
`docs_dir` (default `historian-docs`), `implementation_file`, `prompt_template`,
`exclude_globs`, and `stream` (default `true` — show the model's output live;
set `false` to run quietly).

## Architecture (at a glance)

| Module | Role |
|---|---|
| `__main__.py` | CLI dispatch + command functions (install/init/save/status/pause/resume/finalize/hook) |
| `config.py` | config defaults, path resolution, state; legacy-key shims |
| `shadowgit.py` | the shadow git repo: snapshot / diff / status |
| `collector.py` | build the model payload (prompts, file buckets, diffstat, capped diff) |
| `document.py` | render the iteration template, call the provider (retry/backoff), append the section |
| `finalize.py` | generate the three summary docs |
| `providers/` | `get_provider(name)`; `cli`, `api`, `stub` — one `analyze(prompt, cfg)` contract |
| `prompts/` | the iteration + finalize templates |

Flow: `save` → `shadowgit.snapshot` → `collector.build_payload` → `document.generate`
(→ provider) → append to `historian-docs/implementation.md` → advance the snapshot.

## Extending

- **New provider:** add `historian/providers/<name>.py` with `analyze(prompt, cfg) -> str`, set `"provider": "<name>"`. Nothing else changes.
- **Change iteration content:** edit `historian/prompts/iteration.md`.
- **Change final docs:** edit the templates in `historian/prompts/`.

## Data residency & secrets

Only the prompt and diff leave your machine (to the provider you configure).
`exclude_globs` (default: `.env*`, `*.pem`, `*.key`, `*.pfx`, build dirs) keeps
matching files out of the shadow repo, so they never appear in a diff or reach
the provider. The historian's own `historian-docs/` output is excluded too, so it
never documents itself. For a fully local setup, point `provider` at Ollama or a local
API — no other change needed.

## Cross-platform

Windows-first, cross-platform. stdin is decoded as `utf-8-sig` to tolerate a
BOM from some shells. Requires Python 3.8+ and `git` on PATH.

## Test

```
python test_historian.py
```

Offline end-to-end smoke test (stub provider, no network).
