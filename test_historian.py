"""End-to-end smoke test for the historian pipeline. Offline: forces the stub
provider, no network. Run: `python test_historian.py`.

Exercises init -> file changes -> save (snapshot -> collector -> document ->
append), the no-change no-op, and idempotency."""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from historian import config
from historian.__main__ import cmd_init, cmd_save


def main():
    tmp = tempfile.mkdtemp(prefix="historian_smoke_")
    cwd = os.getcwd()
    try:
        (Path(tmp) / "seed.txt").write_text("seed\n", encoding="utf-8")
        os.chdir(tmp)

        cmd_init()
        p = config.paths(config.find_root())
        c = json.loads(p.config.read_text(encoding="utf-8"))
        c["provider"] = "stub"
        p.config.write_text(json.dumps(c), encoding="utf-8")

        # one milestone: create + modify
        (Path(tmp) / "new.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        (Path(tmp) / "seed.txt").write_text("changed\n", encoding="utf-8")
        assert cmd_save("smoke feature") == 0

        cfg = config.load(p)
        impl = p.root / cfg["docs_dir"] / cfg["implementation_file"]
        assert "## Iteration 1" in impl.read_text(encoding="utf-8")
        assert config.read_state(p)["last_documented"] == 1

        # no changes -> no-op, no new iteration
        assert cmd_save("noop") == 0
        assert impl.read_text(encoding="utf-8").count("## Iteration") == 1
        assert config.read_state(p)["iteration"] == 1

        print("test_historian: OK")
    finally:
        os.chdir(cwd)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
