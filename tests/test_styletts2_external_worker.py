from __future__ import annotations

import io
import json
import sys
import types
from pathlib import Path


def _install_fake_styletts2(monkeypatch, observed):
    styletts2_fork = types.ModuleType("styletts2_fork")
    tts_module = types.ModuleType("styletts2_fork.tts")

    class FakeStyleTTS2:
        def __init__(self, **kwargs):
            observed["loads"] = observed.get("loads", 0) + 1
            observed["init_kwargs"] = kwargs

        def inference(self, text, **kwargs):
            observed.setdefault("calls", []).append((text, kwargs))
            Path(kwargs["output_wav_file"]).write_bytes(b"RIFFstyletts2")
            return [0.0]

    tts_module.StyleTTS2 = FakeStyleTTS2
    styletts2_fork.tts = tts_module
    monkeypatch.setitem(sys.modules, "styletts2_fork", styletts2_fork)
    monkeypatch.setitem(sys.modules, "styletts2_fork.tts", tts_module)


def test_styletts2_worker_generates_file_with_parameters(monkeypatch, tmp_path):
    from src.services import styletts2_external_worker

    observed = {}
    _install_fake_styletts2(monkeypatch, observed)

    ref = tmp_path / "ref.wav"
    ref.write_bytes(b"RIFFref")
    out = tmp_path / "out.wav"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "styletts2_external_worker",
            "--reference",
            str(ref),
            "--out",
            str(out),
            "--text",
            "Teste.",
            "--alpha",
            "0.25",
            "--beta",
            "0.65",
            "--diffusion-steps",
            "3",
            "--embedding-scale",
            "1.4",
        ],
    )

    assert styletts2_external_worker.main() == 0
    assert out.read_bytes() == b"RIFFstyletts2"
    assert observed["loads"] == 1
    call = observed["calls"][0]
    assert call[0] == "Teste."
    assert call[1]["target_voice_path"] == str(ref)
    assert call[1]["alpha"] == 0.25
    assert call[1]["beta"] == 0.65
    assert call[1]["diffusion_steps"] == 3
    assert call[1]["embedding_scale"] == 1.4


def test_styletts2_worker_server_reuses_loaded_model(monkeypatch, tmp_path):
    from src.services import styletts2_external_worker

    observed = {}
    _install_fake_styletts2(monkeypatch, observed)

    ref = tmp_path / "ref.wav"
    ref.write_bytes(b"RIFFref")
    out1 = tmp_path / "out1.wav"
    out2 = tmp_path / "out2.wav"
    stdin = "\n".join(
        [
            json.dumps({"id": "one", "text": "Primeiro.", "out": str(out1)}),
            json.dumps({"id": "two", "text": "Segundo.", "out": str(out2)}),
        ]
    )
    stdout = io.StringIO()

    monkeypatch.setattr(sys, "stdin", io.StringIO(stdin + "\n"))
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "styletts2_external_worker",
            "--server",
            "--reference",
            str(ref),
            "--alpha",
            "0.2",
            "--beta",
            "0.6",
            "--diffusion-steps",
            "2",
            "--embedding-scale",
            "1.0",
        ],
    )

    assert styletts2_external_worker.main() == 0

    messages = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert messages[0]["type"] == "ready"
    assert messages[1]["id"] == "one"
    assert messages[1]["ok"] is True
    assert messages[2]["id"] == "two"
    assert messages[2]["ok"] is True
    assert observed["loads"] == 1
    assert out1.read_bytes() == b"RIFFstyletts2"
    assert out2.read_bytes() == b"RIFFstyletts2"
