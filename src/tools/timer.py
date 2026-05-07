"""Timers e alarmes com notificacao sonora (thread em background)."""
from __future__ import annotations

import logging
import re
import threading
import time
import winsound
from datetime import datetime, timedelta

from .base import ToolResult

logger = logging.getLogger(__name__)


class _TimerManager:
    """Singleton que roda uma thread checando timers pendentes."""

    _instance: _TimerManager | None = None

    def __new__(cls) -> _TimerManager:
        if cls._instance is None:
            obj = super().__new__(cls)
            obj._timers: list[dict] = []
            obj._lock = threading.Lock()
            obj._thread = threading.Thread(target=obj._loop, daemon=True)
            obj._thread.start()
            cls._instance = obj
        return cls._instance

    def add(self, fire_at: datetime, label: str) -> None:
        with self._lock:
            self._timers.append({"fire_at": fire_at, "label": label, "fired": False})

    def list_active(self) -> list[dict]:
        with self._lock:
            now = datetime.now()
            return [t for t in self._timers if not t["fired"] and t["fire_at"] > now]

    def _loop(self) -> None:
        while True:
            now = datetime.now()
            with self._lock:
                for t in self._timers:
                    if not t["fired"] and now >= t["fire_at"]:
                        t["fired"] = True
                        label = t["label"]
                        threading.Thread(target=self._fire, args=(label,), daemon=True).start()
            time.sleep(1)

    @staticmethod
    def _fire(label: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n*** TIMER: {label} ({stamp}) ***", flush=True)
        try:
            for _ in range(3):
                winsound.Beep(1000, 350)
                time.sleep(0.15)
        except Exception:
            pass


class TimerTool:
    name = "timer"
    description = "Cria timers e alarmes com notificacao sonora."
    critical = False

    def __init__(self) -> None:
        self.manager = _TimerManager()

    # -- acoes --

    def set_timer(self, duration: str, label: str = "") -> ToolResult:
        seconds = self._parse_duration(duration)
        if seconds is None or seconds <= 0:
            return ToolResult(False, f"Duracao nao reconhecida: {duration}")
        fire_at = datetime.now() + timedelta(seconds=seconds)
        label = label or f"Timer de {duration}"
        self.manager.add(fire_at, label)
        return ToolResult(
            True,
            f"Timer criado: '{label}' — dispara em {self._fmt(seconds)} ({fire_at.strftime('%H:%M:%S')}).",
        )

    def set_alarm(self, time_str: str, label: str = "") -> ToolResult:
        try:
            target = datetime.strptime(time_str.strip(), "%H:%M")
        except ValueError:
            return ToolResult(False, f"Horario invalido: {time_str}. Use HH:MM.")
        now = datetime.now()
        fire_at = now.replace(hour=target.hour, minute=target.minute, second=0, microsecond=0)
        if fire_at <= now:
            fire_at += timedelta(days=1)
        label = label or f"Alarme para {time_str}"
        self.manager.add(fire_at, label)
        return ToolResult(True, f"Alarme criado: '{label}' — dispara as {fire_at.strftime('%H:%M')}.")

    def list_active(self) -> ToolResult:
        active = self.manager.list_active()
        if not active:
            return ToolResult(True, "Nenhum timer ativo.")
        lines: list[str] = []
        for t in active:
            remaining = t["fire_at"] - datetime.now()
            lines.append(
                f"- {t['label']} as {t['fire_at'].strftime('%H:%M:%S')} "
                f"(falta {self._fmt(int(remaining.total_seconds()))})"
            )
        return ToolResult(True, "Timers ativos:\n" + "\n".join(lines))

    def run(self, command: str) -> ToolResult:
        lowered = (command or "").lower()
        if any(kw in lowered for kw in ("listar", "ativos", "quais", "pendentes")):
            return self.list_active()
        hhmm = re.search(r"(\d{1,2}:\d{2})", command)
        if hhmm and any(kw in lowered for kw in ("alarme", "hora", "as ", "às")):
            return self.set_alarm(hhmm.group(1), command)
        return self.set_timer(command, command)

    # -- helpers --

    @staticmethod
    def _parse_duration(text: str) -> int | None:
        text = text.lower().strip()
        total = 0
        found = False
        for pattern, mult in [
            (r"(\d+)\s*h(?:ora)?s?", 3600),
            (r"(\d+)\s*min(?:uto)?s?", 60),
            (r"(\d+)\s*s(?:eg(?:undo)?)?s?\b", 1),
        ]:
            for m in re.finditer(pattern, text):
                total += int(m.group(1)) * mult
                found = True
        if found:
            return total
        digits = re.search(r"(\d+)", text)
        if digits:
            return int(digits.group(1)) * 60  # assume minutos
        return None

    @staticmethod
    def _fmt(seconds: int) -> str:
        if seconds < 60:
            return f"{seconds}s"
        if seconds < 3600:
            m, s = divmod(seconds, 60)
            return f"{m}min" + (f" {s}s" if s else "")
        h, rest = divmod(seconds, 3600)
        m = rest // 60
        return f"{h}h" + (f" {m}min" if m else "")
