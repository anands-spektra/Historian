"""File-based iteration queue. One JSON event per iteration, named so a
lexical sort matches iteration order. Writes are atomic (temp + rename)."""

import json
import os


def _name(iteration):
    return f"event-{iteration:06d}.json"


def enqueue(paths, event):
    paths.queue.mkdir(parents=True, exist_ok=True)
    dest = paths.queue / _name(event["iteration"])
    tmp = paths.queue / (_name(event["iteration"]) + ".tmp")
    tmp.write_text(json.dumps(event, indent=2), encoding="utf-8")
    os.replace(tmp, dest)  # atomic on Windows and POSIX
    return dest
