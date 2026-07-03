from __future__ import annotations

from src.jarvis_unified.models import JarvisEvent
from src.core.interaction_loop import InteractionLoop


def make_unified_event_handler(loop: InteractionLoop):
    """Retorna um callback para encaminhar eventos do bridge para o agente desktop."""
    def handle_event(event: JarvisEvent) -> None:
        if event.type != "user_utterance":
            return

        text = str(event.payload.get("text") or "").strip()
        if not text:
            return

        source = event.source_device or "Unified"
        loop.task_queue.put((text, f"Unified:{source}"))

    return handle_event
