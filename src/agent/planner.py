"""
Planner + Executor + Error Handler — Pipeline autônomo inspirado no Mark-XXXV.
Decompõe tarefas complexas em passos, executa com retry e replan automático.
"""

from __future__ import annotations

import json
import re
import time
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


# ═══════════════════════════════════════════════════════════════════════════════
# Error Handler
# ═══════════════════════════════════════════════════════════════════════════════

class ErrorDecision(Enum):
    RETRY  = "retry"
    SKIP   = "skip"
    REPLAN = "replan"
    ABORT  = "abort"


def analyze_error(step: dict, error: str, attempt: int, max_attempts: int = 2) -> dict:
    """Analisa um erro e decide o que fazer: retry, skip, replan ou abort."""
    if attempt >= max_attempts:
        return {
            "decision": ErrorDecision.REPLAN,
            "reason": f"Falhou {attempt} vezes: {error[:100]}",
            "user_message": "Tentando outra abordagem.",
        }

    # Heurísticas simples para decisão rápida sem gastar API
    error_lower = error.lower()

    # Erros transitórios → retry
    transient = ["timeout", "connection", "429", "rate limit", "temporary", "socket"]
    if any(t in error_lower for t in transient):
        return {
            "decision": ErrorDecision.RETRY,
            "reason": f"Erro transitório: {error[:100]}",
            "user_message": "Tentando novamente...",
        }

    # Erros fatais → abort
    fatal = ["permission denied", "access denied", "not found", "invalid api", "authentication"]
    if any(f in error_lower for f in fatal):
        return {
            "decision": ErrorDecision.ABORT,
            "reason": f"Erro fatal: {error[:100]}",
            "user_message": "Não foi possível completar essa tarefa.",
        }

    # Se o step não é crítico → skip
    if not step.get("critical", True):
        return {
            "decision": ErrorDecision.SKIP,
            "reason": f"Step não crítico falhou: {error[:100]}",
            "user_message": "Pulando esse passo.",
        }

    # Default → replan
    return {
        "decision": ErrorDecision.REPLAN,
        "reason": f"Erro inesperado: {error[:100]}",
        "user_message": "Ajustando a abordagem.",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Planner
# ═══════════════════════════════════════════════════════════════════════════════

PLANNER_PROMPT = """Você é o módulo de planejamento de uma assistente IA.
Sua função: decompor qualquer objetivo do usuário em uma sequência de passos usando APENAS as ferramentas disponíveis.

FERRAMENTAS DISPONÍVEIS:
- search_web: pesquisa na internet (query)
- analyze_screen: captura e analisa a tela (instruction)
- manage_files: gerencia arquivos (action, path, argument)
- open_windows_app: abre/fecha apps (action, target)
- run_utility: clipboard, timer, notas, volume (action, argument, detail)
- manage_memory: salva/busca fatos do usuário (action, content, category)
- control_spotify: controle do Spotify (action, argument)
- create_python_skill: cria/lê/edita skills Python (action, filename, code)
- code_helper: escreve, edita, executa código (action, description, language, file_path)

REGRAS:
- Máximo 5 passos. Use o mínimo necessário.
- Cada passo é independente. Não referencie resultados de passos anteriores nos parâmetros.
- Retorne APENAS JSON válido, sem markdown, sem explicação.

FORMATO:
{
  "goal": "...",
  "steps": [
    {
      "step": 1,
      "tool": "tool_name",
      "description": "o que este passo faz",
      "parameters": {},
      "critical": true
    }
  ]
}"""


def create_plan(goal: str, llm_service, context: str = "") -> dict:
    """Cria um plano de execução para um objetivo complexo."""
    user_input = f"Objetivo: {goal}"
    if context:
        user_input += f"\n\nContexto: {context}"

    try:
        response = llm_service.chat(
            system_prompt=PLANNER_PROMPT,
            messages=[{"role": "user", "content": user_input}]
        )
        if not response:
            return _fallback_plan(goal)

        text = response.strip()
        text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
        plan = json.loads(text)

        if "steps" not in plan or not isinstance(plan["steps"], list):
            raise ValueError("Estrutura de plano inválida")

        print(f"[Planner] ✅ Plano: {len(plan['steps'])} passos")
        for s in plan["steps"]:
            print(f"  Passo {s['step']}: [{s['tool']}] {s['description']}")

        return plan

    except json.JSONDecodeError as e:
        print(f"[Planner] ⚠️ Falha ao parsear JSON: {e}")
        return _fallback_plan(goal)
    except Exception as e:
        print(f"[Planner] ⚠️ Planejamento falhou: {e}")
        return _fallback_plan(goal)


def _fallback_plan(goal: str) -> dict:
    """Plano fallback: pesquisar na web."""
    print("[Planner] 🔄 Usando plano fallback")
    return {
        "goal": goal,
        "steps": [
            {
                "step": 1,
                "tool": "search_web",
                "description": f"Pesquisar: {goal}",
                "parameters": {"query": goal},
                "critical": True
            }
        ]
    }


def replan(goal: str, completed_steps: list, failed_step: dict, error: str, llm_service) -> dict:
    """Cria um plano revisado após falha."""
    completed_summary = "\n".join(
        f"  - Passo {s['step']} ({s['tool']}): FEITO" for s in completed_steps
    )

    prompt = f"""Objetivo: {goal}

Já completados:
{completed_summary if completed_summary else '  (nenhum)'}

Passo que falhou: [{failed_step.get('tool')}] {failed_step.get('description')}
Erro: {error}

Crie um plano REVISADO para o trabalho restante. Não repita passos já concluídos."""

    try:
        response = llm_service.chat(
            system_prompt=PLANNER_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )
        if not response:
            return _fallback_plan(goal)

        text = response.strip()
        text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
        plan = json.loads(text)

        print(f"[Planner] 🔄 Plano revisado: {len(plan.get('steps', []))} passos")
        return plan
    except Exception as e:
        print(f"[Planner] ⚠️ Replanejamento falhou: {e}")
        return _fallback_plan(goal)


# ═══════════════════════════════════════════════════════════════════════════════
# Executor
# ═══════════════════════════════════════════════════════════════════════════════

MAX_REPLAN_ATTEMPTS = 2


def execute_plan(
    goal: str,
    llm_service,
    execute_tool_fn: Callable[[str, dict], str],
    on_status: Callable[[str], None] | None = None,
    cancel_flag: threading.Event | None = None,
) -> str:
    """
    Executa um plano completo com retry, error handling e replan.
    
    Args:
        goal: Objetivo do usuário
        llm_service: Instância do LLMService para o planner
        execute_tool_fn: Função que executa uma ferramenta (name, args) -> result
        on_status: Callback para status updates
        cancel_flag: Event para cancelamento
    
    Returns:
        Resultado final em texto
    """
    if on_status:
        on_status(f"Planejando: {goal[:60]}...")

    plan = create_plan(goal, llm_service)
    replan_attempts = 0
    completed_steps = []
    step_results = {}

    while True:
        steps = plan.get("steps", [])
        if not steps:
            msg = "Não consegui criar um plano válido para essa tarefa."
            if on_status:
                on_status(msg)
            return msg

        success = True
        failed_step = None
        failed_error = ""

        for step in steps:
            if cancel_flag and cancel_flag.is_set():
                return "Tarefa cancelada."

            step_num = step.get("step", "?")
            tool = step.get("tool", "search_web")
            desc = step.get("description", "")
            params = step.get("parameters", {})

            if on_status:
                on_status(f"▶️ Passo {step_num}: {desc[:60]}")

            print(f"\n[Executor] ▶️ Passo {step_num}: [{tool}] {desc}")

            attempt = 1
            step_ok = False

            while attempt <= 3:
                if cancel_flag and cancel_flag.is_set():
                    return "Tarefa cancelada."
                try:
                    result = execute_tool_fn(tool, params)
                    step_results[step_num] = result
                    completed_steps.append(step)
                    print(f"[Executor] ✅ Passo {step_num} ok: {str(result)[:100]}")
                    step_ok = True
                    break

                except Exception as e:
                    error_msg = str(e)
                    print(f"[Executor] ❌ Passo {step_num} tentativa {attempt} falhou: {error_msg}")

                    recovery = analyze_error(step, error_msg, attempt)
                    decision = recovery["decision"]

                    if on_status and recovery.get("user_message"):
                        on_status(recovery["user_message"])

                    if decision == ErrorDecision.RETRY:
                        attempt += 1
                        time.sleep(2)
                        continue
                    elif decision == ErrorDecision.SKIP:
                        print(f"[Executor] ⏭️ Pulando passo {step_num}")
                        completed_steps.append(step)
                        step_ok = True
                        break
                    elif decision == ErrorDecision.ABORT:
                        return f"Tarefa abortada. {recovery.get('reason', '')}"
                    else:  # REPLAN
                        failed_step = step
                        failed_error = error_msg
                        success = False
                        break

            if not step_ok and not failed_step:
                failed_step = step
                failed_error = "Máximo de tentativas excedido"
                success = False

            if not success:
                break

        if success:
            # Gera resumo dos resultados
            return _summarize_results(goal, completed_steps, step_results, llm_service)

        if replan_attempts >= MAX_REPLAN_ATTEMPTS:
            return f"Tarefa falhou após {replan_attempts} tentativas de replanejamento."

        if on_status:
            on_status("Ajustando abordagem...")

        replan_attempts += 1
        plan = replan(goal, completed_steps, failed_step, failed_error, llm_service)


def _summarize_results(goal: str, completed_steps: list, step_results: dict, llm_service) -> str:
    """Gera um resumo dos resultados da execução."""
    fallback = f"Concluído. {len(completed_steps)} passos executados para: {goal[:60]}."

    # Coleta resultados relevantes
    results_text = ""
    for step_num, result in step_results.items():
        if result and len(str(result)) > 20:
            results_text += f"\n--- Resultado passo {step_num} ---\n{str(result)[:500]}\n"

    if results_text:
        try:
            summary = llm_service.chat(
                system_prompt="Você é um assistente conciso. Responda em 1-3 frases curtas em português.",
                messages=[{
                    "role": "user",
                    "content": (
                        f'Objetivo: "{goal}"\n'
                        f"Resultados obtidos:\n{results_text}\n\n"
                        "Resuma o que foi realizado de forma natural e direta."
                    )
                }]
            )
            if summary and len(summary) > 10:
                return summary.strip()
        except Exception:
            pass

    return fallback


# ═══════════════════════════════════════════════════════════════════════════════
# Task Queue
# ═══════════════════════════════════════════════════════════════════════════════

class TaskStatus(Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    LOW    = 3
    NORMAL = 2
    HIGH   = 1


@dataclass(order=True)
class Task:
    priority:    int
    created_at:  float = field(compare=False)
    task_id:     str   = field(compare=False)
    goal:        str   = field(compare=False)
    status:      TaskStatus = field(compare=False, default=TaskStatus.PENDING)
    result:      Any        = field(compare=False, default=None)
    error:       str        = field(compare=False, default="")
    cancel_flag: threading.Event = field(compare=False, default_factory=threading.Event)


class AgentTaskQueue:
    """Fila de tarefas com prioridade, cancelamento e execução em background."""

    def __init__(self, max_concurrent: int = 1):
        self._queue: list[Task] = []
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._tasks: dict[str, Task] = {}
        self._running = False
        self._worker_thread: threading.Thread | None = None
        self._max_concurrent = max_concurrent
        self._active_count = 0
        self._execute_fn: Callable | None = None
        self._llm_service = None

    def configure(self, llm_service, execute_tool_fn: Callable):
        """Configura o LLM e a função de execução de ferramentas."""
        self._llm_service = llm_service
        self._execute_fn = execute_tool_fn

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop, daemon=True, name="AgentTaskQueue"
        )
        self._worker_thread.start()
        print("[TaskQueue] ✅ Iniciado")

    def stop(self) -> None:
        self._running = False
        with self._condition:
            self._condition.notify_all()
        print("[TaskQueue] 🔴 Parado")

    def submit(
        self,
        goal: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        on_complete: Callable | None = None,
    ) -> str:
        task_id = str(uuid.uuid4())[:8]
        task = Task(
            priority=priority.value,
            created_at=time.time(),
            task_id=task_id,
            goal=goal,
        )

        with self._condition:
            self._queue.append(task)
            self._queue.sort(key=lambda t: (t.priority, t.created_at))
            self._tasks[task_id] = task
            self._condition.notify()

        print(f"[TaskQueue] 📥 Tarefa enfileirada: [{task_id}] {goal[:60]}")
        return task_id

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                return False
            task.cancel_flag.set()
            task.status = TaskStatus.CANCELLED
            print(f"[TaskQueue] 🚫 Tarefa cancelada: [{task_id}]")
            return True

    def get_status(self, task_id: str) -> dict | None:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None
            return {
                "task_id": task.task_id,
                "goal": task.goal,
                "status": task.status.value,
                "result": task.result,
                "error": task.error,
            }

    def get_all_statuses(self) -> list[dict]:
        with self._lock:
            return [
                {"task_id": t.task_id, "goal": t.goal[:50], "status": t.status.value}
                for t in self._tasks.values()
            ]

    def pending_count(self) -> int:
        with self._lock:
            return sum(1 for t in self._queue if t.status == TaskStatus.PENDING)

    def _worker_loop(self) -> None:
        while self._running:
            task = None
            with self._condition:
                while self._running and not self._next_task():
                    self._condition.wait(timeout=1.0)
                task = self._next_task()
                if task:
                    task.status = TaskStatus.RUNNING
                    self._active_count += 1
                    try:
                        self._queue.remove(task)
                    except ValueError:
                        pass

            if task:
                threading.Thread(
                    target=self._run_task, args=(task,),
                    daemon=True, name=f"AgentTask-{task.task_id}"
                ).start()

    def _next_task(self) -> Task | None:
        if self._active_count >= self._max_concurrent:
            return None
        for task in self._queue:
            if task.status == TaskStatus.PENDING and not task.cancel_flag.is_set():
                return task
        return None

    def _run_task(self, task: Task) -> None:
        print(f"[TaskQueue] ▶️ Executando: [{task.task_id}] {task.goal[:60]}")
        try:
            if not self._llm_service or not self._execute_fn:
                raise RuntimeError("TaskQueue não configurado. Chame configure() primeiro.")

            result = execute_plan(
                goal=task.goal,
                llm_service=self._llm_service,
                execute_tool_fn=self._execute_fn,
                cancel_flag=task.cancel_flag,
            )

            with self._lock:
                if task.cancel_flag.is_set():
                    task.status = TaskStatus.CANCELLED
                else:
                    task.status = TaskStatus.COMPLETED
                    task.result = result
                self._active_count -= 1

            print(f"[TaskQueue] ✅ Concluído: [{task.task_id}]")

        except Exception as e:
            with self._lock:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                self._active_count -= 1
            print(f"[TaskQueue] ❌ Falhou: [{task.task_id}] {e}")

        with self._condition:
            self._condition.notify()
