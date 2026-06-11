import logging
import os
import sys
import json
import contextvars

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
client_ip_var: contextvars.ContextVar[str] = contextvars.ContextVar("client_ip", default="")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging():
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    use_json = os.getenv("LOG_JSON", "false").lower() in ("1", "true", "yes")

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    if use_json:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)-7s [%(name)s] (req=%(request_id)s) %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())
    root.addHandler(handler)

    log_file = os.getenv("LOG_FILE")
    if log_file:
        fh = logging.FileHandler(log_file)
        fh.setFormatter(formatter)
        fh.addFilter(RequestIdFilter())
        root.addHandler(fh)

    for noisy in ("httpx", "httpcore", "urllib3", "google_genai", "google.genai"):
        logging.getLogger(noisy).setLevel(os.getenv("LIB_LOG_LEVEL", "WARNING").upper())

    logging.getLogger("cvforge").info("logging configured level=%s json=%s file=%s", level, use_json, log_file or "-")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"cvforge.{name}")
