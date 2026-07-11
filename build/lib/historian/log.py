"""Single rotating logger. Never writes to stdout/stderr (hooks must keep
stdout clean for Claude Code)."""

import logging
from logging.handlers import RotatingFileHandler


def get_logger(paths):
    logger = logging.getLogger("historian")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    logger.propagate = False
    paths.log.parent.mkdir(parents=True, exist_ok=True)
    h = RotatingFileHandler(paths.log, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(h)
    return logger
