from __future__ import annotations

from collections.abc import Callable

from src.jarvis_unified.models import JarvisEvent, JarvisSession


DesktopTurnHandler = Callable[[str, JarvisEvent], str | None]


class UnifiedCommandRouter:
    """Routes unified Jarvis events into safe first-step responses/actions."""

    def __init__(
        self,
        device_id: str = "desktop:local",
        desktop_turn_handler: DesktopTurnHandler | None = None,
    ) -> None:
        self.device_id = device_id
        self.desktop_turn_handler = desktop_turn_handler

    def route_event(self, event: JarvisEvent, session: JarvisSession) -> list[JarvisEvent]:
        if event.type != "user_utterance":
            return []

        text = str(event.payload.get("text") or "").strip()
        if not text:
            return []

        reply = self._handle_user_utterance(text, event)
        if not reply:
            return []

        target = event.source_device or session.display_endpoint or "*"
        return [
            JarvisEvent.create(
                session_id=session.session_id,
                source_device=self.device_id,
                target_device=target,
                event_type="assistant_delta",
                payload={"text": reply, "render": False},
            ),
            JarvisEvent.create(
                session_id=session.session_id,
                source_device=self.device_id,
                target_device=target,
                event_type="render_update",
                payload={
                    "surface_id": "assistant-live",
                    "op": "append",
                    "block": {"type": "assistant_transcript", "text": reply},
                },
            ),
        ]

    def _handle_user_utterance(self, text: str, event: JarvisEvent) -> str:
        if self.desktop_turn_handler is not None:
            reply = self.desktop_turn_handler(text, event)
            return str(reply) if reply else ""
        return f"Recebi no Jarvis do PC: {text}"
