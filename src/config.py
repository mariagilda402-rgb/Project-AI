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


def _as_int(
    value: str | None,
    default: int,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    try:
        parsed = int(float((value or "").strip() or str(default)))
    except (TypeError, ValueError):
        parsed = default
    if minimum is not None:
        parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


def _as_float(
    value: str | None,
    default: float,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    try:
        parsed = float((value or "").strip() or str(default))
    except (TypeError, ValueError):
        parsed = default
    if minimum is not None:
        parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


def _normalize_llm_provider(raw: str | None) -> str:
    """gemini | openrouter | nvidia | groq — provedor principal para chat (fallback tenta os outros)."""
    if not raw:
        return "gemini"
    v = raw.strip().lower()
    if v in ("gemini", "google"):
        return "gemini"
    if v in ("ollama", "local"):
        return "ollama"
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


def _normalize_choice(raw: str | None, allowed: set[str], default: str) -> str:
    value = (raw or "").strip().lower()
    return value if value in allowed else default


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
    ollama_model: str
    ollama_base_url: str
    openai_api_key: str
    tts_model: str
    tts_voice: str
    use_mic: bool
    gemini_max_rpm: int
    gemini_retry_attempts: int
    gemini_use_function_calling: bool
    stt_language: str
    stt_energy_threshold: int
    stt_dynamic_energy: bool
    stt_pause_threshold: float
    stt_non_speaking_duration: float
    stt_calibration_seconds: float
    stt_min_audio_seconds: float
    tts_provider: str
    tts_provider_order: str
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
    xtts_model_name: str
    xtts_speaker_wav: str
    xtts_language: str
    xtts_device: str
    xtts_rvc_voice: str
    xtts_python: str
    xtts_persistent: bool
    xtts_preload: bool
    styletts2_command: str
    styletts2_reference_wav: str
    styletts2_python: str
    styletts2_model_checkpoint: str
    styletts2_config: str
    styletts2_alpha: float
    styletts2_beta: float
    styletts2_diffusion_steps: int
    styletts2_embedding_scale: float
    styletts2_persistent: bool
    styletts2_preload: bool
    tts_prefetch_chunks: bool
    start_vision_tracker: bool
    start_heartbeat: bool
    start_proactive_agent: bool
    enable_clap_trigger: bool
    clap_threshold: float
    clap_min_gap: float
    clap_max_gap: float
    clap_cooldown: float
    piper_repo_id: str
    piper_jarvis_quality: str
    piper_model_file: str
    piper_config_file: str
    piper_use_cuda: bool
    piper_fx_preset: str
    ui_motion_level: str = "balanced"
    ui_density: str = "comfortable"
    require_critical_confirmation: bool = True
    enable_command_logs: bool = True
    use_face_auth: bool = False
    elevenlabs_api_keys: str = ""
    vision_detail_default: bool = False
    panel_hotkey: str = "win+shift+a"
    study_professor_mode: bool = False


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
        ollama_model=(os.getenv("OLLAMA_MODEL", "qwen3:1.7b") or "").strip() or "qwen3:1.7b",
        ollama_base_url=(os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1") or "").strip() or "http://localhost:11434/v1",
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
        enable_command_logs=_as_bool(os.getenv("ENABLE_COMMAND_LOGS"), default=True),
        stt_language=os.getenv("STT_LANGUAGE", "pt-BR"),
        stt_energy_threshold=_as_int(
            os.getenv("STT_ENERGY_THRESHOLD"), 1100, minimum=150, maximum=8000
        ),
        stt_dynamic_energy=_as_bool(os.getenv("STT_DYNAMIC_ENERGY"), default=True),
        stt_pause_threshold=_as_float(
            os.getenv("STT_PAUSE_THRESHOLD"), 0.8, minimum=0.25, maximum=3.0
        ),
        stt_non_speaking_duration=_as_float(
            os.getenv("STT_NON_SPEAKING_DURATION"), 0.35, minimum=0.1, maximum=2.0
        ),
        stt_calibration_seconds=_as_float(
            os.getenv("STT_CALIBRATION_SECONDS"), 0.8, minimum=0.1, maximum=5.0
        ),
        stt_min_audio_seconds=_as_float(
            os.getenv("STT_MIN_AUDIO_SECONDS"), 0.35, minimum=0.05, maximum=3.0
        ),
        tts_provider=(os.getenv("TTS_PROVIDER", "xtts") or "xtts").strip().lower(),
        tts_provider_order=(
            os.getenv(
                "TTS_PROVIDER_ORDER",
                "edge,kokoro,rvc,piper,openai,elevenlabs,murf,fish,local",
            )
            or ""
        ).strip(),
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
        xtts_model_name=(
            os.getenv("XTTS_MODEL_NAME", "tts_models/multilingual/multi-dataset/xtts_v2")
            or "tts_models/multilingual/multi-dataset/xtts_v2"
        ).strip(),
        xtts_speaker_wav=(os.getenv("XTTS_SPEAKER_WAV", "") or "").strip(),
        xtts_language=(os.getenv("XTTS_LANGUAGE", "pt") or "pt").strip().lower(),
        xtts_device=(os.getenv("XTTS_DEVICE", "auto") or "auto").strip().lower(),
        xtts_rvc_voice=(os.getenv("XTTS_RVC_VOICE", "Jarvis") or "Jarvis").strip(),
        xtts_python=(os.getenv("XTTS_PYTHON", "") or "").strip(),
        xtts_persistent=_as_bool(os.getenv("XTTS_PERSISTENT"), default=True),
        xtts_preload=_as_bool(os.getenv("XTTS_PRELOAD"), default=True),
        styletts2_command=(os.getenv("STYLETTS2_COMMAND", "") or "").strip(),
        styletts2_reference_wav=(os.getenv("STYLETTS2_REFERENCE_WAV", "") or "").strip(),
        styletts2_python=(os.getenv("STYLETTS2_PYTHON", "") or "").strip(),
        styletts2_model_checkpoint=(os.getenv("STYLETTS2_MODEL_CHECKPOINT", "") or "").strip(),
        styletts2_config=(os.getenv("STYLETTS2_CONFIG", "") or "").strip(),
        styletts2_alpha=max(0.0, min(1.0, float(os.getenv("STYLETTS2_ALPHA", "0.3") or "0.3"))),
        styletts2_beta=max(0.0, min(1.0, float(os.getenv("STYLETTS2_BETA", "0.7") or "0.7"))),
        styletts2_diffusion_steps=max(
            1, min(20, int(os.getenv("STYLETTS2_DIFFUSION_STEPS", "3") or "3"))
        ),
        styletts2_embedding_scale=max(
            0.1, min(10.0, float(os.getenv("STYLETTS2_EMBEDDING_SCALE", "1.0") or "1.0"))
        ),
        styletts2_persistent=_as_bool(os.getenv("STYLETTS2_PERSISTENT"), default=True),
        styletts2_preload=_as_bool(os.getenv("STYLETTS2_PRELOAD"), default=False),
        tts_prefetch_chunks=_as_bool(os.getenv("TTS_PREFETCH_CHUNKS"), default=True),
        start_vision_tracker=_as_bool(os.getenv("START_VISION_TRACKER"), default=False),
        start_heartbeat=_as_bool(os.getenv("START_HEARTBEAT"), default=True),
        start_proactive_agent=_as_bool(os.getenv("START_PROACTIVE_AGENT"), default=False),
        enable_clap_trigger=_as_bool(os.getenv("ENABLE_CLAP_TRIGGER"), default=True),
        clap_threshold=_as_float(os.getenv("CLAP_THRESHOLD"), 0.15, minimum=0.03, maximum=1.0),
        clap_min_gap=_as_float(os.getenv("CLAP_MIN_GAP"), 0.1, minimum=0.02, maximum=1.0),
        clap_max_gap=_as_float(os.getenv("CLAP_MAX_GAP"), 1.2, minimum=0.2, maximum=4.0),
        clap_cooldown=_as_float(os.getenv("CLAP_COOLDOWN"), 3.0, minimum=0.5, maximum=20.0),
        piper_repo_id=(os.getenv("PIPER_REPO_ID", "rhasspy/piper-voices") or "").strip() or "rhasspy/piper-voices",
        piper_jarvis_quality=(os.getenv("PIPER_JARVIS_QUALITY", "medium") or "medium").strip().lower(),
        piper_model_file=(os.getenv("PIPER_MODEL_FILE", "") or "").strip(),
        piper_config_file=(os.getenv("PIPER_CONFIG_FILE", "") or "").strip(),
        piper_use_cuda=_as_bool(os.getenv("PIPER_USE_CUDA"), default=False),
        piper_fx_preset=(os.getenv("PIPER_FX_PRESET", "none") or "none").strip().lower(),
        ui_motion_level=_normalize_choice(
            os.getenv("UI_MOTION_LEVEL"),
            {"reduced", "balanced", "expressive"},
            "balanced",
        ),
        ui_density=_normalize_choice(
            os.getenv("UI_DENSITY"),
            {"comfortable", "compact"},
            "comfortable",
        ),
        use_face_auth=_as_bool(os.getenv("USE_FACE_AUTH"), default=False),
        elevenlabs_api_keys=os.getenv("ELEVENLABS_API_KEYS", ""),
        vision_detail_default=_as_bool(os.getenv("VISION_DETAIL_DEFAULT"), default=False),
        panel_hotkey=(os.getenv("PANEL_HOTKEY", "win+shift+a") or "win+shift+a").strip().lower(),
        study_professor_mode=_as_bool(os.getenv("STUDY_PROFESSOR_MODE"), default=False),
    )
