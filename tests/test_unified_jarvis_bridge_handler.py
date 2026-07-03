from src.jarvis_unified.bridge_handler import make_unified_event_handler
from src.jarvis_unified.models import JarvisEvent


class DummyQueue:
    def __init__(self):
        self.items = []

    def put(self, item):
        self.items.append(item)


class DummyLoop:
    def __init__(self):
        self.task_queue = DummyQueue()


def test_unified_event_handler_forwards_user_utterance_to_task_queue():
    loop = DummyLoop()
    handler = make_unified_event_handler(loop)

    event = JarvisEvent.create(
        session_id="s1",
        source_device="mobile:moto-e20",
        event_type="user_utterance",
        payload={"text": "teste comando"},
    )

    handler(event)

    assert loop.task_queue.items == [("teste comando", "Unified:mobile:moto-e20")]


def test_unified_event_handler_ignores_non_utterance_events():
    loop = DummyLoop()
    handler = make_unified_event_handler(loop)

    event = JarvisEvent.create(
        session_id="s1",
        source_device="mobile:moto-e20",
        event_type="assistant_delta",
        payload={"text": "ok"},
    )

    handler(event)

    assert loop.task_queue.items == []
