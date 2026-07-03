from __future__ import annotations

import threading
from uuid import uuid4

from src.jarvis_unified.models import JarvisSession, utc_now_iso


class JarvisSessionState:
    def __init__(self, active_user: str = "local") -> None:
        self._lock = threading.RLock()
        self._session = JarvisSession.create(active_user=active_user)

    def current(self) -> JarvisSession:
        with self._lock:
            return JarvisSession(**self._session.to_dict())

    def set_voice_endpoint(self, device_id: str) -> JarvisSession:
        with self._lock:
            self._session.voice_endpoint = str(device_id or "")
            self._touch()
            return self.current()

    def set_display_endpoint(self, device_id: str) -> JarvisSession:
        with self._lock:
            self._session.display_endpoint = str(device_id or "")
            self._touch()
            return self.current()

    def set_action_target(self, device_id: str) -> JarvisSession:
        with self._lock:
            self._session.action_target = str(device_id or "")
            self._touch()
            return self.current()

    def interrupt(self) -> JarvisSession:
        with self._lock:
            self._session.interruption_token = str(uuid4())
            self._touch()
            return self.current()

    def _touch(self) -> None:
        self._session.last_turn_at = utc_now_iso()

