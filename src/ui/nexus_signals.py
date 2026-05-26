"""Sinais para abrir janelas Nexus no pywebview (qualquer thread → fila drenada no GUI)."""
from __future__ import annotations


def enqueue_nexus_desktop_open(module: str, payload: dict | None = None) -> None:
    """Pedido de abertura de módulo; substitui qualquer pedido pendente (só a última ação conta)."""
    try:
        from src.ui.desktop_app import APP_INSTANCE

        if not APP_INSTANCE:
            return
        with APP_INSTANCE._nexus_lock:
            APP_INSTANCE._nexus_signal_q.append((str(module or "overview"), dict(payload or {})))
    except Exception:
        pass
