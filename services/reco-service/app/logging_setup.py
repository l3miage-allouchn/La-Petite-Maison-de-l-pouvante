"""Structured JSON logs with a correlation id taken from HTTP headers or Kafka headers."""

import logging
import re
import sys
import uuid
from contextvars import ContextVar

from pythonjsonlogger.json import JsonFormatter

correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)

_VALID_CORRELATION_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")


def sanitize_correlation_id(value: str | None) -> str:
    """Accepts only safe identifiers (prevents log injection); otherwise generates a new one."""
    if value is not None and _VALID_CORRELATION_ID.fullmatch(value):
        return value
    return str(uuid.uuid4())


class _CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get()
        return True


def configure_logging(level: str = "INFO", fmt: str = "json") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_CorrelationFilter())
    if fmt == "json":
        handler.setFormatter(
            JsonFormatter(
                "{levelname}{name}{message}{correlation_id}",
                style="{",
                rename_fields={"levelname": "level", "name": "logger"},
                static_fields={"service": "reco-service"},
                timestamp="@timestamp",  # ISO-8601 UTC, like the Java services
            )
        )
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-5s [%(correlation_id)s] %(name)s - %(message)s")
        )
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    # Uvicorn access logs are replaced by our own request log (with correlation id).
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("aiokafka").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
