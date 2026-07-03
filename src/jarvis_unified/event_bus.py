from __future__ import annotations

import threading
from collections.abc import Callable

from src.jarvis_unified.models import JarvisEvent

EventHandler = Callable[[JarvisEvent], None]


class JarvisEventBus:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._subscribers: list[EventHandler] = []
        self._history: list[JarvisEvent] = []

    def subscribe(self, handler: EventHandler) -> Callable[[], None]:
        with self._lock:
            self._subscribers.append(handler)

        def unsubscribe() -> None:
            with self._lock:
                if handler in self._subscribers:
                    self._subscribers.remove(handler)

        return unsubscribe

    def publish(self, event: JarvisEvent) -> None:
        with self._lock:
            self._history.append(event)
            self._history = self._history[-200:]
            subscribers = list(self._subscribers)
        for handler in subscribers:
            handler(event)

    def history(self, limit: int = 50) -> list[JarvisEvent]:
        with self._lock:
            return list(self._history[-max(1, int(limit)):])

