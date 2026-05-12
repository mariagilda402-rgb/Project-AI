from __future__ import annotations

import re
import time

from src.agent.gemini_tools import build_agent_tool, build_openai_agent_tools
from src.agent.prompts import (
    build_function_calling_system_prompt,
    build_marker_agent_system_prompt,
    build_vision_instruction,
)
from src.agent.tool_markers import parse_tool_markers
from src.agents.agent_model import AgentManager
from src.memory.store import MemoryStore
from src.memory.vector_db import SemanticMemory
from src.services.llm import LLMService
from src.services.vision import VisionService
from src.tools.registry import ToolRegistry
from src.tools.memory_manager import MemoryManagerTool
from src.utils.window_context import build_proactive_context
from src.services.gemini_live import GeminiLiveService


def _is_short_greeting(text: str) -> bool:
    """Evita function calling (ex.: analyze_screen) em saudações — resposta fica muito mais rápida."""
    raw = (text or "").strip().lower()
    core = raw.strip("!.?… \t")
    if len(core) > 22:
        return False
    greetings = {
        "oi",
        "olá",
        "ola",
        "hey",
        "hi",
        "hello",
        "eae",
        "e aí",
        "e ai",
        "bom dia",
        "boa tarde",
        "boa noite",
        "salve",
        "opa",
    }
    return core in greetings


class AgentOrchestrator:
    def __init__(
        self,
        llm: LLMService,
        vision: VisionService,
        tools: ToolRegistry,
        memory: MemoryStore,
        use_function_calling: bool = True,
        assistant_base_persona: str = "",
    ) -> None:
        self.llm = llm
        self.vision = vision
        self.tools = tools
        self.memory = memory
        self.use_function_calling = use_function_calling
        self.assistant_base_persona = assistant_base_persona or ""
        self.semantic_memory = SemanticMemory()
        self.agent_manager = AgentManager()
        self.live_service = None
        self.is_live_mode = False
        self._live_task = None

    @property
    def _active_persona(self) -> str:
        """Retorna a persona do agente ativo (ou a persona base como fallback)."""
        try:
            return self.agent_manager.get_active_agent().persona
        except Exception:
            return self.assistant_base_persona

    @property
    def _active_memory_collection(self) -> str:
        """Retorna o nome da coleção de memória do agente ativo."""
        try:
            return self.agent_manager.get_active_agent().memory_collection
        except Exception:
            return "user_memories"

    def handle_user_message(self, text: str) -> str:
        # Contexto invisivel: data, hora, janela
        ctx = build_proactive_context()
        
        # RAG Semântico — busca na coleção do agente ativo (apenas se não for saudação curta)
        rag_context = ""
        agent_collection = self._active_memory_collection
        if self.semantic_memory.enabled and not _is_short_greeting(text):
            emb = self.llm.generate_embedding(text)
            if emb:
                memories = self.semantic_memory.search_memories(emb, top_k=2, collection_name=agent_collection)
                if memories:
                    rag_context = " [Fatos que você sabe sobre o usuário: " + " | ".join(memories) + "]"
                
        enriched_text = f"{ctx}{rag_context} {text}"
        
        self.memory.add_short_term("user", enriched_text)
        self.memory.maybe_record_persona_note(text)
        
        # Se estamos em modo Live, o processamento é feito pelo serviço de streaming
        if self.is_live_mode:
            return "Estou ouvindo em tempo real, Sir."
            
        history = self.memory.get_recent_short_term(limit=10)
        prefs = self.memory.get_long_term("preferences", default=[])
        persona_notes = self.memory.get_long_term("persona_evolution", default=[])

        final = ""
        fc_allowed = self.use_function_calling and not _is_short_greeting(text)
        fc_gemini = fc_allowed and self.llm.wants_gemini_native_tools()
        fc_nvidia = fc_allowed and self.llm.wants_nvidia_native_tools()
        fc_groq = fc_allowed and self.llm.wants_groq_native_tools()

        pref_text = str(prefs[-5:])
        system_fc = build_function_calling_system_prompt(
            self._active_persona,
            persona_notes if isinstance(persona_notes, list) else [],
            pref_text,
        )
        prev_tool: str | None = None

        def on_fc(name: str, args: dict) -> str:
            nonlocal prev_tool
            if prev_tool == "open_windows_application" and name == "analyze_screen":
                time.sleep(2.0)
            out = self._execute_function_tool(name, args, text)
            prev_tool = name
            return out

        dynamic_tools = [t for t in self.tools.tools if hasattr(t, "parameters")]

        if fc_gemini:
            final = (
                self.llm.chat_with_functions(
                    system_instruction=system_fc,
                    messages=history,
                    tools=[build_agent_tool(dynamic_tools)],
                    on_function_call=on_fc,
                    force_tool=False  # O LLM decide naturalmente quando agir
                )
                or ""
            ).strip()
        elif fc_nvidia:
            prev_tool = None
            final = (
                self.llm.chat_with_openai_tools(
                    system_instruction=system_fc,
                    messages=history,
                    tools=build_openai_agent_tools(dynamic_tools),
                    client=self.llm.nvidia_client,
                    model=self.llm.nvidia_model,
                    on_function_call=on_fc,
                )
                or ""
            ).strip()
        elif fc_groq:
            prev_tool = None
            final = (
                self.llm.chat_with_openai_tools(
                    system_instruction=system_fc,
                    messages=history,
                    tools=build_openai_agent_tools(dynamic_tools),
                    client=self.llm.groq_client,
                    model=self.llm.groq_model,
                    on_function_call=on_fc,
                )
                or ""
            ).strip()

        if not final:
            # Evita segunda rajada ao Gemini se function calling Gemini já falhou (ex.: cota 429).
            skip_gemini = fc_gemini
            final = self._handle_marker_tools(
                text,
                history,
                prefs,
                persona_notes if isinstance(persona_notes, list) else [],
                skip_gemini=skip_gemini,
            ).strip()

        if not final:
            final = (
                "Nao obtive texto util da assistente. "
                "Tente reformular ou verifique a conexao com a LLM."
            )

        final = self._clean_response(final)
        self.memory.add_short_term("assistant", final)
        self.memory.maybe_store_preference(text, final, consent_for_sensitive=True)

        # Log qual LLM respondeu
        provider = getattr(self.llm, "last_provider", self.llm.primary_llm_provider)
        model = getattr(self.llm, "last_model", "")
        print(f"\n[🤖 LLM] {provider.upper()} | {model}", flush=True)

        # Auto-sumarizacao: condensa mensagens antigas quando a sessao cresce.
        self._maybe_summarize()

        # RAG - Extração de Memórias Assíncrona (na coleção do agente ativo)
        if self.semantic_memory.enabled:
            import threading
            threading.Thread(
                target=self._extract_semantic_memory,
                args=(text, final, agent_collection),
                daemon=True
            ).start()

        # Daily Log — alimenta o Heartbeat Service
        try:
            from src.services.heartbeat import append_daily_log
            short_user = text[:80].replace("\n", " ")
            short_reply = final[:80].replace("\n", " ")
            append_daily_log(f"User: {short_user} → AI: {short_reply}")
        except Exception:
            pass

        # Structured Memory Extraction (async, two-stage)
        import threading
        threading.Thread(
            target=self._extract_structured_memory_async,
            args=(text, final),
            daemon=True
        ).start()

        return final

    def _extract_semantic_memory(self, user_text: str, assistant_text: str, collection_name: str):
        """Thread em background que extrai fatos definitivos da conversa para o ChromaDB."""
        from src.agent.prompts import EXTRACT_MEMORY_PROMPT
        
        # Envia os dois lados da conversa e pede ao LLM para extrair
        prompt = f"Usuário disse: {user_text}\nVocê respondeu: {assistant_text}"
        
        try:
            extracted = self.llm.chat(
                system_prompt=EXTRACT_MEMORY_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            
            if extracted and "vazio" not in extracted.lower():
                lines = [line.strip() for line in extracted.split("\n") if line.strip() and "vazio" not in line.lower()]
                for fact in lines:
                    emb = self.llm.generate_embedding(fact)
                    if emb:
                        self.semantic_memory.save_memory(fact, emb, collection_name=collection_name)
                        agent_name = self.agent_manager.get_active_agent().name
                        print(f"[RAG {agent_name}] Novo fato aprendido: {fact}")
        except Exception as e:
            import traceback
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[RAG JARVIS] Erro na thread de extração de memória: {e}")
            logger.debug(traceback.format_exc())

    def _extract_structured_memory_async(self, user_text: str, assistant_text: str):
        """Thread em background: extração de memória estruturada em 2 estágios."""
        try:
            from src.memory.structured_memory import (
                should_extract_memory,
                extract_structured_memory,
                update_structured_memory,
            )

            # Stage 1: Verificação rápida YES/NO
            if not should_extract_memory(user_text, assistant_text, self.llm):
                return

            # Stage 2: Extração detalhada em JSON
            data = extract_structured_memory(user_text, assistant_text, self.llm)
            if data:
                update_structured_memory(data)
                print(f"[StructuredMemory] 💾 Auto-extraído: {list(data.keys())}")

        except Exception as e:
            if "429" not in str(e):
                print(f"[StructuredMemory] ⚠️ Extração async falhou: {e}")

    def _maybe_summarize(self) -> None:
        """Se ha mensagens suficientes, usa o LLM para resumir as mais antigas."""
        if not self.memory.should_summarize():
            return
        old_msgs = self.memory.get_messages_for_summary()
        if not old_msgs:
            return
        # Monta um prompt de sumarizacao.
        lines = []
        for m in old_msgs:
            role = m.get("role", "user")
            content = m.get("content", "")
            lines.append(f"{role}: {content[:300]}")
        conversation_text = "\n".join(lines)
        summary_prompt = (
            "Resuma a conversa abaixo em no maximo 4 frases em portugues, "
            "preservando: (1) topicos discutidos, (2) decisoes tomadas, "
            "(3) dados importantes mencionados (nomes, valores, horarios). "
            "Nao invente nada que nao esteja na conversa.\n\n"
            f"{conversation_text}"
        )
        summary = self.llm.chat(
            "Voce e um assistente que faz resumos concisos.",
            [{"role": "user", "content": summary_prompt}],
            skip_gemini=True,
        )
        if summary and len(summary) > 10:
            self.memory.apply_summary(summary)

    @staticmethod
    def _clean_response(text: str) -> str:
        """Remove tags <function=...> que modelos Groq/Llama vazam quando function calling falha."""
        # <function=name>{...}</function>  ou  <function=name {json} </function>
        cleaned = re.sub(
            r"<function=[^>]*>.*?</function>",
            "",
            text,
            flags=re.DOTALL,
        )
        # Variante sem closing tag: <function=name>{...}
        cleaned = re.sub(
            r"<function=[^>]*>\{[^}]*\}",
            "",
            cleaned,
        )
        # Limpa espacos extras resultantes.
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    def _handle_marker_tools(
        self,
        user_text: str,
        history: list[dict[str, str]],
        prefs: list,
        persona_notes: list[str],
        skip_gemini: bool = False,
    ) -> str:
        system_prompt = build_marker_agent_system_prompt(
            self._active_persona, persona_notes
        )
        context_messages = history + [
            {
                "role": "system",
                "content": f"Preferencias salvas (resumo): {prefs[-5:]}",
            }
        ]
        raw_reply = self.llm.chat(
            system_prompt, context_messages, skip_gemini=skip_gemini
        )
        speakable, steps = parse_tool_markers(raw_reply)

        chunks: list[str] = []
        if speakable:
            chunks.append(speakable)

        for i, step in enumerate(steps):
            if step.kind == "vision":
                vision_prompt = self._vision_context(user_text, speakable)
                vision_text = self.vision.describe_screen(
                    build_vision_instruction(vision_prompt)
                )
                chunks.append(vision_text)
            else:
                result = self.tools.run_by_marker(step.kind, step.arg, user_text)
                # Só silencia o sucesso de ferramentas de acao para nao ficar narrando, mas fala as de consulta (list, search, etc)
                if result.message:
                    silent_tools = {"whatsapp_send", "whatsapp", "memory_save", "timer_set", "clipboard_write", "media_control", "notes_save", "open_app", "app", "apps", "spotify", "browser", "open_browser"}
                    if result.ok and step.kind in silent_tools:
                        pass # Sucesso silencioso
                    elif not result.ok:
                        chunks.append(f"[Aviso do sistema: {result.message}]")
                    else:
                        chunks.append(result.message)
                if (
                    step.kind in ("open_app", "app")
                    and i + 1 < len(steps)
                    and steps[i + 1].kind == "vision"
                ):
                    time.sleep(2.0)

        return "\n\n".join(c for c in chunks if c.strip())

    def _execute_function_tool(self, name: str, args: dict, user_text: str) -> str:
        args = args or {}
        
        # Log de comando (se habilitado nas configurações)
        from src.config import load_settings
        if load_settings().enable_command_logs:
            print(f"\n[🛠️ TOOL CALL] {name}({args})")

        # 1) analyze_screen
        if name == "analyze_screen":
            instr = (args.get("instruction") or "").strip()
            vision_prompt = self._vision_context(user_text, instr)
            res = self.vision.describe_screen(
                build_vision_instruction(vision_prompt)
            )
            if load_settings().enable_command_logs:
                print(f"[✅ RESULT] analyze_screen concluído.")
            return res

        # 2) search_web
        if name == "search_web":
            query = (args.get("query") or "").strip()
            r = self.tools.run_by_marker("web_search", query, user_text)
            return r.message or "Sem resultados."



        # 4) run_utility (consolidado: clipboard, timer, system_info, media, notes)
        if name == "run_utility":
            action = (args.get("action") or "").strip().lower()
            argument = (args.get("argument") or "").strip()
            detail = (args.get("detail") or "").strip()
            return self._handle_utility(action, argument, detail, user_text)

        # 5) manage_memory
        if name == "manage_memory":
            action = (args.get("action") or "").strip().lower()
            content = (args.get("content") or "").strip()
            category = (args.get("category") or "geral").strip()
            r = self.tools.run_by_marker(
                f"memory_{action}", f"{content}|{category}", user_text
            )
            return r.message or "Feito."

        # 6) run_productivity_command
        if name == "run_productivity_command":
            cmd = (args.get("command") or "").strip()
            r = self.tools.run_by_marker("productivity", cmd, user_text)
            return r.message or ("Feito." if r.ok else "Nao executado.")

        # 7) run_finance_command
        if name == "run_finance_command":
            cmd = (args.get("command") or "").strip()
            r = self.tools.run_by_marker("finance", cmd, user_text)
            return r.message or ("Feito." if r.ok else "Nao executado.")

        # 8) control_visualizer
        if name == "control_visualizer":
            cmd = (args.get("command") or "").strip()
            r = self.tools.run_by_marker("visualizer_control", cmd, user_text)
            return r.message or "Feito."
            
        # 9) whatsapp_send
        if name == "whatsapp_send":
            target = (args.get("target") or "").strip()
            msg = (args.get("message") or "").strip()
            # Bypassa confirmacao de terminal pois pedimos p/ LLM confirmar via voz
            wa = self.tools._find_tool("whatsapp")
            if not wa: return "WhatsApp indisponivel."
            r = wa.run(f"{target}|{msg}")
            return r.message or ("Enviado." if r.ok else "Falhou.")

        # 10) control_spotify
        if name == "control_spotify":
            action = (args.get("action") or "").strip().lower()
            argument = (args.get("argument") or "").strip()
            r = self.tools.run_by_marker("spotify", f"{action}|{argument}", user_text)
            return r.message or "Feito."

        # 11) manage_files
        if name == "manage_files":
            action = (args.get("action") or "").strip().lower()
            path = (args.get("path") or "").strip()
            argument = (args.get("argument") or "").strip()
            r = self.tools.run_by_marker("file_manager", f"{action}|{path}|{argument}", user_text)
            return r.message or "Feito."

        # 12) open_windows_app (Antigo manage_apps)
        if name == "open_windows_app":
            action = (args.get("action") or "").strip().lower()
            target = (args.get("target") or "").strip()
            argument = (args.get("argument") or "").strip()
            res = self.tools.run_by_marker("app_manager", f"{action}|{target}|{argument}", user_text)
            if load_settings().enable_command_logs:
                print(f"[✅ RESULT] {res.message}")
            return res.message or "Done."

        # 13) toggle_live
        if name == "toggle_live":
            enable = args.get("enable", True)
            if isinstance(enable, str):
                enable = enable.lower() in ("true", "1", "yes", "ativar")
            return self.toggle_live_mode(enable)
            return res.message or "Feito."

        # 13) delegate_to_agent
        if name == "delegate_to_agent":
            target_name = (args.get("target_agent") or "").strip()
            query = (args.get("query") or "").strip()
            if load_settings().enable_command_logs:
                print(f"[🤖 DELEGANDO] Chamando o agente '{target_name}' para: {query}")
            
            target_agent = self.agent_manager.find_agent_by_name(target_name)
            if not target_agent:
                return f"Erro: Agente '{target_name}' não encontrado no sistema."
            
            # Instancia o prompt do agente alvo
            from src.agent.prompts import build_function_calling_system_prompt
            sys_prompt = build_function_calling_system_prompt(
                target_agent.persona, [], ""
            )
            # Sem passar history grande para o delegado para economizar contexto e manter o escopo, 
            # apenas a query enviada.
            try:
                ans = self.llm.chat(system_prompt=sys_prompt, messages=[{"role": "user", "content": query}])
                # Retornamos no formato VOICE_SWAP para o main.py parsear as vozes, mas dizemos à IA atual
                # para que ela REPASSE essa resposta exatamente como a recebeu
                return f"O agente {target_name} te enviou a resposta. VOCE DEVE responder ao usuario EXATAMENTE com o texto abaixo e adicionar as tags como ele te mandou:\n<VOICE_SWAP:{target_agent.id}>{ans}</VOICE_SWAP>"
            except Exception as e:
                return f"O agente '{target_name}' falhou ao processar a resposta: {e}"

        # 14) set_ai_volume
        if name == "set_ai_volume":
            volume = (args.get("volume") or "").strip()
            if self.tts:
                self.tts.set_volume(volume)
                return f"Volume da minha voz ajustado para {volume}."
            return "Serviço de voz indisponível."

        # 15) agent_task — Planner + Executor pipeline
        if name == "agent_task":
            goal = (args.get("goal") or "").strip()
            if not goal:
                return "Objetivo não especificado."
            from src.agent.planner import execute_plan
            try:
                result = execute_plan(
                    goal=goal,
                    llm_service=self.llm,
                    execute_tool_fn=lambda tool_name, params: self._execute_function_tool(
                        tool_name, params, goal
                    ),
                )
                return result
            except Exception as e:
                return f"Tarefa falhou: {e}"

        # 16) save_memory — Memória estruturada silenciosa
        if name == "save_memory":
            category = (args.get("category") or "notes").strip()
            key = (args.get("key") or "").strip()
            value = (args.get("value") or "").strip()
            if key and value:
                from src.memory.structured_memory import update_structured_memory
                update_structured_memory({category: {key: {"value": value}}})
                print(f"[Memory] 💾 save_memory: {category}/{key} = {value}")
                # Log no heartbeat diário
                try:
                    from src.services.heartbeat import append_daily_log
                    append_daily_log(f"Memória salva: {category}/{key} = {value}")
                except Exception:
                    pass
            return "ok"

        # Fallback para Skills Dinâmicas e Novas Ferramentas
        dynamic_tool = self.tools._find_tool(name)
        if dynamic_tool:
            try:
                if hasattr(dynamic_tool, "execute"):
                    return dynamic_tool.execute(args, context={"llm": self.llm, "vision": self.vision})
                return dynamic_tool.run(str(args)).message
            except Exception as e:
                return f"Erro ao executar a ferramenta '{name}': {e}"

        return f"Funcao desconhecida: {name}"
    def _handle_open_or_run(self, target: str, user_text: str) -> str:
        """Roteia open_or_run para o marker correto baseado no target."""
        t = target.lower()
        if t in ("notepad", "bloco de notas"):
            r = self.tools.run_by_marker("notepad", None, user_text)
        elif t in ("browser", "navegador"):
            r = self.tools.run_by_marker("open_browser", None, user_text)
        elif target.startswith(("http://", "https://", "www.")) or "." in target.split("/")[0]:
            r = self.tools.run_by_marker("open_browser_url", target, user_text)
        elif any(kw in t for kw in ("alarme", "alarm")):
            r = self.tools.run_by_marker("desktop", target, user_text)
        else:
            # Tenta como nome de app; se tiver espaco e parecer busca, abre no Google.
            if " " in target and not any(c in t for c in (".", "\\", "/")):
                r = self.tools.run_by_marker("open_browser_url", target, user_text)
            else:
                r = self.tools.run_by_marker("open_app", target, user_text)
        return r.message or ("Feito." if r.ok else "Nao executado.")

    def _handle_utility(self, action: str, argument: str, detail: str, user_text: str) -> str:
        """Roteia run_utility para o marker correto baseado na acao."""
        # Clipboard
        if action == "clipboard_read":
            r = self.tools.run_by_marker("clipboard_read", None, user_text)
        elif action == "clipboard_write":
            r = self.tools.run_by_marker("clipboard_write", argument, user_text)
        # Timer
        elif action == "timer_set":
            r = self.tools.run_by_marker("timer_set", f"{argument}|{detail}", user_text)
        elif action == "timer_list":
            r = self.tools.run_by_marker("timer_list", None, user_text)
        # System Info
        elif action == "system_info":
            r = self.tools.run_by_marker("system_info", None, user_text)
        # Media Control
        elif action in (
            "volume_up", "volume_down", "mute", "unmute",
            "play_pause", "play", "pause", "next", "previous", "stop",
        ):
            r = self.tools.run_by_marker("media_control", action, user_text)
        # Notes
        elif action == "note_save":
            r = self.tools.run_by_marker("note_save", f"{argument}|{detail}", user_text)
        elif action == "note_list":
            r = self.tools.run_by_marker("note_list", None, user_text)
        elif action == "note_search":
            r = self.tools.run_by_marker("note_search", argument, user_text)
        elif action == "note_delete":
            r = self.tools.run_by_marker("note_delete", argument, user_text)
        else:
            return f"Acao de utilitario desconhecida: {action}"
        return r.message or "Feito."

    @staticmethod
    def _vision_context(user_text: str, speakable: str) -> str:
        s = (speakable or "").strip()
        if s:
            return f"{user_text.strip()}\n\nInstrucoes adicionais da assistente (voz): {s}"
        return user_text.strip()

    # ── Multi-Agent Modes (Fase 3.2) ──

    def _chat_as_agent(self, agent_profile, text: str, extra_context: str = "") -> str:
        """Chat simples como um agente específico (sem function calling/tools)."""
        prompt = text
        if extra_context:
            prompt = f"{extra_context}\n\nUsuário: {text}"
        response = self.llm.chat(
            system_prompt=agent_profile.persona,
            messages=[{"role": "user", "content": prompt}]
        )
        return (response or "Sem resposta.").strip()

    def handle_round_robin(self, text: str, agent_ids: list[str], chained: bool = False):
        """Fase 3.2.1 — Cada agente responde em sequência (Generator para baixa latência)."""
        context_chain = ""
        for aid in agent_ids:
            ag = self.agent_manager._agents.get(aid)
            if not ag:
                continue
            extra = ""
            if chained and context_chain:
                extra = f"[Respostas dos agentes anteriores:\n{context_chain}]\nAgora é sua vez."
            resp = self._chat_as_agent(ag, text, extra)
            context_chain += f"{ag.name}: {resp}\n\n"
            print(f"[Round-Robin] {ag.name} respondeu.")
            yield {"agent_id": ag.id, "name": ag.name, "response": resp}

    def handle_debate(self, topic: str, agent_ids: list[str], rounds: int = 3):
        """Fase 3.2.2 — Os agentes debatem um tema entre si (Generator para baixa latência)."""
        history = f"Tema do debate: {topic}"
        for r in range(rounds):
            for aid in agent_ids:
                ag = self.agent_manager._agents.get(aid)
                if not ag:
                    continue
                extra = f"{history}\n\n[Rodada {r+1}] É sua vez de argumentar. Seja conciso (max 3 parágrafos)."
                resp = self._chat_as_agent(ag, topic, extra)
                history += f"\n\n{ag.name} (Rodada {r+1}): {resp}"
                print(f"[Debate] Rodada {r+1} — {ag.name} respondeu.")
                yield {"agent_id": ag.id, "name": ag.name, "response": resp, "round": r + 1}

    def toggle_live_mode(self, enable: bool) -> str:
        """Ativa ou desativa o modo de conversa em tempo real (Gemini Live)."""
        import os
        import asyncio
        import threading

        if enable == self.is_live_mode:
            return f"O modo Live já está {'ativado' if enable else 'desativado'}."

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "Erro: Chave GEMINI_API_KEY não encontrada no .env."

        if enable:
            try:
                self.live_service = GeminiLiveService(
                    api_key=api_key, 
                    tool_registry=self.tools,
                    visualizer=self.tools._find_tool("visualizer_control") # Tenta vincular o visualizer
                )
                self.is_live_mode = True
                
                # Inicia o loop do Live em uma thread separada para não travar o app
                def run_live():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.live_service.start())

                self._live_thread = threading.Thread(target=run_live, daemon=True)
                self._live_thread.start()
                
                return "Modo Live ativado, Sir. A partir de agora estou ouvindo você em tempo real."
            except Exception as e:
                self.is_live_mode = False
                return f"Falha ao ativar modo Live: {e}"
        else:
            if self.live_service:
                self.live_service.stop()
            self.is_live_mode = False
            return "Modo Live desativado. Voltando ao protocolo de comunicação padrão."
