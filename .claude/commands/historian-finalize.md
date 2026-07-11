---
description: Generate final PROJECT_ARCHITECTURE / KNOWLEDGE_BASE / WORKFLOW docs from the historian iteration log
---

Run the historian finalize step and report which files were generated:

```
python -m historian finalize
```

It reads `docs/implementation.md` plus the current source tree and writes
`docs/PROJECT_ARCHITECTURE.md`, `docs/KNOWLEDGE_BASE.md`, and `docs/WORKFLOW.md`.
