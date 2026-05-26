import sys
import os
import logging
import threading
import time
import json
from pathlib import Path
import queue
import atexit
import signal

# ══════════════════════════════════════════════════════════════════════════════
# GUARDA ANTI-ZUMBI: Mata instâncias anteriores do Jarvis antes de qualquer
# import pesado. Resolve o problema de 100+ processos acumulados.
# ══════════════════════════════════════════════════════════════════════════════

_PID_FILE = Path(__file__).resolve().parent.parent / "data" / "jarvis.pid"


def _kill_previous_instances():
    """Mata qualquer processo Python anterior que esteja rodando main.py."""
    my_pid = os.getpid()
    my_ancestors = set()
    try:
        import psutil
        curr = psutil.Process(my_pid).parent()
        while curr:
            my_ancestors.add(curr.pid)
            curr = curr.parent()
    except Exception:
        pass

    # 1. Tenta ler o PID do lockfile anterior
    if _PID_FILE.exists():
        try:
            old_pid = int(_PID_FILE.read_text().strip())
            if old_pid != my_pid and old_pid not in my_ancestors:
                try:
                    import psutil
                    proc = psutil.Process(old_pid)
                    if "python" in proc.name().lower():
                        print(f"[Guarda] Encerrando instância anterior (PID {old_pid})...")
                        # Mata toda a árvore de processos filhos
                        children = proc.children(recursive=True)
                        for child in children:
                            if child.pid == my_pid or child.pid in my_ancestors:
                                continue
                            try:
                                child.kill()
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
                        proc.kill()
                        proc.wait(timeout=5)
                        print(f"[Guarda] PID {old_pid} encerrado com sucesso.")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass  # Já morreu
                except ImportError:
                    # Fallback sem psutil: tenta taskkill no Windows
                    try:
                        os.system(f'taskkill /PID {old_pid} /F /T >nul 2>&1')
                    except Exception:
                        pass
                except Exception as e:
                    print(f"[Guarda] Erro ao matar PID {old_pid}: {e}")
        except (ValueError, OSError):
            pass

    # 2. Varredura geral: mata qualquer python.exe rodando main.py (exceto eu e meus pais)
    try:
        import psutil
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if proc.info["pid"] == my_pid or proc.info["pid"] in my_ancestors:
                    continue
                if "python" not in (proc.info["name"] or "").lower():
                    continue
                cmdline = proc.info.get("cmdline") or []
                cmd_str = " ".join(cmdline).lower()
                if "src\\main.py" in cmd_str or "src/main.py" in cmd_str:
                    print(f"[Guarda] Matando processo zumbi: PID {proc.info['pid']}")
                    children = proc.children(recursive=True)
                    for child in children:
                        if child.pid == my_pid or child.pid in my_ancestors:
                            continue
                        try:
                            child.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except ImportError:
        pass  # Sem psutil, a limpeza por PID file já cobre o caso principal

    # 3. Grava o PID atual no lockfile
    try:
        _PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        _PID_FILE.write_text(str(my_pid))
    except OSError:
        pass


def _cleanup_on_exit():
    """Remove o PID file ao sair normalmente."""
    try:
        if _PID_FILE.exists() and _PID_FILE.read_text().strip() == str(os.getpid()):
            _PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass


# Executa a guarda IMEDIATAMENTE, antes de qualquer import pesado
_kill_previous_instances()
atexit.register(_cleanup_on_exit)

# Captura SIGTERM/SIGINT para garantir limpeza
def _signal_handler(signum, frame):
    _cleanup_on_exit()
    os._exit(0)

signal.signal(signal.SIGTERM, _signal_handler)
try:
    signal.signal(signal.SIGINT, _signal_handler)
except (OSError, ValueError):
    pass  # Pode falhar em threads secundárias

# Agora importa o keyboard (que tem side effects)
import keyboard

# Global Queue for tasks
task_queue = queue.Queue()

# Adiciona a pasta raiz ao sys.path para permitir imports do tipo 'from src...'
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))
from src.agent.orchestrator import AgentOrchestrator
from src.config import load_settings
from src.integrations.super_productivity import SuperProductivityConnector
from src.memory.store import MemoryStore
from src.services.llm import LLMService
from src.services.stt import STTService
from src.services.tts import TTSService
from src.services.vision import VisionService
from src.tools.clipboard import ClipboardTool
from src.tools.desktop import DesktopAutomationTool
from src.tools.finance import FinanceTool
from src.tools.media_control import MediaControlTool
from src.tools.memory_manager import MemoryManagerTool

from src.tools.productivity import ProductivityTool
from src.tools.registry import ToolRegistry
from src.tools.critical_confirm import (
    CriticalConfirmationBus,
    load_critical_confirm_enabled,
    try_voice_resolve_confirmation,
)
from src.tools.system_info import SystemInfoTool
from src.tools.timer import TimerTool
from src.tools.web_search import WebSearchTool
from src.tools.whatsapp import WhatsAppTool
from src.tools.visualizer_control import VisualizerControlTool
from src.tools.spotify import SpotifyTool
from src.tools.file_manager import FileManagerTool
from src.tools.app_manager import AppManagerTool
from src.tools.image_generator import GenerateImageTool, ShowImageTool, ListImagesTool
from src.tools.hacker_mode import HackerModeTool
from src.tools.nexus import NexusTool
from src.tools.habit_tracker import HabitTrackerTool
from src.tools.code_helper import CodeHelperTool
from src.tools.browser_agent import BrowserAgentTool
from src.tools.persona_manager import PersonaManagerTool
from src.tools.dev_agent import DevAgentTool
from src.tools.cmd_control import CmdControlTool
from src.tools.settings_manager import SettingsManagerTool
from src.tools.file_processor import FileProcessorTool
from src.tools.system_control import SystemControlTool
from src.tools.toggle_live import ToggleLiveTool
from src.tools.news import NewsTool
from src.skills.system_exit import SystemExitTool
from src.skills.change_voice import ChangeVoiceSkill
from src.tools.skill_manager import load_dynamic_skills
from src.runtime_status import RuntimeStatus

# Globais para acesso dos tools (ex: settings_manager)
vision_tracker = None


def _viz_set(func_name: str, *args, **kwargs):
    try:
        from src.services import visualizer
        getattr(visualizer, func_name)(*args, **kwargs)
    except Exception:
        pass


def main() -> None:
    global vision_tracker
    logging.basicConfig(level=logging.WARNING)
    settings = load_settings()
    runtime_status = RuntimeStatus()
    runtime_status.mark_startup_phase("settings_loaded", settings.llm_provider)

    if settings.enable_visualizer:
        from src.services import visualizer
        visualizer.start()
        runtime_status.mark_startup_phase("visualizer_started")

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
        elevenlabs_api_keys=settings.elevenlabs_api_keys,
        piper_repo_id=settings.piper_repo_id,
        piper_jarvis_quality=settings.piper_jarvis_quality,
        piper_model_file=settings.piper_model_file,
        piper_config_file=settings.piper_config_file,
        piper_use_cuda=settings.piper_use_cuda,
        piper_fx_preset=settings.piper_fx_preset,
        kokoro_voice="pf_dora",
        xtts_model_name=settings.xtts_model_name,
        xtts_speaker_wav=settings.xtts_speaker_wav,
        xtts_language=settings.xtts_language,
        xtts_device=settings.xtts_device,
        xtts_rvc_voice=settings.xtts_rvc_voice,
        xtts_python=settings.xtts_python,
        xtts_persistent=settings.xtts_persistent,
        styletts2_command=settings.styletts2_command,
        styletts2_reference_wav=settings.styletts2_reference_wav,
        styletts2_python=settings.styletts2_python,
        styletts2_model_checkpoint=settings.styletts2_model_checkpoint,
        styletts2_config=settings.styletts2_config,
        styletts2_alpha=settings.styletts2_alpha,
        styletts2_beta=settings.styletts2_beta,
        styletts2_diffusion_steps=settings.styletts2_diffusion_steps,
        styletts2_embedding_scale=settings.styletts2_embedding_scale,
        styletts2_persistent=settings.styletts2_persistent,
        styletts2_preload=settings.styletts2_preload,
        tts_prefetch_chunks=settings.tts_prefetch_chunks,
        fish_audio_api_key=__import__("os").environ.get("FISH_AUDIO_API_KEY", ""),
    )
    runtime_status.mark_startup_phase("tts_ready", settings.tts_provider)
    if settings.xtts_preload:
        tts.warmup_xtts_async()
        runtime_status.mark_startup_phase("xtts_preload_scheduled")
    if settings.styletts2_preload:
        tts.warmup_styletts2_async()
        runtime_status.mark_startup_phase("styletts2_preload_scheduled")
    llm = LLMService(
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
        primary_llm_provider=settings.llm_provider,
        fallback_gemini=settings.llm_fallback_gemini,
        runtime_status=runtime_status,
    )
    runtime_status.mark_startup_phase("llm_ready", settings.llm_provider)
    # Set global reference for tools that need LLM access
    import src.services.llm as _llm_module
    _llm_module._global_llm_instance = llm

    vision = VisionService(
        vision_provider=settings.vision_provider,
        gemini_api_key=settings.gemini_api_key,
        gemini_model=settings.gemini_model,
        nvidia_api_key=settings.nvidia_api_key,
        nvidia_model=settings.nvidia_vision_model or settings.nvidia_model,
        groq_api_key=settings.groq_api_key,
        groq_vision_model=settings.groq_vision_model,
    )
    memory = MemoryStore()
    runtime_status.mark_startup_phase("vision_memory_ready", settings.vision_provider)

    confirm_bus = CriticalConfirmationBus()
    confirm_bus.enabled = load_critical_confirm_enabled(
        settings.require_critical_confirmation
    )
    tools = ToolRegistry(
        tools=[
            DesktopAutomationTool(),
            ProductivityTool(SuperProductivityConnector()),
            FinanceTool(),
            WebSearchTool(),
            ClipboardTool(),
            TimerTool(),
            SystemInfoTool(),

            SpotifyTool(),
            AppManagerTool(),
            FileManagerTool(),
            MediaControlTool(),
            MemoryManagerTool(),
            WhatsAppTool(),
            VisualizerControlTool(),
            GenerateImageTool(),
            ShowImageTool(),
            ListImagesTool(),
            HackerModeTool(),
            NexusTool(),
            HabitTrackerTool(),
            CodeHelperTool(),
            BrowserAgentTool(),
            PersonaManagerTool(),
            DevAgentTool(),
            CmdControlTool(),
            SettingsManagerTool(),
            FileProcessorTool(),
            SystemControlTool(),
            ToggleLiveTool(),
            NewsTool(),
            ChangeVoiceSkill(tts_instance=tts),
            SystemExitTool()
        ] + load_dynamic_skills(),
        require_critical_confirmation=settings.require_critical_confirmation,
        confirm_bus=confirm_bus,
    )
    runtime_status.mark_startup_phase("tools_ready", str(len(tools.tools)))
    agent = AgentOrchestrator(
        llm=llm, vision=vision, tools=tools, memory=memory,
        use_function_calling=settings.gemini_use_function_calling,
        assistant_base_persona=settings.assistant_base_persona,
        confirm_bus=confirm_bus,
    )
    runtime_status.mark_startup_phase("agent_ready")

    # Inicia rastreador de gestos/visao apenas quando configurado.
    if settings.start_vision_tracker or settings.use_face_auth:
        from src.services.vision_tracker import VisionTracker

        vision_tracker = VisionTracker(
            task_queue=task_queue,
            tts_instance=tts,
            use_face_auth=settings.use_face_auth,
        )
        vision_tracker.start()
        runtime_status.mark_startup_phase("vision_tracker_started")

    # Inicia Heartbeat Service (consolidação periódica de memória)
    heartbeat = None
    if settings.start_heartbeat:
        from src.services.heartbeat import HeartbeatService

        heartbeat = HeartbeatService(interval_minutes=30, llm_service=llm)
        heartbeat.start()
        runtime_status.mark_startup_phase("heartbeat_started")

    # Inicia agente proativo somente quando o usuario escolher no painel.
    proactive = None
    if settings.start_proactive_agent:
        from src.services.proactive_agent import ProactiveAgent
        proactive = ProactiveAgent(agent_orchestrator=agent, tts_instance=tts, min_interval_minutes=15, max_interval_minutes=45)
        proactive.start()
        runtime_status.mark_startup_phase("proactive_agent_started")

    if settings.use_mic:
        stt.calibrate(duration=settings.stt_calibration_seconds)
        runtime_status.set_stt_info(stt_backend, stt.calibrated)
        runtime_status.mark_startup_phase("stt_calibrated", str(stt.recognizer.energy_threshold))

    # Estado global para lidar com interrupções
    agent_lock = threading.Lock()
    is_processing = False

    # Chat history para o painel
    chat_log = []
    _chat_log_lock = threading.Lock()

    def _add_chat(role: str, name: str, text: str):
        """Adiciona uma entrada ao log de chat."""
        import datetime
        with _chat_log_lock:
            chat_log.append({
                "role": role,          # "user" | "assistant" | "system"
                "name": name,
                "text": text,
                "time": datetime.datetime.now().strftime("%H:%M:%S")
            })
            # Mantém apenas as últimas 200 mensagens
            if len(chat_log) > 200:
                del chat_log[:len(chat_log) - 200]

    # Captura de logs do sistema
    system_logs = []
    _log_lock = threading.Lock()

    class _LogCapture:
        """Intercepta print() para capturar logs do sistema."""
        def __init__(self, original):
            self._original = original
        def write(self, text):
            self._original.write(text)
            if text.strip():
                with _log_lock:
                    import datetime
                    system_logs.append({
                        "text": text.strip(),
                        "time": datetime.datetime.now().strftime("%H:%M:%S")
                    })
                    if len(system_logs) > 500:
                        del system_logs[:len(system_logs) - 500]
        def flush(self):
            self._original.flush()

    sys.stdout = _LogCapture(sys.stdout)

    def _detect_agent_by_name(text: str):
        """Fase 3.2.3 — Detecta se o texto começa com o nome de um agente.
        Retorna (agent_id, texto_limpo) ou (None, texto_original)."""
        text_lower = text.strip().lower()
        best_match = None
        best_len = 0
        for ag in agent.agent_manager.list_agents():
            name_lower = ag.name.strip().lower()
            # Checa se começa com o nome do agente (com separador: vírgula, espaço, etc.)
            for prefix in [name_lower + ",", name_lower + " ", name_lower + "!"]:
                if text_lower.startswith(prefix) and len(name_lower) > best_len:
                    best_match = ag.id
                    best_len = len(name_lower)
        if best_match:
            # Remove o nome do agente do início do texto
            cleaned = text.strip()[best_len:].lstrip(" ,!.:").strip()
            return best_match, cleaned if cleaned else text.strip()
        return None, text

    def _process_and_respond(text: str, source: str = ""):
        nonlocal is_processing
        if not text: return
        tag = f" ({source})" if source else ""

        # Fase 3.2.3 — Chamada por Nome: detecta agente no início da frase
        called_agent_id, cleaned_text = _detect_agent_by_name(text)
        original_agent_id = agent.agent_manager._active_agent_id
        if called_agent_id and called_agent_id != original_agent_id:
            agent.agent_manager.set_active_agent(called_agent_id)
            called_name = agent.agent_manager.get_active_agent().name
            print(f"\n[Chamada por Nome] Direcionando para '{called_name}'")
            text = cleaned_text  # Usa texto sem o nome do agente

        # Bloqueia para não rodar duas chamadas da LLM ao mesmo tempo
        with agent_lock:
            is_processing = True
            runtime_status.set_processing(True)
            try:
                _viz_set("set_thinking")
                _add_chat("user", "Você", text)
                response_gen = agent.handle_user_message(text)

                active_ag = agent.agent_manager.get_active_agent()

                import types
                if isinstance(response_gen, types.GeneratorType):
                    # Modo Streaming (Latência Zero)
                    _viz_set("set_speaking")
                    llm_used = getattr(agent.llm, "last_model", "")
                    llm_tag = f" [{llm_used}]" if llm_used else ""

                    tts.apply_agent_voice(
                        provider=active_ag.tts_provider, voice=active_ag.tts_voice,
                        speed=active_ag.tts_speed, edge_rate=active_ag.edge_tts_rate,
                        edge_vol=active_ag.edge_tts_volume, kokoro_voice=active_ag.kokoro_voice
                    )

                    full_response = ""
                    tts_buffer = ""

                    import threading
                    import queue

                    tts_queue = queue.Queue()

                    def tts_worker():
                        while True:
                            text_chunk = tts_queue.get()
                            if text_chunk is None:
                                break
                            if text_chunk.strip():
                                tts.speak(text_chunk)
                            tts_queue.task_done()

                    tts_thread = threading.Thread(target=tts_worker, daemon=True)
                    tts_thread.start()

                    for chunk in response_gen:
                        if tts._interrupt_event.is_set():
                            break
                        if chunk:
                            print(chunk, end="", flush=True)
                            full_response += chunk
                            tts_buffer += chunk

                            # Se encontrar pontuação final, despacha para TTS
                            import re
                            if re.search(r'[.!?\n]\s*$', tts_buffer):
                                # Despacha o buffer para a fila de TTS
                                to_speak = tts_buffer.strip()
                                if to_speak:
                                    tts_queue.put(to_speak)
                                tts_buffer = ""

                    print()

                    # Despacha o que sobrou
                    if tts_buffer.strip():
                        tts_queue.put(tts_buffer.strip())

                    # Finaliza a thread do TTS
                    tts_queue.put(None)
                    # Não bloqueamos esperando tts terminar,
                    # porque ele pode continuar falando enquanto a UI volta a ficar "idle".
                    # Mas se preferir esperar:
                    # tts_thread.join()

                    _add_chat("assistant", active_ag.name, full_response)
                    _viz_set("set_idle")

                else:
                    # Modo Legado (String Inteira)
                    response = response_gen
                    _add_chat("assistant", active_ag.name, response)

                    # Se o usuário interrompeu enquanto ela pensava, não fala.
                    if not tts._interrupt_event.is_set():
                        import re
                        # Aplica a voz do agente ativo por padrao
                        tts.apply_agent_voice(
                            provider=active_ag.tts_provider, voice=active_ag.tts_voice,
                            speed=active_ag.tts_speed, edge_rate=active_ag.edge_tts_rate,
                            edge_vol=active_ag.edge_tts_volume, kokoro_voice=active_ag.kokoro_voice
                        )

                        segments = re.split(r'(<VOICE_SWAP:.*?>.*?</VOICE_SWAP>)', response, flags=re.DOTALL)
                        _viz_set("set_speaking")
                        llm_used = getattr(agent.llm, "last_model", "")
                        llm_tag = f" [{llm_used}]" if llm_used else ""

                        for segment in segments:
                            if not segment.strip(): continue
                            if tts._interrupt_event.is_set(): break

                            match = re.match(r'<VOICE_SWAP:(.*?)>(.*?)</VOICE_SWAP>', segment, flags=re.DOTALL)
                            if match:
                                target_id = match.group(1).strip()
                                text_to_speak = match.group(2).strip()

                                target_agent = agent.agent_manager._agents.get(target_id)
                                if target_agent:
                                    print(f"\n>>> [{target_agent.name} assumiu a fala]")
                                    tts.apply_agent_voice(
                                        provider=target_agent.tts_provider, voice=target_agent.tts_voice,
                                        speed=target_agent.tts_speed, edge_rate=target_agent.edge_tts_rate,
                                        edge_vol=target_agent.edge_tts_volume, kokoro_voice=target_agent.kokoro_voice
                                    )
                                    print(f"{target_agent.name}{tag}{llm_tag}: {text_to_speak}", flush=True)
                                    tts.speak(text_to_speak)

                                    # Restaura a voz original para os proximos pedacos
                                    tts.apply_agent_voice(
                                        provider=active_ag.tts_provider, voice=active_ag.tts_voice,
                                        speed=active_ag.tts_speed, edge_rate=active_ag.edge_tts_rate,
                                        edge_vol=active_ag.edge_tts_volume, kokoro_voice=active_ag.kokoro_voice
                                    )
                                else:
                                    print(f"{active_ag.name}{tag}{llm_tag}: {text_to_speak}", flush=True)
                                    tts.speak(text_to_speak)
                            else:
                                print(f"{active_ag.name}{tag}{llm_tag}: {segment.strip()}", flush=True)
                                tts.speak(segment.strip())

                        _viz_set("set_idle")
                    else:
                        print(f"[{active_ag.name}{tag} Interrompido antes de falar]")
                        tts._interrupt_event.clear()

            except Exception as e:
                print(f"\n[Erro{tag}] {e}")
                _viz_set("set_error", str(e))
                time.sleep(2)
            finally:
                is_processing = False
                runtime_status.set_processing(False)
                # Fase 3.2.3 — Restaura o agente original após chamada por nome
                if called_agent_id and called_agent_id != original_agent_id:
                    agent.agent_manager.set_active_agent(original_agent_id)
                if mic_currently_enabled:
                    _viz_set("set_listening")
                else:
                    _viz_set("set_idle")

    stop_listening_bg = None
    mic_currently_enabled = settings.use_mic
    runtime_status.set_mic_listening(mic_currently_enabled)

    # Trabalhador que consome a fila de interações (texto ou voz)
    def interaction_worker():
        nonlocal mic_currently_enabled
        while True:
            item = task_queue.get()
            if item is None: break
            text, source = item
            runtime_status.set_enqueue_preview(text)

            if text == "/toggle_mic":
                mic_currently_enabled = not mic_currently_enabled
                runtime_status.set_mic_listening(mic_currently_enabled)
                if mic_currently_enabled:
                    _start_mic()
                else:
                    _stop_mic()
                try:
                    state_file = Path("data/visualizer_state.json")
                    state_file.parent.mkdir(parents=True, exist_ok=True)
                    prev = {}
                    if state_file.exists():
                        prev = json.loads(state_file.read_text(encoding="utf-8") or "{}")
                    prev["mic_enabled"] = mic_currently_enabled
                    state_file.write_text(json.dumps(prev, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception:
                    pass
                task_queue.task_done()
                continue

            if text == "/tts_test":
                try:
                    tts.speak("Teste de voz.")
                    runtime_status.set_diagnostics("tts", {"ok": True, "message": "Frase curta reproduzida."})
                except Exception as e:
                    runtime_status.set_diagnostics("tts", {"ok": False, "message": str(e)[:300]})
                task_queue.task_done()
                continue

            if text == "/diagnostics_llm":
                try:
                    ping = llm.chat(
                        "Responda apenas: pong",
                        [{"role": "user", "content": "ping"}],
                        skip_gemini=False,
                    )
                    ok = bool((ping or "").strip())
                    runtime_status.set_diagnostics(
                        "llm",
                        {"ok": ok, "message": (ping or "")[:200], "provider": llm.last_provider, "model": llm.last_model},
                    )
                except Exception as e:
                    runtime_status.set_diagnostics("llm", {"ok": False, "message": str(e)[:300]})
                task_queue.task_done()
                continue

            # Fase 3.2 — Modos Multi-Agentes Especiais
            if text.startswith("/roundrobin|"):
                try:
                    _, chained_str, ids_str, query = text.split("|", 3)
                    chained = (chained_str.lower() == "true")
                    agent_ids = [aid.strip() for aid in ids_str.split(",") if aid.strip()]

                    with agent_lock:
                        is_processing = True
                        runtime_status.set_processing(True)
                        _viz_set("set_thinking")
                        results = agent.handle_round_robin(query, agent_ids, chained)
                        _viz_set("set_speaking")
                        for r in results:
                            if tts._interrupt_event.is_set():
                                print("\n[Round-Robin Interrompido pelo Usuário]")
                                tts._interrupt_event.clear()
                                break
                            ag_id = r["agent_id"]
                            ag_name = r["name"]
                            resp = r["response"]
                            target_agent = agent.agent_manager._agents.get(ag_id)
                            if target_agent:
                                tts.apply_agent_voice(
                                    provider=target_agent.tts_provider, voice=target_agent.tts_voice,
                                    speed=target_agent.tts_speed, edge_rate=target_agent.edge_tts_rate,
                                    edge_vol=target_agent.edge_tts_volume, kokoro_voice=target_agent.kokoro_voice
                                )
                                print(f"\n[{ag_name}] (Round-Robin): {resp}", flush=True)
                                tts.speak(resp)
                        is_processing = False
                        runtime_status.set_processing(False)
                        _viz_set("set_idle")
                except Exception as e:
                    print(f"[Erro Round-Robin] {e}")
                finally:
                    # Garantir que eventuais interrupções tardias sejam limpas
                    tts._interrupt_event.clear()
                    task_queue.task_done()
                continue

            if text.startswith("/debate|"):
                try:
                    _, rounds_str, ids_str, topic = text.split("|", 3)
                    rounds = int(rounds_str)
                    agent_ids = [aid.strip() for aid in ids_str.split(",") if aid.strip()]

                    with agent_lock:
                        is_processing = True
                        runtime_status.set_processing(True)
                        _viz_set("set_thinking")
                        results = agent.handle_debate(topic, agent_ids, rounds)
                        _viz_set("set_speaking")
                        for r in results:
                            if tts._interrupt_event.is_set():
                                print("\n[Debate Interrompido pelo Usuário]")
                                tts._interrupt_event.clear()
                                break
                            ag_id = r["agent_id"]
                            ag_name = r["name"]
                            rd = r["round"]
                            resp = r["response"]
                            target_agent = agent.agent_manager._agents.get(ag_id)
                            if target_agent:
                                tts.apply_agent_voice(
                                    provider=target_agent.tts_provider, voice=target_agent.tts_voice,
                                    speed=target_agent.tts_speed, edge_rate=target_agent.edge_tts_rate,
                                    edge_vol=target_agent.edge_tts_volume, kokoro_voice=target_agent.kokoro_voice
                                )
                                print(f"\n[{ag_name}] (Debate Rodada {rd}): {resp}", flush=True)
                                tts.speak(resp)
                        is_processing = False
                        runtime_status.set_processing(False)
                        _viz_set("set_idle")
                except Exception as e:
                    print(f"[Erro Debate] {e}")
                finally:
                    tts._interrupt_event.clear()
                    task_queue.task_done()
                continue

            if text.startswith("/import_memory|"):
                try:
                    _, collection_name, path = text.split("|", 2)
                    import json
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    if data:
                        with agent_lock:
                            is_processing = True
                            runtime_status.set_processing(True)
                            _viz_set("set_thinking")
                            print(f"\n[Importando {len(data)} memórias para '{collection_name}']")
                            count = 0
                            for item in data:
                                m_text = item.get("text")
                                if m_text:
                                    emb = agent.llm.generate_embedding(m_text)
                                    if emb:
                                        agent.semantic_memory.save_memory(m_text, emb, collection_name=collection_name)
                                        count += 1
                            print(f"Importação concluída: {count} memórias salvas.")
                            _viz_set("set_idle")
                            is_processing = False
                            runtime_status.set_processing(False)
                except Exception as e:
                    print(f"[Erro Importação] {e}")
                    is_processing = False
                    runtime_status.set_processing(False)
                    _viz_set("set_idle")
                continue

            if text == "/reload_skills":
                try:
                    from src.tools.skill_manager import load_dynamic_skills
                    # Filtra apenas as ferramentas que NÃO são dinâmicas (BaseTool original)
                    # Hack simples: as fixas que adicionei em main.py. Como posso separá-las?
                    # Ou apenas recria a lista fixa?
                    # Mais fácil: vamos apenas usar o module pra saber.
                    fixas = [t for t in agent.tools.tools if not t.__class__.__module__.startswith("src.skills.")]
                    agent.tools.tools = fixas + load_dynamic_skills()
                    print("\n[Sistema] Habilidades dinâmicas recarregadas com sucesso!")
                except Exception as e:
                    print(f"[Erro Reload Skills] {e}")
                finally:
                    task_queue.task_done()
                continue

            _process_and_respond(text, source)
            task_queue.task_done()

    threading.Thread(target=interaction_worker, daemon=True).start()

    # Callback para quando a voz for detectada em background
    def on_voice_recognized(text: str):
        nonlocal is_processing
        if not text.strip(): return

        if try_voice_resolve_confirmation(confirm_bus, text):
            print("\n[Confirmação] Resposta por voz aceita.", flush=True)
            return

        print(f"\nVoce (Voz): {text}")
        if is_processing:
            print("[Interrupção!] Parando a IA para ouvir a nova instrução...")
            tts.stop() # Para a fala atual imediatamente

            # Limpa a fila de tarefas pendentes para focar apenas na nova
            while not task_queue.empty():
                try:
                    task_queue.get_nowait()
                    task_queue.task_done()
                except queue.Empty:
                    break

        task_queue.put((text, "Voz"))

    def _start_mic():
        nonlocal stop_listening_bg
        if stop_listening_bg is None:
            print("\n[Voz] Microfone ativado. Fale a qualquer momento.")
            # Callbacks para o visualizador reagir ao som em tempo real
            stop_listening_bg = stt.start_continuous_listening(
                on_voice_recognized,
                on_speech_start=lambda: _viz_set("set_listening"),
                on_speech_end=lambda: _viz_set("set_idle") if not is_processing else None
            )
            # Começa em IDLE, não em LISTENING
            if not is_processing:
                _viz_set("set_idle")

    def _stop_mic():
        nonlocal stop_listening_bg
        if stop_listening_bg is not None:
            print("\n[Voz] Microfone desativado.")
            stop_listening_bg(wait_for_stop=False)
            stop_listening_bg = None
            if not is_processing:
                _viz_set("set_idle")

    if mic_currently_enabled:
        _start_mic()

    # --- Double-Clap Trigger ---
    def _on_clap():
        nonlocal mic_currently_enabled
        import winsound

        print("\n[ClapDetector] Duas palmas detectadas!", flush=True)
        mic_currently_enabled = not mic_currently_enabled
        runtime_status.set_mic_listening(mic_currently_enabled)
        if mic_currently_enabled:
            try: winsound.Beep(2000, 150)
            except: pass
            print("[Sistema] Assistente ACORDADA pelas palmas.")
            _start_mic()
        else:
            try: winsound.Beep(1000, 150)
            except: pass
            print("[Sistema] Assistente DORMIR pelas palmas.")
            _stop_mic()

    clap_detector = None
    if settings.enable_clap_trigger:
        try:
            from src.services.clap_detector import ClapDetector
            clap_detector = ClapDetector(
                on_clap_callback=_on_clap,
                threshold=settings.clap_threshold,
                min_gap=settings.clap_min_gap,
                max_gap=settings.clap_max_gap,
                cooldown=settings.clap_cooldown,
            )
            clap_detector.start()
            print("[ClapDetector] Sistema de palmas iniciado em background.")
            runtime_status.mark_startup_phase("clap_detector_started")
        except Exception as e:
            print(f"[ClapDetector] Erro ao iniciar: {e}")

    # Trabalhador para monitorar o WebChat e o estado do Visualizador
    def state_monitor_worker():
        nonlocal mic_currently_enabled
        chat_file = Path("data/browser_chat.txt")
        state_file = Path("data/visualizer_state.json")
        while True:
            # Lendo mensagens da Web
            if chat_file.exists():
                try:
                    with open(chat_file, "r+", encoding="utf-8") as f:
                        lines = f.readlines()
                        f.truncate(0)
                    for line in lines:
                        t = line.strip()
                        if t:
                            if is_processing:
                                tts.stop()
                                # Limpa fila
                                while not task_queue.empty():
                                    try: task_queue.get_nowait(); task_queue.task_done()
                                    except queue.Empty: break
                            task_queue.put((t, "Web"))
                except Exception:
                    pass

            # Monitorando controle do microfone
            if state_file.exists():
                try:
                    with open(state_file, "r", encoding="utf-8") as f:
                        state = json.load(f)
                        wanted_mic = state.get("mic_enabled", True)
                        if wanted_mic != mic_currently_enabled:
                            mic_currently_enabled = wanted_mic
                            runtime_status.set_mic_listening(mic_currently_enabled)
                            if wanted_mic: _start_mic()
                            else: _stop_mic()
                except Exception:
                    pass

            time.sleep(1)

    threading.Thread(target=state_monitor_worker, daemon=True).start()

    def terminal_worker():
        print("Pronta. Digite para conversar ou apenas fale se o microfone estiver ativo.")
        while True:
            try:
                user_text = input("Voce: ").strip()
                if not user_text:
                    continue

                # Filtra colagens acidentais de logs ou comandos do terminal
                if user_text.startswith("& ") or user_text.startswith("[UI]") or user_text.startswith("[TTS]") or user_text.startswith("[🛠️"):
                    continue

                if user_text.lower() in {"sair", "exit"}:
                    # Para fechar graciosamente, precisa fechar a UI se existir
                    import os
                    os._exit(0)
                if user_text:
                    if is_processing:
                        tts.stop() # Permite interromper digitando também
                        # Limpa fila
                        while not task_queue.empty():
                            try: task_queue.get_nowait(); task_queue.task_done()
                            except queue.Empty: break
                    task_queue.put((user_text, "Texto"))
            except (KeyboardInterrupt, EOFError):
                import os
                os._exit(0)

    threading.Thread(target=terminal_worker, daemon=True).start()

    # Inicia a UI Nativa Desktop (PyWebView bloqueia a Main Thread)
    try:
        from src.ui.desktop_app import DesktopApp
        app = DesktopApp(
            task_queue=task_queue,
            agent_manager=agent.agent_manager,
            settings=settings,
            chat_log=chat_log,
            system_logs=system_logs,
            confirm_bus=confirm_bus,
            runtime_status=runtime_status,
            llm=llm,
            tts=tts,
            stt=stt,
            tools=tools,
        )
        runtime_status.mark_startup_phase("ui_starting")
        app.start()
    except KeyboardInterrupt:
        print("\nEncerrando por Ctrl+C...")
        import os
        os._exit(0)
    except Exception as e:
        print(f"[UI] Erro ao iniciar Desktop UI: {e}")
        # Fallback de bloqueio caso falhe (pra não fechar o app direto)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            import os
            os._exit(0)

    if stop_listening_bg:
        stop_listening_bg(wait_for_stop=False)
    print("Encerrando.")


if __name__ == "__main__":
    main()
