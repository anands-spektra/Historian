---
name: historian
description: Document a development milestone or generate project docs with the AI Development Historian. Use when the user asks to save/record a milestone, "document what we built", "run historian", generate project architecture/knowledge-base/summary docs, or check historian status. Runs the local `historian` CLI — do NOT hand-write the docs yourself; the whole point is to offload documentation to the historian's configured model.
---

# Historian skill

The AI Development Historian documents coding milestones by snapshotting the
project into a private shadow git repo, sending the diff to a configured model,
and writing docs into `historian-docs/`. **Always invoke the CLI — never write
the iteration docs yourself.** Delegating the writing is the point (it saves the
main assistant's tokens).

## When to use

| User intent | Command |
|---|---|
| "Save / record this milestone", "document what we built" | `historian save "<short feature title>"` |
| "Generate the project docs / architecture / summary" | `historian finalize` |
| "What's the historian status / what's pending?" | `historian status` |
| "Stop / pause recording" · "resume" | `historian pause` · `historian resume` |
| Historian not set up in this repo yet | `historian init` (once), then `save` |

## How to run

Run the CLI via the terminal and report the outcome to the user:

- **Save:** `historian save "<title>"` — derive a concise title from what was
  built this session. It documents everything since the last save.
- **Finalize:** `historian finalize` — writes `PROJECT_ARCHITECTURE.md`,
  `KNOWLEDGE_BASE.md`, `SUMMARY.md` into `historian-docs/`.
- **Status:** `historian status`.

If `historian` is not on PATH, run `python -m historian <cmd>` from the repo root.

## Notes

- Output **streams live** in the terminal; the entry is appended to
  `historian-docs/implementation.md`.
- `save` is a **no-op** if nothing changed since the last save — that's expected.
- On provider failure it prints `save failed: …` (exit 1), writes nothing, and
  loses no work — fixing the provider config and re-running `save` documents
  everything since the last successful save.
- The provider/model is set in `.historian/config.json` (per repo) or the global
  default from `historian install`. Don't change it unless the user asks.
- Do not pre-summarize the diff for the model or write the section yourself —
  just run `save` and let the historian's model produce the documentation.
