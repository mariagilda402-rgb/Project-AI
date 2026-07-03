from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

from src.jarvis_unified.models import DeviceInfo, utc_now_iso


class DeviceRegistry:
    def __init__(self, stale_after_seconds: int = 90) -> None:
        self._lock = threading.RLock()
        self._devices: dict[str, DeviceInfo] = {}
        self.stale_after_seconds = max(10, int(stale_after_seconds))

    def register(self, device: DeviceInfo | dict) -> DeviceInfo:
        info = device if isinstance(device, DeviceInfo) else DeviceInfo.from_dict(device)
        with self._lock:
            info.status = "online"
            info.last_seen = utc_now_iso()
            self._devices[info.device_id] = info
            return DeviceInfo.from_dict(info.to_dict())

    def heartbeat(self, device_id: str) -> DeviceInfo | None:
        with self._lock:
            device = self._devices.get(str(device_id))
            if not device:
                return None
            device.status = "online"
            device.last_seen = utc_now_iso()
            return DeviceInfo.from_dict(device.to_dict())

    def get(self, device_id: str) -> DeviceInfo | None:
        with self._lock:
            device = self._devices.get(str(device_id))
            return DeviceInfo.from_dict(device.to_dict()) if device else None

    def list_devices(self, include_stale: bool = False) -> list[DeviceInfo]:
        with self._lock:
            self.expire_stale()
            devices = list(self._devices.values())
            if not include_stale:
                devices = [device for device in devices if device.status == "online"]
            return [DeviceInfo.from_dict(device.to_dict()) for device in devices]

    def expire_stale(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.stale_after_seconds)
        for device in self._devices.values():
            try:
                seen = datetime.fromisoformat(device.last_seen)
            except ValueError:
                seen = cutoff
            if seen < cutoff:
                device.status = "offline"

