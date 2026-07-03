from src.jarvis_unified.event_bus import JarvisEventBus
from src.jarvis_unified.models import JarvisEvent


def test_event_bus_publishes_to_subscribers():
    bus = JarvisEventBus()
    seen = []
    bus.subscribe(seen.append)

    event = JarvisEvent.create(
        session_id="s1",
        source_device="mobile:moto-e20",
        event_type="interrupt",
        payload={"scope": "all"},
    )
    bus.publish(event)

    assert seen == [event]
    assert bus.history(1) == [event]

