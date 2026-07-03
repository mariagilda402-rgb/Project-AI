from src.jarvis_unified.command_router import UnifiedCommandRouter
from src.jarvis_unified.models import JarvisEvent, JarvisSession


def test_router_turns_mobile_utterance_into_assistant_delta():
    router = UnifiedCommandRouter(device_id="desktop:test")
    session = JarvisSession.create(active_user="local")
    session.display_endpoint = "mobile:moto-e20"

    outgoing = router.route_event(
        JarvisEvent.create(
            session_id=session.session_id,
            source_device="mobile:moto-e20",
            event_type="user_utterance",
            payload={"text": "Jarvis, teste a conexao"},
        ),
        session=session,
    )

    assert [event.type for event in outgoing] == ["assistant_delta", "render_update"]
    assert outgoing[0].source_device == "desktop:test"
    assert outgoing[0].target_device == "mobile:moto-e20"
    assert "teste a conexao" in outgoing[0].payload["text"]


def test_router_can_delegate_utterance_to_desktop_handler():
    seen = []

    def handler(text, event):
        seen.append((text, event.source_device))
        return "Processando pelo Jarvis do PC."

    router = UnifiedCommandRouter(device_id="desktop:test", desktop_turn_handler=handler)
    session = JarvisSession.create(active_user="local")
    event = JarvisEvent.create(
        session_id=session.session_id,
        source_device="mobile:moto-e20",
        event_type="user_utterance",
        payload={"text": "pesquise raiz quadrada"},
    )

    outgoing = router.route_event(event, session=session)

    assert seen == [("pesquise raiz quadrada", "mobile:moto-e20")]
    assert outgoing[0].payload["text"] == "Processando pelo Jarvis do PC."
