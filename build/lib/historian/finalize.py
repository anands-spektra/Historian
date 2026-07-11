"""Generate the three summary documents from the iteration log + source. Manual
step (`historian finalize`), makes one provider call per document."""

import fnmatch
import os
from pathlib import Path

from . import config
from .log import get_logger
from .providers import get_provider
from .document import _analyze_with_retry

_PROMPTS = Path(__file__).parent / "prompts"
_CONTEXT_CAP = 400_000          # byte budget for source excerpts
_PER_FILE_LINES = 300
_SOURCE_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".md", ".json", ".txt",
               ".java", ".go", ".rb", ".rs", ".c", ".cpp", ".h", ".css",
               ".html", ".sh", ".yml", ".yaml", ".toml"}

_DOCS = {
    "architecture.md": "PROJECT_ARCHITECTURE.md",
    "knowledge_base.md": "KNOWLEDGE_BASE.md",
    "workflow.md": "WORKFLOW.md",
}


def _excluded(rel, globs):
    rel = rel.replace("\\", "/")
    segs = rel.split("/")
    for g in globs:
        gg = g.rstrip("/")
        if fnmatch.fnmatch(rel, gg) or any(fnmatch.fnmatch(s, gg) for s in segs):
            return True
    return False


def _file_tree(root, globs):
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        base = "" if rel == "." else rel.replace("\\", "/")
        dirnames[:] = [d for d in dirnames
                       if not _excluded(f"{base}/{d}".lstrip("/"), globs)]
        for f in filenames:
            r = f if not base else f"{base}/{f}"
            if not _excluded(r, globs):
                files.append(r)
    return sorted(files)


def _source_excerpts(root, files):
    out, total = [], 0
    for r in files:
        if os.path.splitext(r)[1].lower() not in _SOURCE_EXT:
            continue
        try:
            text = (root / r).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        excerpt = "\n".join(text.splitlines()[:_PER_FILE_LINES])
        block = f"\n### FILE: {r}\n{excerpt}\n"
        b = len(block.encode("utf-8", "replace"))
        if total + b > _CONTEXT_CAP:
            out.append(f"\n... [source excerpts truncated at ~{_CONTEXT_CAP} bytes] ...\n")
            break
        out.append(block)
        total += b
    return "".join(out)


def _build_context(paths, cfg, impl_text):
    globs = config.effective_excludes(cfg)
    files = _file_tree(paths.root, globs)
    tree = "\n".join(files)
    return (f"== FILE TREE ==\n{tree}\n\n"
            f"== ITERATION LOG (implementation.md) ==\n{impl_text}\n\n"
            f"== SOURCE EXCERPTS ==\n{_source_excerpts(paths.root, files)}")


def run():
    paths = config.paths(config.find_root())
    cfg = config.load(paths)
    log = get_logger(paths)
    impl = paths.root / cfg["docs_dir"] / cfg["implementation_file"]
    if not impl.exists() or not impl.read_text(encoding="utf-8").strip():
        print(f"nothing to finalize: {impl} is missing or empty")
        return 1

    provider = get_provider(cfg["provider"])
    context = _build_context(paths, cfg, impl.read_text(encoding="utf-8"))
    docs_dir = paths.root / cfg["docs_dir"]
    docs_dir.mkdir(parents=True, exist_ok=True)

    for tpl_name, out_name in _DOCS.items():
        tpl = (_PROMPTS / tpl_name).read_text(encoding="utf-8")
        prompt = tpl.replace("[[CONTEXT]]", context)
        print(f"generating {out_name} ...")
        result = _analyze_with_retry(provider, prompt, cfg, log, out_name)
        (docs_dir / out_name).write_text(result.strip() + "\n", encoding="utf-8")
        print(f"  wrote {docs_dir / out_name}")
    return 0
