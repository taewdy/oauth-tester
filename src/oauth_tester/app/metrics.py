from __future__ import annotations

from fastapi import FastAPI


def instrument_metrics(app: FastAPI) -> None:
    try:
        from prometheus_fastapi_instrumentator import Instrumentator

        Instrumentator().instrument(app).expose(app, endpoint="/metrics")
    except Exception:
        # Metrics optional; safe no-op if dependency missing
        pass

