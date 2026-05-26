"""Telemetria local (NDJSON) para depuração e painel."""

from src.telemetry.events import log_event, read_event_tail

__all__ = ["log_event", "read_event_tail"]
