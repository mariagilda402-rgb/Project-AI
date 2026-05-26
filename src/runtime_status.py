"""Estado de execução thread-safe para o painel e telemetria leve."""

from __future__ import annotations

import datetime as _dt
import threading
import time
from typing import Any


class RuntimeStatus:
    """Espelha mic, STT, fila e erros recentes da LLM (atualizado pelo main/worker)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.mic_listening: bool = False
        self.is_processing: bool = False
        self.stt_backend: str = ""
        self.stt_calibrated: bool = False
        self.llm_last_error: str = ""
        self.llm_last_error_time: str = ""
        self.last_enqueue_preview: str = ""
        self.diagnostics: dict[str, Any] = {}
        self._startup_t0 = time.perf_counter()
        self.startup_phases: list[dict[str, Any]] = []

    def set_mic_listening(self, on: bool) -> None:
        with self._lock:
            self.mic_listening = bool(on)

    def set_processing(self, on: bool) -> None:
        with self._lock:
            self.is_processing = bool(on)

    def set_stt_info(self, backend: str, calibrated: bool) -> None:
        with self._lock:
            self.stt_backend = (backend or "").strip() or "unknown"
            self.stt_calibrated = bool(calibrated)

    def set_enqueue_preview(self, text: str) -> None:
        t = (text or "").strip().replace("\n", " ")
        if len(t) > 120:
            t = t[:117] + "..."
        with self._lock:
            self.last_enqueue_preview = t

    def set_llm_error(self, msg: str) -> None:
        m = (msg or "").strip()
        if len(m) > 400:
            m = m[:397] + "..."
        ts = _dt.datetime.now().strftime("%H:%M:%S")
        with self._lock:
            self.llm_last_error = m
            self.llm_last_error_time = ts

    def clear_llm_error(self) -> None:
        with self._lock:
            self.llm_last_error = ""
            self.llm_last_error_time = ""

    def set_diagnostics(self, key: str, value: Any) -> None:
        with self._lock:
            self.diagnostics[key] = value

    def mark_startup_phase(self, name: str, detail: str = "") -> None:
        label = (name or "").strip()
        if not label:
            return
        elapsed_ms = int((time.perf_counter() - self._startup_t0) * 1000)
        with self._lock:
            self.startup_phases.append(
                {
                    "name": label,
                    "detail": (detail or "").strip(),
                    "elapsed_ms": elapsed_ms,
                    "time": _dt.datetime.now().strftime("%H:%M:%S"),
                }
            )
            self.startup_phases = self.startup_phases[-18:]

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "mic_listening": self.mic_listening,
                "is_processing": self.is_processing,
                "stt_backend": self.stt_backend,
                "stt_calibrated": self.stt_calibrated,
                "llm_last_error": self.llm_last_error,
                "llm_last_error_time": self.llm_last_error_time,
                "last_enqueue_preview": self.last_enqueue_preview,
                "diagnostics": dict(self.diagnostics),
                "startup_phases": list(self.startup_phases),
                "startup_total_ms": (
                    self.startup_phases[-1]["elapsed_ms"] if self.startup_phases else 0
                ),
            }
