from __future__ import annotations

import speech_recognition as sr

from src.config import load_settings
from src.services.stt import STTService
from src.services.tts import TTSService


def _status(ok: bool) -> str:
    return "OK" if ok else "FALHOU"


def check_microphone_available() -> bool:
    try:
        names = sr.Microphone.list_microphone_names()
        return len(names) > 0
    except Exception:
        return False


def check_murf_keys(api_key: str, voice_id: str) -> bool:
    return bool(api_key.strip()) and bool(voice_id.strip())


def run_audio_diagnostics(settings: object | None = None) -> dict:
    """Diagnóstico rápido sem captura interativa (adequado ao painel)."""
    s = settings or load_settings()
    mic_ok = check_microphone_available()
    murf_ok = check_murf_keys(getattr(s, "murf_api_key", ""), getattr(s, "murf_voice_id", ""))
    return {
        "microphone_detected": mic_ok,
        "murf_configured": murf_ok,
        "stt_language": getattr(s, "stt_language", "pt-BR"),
        "use_mic": getattr(s, "use_mic", True),
        "stt_energy_threshold": getattr(s, "stt_energy_threshold", 1100),
        "stt_dynamic_energy": getattr(s, "stt_dynamic_energy", True),
        "stt_pause_threshold": getattr(s, "stt_pause_threshold", 0.8),
        "stt_min_audio_seconds": getattr(s, "stt_min_audio_seconds", 0.35),
    }


def run_checks() -> None:
    settings = load_settings()
    print("=== Diagnostico de Audio ===")

    mic_ok = check_microphone_available()
    print(f"[1] Microfone detectado: {_status(mic_ok)}")
    if not mic_ok:
        print("    Dica: conecte/ative um microfone no Windows e permita acesso ao microfone.")

    murf_ok = check_murf_keys(settings.murf_api_key, settings.murf_voice_id)
    print(f"[2] Credenciais Murf (API key + voice id): {_status(murf_ok)}")
    if not murf_ok:
        print("    Dica: preencha MURF_API_KEY e MURF_VOICE_ID no .env para ativar TTS Murf.")

    if murf_ok:
        print("[3] Teste TTS Murf: iniciando...")
        murf_tts = TTSService(
            api_key="",
            model=settings.tts_model,
            voice=settings.tts_voice,
            provider="murf",
            murf_api_key=settings.murf_api_key,
            murf_voice_id=settings.murf_voice_id,
            murf_api_url=settings.murf_api_url,
            allow_system_player_on_failure=settings.tts_allow_system_player,
        )
        ok = murf_tts._speak_with_murf("Teste Murf concluido.")
        print(f"    TTS Murf: {_status(ok)}")
        print(f"    Voice ID normalizado: {murf_tts.murf_voice_id}")
        print("    Ultimo audio salvo em: data/cache/murf_last.mp3")
        if not ok and murf_tts.last_error:
            print(f"    Erro Murf: {murf_tts.last_error}")

    print("[4] Teste TTS local (pyttsx3, som robotizado): iniciando...")
    try:
        local_tts = TTSService(
            api_key="",
            model=settings.tts_model,
            voice=settings.tts_voice,
            provider="local",
        )
        local_tts.speak("Teste de voz local concluido.")
        print(f"    TTS local: {_status(True)}")
    except Exception:
        print(f"    TTS local: {_status(False)}")

    print("[5] Teste STT (SpeechRecognition + Google): iniciando...")
    try:
        stt = STTService(
            use_mic=settings.use_mic,
            language=settings.stt_language,
            energy_threshold=settings.stt_energy_threshold,
            dynamic_energy_threshold=settings.stt_dynamic_energy,
            pause_threshold=settings.stt_pause_threshold,
            non_speaking_duration=settings.stt_non_speaking_duration,
            min_audio_seconds=settings.stt_min_audio_seconds,
        )
        print(f"    Idioma STT: {settings.stt_language}")
        print(f"    Threshold energia: {settings.stt_energy_threshold}")
        if not settings.use_mic:
            print("    USE_MIC=false, pulando captura de voz ao vivo.")
        else:
            print("    Fale algo apos 'Ouvindo...'.")
            text = stt.listen()
            print(f"    Capturado: '{text}'")
        print(f"    STT: {_status(True)}")
    except Exception:
        print(f"    STT: {_status(False)}")

    print("=== Fim do diagnostico ===")


if __name__ == "__main__":
    run_checks()
