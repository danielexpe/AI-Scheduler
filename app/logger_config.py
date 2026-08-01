import os
import logging
from logging.handlers import RotatingFileHandler
import threading
import time

_log_setup_done = False
_app_logger = None


def _build_formatter():
    return logging.Formatter(
        "[%(asctime)s] [%(levelname)-7s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def setup_logging(log_path, level=logging.INFO):
    global _log_setup_done, _app_logger

    if _log_setup_done:
        return _app_logger

    dirname = os.path.dirname(log_path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)

    handler = RotatingFileHandler(
        log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(_build_formatter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    _log_setup_done = True
    _app_logger = logging.getLogger("app")
    _app_logger.info("Logging iniciado -> %s", log_path)
    return _app_logger


def get_logger(name=None):
    return logging.getLogger(name or "app")


def start_heartbeat(name, interval=60):
    logger = logging.getLogger(name)

    def _beat():
        count = 0
        while True:
            count += 1
            logger.info("HEARTBEAT #%d - container ativo", count)
            time.sleep(interval)

    thread = threading.Thread(target=_beat, daemon=True, name=f"heartbeat-{name}")
    thread.start()
    return thread
