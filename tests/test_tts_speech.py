from __future__ import annotations

from pathlib import Path

from src.services.tts import split_text_for_tts, strip_text_for_speech


def test_strip_markdown():
    raw = "**IDE** PyCharm\n\n- item um\n- dois"
    out = strip_text_for_speech(raw)
    assert "**" not in out
    assert "IDE" in out


def test_split_respects_max():
    s = "Um. " * 400
    parts = split_text_for_tts(s, 80)
    assert len(parts) >= 2
    assert all(len(p) <= 85 for p in parts)


def test_default_tts_provider_order_prioritizes_xtts_then_edge_then_kokoro():
    from src.services.tts import resolve_tts_provider_order

    order = resolve_tts_provider_order("xtts")

    assert order[:5] == ["xtts", "edge", "kokoro", "rvc", "piper"]
    assert order[-1] == "local"


def test_tts_provider_order_uses_selected_primary_before_standard_fallbacks():
    from src.services.tts import resolve_tts_provider_order

    order = resolve_tts_provider_order("piper")

    assert order[:3] == ["piper", "edge", "kokoro"]
    assert order.count("piper") == 1


def test_tts_provider_order_honors_configured_fallbacks_after_primary():
    from src.services.tts import resolve_tts_provider_order

    order = resolve_tts_provider_order("xtts", "edge,kokoro,rvc,edge")

    assert order[:4] == ["xtts", "edge", "kokoro", "rvc"]
    assert order.count("edge") == 1


def test_xtts_provider_falls_back_to_edge_then_kokoro(monkeypatch):
    from src.services.tts import TTSService

    service = TTSService.__new__(TTSService)
    service.provider = "xtts"
    service.provider_order = ["xtts", "edge", "kokoro", "local"]
    service.client = None
    service.last_error = ""
    calls = []

    monkeypatch.setattr(
        service,
        "_speak_with_xtts",
        lambda text: calls.append(("xtts", text)) or False,
    )
    monkeypatch.setattr(
        service,
        "_speak_with_edge",
        lambda text: calls.append(("edge", text)) or False,
    )
    monkeypatch.setattr(
        service,
        "_speak_with_kokoro",
        lambda text: calls.append(("kokoro", text)) or True,
    )
    monkeypatch.setattr(
        service,
        "_speak_with_local",
        lambda text: calls.append(("local", text)) or True,
    )

    service._speak_one_chunk("Teste de voz.")

    assert calls == [
        ("xtts", "Teste de voz."),
        ("edge", "Teste de voz."),
        ("kokoro", "Teste de voz."),
    ]


def test_xtts_requires_reference_audio_before_loading_model(tmp_path):
    from src.services.tts import TTSService

    service = TTSService.__new__(TTSService)
    service.xtts_speaker_wav = str(tmp_path / "missing.wav")
    service.xtts_model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
    service.xtts_language = "pt"
    service.xtts_device = "cpu"
    service.last_error = ""

    assert service._speak_with_xtts("Teste de voz.") is False
    assert "XTTS_SPEAKER_WAV" in service.last_error


def test_xtts_external_python_generates_audio_without_inprocess_model(tmp_path, monkeypatch):
    from src.services.tts import TTSService

    ref = tmp_path / "ref.wav"
    ref.write_bytes(b"RIFFfake")
    out_seen = {}

    class Completed:
        returncode = 0
        stderr = ""

    def fake_run(cmd, **kwargs):
        out_path = cmd[cmd.index("--out") + 1]
        out_seen["cmd"] = cmd
        out_seen["out"] = out_path
        Path(out_path).write_bytes(b"RIFFgenerated")
        return Completed()

    service = TTSService.__new__(TTSService)
    service.xtts_python = "C:/xtts/python.exe"
    service.xtts_speaker_wav = str(ref)
    service.xtts_model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
    service.xtts_language = "pt"
    service.xtts_device = "cpu"
    service.last_error = ""

    monkeypatch.setattr("src.services.tts.subprocess.run", fake_run)

    generated = service._generate_xtts_file("Teste de voz.")

    assert generated is not None
    assert generated.read_bytes() == b"RIFFgenerated"
    assert out_seen["cmd"][:3] == ["C:/xtts/python.exe", "-m", "src.services.xtts_external_worker"]


def test_xtts_external_python_uses_persistent_worker_when_enabled(tmp_path, monkeypatch):
    from src.services.tts import TTSService

    ref = tmp_path / "ref.wav"
    ref.write_bytes(b"RIFFfake")
    seen = {}

    class FakeWorker:
        def synthesize(self, text, out):
            seen["text"] = text
            seen["out"] = out
            Path(out).write_bytes(b"RIFFpersistent")

    def fake_worker(**kwargs):
        seen["kwargs"] = kwargs
        return FakeWorker()

    service = TTSService.__new__(TTSService)
    service.xtts_python = "C:/xtts/python.exe"
    service.xtts_persistent = True
    service.xtts_speaker_wav = str(ref)
    service.xtts_model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
    service.xtts_language = "pt"
    service.xtts_device = "cpu"
    service.last_error = ""

    monkeypatch.setattr("src.services.tts._get_xtts_external_worker", fake_worker)

    generated = service._generate_xtts_file("Teste de voz.")

    assert generated is not None
    assert generated.read_bytes() == b"RIFFpersistent"
    assert seen["text"] == "Teste de voz."
    assert seen["kwargs"]["python_exe"] == "C:/xtts/python.exe"
    assert seen["kwargs"]["speaker"] == str(ref)


def test_xtts_warmup_starts_persistent_worker(tmp_path, monkeypatch):
    from src.services.tts import TTSService

    ref = tmp_path / "ref.wav"
    ref.write_bytes(b"RIFFfake")
    seen = {}

    class FakeWorker:
        def preload(self):
            seen["preload"] = True

    class SyncThread:
        def __init__(self, target, **kwargs):
            self.target = target

        def start(self):
            self.target()

    def fake_worker(**kwargs):
        seen["kwargs"] = kwargs
        return FakeWorker()

    service = TTSService.__new__(TTSService)
    service.xtts_python = "C:/xtts/python.exe"
    service.xtts_persistent = True
    service.xtts_speaker_wav = str(ref)
    service.xtts_model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
    service.xtts_language = "pt"
    service.xtts_device = "cpu"

    monkeypatch.setattr("src.services.tts._get_xtts_external_worker", fake_worker)
    monkeypatch.setattr("src.services.tts.threading.Thread", SyncThread)

    assert service.warmup_xtts_async() is True
    assert seen["preload"] is True
    assert seen["kwargs"]["python_exe"] == "C:/xtts/python.exe"


def test_styletts2_requires_command_before_running(tmp_path):
    from src.services.tts import TTSService

    service = TTSService.__new__(TTSService)
    service.styletts2_command = ""
    service.styletts2_reference_wav = str(tmp_path / "reference.wav")
    service.last_error = ""

    assert service._speak_with_styletts2("Teste de voz.") is False
    assert "STYLETTS2_COMMAND" in service.last_error


def test_styletts2_external_python_uses_persistent_worker(tmp_path, monkeypatch):
    from src.services.tts import TTSService

    ref = tmp_path / "ref.wav"
    ref.write_bytes(b"RIFFref")
    seen = {}

    class FakeWorker:
        def synthesize(self, text, out):
            seen["text"] = text
            seen["out"] = out
            Path(out).write_bytes(b"RIFFstyletts2")

    def fake_worker(**kwargs):
        seen["kwargs"] = kwargs
        return FakeWorker()

    service = TTSService.__new__(TTSService)
    service.styletts2_python = "C:/styletts2/python.exe"
    service.styletts2_persistent = True
    service.styletts2_reference_wav = str(ref)
    service.styletts2_alpha = 0.25
    service.styletts2_beta = 0.65
    service.styletts2_diffusion_steps = 3
    service.styletts2_embedding_scale = 1.4
    service.last_error = ""

    monkeypatch.setattr("src.services.tts._get_styletts2_external_worker", fake_worker)

    out = service._generate_styletts2_file("Teste de voz.")

    assert out is not None
    assert out.read_bytes() == b"RIFFstyletts2"
    assert seen["text"] == "Teste de voz."
    assert seen["kwargs"]["python_exe"] == "C:/styletts2/python.exe"
    assert seen["kwargs"]["reference"] == str(ref)
    assert seen["kwargs"]["diffusion_steps"] == 3
    assert seen["kwargs"]["embedding_scale"] == 1.4


def test_styletts2_warmup_starts_persistent_worker(tmp_path, monkeypatch):
    from src.services.tts import TTSService

    ref = tmp_path / "ref.wav"
    ref.write_bytes(b"RIFFref")
    seen = {}

    class FakeWorker:
        def preload(self):
            seen["preload"] = True

    class SyncThread:
        def __init__(self, target, **kwargs):
            self.target = target

        def start(self):
            self.target()

    def fake_worker(**kwargs):
        seen["kwargs"] = kwargs
        return FakeWorker()

    service = TTSService.__new__(TTSService)
    service.styletts2_python = "C:/styletts2/python.exe"
    service.styletts2_persistent = True
    service.styletts2_reference_wav = str(ref)
    service.styletts2_alpha = 0.25
    service.styletts2_beta = 0.65
    service.styletts2_diffusion_steps = 3
    service.styletts2_embedding_scale = 1.4

    monkeypatch.setattr("src.services.tts._get_styletts2_external_worker", fake_worker)
    monkeypatch.setattr("src.services.tts.threading.Thread", SyncThread)

    assert service.warmup_styletts2_async() is True
    assert seen["preload"] is True
    assert seen["kwargs"]["python_exe"] == "C:/styletts2/python.exe"


def test_styletts2_worker_ignores_json_scalar_stdout():
    from src.services.tts import _PersistentStyleTTS2Worker

    worker = _PersistentStyleTTS2Worker(
        python_exe="python",
        reference="voice.wav",
        model_checkpoint="",
        config_path="",
        alpha=0.3,
        beta=0.7,
        diffusion_steps=3,
        embedding_scale=1.0,
        cwd=Path.cwd(),
    )
    worker.stdout_queue.put("177\n")
    worker.stdout_queue.put('{"type":"ready","ok":true}\n')

    assert worker._wait_for_message(None, 1)["ok"] is True


def test_tts_pipeline_prefetches_next_file_before_playing_current(tmp_path, monkeypatch):
    from src.services.tts import TTSService

    events = []
    service = TTSService.__new__(TTSService)
    service.provider = "styletts2"
    service.provider_order = ["styletts2"]
    service.tts_prefetch_chunks = True
    service.pause_between_chunks_sec = 0
    service._interrupt_event = __import__("threading").Event()
    service.last_error = ""

    def fake_generate(provider, text):
        path = tmp_path / f"{text}.wav"
        path.write_bytes(b"RIFF")
        events.append(("generate", text))
        return path

    def fake_play(path):
        events.append(("play", Path(path).stem))

    monkeypatch.setattr(service, "_generate_audio_file_for_provider", fake_generate)
    monkeypatch.setattr(service, "_play_audio_file", fake_play)

    service._speak_prefetched_chunks(["um", "dois"])

    assert events == [
        ("generate", "um"),
        ("generate", "dois"),
        ("play", "um"),
        ("play", "dois"),
    ]


def test_piper_jarvis_medium_model_files():
    from src.services.tts import piper_jarvis_model_files

    model_file, config_file = piper_jarvis_model_files("medium")

    assert model_file == "en/en_GB/jarvis/medium/jarvis-medium.onnx"
    assert config_file == "en/en_GB/jarvis/medium/jarvis-medium.onnx.json"


def test_piper_provider_falls_back_to_edge_when_unavailable(monkeypatch):
    from src.services.tts import TTSService

    service = TTSService.__new__(TTSService)
    service.provider = "piper"
    service.client = None
    service.last_error = ""

    class DummyLocalEngine:
        def say(self, text):
            raise AssertionError("local engine should not be used when Edge fallback succeeds")

        def runAndWait(self):
            raise AssertionError("local engine should not be used when Edge fallback succeeds")

    service.local_engine = DummyLocalEngine()
    calls = []

    monkeypatch.setattr(
        service,
        "_speak_with_piper",
        lambda text: calls.append(("piper", text)) or False,
    )
    monkeypatch.setattr(
        service,
        "_speak_with_edge",
        lambda text: calls.append(("edge", text)) or True,
    )

    service._speak_one_chunk("Teste de voz.")

    assert calls == [("piper", "Teste de voz."), ("edge", "Teste de voz.")]


def test_panel_exposes_piper_jarvis_provider():
    html = Path("src/ui/panel.html").read_text(encoding="utf-8")

    assert '<option value="piper">Piper JARVIS (PC local)</option>' in html


def test_panel_exposes_styletts2_and_fallback_order_controls():
    html = Path("src/ui/panel.html").read_text(encoding="utf-8")

    assert '<option value="styletts2">StyleTTS2 (Clone local)</option>' in html
    assert 'id="cfgTtsFallbackOrder"' in html
    assert 'id="cfgStyleTts2DiffusionSteps"' in html
