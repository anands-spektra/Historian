"""Turn a queued iteration event into a model-ready payload: prompts, file
lists (created/modified/deleted/renamed), diffstat, and the unified diff —
with a byte cap + truncation fallback so large iterations stay bounded."""

from . import shadowgit

_BUCKET = {"A": "created", "M": "modified", "D": "deleted",
           "R": "renamed", "C": "copied", "T": "modified"}


def _parse_name_status(text):
    files = {"created": [], "modified": [], "deleted": [], "renamed": [], "copied": []}
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        bucket = _BUCKET.get(parts[0][0])
        if not bucket:
            continue
        if parts[0][0] in ("R", "C"):
            files[bucket].append(f"{parts[1]} -> {parts[-1]}")
        else:
            files[bucket].append(parts[1])
    return files


def _truncate(diff, cap):
    """Keep whole lines up to ~cap bytes, then a marker. Diffstat carries the
    rest of the structure, so this loses bulk noise, not the shape of the change."""
    out, size = [], 0
    for line in diff.splitlines(keepends=True):
        b = len(line.encode("utf-8", "replace"))
        if size + b > cap:
            break
        out.append(line)
        size += b
    out.append(f"\n... [diff truncated at ~{cap} bytes; see diffstat for the rest] ...\n")
    return "".join(out)


def build_payload(paths, event, cfg):
    a = event.get("prev_commit") or shadowgit.EMPTY_TREE
    b = event["new_commit"]
    diff = shadowgit.diff(paths, a, b)
    cap = cfg.get("diff_cap_bytes", 200000)
    truncated = len(diff.encode("utf-8", "replace")) > cap
    if truncated:
        diff = _truncate(diff, cap)
    return {
        "iteration": event["iteration"],
        "ts": event.get("ts"),
        "prompts": [p.get("prompt", "") for p in event.get("prompts", [])],
        "files": _parse_name_status(shadowgit.name_status(paths, a, b)),
        "diffstat": shadowgit.diffstat(paths, a, b),
        "diff": diff,
        "truncated": truncated,
    }
