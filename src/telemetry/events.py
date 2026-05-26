"""Eventos append-only em NDJSON com rotação simples por tamanho."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

_EVENTS_PATH = Path("data/logs/events.ndjson")
_MAX_BYTES = 5 * 1024 * 1024
_lock = threading.Lock()


def _rotate_if_needed() -> None:
    try:
        if _EVENTS_PATH.exists() and _EVENTS_PATH.stat().st_size > _MAX_BYTES:
            bak = _EVENTS_PATH.with_suffix(".ndjson.bak")
            if bak.exists():
                bak.unlink(missing_ok=True)  # type: ignore[arg-type]
            _EVENTS_PATH.rename(bak)
    except OSError:
        pass


def log_event(event_type: str, payload: dict[str, Any] | None = None) -> None:
    """Regista um evento (falha de LLM, execução de tool, confirmação crítica, etc.)."""
    row = {
        "ts": time.time(),
        "type": str(event_type),
        "data": payload or {},
    }
    line = json.dumps(row, ensure_ascii=False) + "\n"
    with _lock:
        try:
            _EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
            _rotate_if_needed()
            with open(_EVENTS_PATH, "a", encoding="utf-8") as f:
                f.write(line)
        except OSError:
            pass


def read_event_tail(max_lines: int = 50) -> list[dict[str, Any]]:
    """Últimas N linhas parseadas (ignora linhas inválidas)."""
    n = max(1, min(500, int(max_lines)))
    if not _EVENTS_PATH.exists():
        return []
    try:
        raw = _EVENTS_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for line in raw[-n:]:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out
