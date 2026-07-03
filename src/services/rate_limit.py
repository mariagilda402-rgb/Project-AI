from __future__ import annotations

import threading
import time
from collections import deque


class SlidingWindowRateLimiter:
    def __init__(self, max_requests_per_minute: int = 10) -> None:
        self.max_requests_per_minute = max(1, max_requests_per_minute)
        self.window_seconds = 60.0
        self._timestamps: deque[float] = deque()
        self._lock = threading.Lock()

    def wait_for_slot(self) -> None:
        while True:
            wait_seconds = 0.0
            with self._lock:
                now = time.time()
                self._drop_old(now)
                if len(self._timestamps) < self.max_requests_per_minute:
                    self._timestamps.append(now)
                    return
                oldest = self._timestamps[0]
                wait_seconds = max(0.05, self.window_seconds - (now - oldest))
            time.sleep(wait_seconds)

    def _drop_old(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()
