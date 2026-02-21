import os
from dataclasses import dataclass
from typing import Literal


def _parse_bool(val: str | None, default: bool = False) -> bool:
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "y", "on")


def _get_env(name: str, default: str) -> str:
    v = os.getenv(name)
    return default if v is None or v == "" else v


@dataclass(frozen=True)
class LogConfig:
    # базовое
    level: str
    logger_name: str

    # консоль
    console_enabled: bool
    console_format: Literal["text", "json"]

    # файлы
    text_file_enabled: bool
    text_file_path: str

    json_file_enabled: bool
    json_file_path: str

    # ротация
    rotation_when: str       # "midnight", "H", "D", "M", ...
    rotation_interval: int
    rotation_backup_count: int
    rotation_utc: bool

    # поведение
    sanitize_extra: bool
    stream_safe: bool         # если true — можем не писать в stdout во время стрима
    stream_debug: bool        # логировать чанки стрима (лучше false по умолчанию)

    # формат
    datefmt: str
    text_fmt: str

    # json keys
    json_ts_key: str


def load_config() -> LogConfig:
    level = _get_env("LOG_LEVEL", "INFO").upper()
    if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        level = "INFO"

    console_enabled = _parse_bool(os.getenv("LOG_CONSOLE"), True)
    console_format = _get_env("LOG_CONSOLE_FORMAT", "text").lower()
    if console_format not in {"text", "json"}:
        console_format = "text"

    text_file_enabled = _parse_bool(os.getenv("LOG_FILE_TEXT"), True)
    text_file_path = _get_env("LOG_FILE_TEXT_PATH", "logs/app.log")

    json_file_enabled = _parse_bool(os.getenv("LOG_FILE_JSON"), True)
    json_file_path = _get_env("LOG_FILE_JSON_PATH", "logs/app.json.log")

    rotation_when = _get_env("LOG_ROTATION_WHEN", "midnight")
    rotation_interval = int(_get_env("LOG_ROTATION_INTERVAL", "1"))
    rotation_backup = int(_get_env("LOG_ROTATION_BACKUP", "7"))
    rotation_utc = _parse_bool(os.getenv("LOG_ROTATION_UTC"), False)

    sanitize_extra = _parse_bool(os.getenv("LOG_SANITIZE_EXTRA"), True)

    stream_safe = _parse_bool(os.getenv("STREAM_SAFE"), True)
    stream_debug = _parse_bool(os.getenv("STREAM_DEBUG"), False)

    logger_name = _get_env("LOG_NAME", "app")
    datefmt = _get_env("LOG_DATEFMT", "%Y-%m-%d %H:%M:%S")

    text_fmt = _get_env(
        "LOG_TEXT_FMT",
        "[%(asctime)s] [%(levelname)s] %(message)s"
    )

    json_ts_key = _get_env("LOG_JSON_TS_KEY", "ts")

    return LogConfig(
        level=level,
        logger_name=logger_name,
        console_enabled=console_enabled,
        console_format=console_format,  # type: ignore[arg-type]
        text_file_enabled=text_file_enabled,
        text_file_path=text_file_path,
        json_file_enabled=json_file_enabled,
        json_file_path=json_file_path,
        rotation_when=rotation_when,
        rotation_interval=rotation_interval,
        rotation_backup_count=rotation_backup,
        rotation_utc=rotation_utc,
        sanitize_extra=sanitize_extra,
        stream_safe=stream_safe,
        stream_debug=stream_debug,
        datefmt=datefmt,
        text_fmt=text_fmt,
        json_ts_key=json_ts_key,
    )
