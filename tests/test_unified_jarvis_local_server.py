from datetime import datetime, timedelta, timezone

from src.jarvis_unified.local_server import UnifiedJarvisLocalBridge
from src.jarvis_unified.models import DeviceInfo, JarvisEvent


def test_bridge_refreshes_registered_device_on_any_event():
    bridge = UnifiedJarvisLocalBridge()
    bridge.device_registry.register(DeviceInfo(
        device_id="mobile:moto-e20",
        kind="mobile",
        name="Moto E20",
        capabilities={"display": True},
    ))
    stale_seen = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    bridge.device_registry._devices["mobile:moto-e20"].last_seen = stale_seen

    bridge._handle_event(JarvisEvent.create(
        session_id="s1",
        source_device="mobile:moto-e20",
        event_type="interrupt",
        payload={"scope": "all"},
    ))

    refreshed = bridge.device_registry.get("mobile:moto-e20")
    assert refreshed.status == "online"
    assert refreshed.last_seen != stale_seen


def test_bridge_publishes_router_events_after_incoming_event():
    class FakeRouter:
        def route_event(self, event, session):
            if event.type != "user_utterance":
                return []
            return [
                JarvisEvent.create(
                    session_id=session.session_id,
                    source_device="desktop:test",
                    target_device=event.source_device,
                    event_type="assistant_delta",
                    payload={"text": "ok"},
                )
            ]

    seen = []
    bridge = UnifiedJarvisLocalBridge(command_router=FakeRouter(), on_event=seen.append)

    bridge._handle_event(JarvisEvent.create(
        session_id="s1",
        source_device="mobile:moto-e20",
        event_type="user_utterance",
        payload={"text": "oi"},
    ))

    assert [event.type for event in seen] == ["user_utterance", "assistant_delta"]
