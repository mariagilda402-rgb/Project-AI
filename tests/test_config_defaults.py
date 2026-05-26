from __future__ import annotations

from src.config import _default_vision_provider, load_settings


def test_vision_follows_groq_when_llm_is_groq():
    assert (
        _default_vision_provider("", "groq", "gemini-key", "nv-key", "groq-key")
        == "groq"
    )


def test_vision_explicit_overrides():
    assert (
        _default_vision_provider("gemini", "groq", "gk", "nk", "gq") == "gemini"
    )


def test_piper_jarvis_settings_from_env(monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "piper")
    monkeypatch.setenv("PIPER_JARVIS_QUALITY", "high")
    monkeypatch.setenv("PIPER_USE_CUDA", "true")

    settings = load_settings()

    assert settings.tts_provider == "piper"
    assert settings.piper_jarvis_quality == "high"
    assert settings.piper_use_cuda is True


def test_xtts_settings_from_env(monkeypatch):
    monkeypatch.delenv("TTS_PROVIDER", raising=False)
    monkeypatch.setenv("TTS_PROVIDER_ORDER", "edge,kokoro,piper")
    monkeypatch.setenv("XTTS_SPEAKER_WAV", "data/voice_samples/jarvis.wav")
    monkeypatch.setenv("XTTS_LANGUAGE", "pt")
    monkeypatch.setenv("XTTS_DEVICE", "cpu")
    monkeypatch.setenv("XTTS_PERSISTENT", "true")
    monkeypatch.setenv("XTTS_PRELOAD", "true")
    monkeypatch.setenv("STYLETTS2_COMMAND", '["python","inference.py"]')
    monkeypatch.setenv("STYLETTS2_PYTHON", "C:/styletts2/python.exe")
    monkeypatch.setenv("STYLETTS2_ALPHA", "0.25")
    monkeypatch.setenv("STYLETTS2_BETA", "0.65")
    monkeypatch.setenv("STYLETTS2_DIFFUSION_STEPS", "3")
    monkeypatch.setenv("STYLETTS2_EMBEDDING_SCALE", "1.4")
    monkeypatch.setenv("STYLETTS2_PERSISTENT", "true")
    monkeypatch.setenv("STYLETTS2_PRELOAD", "true")

    settings = load_settings()

    assert settings.tts_provider == "xtts"
    assert settings.tts_provider_order == "edge,kokoro,piper"
    assert settings.xtts_speaker_wav == "data/voice_samples/jarvis.wav"
    assert settings.xtts_language == "pt"
    assert settings.xtts_device == "cpu"
    assert settings.xtts_persistent is True
    assert settings.xtts_preload is True
    assert settings.styletts2_command == '["python","inference.py"]'
    assert settings.styletts2_python == "C:/styletts2/python.exe"
    assert settings.styletts2_alpha == 0.25
    assert settings.styletts2_beta == 0.65
    assert settings.styletts2_diffusion_steps == 3
    assert settings.styletts2_embedding_scale == 1.4
    assert settings.styletts2_persistent is True
    assert settings.styletts2_preload is True


def test_stt_sensitivity_settings_from_env(monkeypatch):
    monkeypatch.setenv("STT_ENERGY_THRESHOLD", "850")
    monkeypatch.setenv("STT_DYNAMIC_ENERGY", "false")
    monkeypatch.setenv("STT_PAUSE_THRESHOLD", "0.55")
    monkeypatch.setenv("STT_NON_SPEAKING_DURATION", "0.2")
    monkeypatch.setenv("STT_CALIBRATION_SECONDS", "1.2")
    monkeypatch.setenv("STT_MIN_AUDIO_SECONDS", "0.25")

    settings = load_settings()

    assert settings.stt_energy_threshold == 850
    assert settings.stt_dynamic_energy is False
    assert settings.stt_pause_threshold == 0.55
    assert settings.stt_non_speaking_duration == 0.2
    assert settings.stt_calibration_seconds == 1.2
    assert settings.stt_min_audio_seconds == 0.25


def test_startup_settings_from_env(monkeypatch):
    monkeypatch.setenv("START_VISION_TRACKER", "true")
    monkeypatch.setenv("START_HEARTBEAT", "false")
    monkeypatch.setenv("START_PROACTIVE_AGENT", "true")
    monkeypatch.setenv("ENABLE_CLAP_TRIGGER", "false")
    monkeypatch.setenv("CLAP_THRESHOLD", "0.22")
    monkeypatch.setenv("CLAP_MAX_GAP", "1.7")

    settings = load_settings()

    assert settings.start_vision_tracker is True
    assert settings.start_heartbeat is False
    assert settings.start_proactive_agent is True
    assert settings.enable_clap_trigger is False
    assert settings.clap_threshold == 0.22
    assert settings.clap_max_gap == 1.7


def test_ui_motion_settings_from_env(monkeypatch):
    monkeypatch.setenv("UI_MOTION_LEVEL", "expressive")
    monkeypatch.setenv("UI_DENSITY", "compact")

    settings = load_settings()

    assert settings.ui_motion_level == "expressive"
    assert settings.ui_density == "compact"


def test_ui_motion_settings_fall_back_to_safe_defaults(monkeypatch):
    monkeypatch.setenv("UI_MOTION_LEVEL", "cinematic-chaos")
    monkeypatch.setenv("UI_DENSITY", "tiny")

    settings = load_settings()

    assert settings.ui_motion_level == "balanced"
    assert settings.ui_density == "comfortable"
