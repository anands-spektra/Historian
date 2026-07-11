"""End-to-end smoke test for the historian pipeline. Offline: uses the stub
provider, no network, no detached worker. Run: `python test_historian.py`.

Exercises init -> shadow snapshot -> enqueue -> collector -> worker -> append,
plus payload categorization and idempotency."""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from historian import collector, config, queue, shadowgit, worker
from historian.__main__ import cmd_init


def main():
    tmp = tempfile.mkdtemp(prefix="historian_smoke_")
    cwd = os.getcwd()
    try:
        (Path(tmp) / "seed.txt").write_text("seed\n", encoding="utf-8")
        os.chdir(tmp)

        cmd_init()
        p = config.paths(config.find_root())

        # force the offline stub provider for the test
        c = json.loads(p.config.read_text(encoding="utf-8"))
        c["provider"] = "stub"
        p.config.write_text(json.dumps(c), encoding="utf-8")
        cfg = config.load(p)

        # one iteration: create + modify a file
        (Path(tmp) / "new.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        (Path(tmp) / "seed.txt").write_text("changed\n", encoding="utf-8")
        prev = config.read_state(p)["last_shadow_commit"]
        new = shadowgit.snapshot(p, "iter 1")
        queue.enqueue(p, {"iteration": 1, "ts": "2026-01-01T00:00:00", "session_id": "s",
                          "prompts": [{"prompt": "add f()"}],
                          "prev_commit": prev, "new_commit": new})
        config.update_state(p, iteration=1, last_shadow_commit=new)

        # collector categorization
        ev = json.loads((p.queue / "event-000001.json").read_text(encoding="utf-8"))
        pl = collector.build_payload(p, ev, cfg)
        assert "new.py" in pl["files"]["created"], pl["files"]
        assert "seed.txt" in pl["files"]["modified"], pl["files"]
        assert pl["prompts"] == ["add f()"]

        # worker drains offline
        worker.run()
        impl_file = p.root / cfg["docs_dir"] / cfg["implementation_file"]
        impl = impl_file.read_text(encoding="utf-8")
        assert "## Iteration 1" in impl
        assert not list(p.queue.glob("event-*.json")), "queue not drained"
        assert config.read_state(p)["last_documented"] == 1

        # idempotency: a second run adds nothing
        worker.run()
        assert impl_file.read_text(encoding="utf-8").count("## Iteration 1") == 1

        print("test_historian: OK")
    finally:
        os.chdir(cwd)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
