import os
import threading
from src.config import load_settings
from src.services.llm import LLMService
from src.services.vision import VisionService
from src.services.stt import STTService
from src.services.tts import TTSService
from src.memory.store import MemoryStore
from src.tools.registry import ToolRegistry
from src.tools.critical_confirm import CriticalConfirmationBus, load_critical_confirm_enabled
from src.agent.orchestrator import AgentOrchestrator
from src.runtime_status import RuntimeStatus
from src.tools.skill_manager import load_dynamic_skills

def boot_system():
    """Inicializa todos os serviços core do Jarvis."""
    settings = load_settings()
    runtime_status = RuntimeStatus()
    runtime_status.mark_startup_phase("settings_loaded", settings.llm_provider)

    # 1. Core Services
    llm = LLMService(
        primary_llm_provider=settings.llm_provider,
        gemini_api_key=settings.gemini_api_key,
        gemini_model=settings.gemini_model,
        openrouter_api_key=settings.openrouter_api_key,
        openrouter_model=settings.openrouter_model,
        nvidia_api_key=settings.nvidia_api_key,
        nvidia_model=settings.nvidia_model,
        groq_api_key=settings.groq_api_key,
        groq_model=settings.groq_model,
        ollama_model=settings.ollama_model,
        ollama_base_url=settings.ollama_base_url,
        gemini_max_rpm=settings.gemini_max_rpm,
        gemini_retry_attempts=settings.gemini_retry_attempts,
        runtime_status=runtime_status,
    )

    vision = VisionService(
        vision_provider=settings.vision_provider,
        gemini_api_key=settings.gemini_api_key,
        gemini_model=settings.gemini_model,
        nvidia_api_key=settings.nvidia_api_key,
        nvidia_model=settings.nvidia_vision_model,
        groq_api_key=settings.groq_api_key,
        groq_vision_model=settings.groq_vision_model,
        max_rpm=settings.gemini_max_rpm,
        retry_attempts=settings.gemini_retry_attempts,
    )

    memory = MemoryStore()

    # 2. Audio Services
    stt = STTService(
        use_mic=settings.use_mic,
        language=settings.stt_language,
        groq_api_key=settings.groq_api_key,
        energy_threshold=settings.stt_energy_threshold,
        dynamic_energy_threshold=settings.stt_dynamic_energy,
        pause_threshold=settings.stt_pause_threshold,
        non_speaking_duration=settings.stt_non_speaking_duration,
        min_audio_seconds=settings.stt_min_audio_seconds,
    )
    stt_backend = "groq" if stt.groq_client else "google"
    runtime_status.set_stt_info(stt_backend, stt.calibrated)
    runtime_status.mark_startup_phase("stt_ready", stt_backend)

    tts = TTSService(
        api_key=settings.openai_api_key,
        model=settings.tts_model,
        voice=settings.tts_voice,
        provider=settings.tts_provider,
        provider_order=settings.tts_provider_order,
        murf_api_key=settings.murf_api_key,
        murf_voice_id=settings.murf_voice_id,
        murf_api_url=settings.murf_api_url,
        allow_system_player_on_failure=settings.tts_allow_system_player,
        max_chunk_chars=settings.tts_max_chunk_chars,
        pause_between_chunks_sec=settings.tts_pause_between_chunks_sec,
        edge_tts_rate=settings.edge_tts_rate,
        edge_tts_volume=settings.edge_tts_volume,
        tts_prefetch_chunks=settings.tts_prefetch_chunks,
        elevenlabs_api_keys=settings.elevenlabs_api_keys,
        fish_audio_api_key=settings.fish_audio_api_key,
    )
    runtime_status.mark_startup_phase("tts_ready", settings.tts_provider)

    # 3. Confirmation Bus
    confirm_bus = CriticalConfirmationBus()
    confirm_bus.enabled = load_critical_confirm_enabled(settings.require_critical_confirmation)

    # 4. Tools Registry
    tools = ToolRegistry(
        tools=[],
        require_critical_confirmation=settings.require_critical_confirmation,
        confirm_bus=confirm_bus
    )
    # Import e registro manual das tools fixas (as skills dinâmicas são carregadas via skill_manager)
    try:
        from src.tools.clipboard import ClipboardTool
        from src.tools.desktop import DesktopAutomationTool
        from src.tools.system_info import SystemInfoTool
        from src.tools.web_search import WebSearchTool
        from src.tools.timer import TimerTool
        from src.tools.code_helper import CodeHelperTool
        from src.tools.file_manager import FileManagerTool
        
        # Tools básicas (podemos expandir isso depois para um loader de tools fixas se necessário)
        tools.tools.append(ClipboardTool())
        tools.tools.append(DesktopAutomationTool())
        tools.tools.append(SystemInfoTool())
        tools.tools.append(WebSearchTool())
        tools.tools.append(TimerTool())
        tools.tools.append(CodeHelperTool())
        tools.tools.append(FileManagerTool())
    except Exception as e:
        print(f"[Boot] Erro ao carregar tools base: {e}")

    # Carrega as dinâmicas
    try:
        dyn_tools = load_dynamic_skills()
        for dt in dyn_tools:
            tools.tools.append(dt)
    except Exception as e:
        print(f"[Boot] Erro ao carregar skills dinâmicas: {e}")

    # 5. Agent Orchestrator
    agent = AgentOrchestrator(
        llm=llm,
        vision=vision,
        tools=tools,
        memory=memory,
        use_function_calling=settings.gemini_use_function_calling,
        assistant_base_persona=settings.assistant_base_persona,
        confirm_bus=confirm_bus
    )

    return {
        "settings": settings,
        "runtime_status": runtime_status,
        "llm": llm,
        "vision": vision,
        "stt": stt,
        "tts": tts,
        "memory": memory,
        "tools": tools,
        "confirm_bus": confirm_bus,
        "agent": agent
    }
