from __future__ import annotations

from src.services.stt import STTService


def test_stt_service_applies_sensitivity_settings():
    stt = STTService(
        use_mic=True,
        language="pt-BR",
        energy_threshold=750,
        dynamic_energy_threshold=False,
        pause_threshold=0.55,
        non_speaking_duration=0.2,
        min_audio_seconds=0.25,
    )

    assert stt.recognizer.energy_threshold == 750
    assert stt.recognizer.dynamic_energy_threshold is False
    assert stt.recognizer.pause_threshold == 0.55
    assert stt.recognizer.non_speaking_duration == 0.2
    assert stt.min_audio_seconds == 0.25


def test_stt_service_configure_updates_running_recognizer():
    stt = STTService(use_mic=False)

    stt.configure(
        use_mic=True,
        language="en-US",
        energy_threshold=900,
        dynamic_energy_threshold=True,
        pause_threshold=0.7,
        non_speaking_duration=0.3,
        min_audio_seconds=0.4,
    )

    assert stt.use_mic is True
    assert stt.language == "en-US"
    assert stt.recognizer.energy_threshold == 900
    assert stt.recognizer.dynamic_energy_threshold is True
    assert stt.recognizer.pause_threshold == 0.7
    assert stt.recognizer.non_speaking_duration == 0.3
    assert stt.min_audio_seconds == 0.4
