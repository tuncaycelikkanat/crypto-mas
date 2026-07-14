"""
Centralised logging setup for crypto-mas.

Call setup_logging() once at application startup (api/main.py, scheduler/main.py).
"""
import logging
import logging.config
from pathlib import Path


def setup_logging(env: str = "dev", log_dir: str = "logs") -> None:
    """Configure application-wide logging.

    Args:
        env: 'dev' for coloured console output, 'prod' for JSON + file.
        log_dir: Directory where rotating log files are written.
    """
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_file = str(Path(log_dir) / "crypto_mas.log")

    if env == "prod":
        formatter_class = "logging.Formatter"
        format_str = '{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
    else:
        formatter_class = "logging.Formatter"
        format_str = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "class": formatter_class,
                "format": format_str,
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "standard",
                "filename": log_file,
                "maxBytes": 10 * 1024 * 1024,  # 10 MB
                "backupCount": 5,
                "encoding": "utf-8",
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["console", "file"],
        },
        "loggers": {
            "crypto_mas": {
                "level": "DEBUG" if env == "dev" else "INFO",
                "propagate": True,
            },
            "uvicorn": {"level": "INFO", "propagate": True},
            "apscheduler": {"level": "WARNING", "propagate": True},
        },
    }

    logging.config.dictConfig(config)
    logging.getLogger(__name__).info(
        "Logging configured. env=%s log_file=%s", env, log_file
    )
