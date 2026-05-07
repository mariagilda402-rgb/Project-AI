from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv

# Carrega .env na raiz do projeto mesmo se o CWD for outro (ex.: IDE).
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, encoding="utf-8-sig")


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _normalize_llm_provider(raw: str | None) -> str:
    """gemini | openrouter | nvidia | groq — provedor principal para chat (fallback tenta os outros)."""
    if not raw:
        return "gemini"
    v = raw.strip().lower()
    if v in ("gemini", "google"):
        return "gemini"
    if v in ("openrouter", "open_router"):
        return "openrouter"
    if v in ("nvidia", "nvidia_nim", "nim"):
        return "nvidia"
    if v in ("groq",):
        return "groq"
    return "gemini"


def _normalize_vision_provider(raw: str | None) -> str:
    """gemini | nvidia | groq — modelo multimodal para captura de tela."""
    if not raw:
        return ""
    v = raw.strip().lower()
    if v in ("nvidia", "nim"):
        return "nvidia"
    if v in ("groq",):
        return "groq"
    return "gemini"


def _assistant_persona_from_env(raw: str | None) -> str:
    """Texto livre (use \\n no .env para quebras de linha). Vazio = usa padrao do prompt."""
    v = (raw or "").strip()
    if not v:
        return ""
    return v.replace("\\n", "\n")


def _safe_http_timeout(raw: str | None) -> float:
    try:
        v = float((raw or "").strip() or "180")
    except ValueError:
        v = 180.0
    return max(30.0, min(600.0, v))


def _default_vision_provider(
    explicit: str,
    llm_provider: str,
    gemini_key: str,
    nvidia_key: str,
    groq_key: str,
) -> str:
    """Sem VISION_PROVIDER no .env: prioriza o mesmo ecossistema do chat (ex.: groq com LLM_PROVIDER=groq)."""
    if explicit in ("gemini", "nvidia", "groq"):
        return explicit
    if llm_provider == "groq" and groq_key:
        return "groq"
    if llm_provider == "nvidia" and nvidia_key:
        return "nvidia"
    if llm_provider == "gemini" and gemini_key:
        return "gemini"
    if gemini_key:
        return "gemini"
    if groq_key:
        return "groq"
    if nvidia_key:
        return "nvidia"
    return "gemini"


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    vision_provider: str
    gemini_api_key: str
    gemini_model: str
    openrouter_api_key: str
    openrouter_model: str
    nvidia_api_key: str
    nvidia_model: str
    nvidia_vision_model: str
    groq_api_key: str
    groq_model: str
    groq_vision_model: str
    openai_api_key: str
    tts_model: str
    tts_voice: str
    use_mic: bool
    require_critical_confirmation: bool
    gemini_max_rpm: int
    gemini_retry_attempts: int
    gemini_use_function_calling: bool
    stt_language: str
    tts_provider: str
    murf_api_key: str
    murf_voice_id: str
    murf_api_url: str
    tts_allow_system_player: bool
    tts_max_chunk_chars: int
    tts_pause_between_chunks_sec: float
    edge_tts_rate: str
    edge_tts_volume: str
    llm_http_timeout: float
    assistant_base_persona: str
    llm_fallback_gemini: bool
    enable_visualizer: bool
    kokoro_voice: str
    kokoro_speed: float


def load_settings() -> Settings:
    gemini_key = (os.getenv("GEMINI_API_KEY", "") or "").strip()
    nvidia_key = (os.getenv("NVIDIA_API_KEY", "") or "").strip()
    groq_key = (os.getenv("GROQ_API_KEY", "") or "").strip()
    vision_pv = _normalize_vision_provider(os.getenv("VISION_PROVIDER"))
    llm_pv = _normalize_llm_provider(os.getenv("LLM_PROVIDER"))
    return Settings(
        llm_provider=llm_pv,
        vision_provider=_default_vision_provider(
            vision_pv, llm_pv, gemini_key, nvidia_key, groq_key
        ),
        gemini_api_key=gemini_key,
        gemini_model=(os.getenv("GEMINI_MODEL", "gemini-2.5-flash") or "").strip()
        or "gemini-2.5-flash",
        openrouter_api_key=(os.getenv("OPENROUTER_API_KEY", "") or "").strip(),
        openrouter_model=(os.getenv("OPENROUTER_MODEL", "qwen/qwen3-30b-a3b:free") or "").strip()
        or "qwen/qwen3-30b-a3b:free",
        nvidia_api_key=nvidia_key,
        nvidia_model=(os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct") or "").strip()
        or "meta/llama-3.1-70b-instruct",
        nvidia_vision_model=(os.getenv("NVIDIA_VISION_MODEL", "") or "").strip(),
        groq_api_key=groq_key,
        groq_model=(os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile") or "").strip()
        or "llama-3.3-70b-versatile",
        groq_vision_model=(
            (os.getenv("GROQ_VISION_MODEL", "") or "").strip()
            or "meta-llama/llama-4-scout-17b-16e-instruct"
        ),
        openai_api_key=(os.getenv("OPENAI_API_KEY", "") or "").strip(),
        tts_model=os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
        tts_voice=os.getenv("OPENAI_TTS_VOICE", "alloy"),
        use_mic=_as_bool(os.getenv("USE_MIC"), default=True),
        require_critical_confirmation=_as_bool(
            os.getenv("REQUIRE_CRITICAL_CONFIRMATION"), default=True
        ),
        gemini_max_rpm=int(os.getenv("GEMINI_MAX_RPM", "10")),
        gemini_retry_attempts=int(os.getenv("GEMINI_RETRY_ATTEMPTS", "3")),
        gemini_use_function_calling=_as_bool(
            os.getenv("GEMINI_USE_FUNCTION_CALLING"), default=True
        ),
        stt_language=os.getenv("STT_LANGUAGE", "pt-BR"),
        tts_provider=os.getenv("TTS_PROVIDER", "local"),
        murf_api_key=os.getenv("MURF_API_KEY", ""),
        murf_voice_id=os.getenv("MURF_VOICE_ID", ""),
        murf_api_url=os.getenv("MURF_API_URL", "https://api.murf.ai/v1/speech/generate"),
        tts_allow_system_player=_as_bool(
            os.getenv("TTS_ALLOW_SYSTEM_PLAYER"), default=False
        ),
        tts_max_chunk_chars=max(100, min(8000, int(os.getenv("TTS_MAX_CHUNK_CHARS", "1800")))),
        tts_pause_between_chunks_sec=max(
            0.0, min(3.0, float(os.getenv("TTS_PAUSE_BETWEEN_CHUNKS_SEC", "0.4")))
        ),
        edge_tts_rate=os.getenv("EDGE_TTS_RATE", "+10%"),
        edge_tts_volume=os.getenv("EDGE_TTS_VOLUME", "-20%"),
        llm_http_timeout=_safe_http_timeout(os.getenv("LLM_HTTP_TIMEOUT", "180")),
        assistant_base_persona=_assistant_persona_from_env(
            os.getenv("ASSISTANT_BASE_PERSONA", "")
        ),
        llm_fallback_gemini=_as_bool(os.getenv("LLM_FALLBACK_GEMINI"), default=False),
        enable_visualizer=_as_bool(os.getenv("ENABLE_VISUALIZER"), default=False),
        kokoro_voice=(os.getenv("KOKORO_VOICE", "pf_dora") or "").strip() or "pf_dora",
        kokoro_speed=max(0.5, min(2.0, float(os.getenv("KOKORO_SPEED", "1.0") or "1.0"))),
    )
