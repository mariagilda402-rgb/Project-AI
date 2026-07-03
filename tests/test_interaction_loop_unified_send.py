from src.core.interaction_loop import InteractionLoop


class FakeSession:
    def __init__(self):
        self.session_id = "s1"


class FakeBridge:
    def __init__(self):
        self.session_state = type("S", (), {"current": lambda self: FakeSession()})()
        self.received = []

    def emit_event(self, event):
        self.received.append(event)


class DummyServices(dict):
    def __init__(self):
        # minimal keys required by InteractionLoop.__init__
        super().__init__()
        self["agent"] = object()
        self["llm"] = None
        self["tts"] = None
        self["stt"] = None
        self["runtime_status"] = type("R", (), {"set_processing": lambda *a, **k: None, "set_enqueue_preview": lambda *a, **k: None, "set_mic_listening": lambda *a, **k: None})()
        self["settings"] = type("S", (), {"use_mic": False})()
        self["confirm_bus"] = None


def test_send_unified_assistant_text_emits_events():
    services = DummyServices()
    loop = InteractionLoop(services)
    bridge = FakeBridge()
    loop.set_unified_bridge(bridge)

    # send text to a mobile target
    loop._send_unified_assistant_text("Unified:mobile:moto-e20", "Olá do Jarvis")

    # Expect two events emitted: assistant_delta and render_update
    assert len(bridge.received) == 2
    types = [getattr(evt, "type", None) for evt in bridge.received]
    assert "assistant_delta" in types
    assert "render_update" in types
 