"""Shadow git repo: a private git-dir that tracks the project's work tree
independently of the user's real .git. One commit per iteration; diffs between
consecutive commits are exactly what Claude changed."""

import subprocess


def _git(paths, *args, check=True):
    """Run git against the shadow git-dir + project work-tree."""
    cmd = ["git", "--git-dir", str(paths.shadow_git), "--work-tree", str(paths.root), *args]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout.strip()


def is_initialized(paths):
    return paths.shadow_git.exists()


def init(paths):
    """Create the shadow repo and set self-contained identity/excludes so
    commits never depend on global git config."""
    subprocess.run(
        ["git", "--git-dir", str(paths.shadow_git), "init"],
        capture_output=True, text=True, check=True,
    )
    _git(paths, "config", "user.email", "historian@localhost")
    _git(paths, "config", "user.name", "AI Historian")
    _git(paths, "config", "commit.gpgsign", "false")
    _git(paths, "config", "core.excludesFile", str(paths.shadow_excludes.resolve()))


# Git's canonical empty-tree hash — diff base when an iteration has no predecessor.
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def head(paths):
    return _git(paths, "rev-parse", "HEAD")


def diff(paths, a, b):
    return _git(paths, "diff", a, b)


def name_status(paths, a, b):
    return _git(paths, "diff", "--name-status", a, b)


def diffstat(paths, a, b):
    return _git(paths, "diff", "--stat", a, b)


def status(paths):
    """Porcelain status of the work tree vs the last snapshot (respects excludes).
    Lists uncommitted/untracked changes without mutating anything."""
    return _git(paths, "status", "--porcelain")


def snapshot(paths, message):
    """Stage everything (minus excludes) and commit. --allow-empty so an
    iteration with no file changes still records a commit. Returns the sha."""
    _git(paths, "add", "-A")
    _git(paths, "commit", "--allow-empty", "-m", message)
    return head(paths)
