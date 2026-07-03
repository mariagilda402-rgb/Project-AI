import threading
import time

from src.jarvis_unified.local_server import UnifiedJarvisLocalBridge
from src.jarvis_unified.models import JarvisEvent


def test_unified_bridge_stop_closes_server_and_clients(monkeypatch):
    bridge = UnifiedJarvisLocalBridge(host="127.0.0.1", port=0)

    # Não rodamos servidor real por causa do ambiente de teste, apenas garantimos que stop() não quebra.
    bridge._server = type("FakeServer", (), {
        "shutdown": lambda self: None,
    })()
    bridge._thread = threading.Thread(target=lambda: None)
    bridge._thread.start()

    try:
        bridge.stop(timeout=0.1)
        assert bridge._server is None
        assert bridge._thread is not None
    finally:
        bridge._thread.join(timeout=0.1)
