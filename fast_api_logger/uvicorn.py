import logging
import os
from logging.handlers import TimedRotatingFileHandler


def configure_uvicorn_logging(
    error_log_path: str = "logs/uvicorn_error.log",
    access_log_path: str | None = None,
    when: str = "midnight",
    interval: int = 1,
    backup_count: int = 7,
):
    os.makedirs(os.path.dirname(error_log_path), exist_ok=True)

    error_handler = TimedRotatingFileHandler(
        filename=error_log_path,
        when=when,
        interval=interval,
        backupCount=backup_count,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(
        logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    uvicorn_error_logger.addHandler(error_handler)
    uvicorn_error_logger.setLevel(logging.ERROR)
    uvicorn_error_logger.propagate = False

    # access-логи — опционально
    if access_log_path:
        os.makedirs(os.path.dirname(access_log_path), exist_ok=True)

        access_handler = TimedRotatingFileHandler(
            filename=access_log_path,
            when=when,
            interval=interval,
            backupCount=backup_count,
            encoding="utf-8",
        )
        access_handler.setLevel(logging.INFO)
        access_handler.setFormatter(
            logging.Formatter(
                fmt="[%(asctime)s] %(client_addr)s - \"%(request_line)s\" %(status_code)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

        uvicorn_access_logger = logging.getLogger("uvicorn.access")
        uvicorn_access_logger.handlers = []
        uvicorn_access_logger.addHandler(access_handler)
        uvicorn_access_logger.setLevel(logging.INFO)
        uvicorn_access_logger.propagate = False
