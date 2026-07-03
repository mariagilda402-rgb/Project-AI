import threading
import queue
import time
import json
import re
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class InteractionLoop:
    def __init__(self, services: dict):
        self.services = services
        self.agent = services["agent"]
        self.llm = services["llm"]
        self.tts = services["tts"]
        self.stt = services["stt"]
        self.runtime_status = services["runtime_status"]
        self.settings = services["settings"]
        self.confirm_bus = services["confirm_bus"]
        
        self.task_queue = queue.Queue()
        self.agent_lock = threading.Lock()
        self.is_processing = False

        self._worker_thread: threading.Thread | None = None
        
        self.chat_log = []
        self._chat_log_lock = threading.Lock()
        
        self.mic_currently_enabled = self.settings.use_mic
        self.stop_listening_bg = None
        
        # Opcionais configurados fora
        self.unified_bridge = None
        self._viz_set = lambda *args, **kwargs: None

    def set_viz_callback(self, viz_callback):
        self._viz_set = viz_callback

    def set_unified_bridge(self, bridge):
        self.unified_bridge = bridge

    def _add_chat(self, role: str, name: str, text: str):
        import datetime
        with self._chat_log_lock:
            self.chat_log.append({
                "role": role,
                "name": name,
                "text": text,
                "time": datetime.datetime.now().strftime("%H:%M:%S")
            })
            if len(self.chat_log) > 200:
                del self.chat_log[:len(self.chat_log) - 200]

    def _detect_agent_by_name(self, text: str):
        text_lower = text.strip().lower()
        best_match = None
        best_len = 0
        for ag in self.agent.agent_manager.list_agents():
            name_lower = ag.name.strip().lower()
            for prefix in [name_lower + ",", name_lower + " ", name_lower + "!"]:
                if text_lower.startswith(prefix) and len(name_lower) > best_len:
                    best_match = ag.id
                    best_len = len(name_lower)
        if best_match:
            cleaned = text.strip()[best_len:].lstrip(" ,!.:").strip()
            return best_match, cleaned if cleaned else text.strip()
        return None, text

    def _send_unified_assistant_text(self, source: str, text: str):
        if not self.unified_bridge or not source.startswith("Unified:") or not text:
            return
        target_device = source.split("Unified:", 1)[1].strip()
        if not target_device:
            return
        try:
            from src.jarvis_unified.models import JarvisEvent
            session_id = self.unified_bridge.session_state.current().session_id
            for event_type, payload in [
                ("assistant_delta", {"text": text, "render": False}),
                ("render_update", {
                    "surface_id": "assistant-live",
                    "op": "append",
                    "block": {"type": "assistant_transcript", "text": text},
                }),
            ]:
                self.unified_bridge.emit_event(JarvisEvent.create(
                    session_id=session_id,
                    source_device="desktop:local",
                    target_device=target_device,
                    event_type=event_type,
                    payload=payload,
                ))
        except Exception as exc:
            print(f"[UnifiedJarvis] Falha ao enviar resposta: {exc}")

    def _start_background_task(self, goal: str, speaker_name: str):
        self._add_chat("assistant", "Jarvis", f"⏳ Iniciando tarefa em background: {goal}")
        if self.tts:
            self.tts.speak(f"Iniciando tarefa autônoma: {goal}")
        
        def _bg_worker():
            from src.agent.planner import execute_plan
            from src.agent.action_executor import ActionExecutor
            from src.agent.tool_guardrails import ToolCallGuardrailController
            
            def bg_status(msg):
                print(f"[BG Planner] {msg}")
                self._send_unified_assistant_text("Unified:desktop", f"[Planner] {msg}")
                
            executor = ActionExecutor(
                allowed_tool_names=frozenset(t.name for t in self.services["tools"].tools if hasattr(t, "name")),
                guardrails=ToolCallGuardrailController(),
                tools=self.services["tools"],
                llm=self.services["llm"],
                vision=self.services["vision"],
                confirm_bus=self.services["confirm_bus"],
                agent_manager=self.agent.agent_manager,
            )
            
            def _exec_fn(name, args):
                return executor.execute(name, args, goal)
                
            try:
                result = execute_plan(goal, self.services["llm"], _exec_fn, on_status=bg_status)
                self._add_chat("assistant", "Jarvis (Background)", f"✅ Tarefa concluída: {result}")
                if self.tts:
                    self.tts.speak("A tarefa em background foi concluída.")
            except Exception as e:
                self._add_chat("assistant", "Jarvis (Background)", f"❌ Erro na tarefa: {e}")
                
        threading.Thread(target=_bg_worker, daemon=True).start()

    def _process_and_respond(self, text: str, source: str = ""):
        if not text: return
        tag = f" ({source})" if source else ""

        speaker_name = "Desconhecido"
        access_level = 0
        if source.startswith("Voz:"):
            parts = source.split(":")
            if len(parts) >= 2: speaker_name = parts[1]
            if len(parts) >= 3:
                try: access_level = int(parts[2])
                except: pass
        elif source == "Texto":
            speaker_name = "Admin"
            access_level = 100

        if text.lower().startswith("/task "):
            goal = text[6:].strip()
            self._start_background_task(goal, speaker_name)
            return

        called_agent_id, cleaned_text = self._detect_agent_by_name(text)
        original_agent_id = self.agent.agent_manager._active_agent_id
        if called_agent_id and called_agent_id != original_agent_id:
            self.agent.agent_manager.set_active_agent(called_agent_id)
            called_name = self.agent.agent_manager.get_active_agent().name
            print(f"\n[Chamada por Nome] Direcionando para '{called_name}'")
            text = cleaned_text

        with self.agent_lock:
            self.is_processing = True
            self.runtime_status.set_processing(True)
            try:
                self._viz_set("set_thinking")
                self._add_chat("user", speaker_name, text)
                try:
                    response_gen = self.agent.handle_user_message(text, speaker_name=speaker_name, access_level=access_level)
                except Exception as exc:
                    logger.exception("Agent.handle_user_message failed")
                    response_gen = f"Desculpe, ocorreu um erro ao processar sua solicitação: {exc}"
                active_ag = self.agent.agent_manager.get_active_agent()

                import types
                if isinstance(response_gen, types.GeneratorType):
                    self._viz_set("set_speaking")
                    llm_used = getattr(self.llm, "last_model", "")
                    llm_tag = f" [{llm_used}]" if llm_used else ""

                    self.tts.apply_agent_voice(
                        provider=active_ag.tts_provider, voice=active_ag.tts_voice,
                        speed=active_ag.tts_speed, edge_rate=active_ag.edge_tts_rate,
                        edge_vol=active_ag.edge_tts_volume, kokoro_voice=active_ag.kokoro_voice
                    )

                    full_response = ""
                    tts_buffer = ""
                    tts_queue = queue.Queue()

                    def tts_worker():
                        while True:
                            text_chunk = tts_queue.get()
                            if text_chunk is None: break
                            if text_chunk.strip(): self.tts.speak(text_chunk)
                            tts_queue.task_done()

                    threading.Thread(target=tts_worker, daemon=True).start()

                    for chunk in response_gen:
                        if self.tts._interrupt_event.is_set(): break
                        if chunk:
                            print(chunk, end="", flush=True)
                            full_response += chunk
                            tts_buffer += chunk
                            if re.search(r'[.!?\n]\s*$', tts_buffer):
                                to_speak = tts_buffer.strip()
                                if to_speak: tts_queue.put(to_speak)
                                tts_buffer = ""
                    print()
                    if tts_buffer.strip(): tts_queue.put(tts_buffer.strip())
                    tts_queue.put(None)

                    self._add_chat("assistant", active_ag.name, full_response)
                    try:
                        self._send_unified_assistant_text(source, full_response)
                    except Exception:
                        logger.exception("Failed to send unified assistant text (generator)")
                    self._viz_set("set_idle")
                else:
                    response = response_gen
                    self._add_chat("assistant", active_ag.name, response)
                    try:
                        self._send_unified_assistant_text(source, response)
                    except Exception:
                        logger.exception("Failed to send unified assistant text (immediate)")

                    if not self.tts._interrupt_event.is_set():
                        self.tts.apply_agent_voice(
                            provider=active_ag.tts_provider, voice=active_ag.tts_voice,
                            speed=active_ag.tts_speed, edge_rate=active_ag.edge_tts_rate,
                            edge_vol=active_ag.edge_tts_volume, kokoro_voice=active_ag.kokoro_voice
                        )
                        segments = re.split(r'(<VOICE_SWAP:.*?>.*?</VOICE_SWAP>)', response, flags=re.DOTALL)
                        self._viz_set("set_speaking")
                        llm_used = getattr(self.llm, "last_model", "")
                        llm_tag = f" [{llm_used}]" if llm_used else ""

                        for segment in segments:
                            if not segment.strip(): continue
                            if self.tts._interrupt_event.is_set(): break
                            match = re.match(r'<VOICE_SWAP:(.*?)>(.*?)</VOICE_SWAP>', segment, flags=re.DOTALL)
                            if match:
                                target_id, text_to_speak = match.group(1).strip(), match.group(2).strip()
                                target_agent = self.agent.agent_manager._agents.get(target_id)
                                if target_agent:
                                    print(f"\n>>> [{target_agent.name} assumiu a fala]")
                                    self.tts.apply_agent_voice(
                                        provider=target_agent.tts_provider, voice=target_agent.tts_voice,
                                        speed=target_agent.tts_speed, edge_rate=target_agent.edge_tts_rate,
                                        edge_vol=target_agent.edge_tts_volume, kokoro_voice=target_agent.kokoro_voice
                                    )
                                    print(f"{target_agent.name}{tag}{llm_tag}: {text_to_speak}", flush=True)
                                    self.tts.speak(text_to_speak)
                                    self.tts.apply_agent_voice(
                                        provider=active_ag.tts_provider, voice=active_ag.tts_voice,
                                        speed=active_ag.tts_speed, edge_rate=active_ag.edge_tts_rate,
                                        edge_vol=active_ag.edge_tts_volume, kokoro_voice=active_ag.kokoro_voice
                                    )
                                else:
                                    print(f"{active_ag.name}{tag}{llm_tag}: {text_to_speak}", flush=True)
                                    self.tts.speak(text_to_speak)
                            else:
                                print(f"{active_ag.name}{tag}{llm_tag}: {segment.strip()}", flush=True)
                                self.tts.speak(segment.strip())
                        self._viz_set("set_idle")
                    else:
                        print(f"[{active_ag.name}{tag} Interrompido antes de falar]")
                        self.tts._interrupt_event.clear()
            except Exception as e:
                logger.exception("Unhandled error in processing loop: %s", e)
                self._viz_set("set_error", str(e))
                # notify user via assistant text and TTS where possible
                try:
                    error_text = "Desculpe, ocorreu um erro interno ao processar sua solicitação."
                    self._add_chat("assistant", "Jarvis", error_text)
                    try:
                        self._send_unified_assistant_text(source, error_text)
                    except Exception:
                        logger.exception("Failed to send error message to unified bridge")
                    if self.tts:
                        try:
                            self.tts.speak(error_text)
                        except Exception:
                            logger.exception("Failed to TTS error message")
                except Exception:
                    logger.exception("Failed during error handling notification")
                time.sleep(2)
            finally:
                self.is_processing = False
                self.runtime_status.set_processing(False)
                if called_agent_id and called_agent_id != original_agent_id:
                    self.agent.agent_manager.set_active_agent(original_agent_id)
                if self.mic_currently_enabled:
                    self._viz_set("set_listening")
                else:
                    self._viz_set("set_idle")

    def _start_mic(self):
        if self.stop_listening_bg is None:
            print("\n[Voz] Microfone ativado. Fale a qualquer momento.")
            self.stop_listening_bg = self.stt.start_continuous_listening(
                self.on_voice_recognized,
                on_speech_start=lambda: self._viz_set("set_listening"),
                on_speech_end=lambda: self._viz_set("set_idle") if not self.is_processing else None
            )
            if not self.is_processing:
                self._viz_set("set_idle")

    def _stop_mic(self):
        if self.stop_listening_bg is not None:
            print("\n[Voz] Microfone desativado.")
            self.stop_listening_bg(wait_for_stop=False)
            self.stop_listening_bg = None
            if not self.is_processing:
                self._viz_set("set_idle")

    def on_voice_recognized(self, text: str, audio=None):
        if not text.strip(): return
        from src.tools.critical_confirm import try_voice_resolve_confirmation
        if try_voice_resolve_confirmation(self.confirm_bus, text):
            print("\n[Confirmação] Resposta por voz aceita.", flush=True)
            return

        speaker_name = "Desconhecido"
        access_level = 0
        try:
            from src.services.nexus_service import get_nexus_service
            from src.services.voice_auth_service import resolve_voice_identity
            db_conn = get_nexus_service().db._get_connection()
            identity = resolve_voice_identity(db_conn, text, audio_data=audio)
            speaker_name = identity.name
            access_level = identity.access_level
            if identity.just_registered:
                print("\n[Auth] Admin registrado com sucesso via palavra-chave e biometria de voz!")
                self.tts.speak("Senha aceita. Sua voz foi registrada como administrador do sistema.")
                return
            elif identity.message:
                print(f"\n[Auth] {identity.message}")
        except Exception:
            pass

        print(f"\n{speaker_name} (Nível {access_level}): {text}")
        if self.is_processing:
            print("[Interrupção!] Parando a IA para ouvir a nova instrução...")
            self.tts.stop()
            while not self.task_queue.empty():
                try: self.task_queue.get_nowait(); self.task_queue.task_done()
                except queue.Empty: break

        try:
            from src.services.voice_auth_service import VoiceIdentity, format_voice_source
            source = format_voice_source(VoiceIdentity(speaker_name, access_level))
        except Exception:
            source = f"Voz:{speaker_name}:{access_level}"
        self.task_queue.put((text, source))

    def interaction_worker(self):
        while True:
            item = self.task_queue.get()
            if item is None: break
            text, source = item
            self.runtime_status.set_enqueue_preview(text)

            if text == "/toggle_mic":
                self.mic_currently_enabled = not self.mic_currently_enabled
                self.runtime_status.set_mic_listening(self.mic_currently_enabled)
                if self.mic_currently_enabled: self._start_mic()
                else: self._stop_mic()
                try:
                    state_file = Path("data/visualizer_state.json")
                    state_file.parent.mkdir(parents=True, exist_ok=True)
                    prev = json.loads(state_file.read_text(encoding="utf-8") or "{}") if state_file.exists() else {}
                    prev["mic_enabled"] = self.mic_currently_enabled
                    state_file.write_text(json.dumps(prev, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception: pass
                self.task_queue.task_done()
                continue

            # Para comandos debug /tts_test, /diagnostics_llm omitidos p/ simplificar, mas fáceis de repor
            self._process_and_respond(text, source)
            self.task_queue.task_done()

    def start_loop(self):
        self._worker_thread = threading.Thread(target=self.interaction_worker, daemon=True)
        self._worker_thread.start()
        if self.mic_currently_enabled:
            self._start_mic()
        return self._worker_thread

    def stop_loop(self, timeout: float = 3.0):
        """Stops the interaction worker and related resources cleanly."""
        try:
            # Signal worker to exit
            try:
                self.task_queue.put(None)
            except Exception:
                pass

            # Stop microphone if running
            try:
                self._stop_mic()
            except Exception:
                pass

            # Wait for thread to finish
            if self._worker_thread and self._worker_thread.is_alive():
                self._worker_thread.join(timeout=timeout)
        except Exception as exc:
            print(f"[InteractionLoop] Erro ao parar loop: {exc}")
