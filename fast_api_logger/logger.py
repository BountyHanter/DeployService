import logging
from typing import Any, Mapping

from .config import load_config, LogConfig
from .handlers import build_handlers

# стандартные ключи record'а — чтобы не конфликтовать
_STANDARD_KEYS = set(logging.LogRecord(
    name="", level=0, pathname="", lineno=0, msg="", args=(), exc_info=None
).__dict__.keys()) | {"message", "asctime", "exc_info", "stack_info"}


class SafeLogger:
    """
    Обёртка над logging.Logger:
    - принимает extra
    - при конфликтах переименовывает ключи в <key>_extra
    """
    def __init__(self, logger: logging.Logger, sanitize_extra: bool = True):
        self._logger = logger
        self._sanitize_extra_enabled = sanitize_extra

    def _sanitize_extra(self, extra: Mapping[str, Any] | None) -> dict[str, Any] | None:
        if not extra:
            return None
        if not self._sanitize_extra_enabled:
            return dict(extra)

        sanitized: dict[str, Any] = {}
        for k, v in extra.items():
            if k in _STANDARD_KEYS:
                sanitized[f"{k}_extra"] = v
            else:
                sanitized[k] = v
        return sanitized

    def debug(self, msg: str, *args: Any, extra: Mapping[str, Any] | None = None, **kwargs: Any) -> None:
        self._logger.debug(msg, *args, extra=self._sanitize_extra(extra), **kwargs)

    def info(self, msg: str, *args: Any, extra: Mapping[str, Any] | None = None, **kwargs: Any) -> None:
        self._logger.info(msg, *args, extra=self._sanitize_extra(extra), **kwargs)

    def warning(self, msg: str, *args: Any, extra: Mapping[str, Any] | None = None, **kwargs: Any) -> None:
        self._logger.warning(msg, *args, extra=self._sanitize_extra(extra), **kwargs)

    def error(self, msg: str, *args: Any, extra: Mapping[str, Any] | None = None, **kwargs: Any) -> None:
        self._logger.error(msg, *args, extra=self._sanitize_extra(extra), **kwargs)

    def critical(self, msg: str, *args: Any, extra: Mapping[str, Any] | None = None, **kwargs: Any) -> None:
        self._logger.critical(msg, *args, extra=self._sanitize_extra(extra), **kwargs)

    def exception(self, msg: str, *args: Any, extra: Mapping[str, Any] | None = None, **kwargs: Any) -> None:
        self._logger.exception(msg, *args, extra=self._sanitize_extra(extra), **kwargs)


def configure_logging(cfg: LogConfig | None = None) -> SafeLogger:
    cfg = cfg or load_config()

    logger = logging.getLogger(cfg.logger_name)
    logger.setLevel(cfg.level)
    logger.propagate = False

    # чтобы при повторном импорте не плодить handlers
    if not logger.handlers:
        for h in build_handlers(cfg):
            logger.addHandler(h)

    return SafeLogger(logger, sanitize_extra=cfg.sanitize_extra)


# публичный логгер
log = configure_logging()
