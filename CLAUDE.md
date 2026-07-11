# CLAUDE.md — AI Development Historian

Instructions for Claude Code working in this repository.

## What this project is

A **manual, provider-agnostic** tool that documents coding milestones. The user
runs `historian save "<title>"` when they finish something meaningful; it
snapshots the changes into a private **shadow git repo** (independent of the
user's real git), sends the diff + prompts to a **configurable model**, and
appends a senior-engineer-style entry to `historian-docs/implementation.md`.
`historian finalize` generates `PROJECT_ARCHITECTURE.md`, `KNOWLEDGE_BASE.md`,
and a plain-language `SUMMARY.md`. The goal is to offload documentation to a
second model so it doesn't cost the coding assistant's tokens.

## Layout (`historian/` package — stdlib only, no dependencies)

| Module | Role |
|---|---|
| `__main__.py` | CLI: `install \| init \| save \| status \| pause \| resume \| finalize \| hook` |
| `config.py` | defaults, path resolution, state, global default, legacy-key shims |
| `shadowgit.py` | shadow repo: `snapshot` / `diff` / `name_status` / `diffstat` / `status` |
| `collector.py` | `build_payload` — prompts, file buckets, diffstat, size-capped diff |
| `document.py` | render iteration template, call provider (retry/backoff), append section |
| `finalize.py` | the three summary docs |
| `providers/` | `get_provider(name)`; `cli` (streams output), `api` (OpenAI-compatible), `stub` |
| `prompts/` | `iteration.md` + `architecture/knowledge_base/summary.md` templates |

Output goes to `historian-docs/`. Runtime state lives in `.historian/` (gitignored):
shadow repo, `config.json`, `state.json`, `session/prompts.jsonl`, log.

## Conventions (follow these)

- **Python stdlib ONLY.** No third-party dependencies — keep it installable with
  zero deps. If tempted to add a package, a few lines of stdlib almost always do.
- **Provider contract:** a module in `providers/` exposing
  `analyze(prompt: str, cfg: dict) -> str`. Adding a provider = one new file +
  a config change. No base classes, no plugin registry, no DI framework.
- **Templates use `str.replace` tokens** (`[[DIFF]]`, `[[FILES]]`, …), NOT
  `str.format` — diffs contain `{}` braces.
- **Ponytail style:** smallest change that works; delete over add; no speculative
  abstractions or config for values that never change.
- The docs output folder is **excluded from the shadow repo** so the historian
  never documents its own output. `effective_excludes()` is the single source.
- stdin is decoded `utf-8-sig` (tolerate a BOM from some shells). Windows-first,
  cross-platform (`os.name` branches where needed).
- Hooks/commands that Claude Code invokes must **never break the session** —
  the `hook` path always exits 0.

## Running & testing

- Installed **editable** (`pip install --user -e .`), so the `historian` CLI runs
  from this source — edits take effect immediately.
- Offline end-to-end test: `python test_historian.py` (stub provider, no network).
  Run it before committing non-trivial changes.
- Run from source without install: `PYTHONPATH=. python -m historian <cmd>`.
- Real saves hit the configured provider (default OpenCode/Nemotron). Prefer the
  `stub` provider for tests to stay offline and deterministic.

## Git & commits

- Local git only. One commit per logical change; message style `type: summary`.
- Never commit `build/` or `*.egg-info/` (gitignored — pip build artifacts).
- End commit messages with the Co-Authored-By trailer.

## Docs map

- `README.md` / `USER_MANUAL.md` — **current** usage & setup (keep these accurate).
- `DESIGN.md` — **historical** v1 design (auto/OpenCode-coupled). Do not treat as current.
- `REFACTOR_PLAN.md` — the v1→v2 refactor plan (phases R1–R7).
