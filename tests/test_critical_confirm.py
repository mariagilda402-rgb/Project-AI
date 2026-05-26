import threading
import time

from src.tools.critical_confirm import CriticalConfirmationBus, try_voice_resolve_confirmation


def test_bus_resolve_approves():
    bus = CriticalConfirmationBus(timeout_sec=5.0, stdin_fallback_delay_sec=10.0)
    out: list[bool] = []

    def worker():
        out.append(bus.request("whatsapp", "Enviar mensagem?"))

    t = threading.Thread(target=worker)
    t.start()
    time.sleep(0.05)
    p = bus.get_pending()
    assert p is not None and p["id"]
    assert bus.resolve(p["id"], True) is True
    t.join(timeout=2)
    assert out == [True]


def test_bus_resolve_denies():
    bus = CriticalConfirmationBus(timeout_sec=5.0, stdin_fallback_delay_sec=10.0)
    out: list[bool] = []

    def worker():
        out.append(bus.request("file_manager", "Deletar arquivo?"))

    t = threading.Thread(target=worker)
    t.start()
    time.sleep(0.05)
    p = bus.get_pending()
    assert p is not None
    assert bus.resolve(p["id"], False) is True
    t.join(timeout=2)
    assert out == [False]


def test_bus_wrong_id_ignored():
    bus = CriticalConfirmationBus(timeout_sec=5.0, stdin_fallback_delay_sec=10.0)
    out: list[bool] = []

    def worker():
        out.append(bus.request("x", "y"))

    t = threading.Thread(target=worker)
    t.start()
    time.sleep(0.05)
    assert bus.resolve("wrongid", True) is False
    p = bus.get_pending()
    assert p is not None
    assert bus.resolve(p["id"], True) is True
    t.join(timeout=2)
    assert out == [True]


def test_request_skips_when_bus_disabled():
    bus = CriticalConfirmationBus(timeout_sec=5.0, stdin_fallback_delay_sec=10.0)
    bus.enabled = False
    assert bus.request("whatsapp", "x") is True
    assert bus.get_pending() is None


def test_try_voice_confirm():
    bus = CriticalConfirmationBus(timeout_sec=5.0, stdin_fallback_delay_sec=10.0)
    bus.enabled = True
    out: list[bool] = []

    def worker():
        out.append(bus.request("whatsapp", "Enviar?"))

    t = threading.Thread(target=worker)
    t.start()
    time.sleep(0.05)
    assert try_voice_resolve_confirmation(bus, "confirmar") is True
    t.join(timeout=2)
    assert out == [True]


def test_try_voice_cancel():
    bus = CriticalConfirmationBus(timeout_sec=5.0, stdin_fallback_delay_sec=10.0)
    out: list[bool] = []

    def worker():
        out.append(bus.request("whatsapp", "Enviar?"))

    t = threading.Thread(target=worker)
    t.start()
    time.sleep(0.05)
    assert try_voice_resolve_confirmation(bus, "cancelar") is True
    t.join(timeout=2)
    assert out == [False]


def test_try_voice_ignored_when_no_pending():
    bus = CriticalConfirmationBus(timeout_sec=5.0, stdin_fallback_delay_sec=10.0)
    assert try_voice_resolve_confirmation(bus, "confirmar") is False


def test_try_voice_ignored_when_bus_disabled():
    bus = CriticalConfirmationBus(timeout_sec=5.0, stdin_fallback_delay_sec=10.0)
    bus.enabled = False
    assert try_voice_resolve_confirmation(bus, "confirmar") is False
