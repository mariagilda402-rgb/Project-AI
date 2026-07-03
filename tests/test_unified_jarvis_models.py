from src.jarvis_unified.models import DeviceInfo, JarvisEvent, JarvisSession


def test_device_info_defaults_to_online():
    device = DeviceInfo(
        device_id="mobile:moto-e20",
        kind="mobile",
        name="Moto E20",
        capabilities={"voice_input": True, "display": True},
    )

    assert device.status == "online"
    assert device.capabilities["voice_input"] is True


def test_session_tracks_voice_display_and_action_target():
    session = JarvisSession.create(active_user="maria")

    session.voice_endpoint = "mobile:moto-e20"
    session.display_endpoint = "mobile:moto-e20"
    session.action_target = "desktop:main-pc"

    assert session.voice_endpoint == "mobile:moto-e20"
    assert session.display_endpoint == "mobile:moto-e20"
    assert session.action_target == "desktop:main-pc"
    assert session.interruption_token


def test_event_roundtrip_dict():
    event = JarvisEvent.create(
        session_id="s1",
        source_device="mobile:moto-e20",
        target_device="desktop:main-pc",
        event_type="user_utterance",
        payload={"text": "pesquise raiz quadrada"},
    )

    restored = JarvisEvent.from_dict(event.to_dict())

    assert restored.event_id == event.event_id
    assert restored.type == "user_utterance"
    assert restored.payload["text"] == "pesquise raiz quadrada"

