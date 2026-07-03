import re
from pathlib import Path

content = Path('src/core/interaction_loop.py').read_text(encoding='utf-8')

# 1. Add background task method
background_method = '''
    def _start_background_task(self, goal: str, speaker_name: str):
        self._add_chat("assistant", "Jarvis", f"? Iniciando tarefa em background: {goal}")
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
                self._add_chat("assistant", "Jarvis (Background)", f"? Tarefa concluída: {result}")
                if self.tts:
                    self.tts.speak("A tarefa em background foi concluída.")
            except Exception as e:
                self._add_chat("assistant", "Jarvis (Background)", f"? Erro na tarefa: {e}")
                
        threading.Thread(target=_bg_worker, daemon=True).start()
'''

if '_start_background_task' not in content:
    # insert before _process_and_respond
    content = content.replace('def _process_and_respond(self, text: str, source: str = ""):', background_method + '\n    def _process_and_respond(self, text: str, source: str = ""):')

# 2. Intercept /task inside _process_and_respond
task_interceptor = '''
        if text.lower().startswith("/task "):
            goal = text[6:].strip()
            self._start_background_task(goal, speaker_name)
            return
'''

if '/task' not in content:
    # insert inside _process_and_respond, after getting speaker_name
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if 'called_agent_id, cleaned_text = self._detect_agent_by_name(text)' in line:
            lines.insert(i, task_interceptor)
            break
    content = '\n'.join(lines)

Path('src/core/interaction_loop.py').write_text(content, encoding='utf-8')
print("Patched interaction_loop.py successfully.")
