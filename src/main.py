import sys
import os
from pathlib import Path
import queue

# Global Queue for tasks
task_queue = queue.Queue()

# Adiciona a pasta raiz ao sys.path para permitir imports do tipo 'from src...'
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

    import logging
import threading
import time
import keyboard
import json

from src.agent.orchestrator import AgentOrchestrator
from src.config import load_settings
from src.integrations.super_productivity import SuperProductivityConnector
from src.memory.store import MemoryStore
from src.services.llm import LLMService
from src.services.stt import STTService
from src.services.vision_tracker import VisionTracker
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
from src.tools.spotify import SpotifyTool
from src.tools.file_manager import FileManagerTool
from src.tools.app_manager import AppManagerTool
from src.tools.image_generator import GenerateImageTool, ShowImageTool, ListImagesTool
from src.tools.hacker_mode import HackerModeTool
from src.tools.nexus import NexusTool
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
from src.services.heartbeat import HeartbeatService, append_daily_log

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
        elevenlabs_api_keys=settings.elevenlabs_api_keys,
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
        ollama_model=settings.ollama_model,
        ollama_base_url=settings.ollama_base_url,
        primary_llm_provider=settings.llm_provider,
        fallback_gemini=settings.llm_fallback_gemini,
    )
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
    )
    agent = AgentOrchestrator(
        llm=llm, vision=vision, tools=tools, memory=memory,
        use_function_calling=settings.gemini_use_function_calling,
        assistant_base_persona=settings.assistant_base_persona,
    )
    
    # Inicia Rastreador de Gestos e Visão (MediaPipe) em background
    vision_tracker = VisionTracker(
        task_queue=task_queue, 
        tts_instance=tts, 
        use_face_auth=settings.use_face_auth
    )
    vision_tracker.start()

    # Inicia Heartbeat Service (consolidação periódica de memória)
    heartbeat = HeartbeatService(interval_minutes=30, llm_service=llm)
    heartbeat.start()

    # Inicia Agente Proativo (Puxa assunto baseado na tela, a cada 15-45 min)
    from src.services.proactive_agent import ProactiveAgent
    proactive = ProactiveAgent(agent_orchestrator=agent, tts_instance=tts, min_interval_minutes=15, max_interval_minutes=45)
    proactive.start()

    if settings.use_mic:
        stt.calibrate(duration=2.0)

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
            try:
                _viz_set("set_thinking")
                _add_chat("user", "Você", text)
                response = agent.handle_user_message(text)
                
                active_ag = agent.agent_manager.get_active_agent()
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
                # Fase 3.2.3 — Restaura o agente original após chamada por nome
                if called_agent_id and called_agent_id != original_agent_id:
                    agent.agent_manager.set_active_agent(original_agent_id)
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
            
            # Fase 3.2 — Modos Multi-Agentes Especiais
            if text.startswith("/roundrobin|"):
                try:
                    _, chained_str, ids_str, query = text.split("|", 3)
                    chained = (chained_str.lower() == "true")
                    agent_ids = [aid.strip() for aid in ids_str.split(",") if aid.strip()]
                    
                    with agent_lock:
                        is_processing = True
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
                except Exception as e:
                    print(f"[Erro Importação] {e}")
                    is_processing = False
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

    # Inicia a escuta contínua de voz (modo padrão se use_mic for True)
    stop_listening_bg = None
    mic_currently_enabled = settings.use_mic

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
        print("\n[ClapDetector] Duas palmas detectadas!", flush=True)
        mic_currently_enabled = not mic_currently_enabled
        
        import winsound
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
            
    try:
        from src.services.clap_detector import ClapDetector
        clap_detector = ClapDetector(on_clap_callback=_on_clap)
        clap_detector.start()
        print("[ClapDetector] Sistema de palmas iniciado em background.")
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
        )
        app.start()
    except Exception as e:
        print(f"[UI] Erro ao iniciar Desktop UI: {e}")
        # Fallback de bloqueio caso falhe (pra não fechar o app direto)
        while True:
            time.sleep(1)

    if stop_listening_bg:
        stop_listening_bg(wait_for_stop=False)
    print("Encerrando.")


if __name__ == "__main__":
    main()
