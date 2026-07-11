---
description: Save one historian iteration documenting all changes since the last save
---

Run this and report the result (pass the user's text as a feature title):

```
python -m historian save $ARGUMENTS
```

It snapshots the shadow repo, diffs against the last save, and appends one
"Iteration N" section to `docs/implementation.md`.
