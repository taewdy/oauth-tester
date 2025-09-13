from __future__ import annotations

import logging
import sys
from typing import Any


def configure_logging(as_json: bool, log_level: str) -> None:
    root_logger = logging.getLogger()
    if root_logger.handlers:
        # Avoid duplicating handlers on reload
        return

    handler = logging.StreamHandler(sys.stdout)

    if as_json:
        import json

        class JsonFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                payload: dict[str, Any] = {
                    "level": record.levelname.lower(),
                    "logger": record.name,
                    "message": record.getMessage(),
                    "time": self.formatTime(record, self.datefmt),
                }
                for key in ("request_id", "method", "path"):
                    if hasattr(record, key):
                        payload[key] = getattr(record, key)
                return json.dumps(payload)

        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

