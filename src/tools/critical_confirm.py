"""Confirmação de ações críticas entre o worker da IA e o painel (pywebview) ou terminal."""

from __future__ import annotations

import re
import sys
import threading
import time
import uuid

_PREF_REL = "data/critical_confirm_enabled.json"


def load_critical_confirm_enabled(default: bool) -> bool:
    """Lê preferência persistida; em falha ou arquivo ausente devolve *default*."""
    from pathlib import Path

    path = Path(_PREF_REL)
    if not path.exists():
        return default
    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
        return bool(data.get("enabled", default))
    except Exception:
        return default


def save_critical_confirm_enabled(enabled: bool) -> None:
    from pathlib import Path
    import json

    path = Path(_PREF_REL)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"enabled": bool(enabled)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def try_voice_resolve_confirmation(bus: "CriticalConfirmationBus | None", text: str) -> bool:
    """
    Se houver pedido pendente e o texto for claramente confirmação/cancelamento por voz,
    chama resolve e retorna True (o STT não deve tratar como comando normal).
    """
    if bus is None or not bus.enabled:
        return False
    pending = bus.get_pending()
    if not pending:
        return False
    raw = (text or "").strip().lower()
    t = re.sub(r"[?!.,;:\"'`]+", "", raw).strip()
    if not t:
        return False

    cancel_words = frozenset(
        {"cancelar", "cancela", "não", "nao", "negativo", "aborta", "abortar", "esquece", "deixa"}
    )
    single_approve = frozenset(
        {"confirmar", "confirmo", "sim", "ok", "autorizo", "autorizado", "aprovo", "aprovado"}
    )
    parts = [p for p in t.split() if p]

    def _resolve(approved: bool) -> bool:
        return bool(bus.resolve(pending["id"], approved))

    if len(parts) == 1:
        if parts[0] in single_approve:
            return _resolve(True)
        if parts[0] in cancel_words:
            return _resolve(False)
    if parts in (
        ["pode", "sim"],
        ["pode", "ir"],
        ["pode", "mandar"],
        ["pode", "enviar"],
        ["manda", "ver"],
    ):
        return _resolve(True)
    if 2 <= len(parts) <= 4 and not any(w in cancel_words for w in parts):
        if any(w in single_approve for w in parts):
            return _resolve(True)
    if len(parts) <= 2 and any(w in cancel_words for w in parts):
        return _resolve(False)
    if t.startswith("confirmar") and len(t) <= 24:
        return _resolve(True)
    if t.startswith("cancelar") and len(t) <= 24:
        return _resolve(False)
    return False


class CriticalConfirmationBus:
    """
    Bloqueia a thread que pede confirmação até o painel chamar resolve()
    ou o usuário responder no terminal (fallback após stdin_fallback_delay_sec).
    """

    def __init__(self, timeout_sec: float = 300.0, stdin_fallback_delay_sec: float = 2.0) -> None:
        self._timeout_sec = max(30.0, min(3600.0, float(timeout_sec)))
        self._stdin_delay = max(0.0, min(60.0, float(stdin_fallback_delay_sec)))
        self._lock = threading.Lock()
        self._pending: dict | None = None
        self._done = threading.Event()
        self._approved = False
        self._enabled = True

    @property
    def enabled(self) -> bool:
        with self._lock:
            return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        with self._lock:
            self._enabled = bool(value)

    def get_pending(self) -> dict | None:
        with self._lock:
            if not self._pending:
                return None
            return dict(self._pending)

    def resolve(self, request_id: str, approved: bool) -> bool:
        tool_name = ""
        with self._lock:
            if not self._pending or self._pending.get("id") != request_id:
                return False
            tool_name = str(self._pending.get("tool_name", ""))
            self._approved = bool(approved)
            self._pending = None
        try:
            from src.telemetry.events import log_event

            log_event("critical_confirm", {"approved": bool(approved), "tool": tool_name})
        except Exception:
            pass
        self._done.set()
        return True

    def request(self, tool_name: str, detail: str = "") -> bool:
        with self._lock:
            if not self._enabled:
                return True
        if not detail:
            detail = f'Permitir execução da ferramenta "{tool_name}"?'
        req_id = uuid.uuid4().hex[:12]
        with self._lock:
            self._pending = {"id": req_id, "tool_name": tool_name, "detail": detail}
            self._approved = False
            self._done.clear()

        if not sys.stdin.isatty():
            print(
                "\n[Painel] Ação crítica pendente — confirme no painel ou diga \"confirmar\" / \"cancelar\" no microfone.",
                flush=True,
            )

        if sys.stdin.isatty():

            def _stdin_fallback() -> None:
                time.sleep(self._stdin_delay)
                if self._done.is_set():
                    return
                try:
                    print(
                        f"\n[Confirmação] {detail}\n"
                        f'Ferramenta: {tool_name}\n'
                        "Digite s/n (ou confirme no painel): ",
                        flush=True,
                    )
                    line = input().strip().lower()
                    ok = line in {"s", "sim", "y", "yes"}
                    self.resolve(req_id, ok)
                except (EOFError, KeyboardInterrupt):
                    self.resolve(req_id, False)

            threading.Thread(target=_stdin_fallback, daemon=True).start()

        got = self._done.wait(timeout=self._timeout_sec)
        with self._lock:
            approved = self._approved
            if self._pending and self._pending.get("id") == req_id:
                self._pending = None
            if not got:
                approved = False
        return bool(approved) if got else False
