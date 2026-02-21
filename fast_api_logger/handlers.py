from __future__ import annotations

import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

from .config import LogConfig
from .context import is_streaming
from .formatters import TextFormatter, JsonFormatter


class StreamSafeConsoleHandler(logging.StreamHandler):
    """
    Если stream_safe=true и сейчас is_streaming()==True,
    то в stdout не пишем (чтобы не ломать SSE/стрим).
    """

    def __init__(self, stream_safe: bool):
        super().__init__(sys.stdout)
        self.stream_safe = stream_safe

    def emit(self, record: logging.LogRecord) -> None:
        if self.stream_safe and is_streaming():
            return
        super().emit(record)


def _ensure_dir(path: str) -> None:
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)


def build_handlers(cfg: LogConfig) -> list[logging.Handler]:
    handlers: list[logging.Handler] = []

    text_formatter = TextFormatter(fmt=cfg.text_fmt, datefmt=cfg.datefmt)
    json_formatter = JsonFormatter(ts_key=cfg.json_ts_key, datefmt=cfg.datefmt)

    # console
    if cfg.console_enabled:
        ch = StreamSafeConsoleHandler(stream_safe=cfg.stream_safe)
        ch.setLevel(cfg.level)
        ch.setFormatter(json_formatter if cfg.console_format == "json" else text_formatter)
        handlers.append(ch)

    # text file
    if cfg.text_file_enabled:
        _ensure_dir(cfg.text_file_path)
        fh = TimedRotatingFileHandler(
            filename=cfg.text_file_path,
            when=cfg.rotation_when,
            interval=cfg.rotation_interval,
            backupCount=cfg.rotation_backup_count,
            encoding="utf-8",
            utc=cfg.rotation_utc,
        )
        fh.setLevel(cfg.level)
        fh.setFormatter(text_formatter)
        handlers.append(fh)

    # json file
    if cfg.json_file_enabled:
        _ensure_dir(cfg.json_file_path)
        jh = TimedRotatingFileHandler(
            filename=cfg.json_file_path,
            when=cfg.rotation_when,
            interval=cfg.rotation_interval,
            backupCount=cfg.rotation_backup_count,
            encoding="utf-8",
            utc=cfg.rotation_utc,
        )
        jh.setLevel(cfg.level)
        jh.setFormatter(json_formatter)
        handlers.append(jh)

    return handlers
