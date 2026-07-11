# AI Development Historian — User Manual

A practical, start-to-finish guide: install it once, wire up whichever model
CLI/API you have, and document your coding milestones on demand.

---

## 1. What it does (30 seconds)

You code with Claude Code (or anything). When you finish something meaningful,
you run **`/historian-save "what you built"`**. The historian:

1. Snapshots your files into a private *shadow* git repo (your real git is untouched).
2. Diffs against the previous save.
3. Sends the diff + your prompts to a model **you choose** (OpenCode, Gemini, Ollama, OpenAI, …).
4. Appends a senior-engineer-style entry to `docs/implementation.md`.

When the project matures, **`/historian-finalize`** produces
`PROJECT_ARCHITECTURE.md`, `KNOWLEDGE_BASE.md`, and `WORKFLOW.md`.

Nothing is automatic — *you* decide when a milestone is worth recording.

---

## 2. Prerequisites

- **Python 3.8+** and **git** on your PATH.
- **pipx** (recommended) to install the CLI in isolation:
  ```
  python -m pip install --user pipx
  python -m pipx ensurepath
  ```
  Restart your terminal afterward so `pipx`/`historian` land on PATH.
- **One model provider** — a CLI or an API key. See §6 for setup of each.

---

## 3. One-time install (per machine)

```
pipx install "C:\path\to\gemini"     # the historian repo folder; puts `historian` on PATH
historian install                     # provisions the /historian* slash commands globally
```

`historian install` writes the slash commands to `~/.claude/commands/`. Verify:

```
historian --help          # should print the usage line
```

If `historian` is "not found", your pipx path isn't active — restart the
terminal or run `python -m pipx ensurepath` again.

> Prefer not to use pipx? `pip install "C:\path\to\gemini"` also works, but pipx
> keeps it isolated from your other Python packages.

---

## 4. Set up a repository (per project)

From inside the project you want to document:

```
historian init          # or type /historian in Claude Code
```

This creates a `.historian/` folder (shadow repo, config, state), a `docs/`
folder for output, and adds a passive prompt-capture hook to
`.claude/settings.json`.

> **Restart your Claude Code session after the first `init`.** Claude reads hook
> config at startup, so the prompt-capture hook only becomes active in a fresh
> session. (Saving still works without it — the hook just enriches the "prompts"
> section of each entry.)

---

## 5. Daily workflow

| Step | Command | Notes |
|---|---|---|
| Do your work | — | Edit code with Claude Code as usual |
| Save a milestone | `/historian-save Added OAuth login` | One iteration documenting everything since the last save |
| Check state | `/historian-status` | Provider, iterations, **pending changes**, paused? |
| Pause recording | `/historian-pause` | `save` does nothing until resumed |
| Resume | `/historian-resume` | |
| Generate final docs | `/historian-finalize` | Architecture / knowledge-base / workflow |

Every slash command has a CLI equivalent (`historian save "…"`, `historian
status`, etc.) if you'd rather run it in a terminal.

**Typical session:**
```
# ... 45 minutes of work with Claude across many responses ...
/historian-save Implemented token refresh and retry logic
# -> "saved iteration 3"

/historian-status
# provider          : cli (opencode/nemotron-3-ultra-free)
# iterations saved  : 3
# pending changes   : 0 file(s) since last save

# ... project done ...
/historian-finalize
# -> docs/PROJECT_ARCHITECTURE.md, KNOWLEDGE_BASE.md, WORKFLOW.md
```

Output lands in `docs/` in the project. `docs/implementation.md` grows one
"## Iteration N: <title>" section per save.

---

## 6. Setting up your model provider

Provider config lives in **`.historian/config.json`** (created by `init`). Edit
it, save, and the next `historian save` uses it. Two built-in providers cover
almost everything.

### 6a. `cli` — any command that reads a prompt on stdin

The historian runs `command` + `args`, pipes the prompt to **stdin**, and reads
the answer from **stdout**. Test any candidate first:

```
echo "Reply with OK" | <command> <args>
```

If that prints text, it will work as a provider.

**OpenCode + Nemotron (free)** — the default:
```jsonc
{
  "provider": "cli",
  "command": "opencode",
  "args": ["run", "-m", "opencode/nemotron-3-ultra-free"],
  "env": { "OPENCODE_PERMISSION": "{\"edit\":\"deny\",\"bash\":\"deny\",\"webfetch\":\"deny\"}" }
}
```
Setup: install OpenCode, then `opencode auth login` (or configure a provider in
OpenCode). The `OPENCODE_PERMISSION` env keeps it a pure text tool (no file edits).
Check models with `opencode models`.

**Gemini CLI:**
```jsonc
{
  "provider": "cli",
  "command": "gemini",
  "args": ["-m", "gemini-2.5-pro"],
  "env": { "GEMINI_CLI_TRUST_WORKSPACE": "true" }
}
```
Setup: `npm i -g @google/gemini-cli`, then authenticate (`GEMINI_API_KEY` env var
or `gemini` login). The `GEMINI_CLI_TRUST_WORKSPACE=true` env is required for
headless runs. Verify: `echo "Say OK" | gemini -m gemini-2.5-pro`.

**Ollama (fully local, no key):**
```jsonc
{
  "provider": "cli",
  "command": "ollama",
  "args": ["run", "llama3.3"]
}
```
Setup: install Ollama, `ollama pull llama3.3`. Verify: `echo "Say OK" | ollama run llama3.3`.

**Any other CLI (Codex, a custom script, …):** same pattern — set `command` and
`args` so that piping a prompt to stdin returns text. If the tool needs env vars,
put them in `env`.

### 6b. `api` — OpenAI-compatible HTTP (OpenAI, OpenRouter, local servers)

No CLI needed; the historian calls `<base_url>/chat/completions` directly. The
API key is read from an **environment variable** (never stored in config).

**OpenAI:**
```jsonc
{
  "provider": "api",
  "model": "gpt-4o-mini",
  "api": { "base_url": "https://api.openai.com/v1", "api_key_env": "OPENAI_API_KEY" }
}
```
Then set the key in your environment (PowerShell):
```
setx OPENAI_API_KEY "sk-..."     # new terminals; or $env:OPENAI_API_KEY="sk-..." for the current one
```

**OpenRouter** (access many models via one key):
```jsonc
{
  "provider": "api",
  "model": "meta-llama/llama-3.3-70b-instruct",
  "api": { "base_url": "https://openrouter.ai/api/v1", "api_key_env": "OPENROUTER_API_KEY" }
}
```

**Ollama via its HTTP API** (alternative to the CLI):
```jsonc
{
  "provider": "api",
  "model": "llama3.3",
  "api": { "base_url": "http://localhost:11434/v1", "api_key_env": "OLLAMA_KEY" }
}
```
(Ollama ignores the key, but the field must exist — set `OLLAMA_KEY` to anything.)

### 6c. Switching providers

Just edit `provider` (and the related keys) in `.historian/config.json`. No
reinstall, no code change. Run `historian status` to confirm the active
provider/model.

---

## 7. Other configuration keys

In `.historian/config.json` (all optional; sensible defaults):

| Key | Default | Meaning |
|---|---|---|
| `timeout_sec` | `180` | Max seconds per model call |
| `retry_cap` | `3` | Attempts (with 2/8/30s backoff) before giving up |
| `diff_cap_bytes` | `200000` | Diff size before truncation (diffstat is always kept) |
| `skip_empty_iterations` | `true` | `save` is a no-op when nothing changed |
| `docs_dir` / `implementation_file` | `docs` / `implementation.md` | Where output goes |
| `prompt_template` | `iteration.md` | Which template drives each entry |
| `exclude_globs` | secrets + build dirs | Files never captured or sent (see §9) |

---

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| `historian: command not found` | pipx path not active — restart terminal or `python -m pipx ensurepath` |
| `save failed: <cmd> failed (...)` | Test `echo "hi" \| <command> <args>` directly; fix auth / model name / PATH |
| `save failed: ... returned empty output` | The model returned nothing; try another model or raise `timeout_sec` |
| `no changes since last save` | Nothing changed since the last snapshot (or all changes are in excluded paths) |
| Gemini headless error about trusted folders | Add `"GEMINI_CLI_TRUST_WORKSPACE": "true"` to `env` |
| Prompts not showing in entries | Restart the Claude Code session so the prompt hook activates |
| Something's stuck | `historian status` shows `last error`; details are in `.historian/historian.log` |

---

## 9. Privacy & secrets

Only the **prompt and the diff** leave your machine, and only to the provider
you configured. `exclude_globs` (default: `.env*`, `*.pem`, `*.key`, `*.pfx`,
`node_modules/`, `dist/`, `build/`) keeps matching files out of the shadow repo,
so they never appear in a diff or reach the model. Add your own patterns for
anything sensitive. For **zero data leaving the machine**, use a local provider
(Ollama via `cli` or `api`) — nothing else changes.

---

## 10. Quick reference

```
# once per machine
pipx install "<historian repo>"
historian install

# once per repo
historian init                 # then restart the Claude Code session

# every milestone
historian save "what I built"  # or /historian-save
historian status               # or /historian-status
historian pause / resume
historian finalize             # or /historian-finalize

# switch model: edit .historian/config.json -> provider/command/args or api
```
