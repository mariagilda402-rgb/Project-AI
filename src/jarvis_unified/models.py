from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class DeviceInfo:
    device_id: str
    kind: str
    name: str
    capabilities: dict[str, Any]
    status: str = "online"
    last_seen: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DeviceInfo":
        return cls(
            device_id=str(data["device_id"]),
            kind=str(data["kind"]),
            name=str(data.get("name") or data["device_id"]),
            capabilities=dict(data.get("capabilities") or {}),
            status=str(data.get("status") or "online"),
            last_seen=str(data.get("last_seen") or utc_now_iso()),
        )


@dataclass(slots=True)
class JarvisSession:
    session_id: str
    active_user: str
    voice_endpoint: str = ""
    display_endpoint: str = ""
    action_target: str = ""
    active_tasks: list[dict[str, Any]] = field(default_factory=list)
    interruption_token: str = field(default_factory=lambda: str(uuid4()))
    last_turn_at: str = field(default_factory=utc_now_iso)

    @classmethod
    def create(cls, active_user: str) -> "JarvisSession":
        return cls(session_id=str(uuid4()), active_user=active_user)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class JarvisEvent:
    event_id: str
    session_id: str
    source_device: str
    target_device: str
    type: str
    payload: dict[str, Any]
    created_at: str
    expires_at: str

    @classmethod
    def create(
        cls,
        session_id: str,
        source_device: str,
        target_device: str = "*",
        event_type: str = "",
        payload: dict[str, Any] | None = None,
        ttl_seconds: int = 60,
    ) -> "JarvisEvent":
        now = datetime.now(timezone.utc)
        return cls(
            event_id=str(uuid4()),
            session_id=session_id,
            source_device=source_device,
            target_device=target_device,
            type=event_type,
            payload=dict(payload or {}),
            created_at=now.isoformat(),
            expires_at=(now + timedelta(seconds=max(1, ttl_seconds))).isoformat(),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JarvisEvent":
        return cls(
            event_id=str(data.get("event_id") or uuid4()),
            session_id=str(data.get("session_id") or ""),
            source_device=str(data.get("source_device") or ""),
            target_device=str(data.get("target_device") or "*"),
            type=str(data.get("type") or ""),
            payload=dict(data.get("payload") or {}),
            created_at=str(data.get("created_at") or utc_now_iso()),
            expires_at=str(data.get("expires_at") or utc_now_iso()),
        )

