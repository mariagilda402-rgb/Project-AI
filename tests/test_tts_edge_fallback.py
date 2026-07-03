from __future__ import annotations

import subprocess

from src.services.tts import TTSService


def test_edge_tts_unavailable_skips_edge_provider(monkeypatch):
    service = TTSService.__new__(TTSService)
    service.provider = "edge"
    service.provider_order = ["edge", "local"]
    service.edge_tts_available = False
    service.last_error = ""
    calls = []

    monkeypatch.setattr(
        service,
        "_speak_with_edge",
        lambda text: calls.append(("edge", text)) or False,
    )
    monkeypatch.setattr(
        service,
        "_speak_with_local",
        lambda text: calls.append(("local", text)) or True,
    )

    service._speak_one_chunk("Teste edge indisponível")

    assert calls == [
        ("local", "Teste edge indisponível"),
    ]


def test_install_edge_tts_runs_pip_install(monkeypatch):
    from src.ui.desktop_app import DesktopApi

    api = DesktopApi(None, None, None)
    fake_result = type("R", (), {"returncode": 0, "stderr": "", "stdout": ""})()

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: fake_result)

    fake_tts = type("T", (), {})()
    fake_tts._check_edge_tts_availability = lambda: True
    api._tts = fake_tts

    result = api.install_edge_tts()

    assert result["ok"] is True
    assert api._tts.edge_tts_available is True
