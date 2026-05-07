import sys
import os
from pathlib import Path
import queue

# Adiciona a pasta raiz ao sys.path para permitir imports do tipo 'from src...'
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

import logging
import threading
import time
import keyboard

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
from src.tools.notes import NotesTool
from src.tools.productivity import ProductivityTool
from src.tools.registry import ToolRegistry
from src.tools.system_info import SystemInfoTool
from src.tools.timer import TimerTool
from src.tools.web_search import WebSearchTool
from src.tools.whatsapp import WhatsAppTool
from src.tools.visualizer_control import VisualizerControlTool


def _viz_set(func_name: str, *args, **kwargs):
    try:
        from src.services import visualizer
        getattr(visualizer, func_name)(*args, **kwargs)
    except Exception:
        pass


def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    settings = load_settings()

    if settings.enable_visualizer:
        from src.services import visualizer
        visualizer.start()

    stt = STTService(
        use_mic=settings.use_mic, 
        language=settings.stt_language,
        groq_api_key=settings.groq_api_key
    )
    tts = TTSService(
        api_key=settings.openai_api_key,
        model=settings.tts_model,
        voice=settings.tts_voice,
        provider=settings.tts_provider,
        murf_api_key=settings.murf_api_key,
        murf_voice_id=settings.murf_voice_id,
        murf_api_url=settings.murf_api_url,
        allow_system_player_on_failure=settings.tts_allow_system_player,
    )
    llm = LLMService(
        gemini_api_key=settings.gemini_api_key,
        gemini_model=settings.gemini_model,
        openrouter_api_key=settings.openrouter_api_key,
        openrouter_model=settings.openrouter_model,
        nvidia_api_key=settings.nvidia_api_key,
        nvidia_model=settings.nvidia_model,
        groq_api_key=settings.groq_api_key,
        groq_model=settings.groq_model,
        primary_llm_provider=settings.llm_provider,
        fallback_gemini=settings.llm_fallback_gemini,
    )
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

    tools = ToolRegistry(
        tools=[
            DesktopAutomationTool(),
            ProductivityTool(SuperProductivityConnector()),
            FinanceTool(),
            WebSearchTool(),
            ClipboardTool(),
            TimerTool(),
            SystemInfoTool(),
            NotesTool(),
            MediaControlTool(),
            MemoryManagerTool(),
            WhatsAppTool(),
            VisualizerControlTool(),
        ],
        require_critical_confirmation=settings.require_critical_confirmation,
    )
    agent = AgentOrchestrator(
        llm=llm, vision=vision, tools=tools, memory=memory,
        use_function_calling=settings.gemini_use_function_calling,
        assistant_base_persona=settings.assistant_base_persona,
    )

    if settings.use_mic:
        stt.calibrate(duration=2.0)

    # Estado global para lidar com interrupções
    task_queue = queue.Queue()
    agent_lock = threading.Lock()
    is_processing = False

    def _process_and_respond(text: str, source: str = ""):
        nonlocal is_processing
        if not text: return
        tag = f" ({source})" if source else ""
        
        # Bloqueia para não rodar duas chamadas da LLM ao mesmo tempo
        with agent_lock:
            is_processing = True
            try:
                _viz_set("set_thinking")
                response = agent.handle_user_message(text)
                
                # Se o usuário interrompeu enquanto ela pensava, não fala.
                if not tts._interrupt_event.is_set():
                    print(f"IA{tag}: {response}", flush=True)
                    tts.speak(response)
                else:
                    print(f"[IA{tag} Interrompida antes de falar]")
                    tts._interrupt_event.clear()
                    
            except Exception as e:
                print(f"\n[Erro{tag}] {e}")
                _viz_set("set_error", str(e))
                time.sleep(2)
            finally:
                is_processing = False
                if mic_currently_enabled:
                    _viz_set("set_listening")
                else:
                    _viz_set("set_idle")

    # Trabalhador que consome a fila de interações (texto ou voz)
    def interaction_worker():
        while True:
            item = task_queue.get()
            if item is None: break
            text, source = item
            _process_and_respond(text, source)
            task_queue.task_done()

    threading.Thread(target=interaction_worker, daemon=True).start()

    # Callback para quando a voz for detectada em background
    def on_voice_recognized(text: str):
        nonlocal is_processing
        print(f"\nVoce (Voz): {text}")
        if is_processing:
            print("[Interrupção!] Parando a IA para ouvir a nova instrução...")
            tts.stop() # Para a fala atual imediatamente
            # O texto novo será enfileirado e processado em seguida
        
        task_queue.put((text, "Voz"))

    # Inicia a escuta contínua de voz (modo padrão se use_mic for True)
    stop_listening_bg = None
    mic_currently_enabled = settings.use_mic

    def _start_mic():
        nonlocal stop_listening_bg
        if stop_listening_bg is None:
            print("\n[Voz] Microfone ativado. Fale a qualquer momento.")
            stop_listening_bg = stt.start_continuous_listening(on_voice_recognized)
            _viz_set("set_listening")

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
                            if is_processing: tts.stop()
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
                            if wanted_mic: _start_mic()
                            else: _stop_mic()
                except Exception:
                    pass

            time.sleep(1)

    threading.Thread(target=state_monitor_worker, daemon=True).start()

    # O loop principal agora apenas coleta texto digitado
    print("Pronta. Digite para conversar ou apenas fale se o microfone estiver ativo.")
    while True:
        try:
            user_text = input("Voce: ").strip()
            if user_text.lower() in {"sair", "exit"}:
                break
            if user_text:
                if is_processing:
                    tts.stop() # Permite interromper digitando também
                task_queue.put((user_text, "Texto"))
        except (KeyboardInterrupt, EOFError):
            break

    if stop_listening_bg:
        stop_listening_bg(wait_for_stop=False)
    print("Encerrando.")


if __name__ == "__main__":
    main()
