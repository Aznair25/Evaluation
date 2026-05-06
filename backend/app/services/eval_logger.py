"""Per-evaluation logger.

Each evaluation gets its own logger that propagates to the root handler
(container stdout). Callers obtain a bound logger via
``get_eval_logger(evaluation_id)`` and use it like any standard logger.
"""

import logging
import threading


_loggers: dict[str, logging.Logger] = {}
_lock = threading.Lock()

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def get_eval_logger(evaluation_id: str) -> logging.Logger:
    """Return (or create) the per-evaluation logger."""
    with _lock:
        if evaluation_id in _loggers:
            return _loggers[evaluation_id]

        logger = logging.getLogger(f"eval.{evaluation_id}")
        logger.setLevel(logging.DEBUG)
        logger.handlers.clear()
        # Propagate to root so logs appear in container stdout
        logger.propagate = True

        _loggers[evaluation_id] = logger
        return logger


def cleanup_eval_logger(evaluation_id: str) -> None:
    """Remove the logger entry (call at end of pipeline)."""
    with _lock:
        logger = _loggers.pop(evaluation_id, None)
        if logger:
            for h in logger.handlers[:]:
                h.close()
                logger.removeHandler(h)
