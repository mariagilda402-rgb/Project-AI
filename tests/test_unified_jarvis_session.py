from src.jarvis_unified.device_registry import DeviceRegistry
from src.jarvis_unified.models import DeviceInfo
from src.jarvis_unified.session_state import JarvisSessionState


def test_session_handoff_and_action_target():
    state = JarvisSessionState(active_user="maria")
    session = state.current()

    state.set_voice_endpoint("mobile:moto-e20")
    state.set_display_endpoint("mobile:moto-e20")
    state.set_action_target("desktop:main-pc")

    updated = state.current()
    assert updated.session_id == session.session_id
    assert updated.voice_endpoint == "mobile:moto-e20"
    assert updated.display_endpoint == "mobile:moto-e20"
    assert updated.action_target == "desktop:main-pc"


def test_interrupt_rotates_token():
    state = JarvisSessionState(active_user="maria")
    first = state.current().interruption_token

    second = state.interrupt().interruption_token

    assert second != first


def test_device_registry_registers_and_heartbeats():
    registry = DeviceRegistry()
    device = registry.register(DeviceInfo(
        device_id="desktop:main-pc",
        kind="desktop",
        name="Main PC",
        capabilities={"desktop_control": True},
    ))

    assert device.status == "online"
    assert registry.heartbeat("desktop:main-pc") is not None
    assert registry.get("desktop:main-pc").name == "Main PC"

