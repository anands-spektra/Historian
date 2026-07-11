"""Fire-and-forget detached subprocess. The stop hook uses this to launch the
worker without blocking Claude; the child outlives the hook."""

import os
import subprocess


def spawn_detached(argv, cwd):
    kwargs = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL,
              "stderr": subprocess.DEVNULL, "cwd": str(cwd)}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(argv, **kwargs)
