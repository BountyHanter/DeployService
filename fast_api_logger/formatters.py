from __future__ import annotations

import json
import logging
from typing import Any

from .context import get_context


def _safe_json_value(obj: Any) -> Any:
    """
    Безопасная сериализация значений для JSON-логов.
    Если объект не сериализуется — превращаем в str(obj).
    """
    try:
        json.dumps(obj, ensure_ascii=False)
        return obj
    except Exception:
        try:
            return str(obj)
        except Exception:
            return "<not serializable>"


def _standard_logrecord_keys() -> set[str]:
    """
    Набор стандартных ключей LogRecord, чтобы отличать extra.
    """
    return set(
        logging.LogRecord(
            name="", level=0, pathname="", lineno=0, msg="", args=(), exc_info=None
        ).__dict__.keys()
    )


class TextFormatter(logging.Formatter):
    """
    Человекочитаемый лог + контекст/extra в хвосте.
    Контекст добавляется автоматически, но extra имеет приоритет.
    """

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)

        standard = _standard_logrecord_keys()

        # 1) собираем extra из record (включая то, что передали в log.info(..., extra=...))
        extras: dict[str, Any] = {
            k: record.__dict__[k]
            for k in record.__dict__.keys()
            if k not in standard and k not in {"message", "asctime"}
        }

        # 2) подтягиваем контекст, но НЕ перезаписываем extra
        ctx = get_context()
        for k, v in ctx.items():
            extras.setdefault(k, v)

        if extras:
            tail = " | " + " ".join(f"{k}={extras[k]}" for k in sorted(extras.keys()))
            return base + tail
        return base


class JsonFormatter(logging.Formatter):
    """
    JSON лог:
    - базовые поля
    - контекст (contextvars)
    - extra (имеет приоритет над контекстом)
    - traceback если exc_info
    """

    def __init__(self, ts_key: str, datefmt: str | None = None):
        super().__init__(datefmt=datefmt)
        self.ts_key = ts_key

    def format(self, record: logging.LogRecord) -> str:
        standard = _standard_logrecord_keys()

        data: dict[str, Any] = {
            self.ts_key: self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
        }

        # 1) сначала контекст
        ctx = get_context()
        for k, v in ctx.items():
            # не перезаписываем базовые поля
            if k not in data:
                data[k] = _safe_json_value(v)

        # 2) затем extra из record (имеет приоритет над контекстом)
        for k, v in record.__dict__.items():
            if k in standard or k in {"message"}:
                continue
            data[k] = _safe_json_value(v)

        # 3) исключения
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)

        return json.dumps(data, ensure_ascii=False)
