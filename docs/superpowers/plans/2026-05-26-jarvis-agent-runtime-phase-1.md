# Jarvis Agent Runtime Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first runtime layer that lets Jarvis infer modes automatically, expose only relevant tools, and block repeated/no-progress tool loops.

**Architecture:** Keep `AgentOrchestrator` as the compatibility shell. Add focused runtime modules for mode resolution, toolset selection, schema filtering, tool guardrails, and action execution. Integrate them incrementally so Gemini, NVIDIA, Groq, and marker fallback can keep using the existing tools.

**Tech Stack:** Python 3.11, pytest, existing `google.genai.types` schemas, existing `ToolRegistry`, existing Nexus and desktop tools.

---

## File Structure

- Create `src/agent/runtime_modes.py`
  - Owns lightweight dataclasses/enums used by the runtime.
- Create `src/agent/mode_resolver.py`
  - Deterministic intent-to-mode classifier. No LLM call.
- Create `src/agent/toolsets.py`
  - Maps modes to allowed built-in function tools and dynamic tools.
- Create `src/agent/tool_guardrails.py`
  - Provider-neutral guardrail controller for repeated calls and no-progress loops.
- Create `src/agent/action_executor.py`
  - Checks allowed tools and guardrails before delegating to the existing executor.
- Modify `src/agent/gemini_tools.py`
  - Add optional `allowed_tool_names` filtering to Gemini/OpenAI schema builders.
- Modify `src/agent/prompts.py`
  - Add an active mode/toolset block to function-calling prompts.
- Modify `src/agent/orchestrator.py`
  - Resolve mode, select tools, filter schemas, reset guardrails per turn, and route function calls through `ActionExecutor`.
- Test `tests/test_agent_runtime_modes.py`
  - Mode inference and toolset selection.
- Test `tests/test_agent_runtime_tool_schemas.py`
  - Gemini/OpenAI tool schema filtering.
- Test `tests/test_agent_tool_guardrails.py`
  - Repeated calls and no-progress protection.
- Test `tests/test_agent_action_executor.py`
  - Allowed-tool enforcement and guardrail integration.
- Extend `tests/test_gemini_tools.py`
  - Preserve default schema behavior while proving filtered mode behavior.

---

### Task 1: Runtime Models And Mode Resolver

**Files:**
- Create: `src/agent/runtime_modes.py`
- Create: `src/agent/mode_resolver.py`
- Create: `tests/test_agent_runtime_modes.py`

- [ ] **Step 1: Write failing mode resolver tests**

Create `tests/test_agent_runtime_modes.py`:

```python
from __future__ import annotations

from src.agent.mode_resolver import ModeResolver
from src.agent.runtime_modes import AgentMode


def test_mode_resolver_infers_pc_mode_for_app_command():
    result = ModeResolver().resolve("Abra o Spotify e toque uma musica")

    assert result.mode == AgentMode.PC
    assert result.explicit is False
    assert result.confidence >= 0.7


def test_mode_resolver_infers_news_mode_and_visible_window():
    result = ModeResolver().resolve("Abra o modo noticias e procure sobre inteligencia artificial")

    assert result.mode == AgentMode.NEWS
    assert result.explicit is True
    assert result.open_window is True


def test_mode_resolver_infers_psych_coach_mode():
    result = ModeResolver().resolve("Quero conversar sobre meu dia, estou bem desanimado")

    assert result.mode == AgentMode.PSYCH_COACH
    assert result.reason


def test_mode_resolver_marks_destructive_file_request_as_risky():
    result = ModeResolver().resolve("Limpa e apaga essa pasta de downloads")

    assert result.mode == AgentMode.FILES
    assert result.risky is True


def test_mode_resolver_defaults_short_greeting_to_chat():
    result = ModeResolver().resolve("oi")

    assert result.mode == AgentMode.CHAT
    assert result.confidence == 1.0
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest tests\test_agent_runtime_modes.py -q
```

Expected: fail because `src.agent.mode_resolver` does not exist.

- [ ] **Step 3: Add runtime model types**

Create `src/agent/runtime_modes.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class AgentMode(StrEnum):
    CHAT = "chat"
    PC = "pc"
    NEXUS = "nexus"
    NEWS = "news"
    PSYCH_COACH = "psych_coach"
    WORKFLOW = "workflow"
    FILES = "files"
    WEB = "web"
    VISION = "vision"


@dataclass(frozen=True)
class ModeResolution:
    mode: AgentMode
    confidence: float
    reason: str
    explicit: bool = False
    risky: bool = False
    open_window: bool = False


@dataclass(frozen=True)
class RuntimeContext:
    resolution: ModeResolution
    allowed_tool_names: frozenset[str] = field(default_factory=frozenset)

    @property
    def mode(self) -> AgentMode:
        return self.resolution.mode
```

- [ ] **Step 4: Add deterministic mode resolver**

Create `src/agent/mode_resolver.py`:

```python
from __future__ import annotations

import re

from src.agent.runtime_modes import AgentMode, ModeResolution


_SHORT_GREETINGS = {"oi", "ola", "olá", "hey", "hi", "hello", "bom dia", "boa tarde", "boa noite"}


def _fold(text: str) -> str:
    table = str.maketrans("áàâãäéèêëíìîïóòôõöúùûüç", "aaaaaeeeeiiiiooooouuuuc")
    return (text or "").lower().translate(table)


class ModeResolver:
    def resolve(self, text: str) -> ModeResolution:
        raw = (text or "").strip()
        folded = _fold(raw)
        compact = folded.strip(" !?.\t\r\n")

        if compact in _SHORT_GREETINGS:
            return ModeResolution(AgentMode.CHAT, 1.0, "short greeting")

        explicit = bool(re.search(r"\b(modo|mode|entra no modo|abr(e|ir) o modo)\b", folded))
        open_window = bool(re.search(r"\b(abre|abrir|mostra|mostrar|janela|painel|modo)\b", folded))

        if self._has_any(folded, ["noticia", "noticias", "manchete", "jornal", "briefing"]):
            return ModeResolution(AgentMode.NEWS, 0.95 if explicit else 0.82, "news keywords", explicit, False, open_window)

        if self._has_any(folded, ["psicologo", "terapia", "coach", "motivacional", "desanimado", "ansioso", "triste", "meu dia"]):
            return ModeResolution(AgentMode.PSYCH_COACH, 0.82, "psych/coach keywords", explicit, False, False)

        if self._has_any(folded, ["workflow", "rotina", "modo estudo", "modo dormir", "gravar", "salve isso como"]):
            return ModeResolution(AgentMode.WORKFLOW, 0.86, "workflow keywords", explicit, False, open_window)

        if self._has_any(folded, ["arquivo", "pasta", "downloads", "documentos", "apaga", "delete", "deleta", "limpa"]):
            risky = self._has_any(folded, ["apaga", "delete", "deleta", "remove", "limpa", "sobrescreve"])
            return ModeResolution(AgentMode.FILES, 0.82, "file keywords", explicit, risky, False)

        if self._has_any(folded, ["abre", "abrir", "fecha", "fechar", "spotify", "chrome", "notepad", "bloco de notas", "clipboard", "area de transferencia"]):
            return ModeResolution(AgentMode.PC, 0.78, "pc/app keywords", explicit, False, open_window)

        if self._has_any(folded, ["habito", "habitos", "treino", "flexao", "financa", "gasto", "receita", "nota", "flashcard", "quiz", "enem", "loja", "xp"]):
            return ModeResolution(AgentMode.NEXUS, 0.78, "nexus keywords", explicit, False, open_window)

        if self._has_any(folded, ["pesquise", "pesquisar", "procure", "buscar", "clima", "cotacao"]):
            return ModeResolution(AgentMode.WEB, 0.72, "web/search keywords", explicit, False, False)

        if self._has_any(folded, ["tela", "monitor", "o que voce ve", "o que aparece"]):
            return ModeResolution(AgentMode.VISION, 0.76, "vision keywords", explicit, False, False)

        return ModeResolution(AgentMode.CHAT, 0.55, "default chat")

    @staticmethod
    def _has_any(text: str, needles: list[str]) -> bool:
        return any(needle in text for needle in needles)
```

- [ ] **Step 5: Run GREEN**

Run:

```powershell
python -m pytest tests\test_agent_runtime_modes.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit Task 1**

Run:

```powershell
git add src\agent\runtime_modes.py src\agent\mode_resolver.py tests\test_agent_runtime_modes.py
git commit -m "feat: add Jarvis runtime mode resolver"
```

---

### Task 2: Toolset Selector

**Files:**
- Create: `src/agent/toolsets.py`
- Modify: `tests/test_agent_runtime_modes.py`

- [ ] **Step 1: Add failing toolset tests**

Append to `tests/test_agent_runtime_modes.py`:

```python
from src.agent.toolsets import ToolsetSelector


def test_toolset_selector_limits_chat_tools():
    resolution = ModeResolver().resolve("oi")
    allowed = ToolsetSelector().allowed_tools(resolution)

    assert "analyze_screen" not in allowed
    assert "manage_files" not in allowed
    assert "save_memory" in allowed


def test_toolset_selector_news_keeps_visible_window_path():
    resolution = ModeResolver().resolve("Abra o modo noticias e procure sobre IA")
    allowed = ToolsetSelector().allowed_tools(resolution)

    assert "nexus_command" in allowed
    assert "search_web" in allowed
    assert "manage_files" not in allowed


def test_toolset_selector_pc_exposes_app_and_clipboard_tools():
    resolution = ModeResolver().resolve("Abra o bloco de notas e copie o resumo")
    allowed = ToolsetSelector().allowed_tools(resolution)

    assert "open_windows_app" in allowed
    assert "run_utility" in allowed
    assert "nexus_command" not in allowed


def test_toolset_selector_psych_coach_excludes_desktop_mutation():
    resolution = ModeResolver().resolve("Estou triste, quero conversar como psicologo")
    allowed = ToolsetSelector().allowed_tools(resolution)

    assert "nexus_command" in allowed
    assert "manage_memory" in allowed
    assert "open_windows_app" not in allowed
    assert "whatsapp_send" not in allowed
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest tests\test_agent_runtime_modes.py -q
```

Expected: fail because `src.agent.toolsets` does not exist.

- [ ] **Step 3: Add toolset selector**

Create `src/agent/toolsets.py`:

```python
from __future__ import annotations

from src.agent.runtime_modes import AgentMode, ModeResolution


BASE_SAFE_TOOLS = frozenset({"save_memory", "manage_memory"})

MODE_TOOLSETS: dict[AgentMode, frozenset[str]] = {
    AgentMode.CHAT: BASE_SAFE_TOOLS,
    AgentMode.PC: frozenset({
        "open_windows_app",
        "run_utility",
        "control_spotify",
        "analyze_screen",
        "search_web",
        "control_visualizer",
    }),
    AgentMode.NEXUS: frozenset({
        "nexus_command",
        "run_finance_command",
        "run_productivity_command",
        "manage_memory",
        "save_memory",
        "control_visualizer",
    }),
    AgentMode.NEWS: frozenset({
        "nexus_command",
        "search_web",
        "manage_memory",
        "save_memory",
        "control_visualizer",
    }),
    AgentMode.PSYCH_COACH: frozenset({
        "nexus_command",
        "manage_memory",
        "save_memory",
        "run_productivity_command",
        "control_visualizer",
    }),
    AgentMode.WORKFLOW: frozenset({
        "nexus_command",
        "open_windows_app",
        "run_utility",
        "control_spotify",
        "analyze_screen",
        "search_web",
        "control_visualizer",
        "manage_memory",
        "save_memory",
    }),
    AgentMode.FILES: frozenset({
        "manage_files",
        "analyze_screen",
        "manage_memory",
        "save_memory",
        "control_visualizer",
    }),
    AgentMode.WEB: frozenset({
        "search_web",
        "manage_memory",
        "save_memory",
        "control_visualizer",
    }),
    AgentMode.VISION: frozenset({
        "analyze_screen",
        "manage_memory",
        "save_memory",
        "control_visualizer",
    }),
}


class ToolsetSelector:
    def allowed_tools(self, resolution: ModeResolution) -> frozenset[str]:
        tools = set(MODE_TOOLSETS.get(resolution.mode, BASE_SAFE_TOOLS))
        if resolution.risky:
            tools.add("control_visualizer")
        return frozenset(tools)
```

- [ ] **Step 4: Run GREEN**

Run:

```powershell
python -m pytest tests\test_agent_runtime_modes.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 2**

Run:

```powershell
git add src\agent\toolsets.py tests\test_agent_runtime_modes.py
git commit -m "feat: add Jarvis mode toolsets"
```

---

### Task 3: Filter Gemini And OpenAI Tool Schemas

**Files:**
- Create: `tests/test_agent_runtime_tool_schemas.py`
- Modify: `src/agent/gemini_tools.py`
- Modify: `tests/test_gemini_tools.py`

- [ ] **Step 1: Write failing schema filter tests**

Create `tests/test_agent_runtime_tool_schemas.py`:

```python
from __future__ import annotations

from src.agent.gemini_tools import build_agent_tool, build_openai_agent_tools


def _gemini_names(allowed: set[str]) -> set[str]:
    tool = build_agent_tool(allowed_tool_names=allowed)
    return {fd.name for fd in (tool.function_declarations or [])}


def _openai_names(allowed: set[str]) -> set[str]:
    return {item["function"]["name"] for item in build_openai_agent_tools(allowed_tool_names=allowed)}


def test_gemini_schema_filters_to_news_tools():
    names = _gemini_names({"nexus_command", "search_web", "save_memory"})

    assert names == {"nexus_command", "search_web", "save_memory"}


def test_openai_schema_filters_to_pc_tools():
    names = _openai_names({"open_windows_app", "run_utility", "control_spotify"})

    assert "open_windows_app" in names
    assert "run_utility" in names
    assert "control_spotify" in names
    assert "nexus_command" not in names
    assert "manage_files" not in names


def test_schema_filter_none_preserves_default_behavior():
    all_names = _openai_names(set())
    default_names = {item["function"]["name"] for item in build_openai_agent_tools()}

    assert all_names == set()
    assert "nexus_command" in default_names
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest tests\test_agent_runtime_tool_schemas.py -q
```

Expected: fail because `allowed_tool_names` is not accepted.

- [ ] **Step 3: Add schema filter helpers**

Modify `src/agent/gemini_tools.py`.

Change:

```python
def build_agent_tool(dynamic_tools: list = None) -> types.Tool:
```

to:

```python
def build_agent_tool(dynamic_tools: list = None, allowed_tool_names: set[str] | frozenset[str] | None = None) -> types.Tool:
```

After the dynamic tool loop, before the return, add:

```python
    if allowed_tool_names is not None:
        allowed = set(allowed_tool_names)
        declarations = [fd for fd in declarations if fd.name in allowed]

    return types.Tool(function_declarations=declarations)
```

Inside the dynamic tool loop, before duplicate checks, add:

```python
            if allowed_tool_names is not None and tool.name not in allowed_tool_names:
                continue
```

Change:

```python
def build_openai_agent_tools(dynamic_tools: list = None) -> list[dict]:
```

to:

```python
def build_openai_agent_tools(dynamic_tools: list = None, allowed_tool_names: set[str] | frozenset[str] | None = None) -> list[dict]:
```

Inside the dynamic tool loop, before appending, add:

```python
            if allowed_tool_names is not None and tool.name not in allowed_tool_names:
                continue
```

Before the final return, replace:

```python
    return funcs
```

with:

```python
    if allowed_tool_names is not None:
        allowed = set(allowed_tool_names)
        funcs = [item for item in funcs if item["function"]["name"] in allowed]

    return funcs
```

- [ ] **Step 4: Add default behavior regression**

Append to `tests/test_gemini_tools.py`:

```python
def test_schema_filter_none_keeps_existing_static_tools():
    gemini = build_agent_tool()
    gemini_names = {fd.name for fd in (gemini.function_declarations or [])}
    openai_names = {t["function"]["name"] for t in build_openai_agent_tools()}

    assert "nexus_command" in gemini_names
    assert "open_windows_app" in gemini_names
    assert "nexus_command" in openai_names
```

- [ ] **Step 5: Run GREEN**

Run:

```powershell
python -m pytest tests\test_agent_runtime_tool_schemas.py tests\test_gemini_tools.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit Task 3**

Run:

```powershell
git add src\agent\gemini_tools.py tests\test_agent_runtime_tool_schemas.py tests\test_gemini_tools.py
git commit -m "feat: filter Jarvis tool schemas by mode"
```

---

### Task 4: Tool Guardrails

**Files:**
- Create: `src/agent/tool_guardrails.py`
- Create: `tests/test_agent_tool_guardrails.py`

- [ ] **Step 1: Write failing guardrail tests**

Create `tests/test_agent_tool_guardrails.py`:

```python
from __future__ import annotations

from src.agent.tool_guardrails import ToolCallGuardrailController


def test_guardrail_blocks_exact_repeated_call_after_threshold():
    guard = ToolCallGuardrailController(exact_repeat_limit=2)

    assert guard.before_call("search_web", {"query": "x"}).allow is True
    guard.after_call("search_web", {"query": "x"}, "same result")
    assert guard.before_call("search_web", {"query": "x"}).allow is True
    guard.after_call("search_web", {"query": "x"}, "same result")

    decision = guard.before_call("search_web", {"query": "x"})

    assert decision.allow is False
    assert "repetida" in decision.message.lower()


def test_guardrail_resets_per_turn():
    guard = ToolCallGuardrailController(exact_repeat_limit=1)

    guard.after_call("search_web", {"query": "x"}, "same")
    assert guard.before_call("search_web", {"query": "x"}).allow is False

    guard.reset_turn()

    assert guard.before_call("search_web", {"query": "x"}).allow is True


def test_guardrail_flags_repeated_no_progress_result():
    guard = ToolCallGuardrailController(no_progress_limit=2)

    guard.after_call("analyze_screen", {"instruction": "olhe"}, "Sem mudanca.")
    decision = guard.after_call("analyze_screen", {"instruction": "olhe"}, "Sem mudanca.")

    assert decision.allow is False
    assert "sem progresso" in decision.message.lower()
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest tests\test_agent_tool_guardrails.py -q
```

Expected: fail because `src.agent.tool_guardrails` does not exist.

- [ ] **Step 3: Add guardrail controller**

Create `src/agent/tool_guardrails.py`:

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ToolGuardrailDecision:
    allow: bool
    message: str = ""


class ToolCallGuardrailController:
    def __init__(self, exact_repeat_limit: int = 3, no_progress_limit: int = 3) -> None:
        self.exact_repeat_limit = max(1, exact_repeat_limit)
        self.no_progress_limit = max(1, no_progress_limit)
        self._call_counts: dict[str, int] = {}
        self._result_counts: dict[tuple[str, str], int] = {}

    def reset_turn(self) -> None:
        self._call_counts.clear()
        self._result_counts.clear()

    def before_call(self, tool_name: str, args: Mapping[str, Any] | None) -> ToolGuardrailDecision:
        key = self._call_key(tool_name, args)
        count = self._call_counts.get(key, 0)
        if count >= self.exact_repeat_limit:
            return ToolGuardrailDecision(False, f"Chamada repetida bloqueada: {tool_name}.")
        self._call_counts[key] = count + 1
        return ToolGuardrailDecision(True)

    def after_call(self, tool_name: str, args: Mapping[str, Any] | None, result: Any) -> ToolGuardrailDecision:
        text = self._normalize_result(result)
        result_key = (tool_name, text)
        count = self._result_counts.get(result_key, 0) + 1
        self._result_counts[result_key] = count
        if count >= self.no_progress_limit and self._looks_no_progress(text):
            return ToolGuardrailDecision(False, f"Ferramenta interrompida por resultado sem progresso: {tool_name}.")
        return ToolGuardrailDecision(True)

    @staticmethod
    def _call_key(tool_name: str, args: Mapping[str, Any] | None) -> str:
        try:
            payload = json.dumps(args or {}, sort_keys=True, ensure_ascii=False)
        except TypeError:
            payload = repr(args)
        return f"{tool_name}:{payload}"

    @staticmethod
    def _normalize_result(result: Any) -> str:
        return " ".join(str(result or "").strip().lower().split())[:500]

    @staticmethod
    def _looks_no_progress(text: str) -> bool:
        if not text:
            return True
        markers = [
            "sem mudanca",
            "sem mudança",
            "sem resultados",
            "nenhum resultado",
            "nao executado",
            "não executado",
            "falhou",
            "erro",
        ]
        return any(marker in text for marker in markers)
```

- [ ] **Step 4: Run GREEN**

Run:

```powershell
python -m pytest tests\test_agent_tool_guardrails.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 4**

Run:

```powershell
git add src\agent\tool_guardrails.py tests\test_agent_tool_guardrails.py
git commit -m "feat: add Jarvis tool guardrails"
```

---

### Task 5: Action Executor

**Files:**
- Create: `src/agent/action_executor.py`
- Create: `tests/test_agent_action_executor.py`

- [ ] **Step 1: Write failing action executor tests**

Create `tests/test_agent_action_executor.py`:

```python
from __future__ import annotations

from src.agent.action_executor import ActionExecutor
from src.agent.tool_guardrails import ToolCallGuardrailController


def test_action_executor_blocks_tool_outside_selected_toolset():
    executor = ActionExecutor(
        allowed_tool_names=frozenset({"search_web"}),
        guardrails=ToolCallGuardrailController(),
        legacy_execute=lambda name, args, user_text: "should not run",
    )

    result = executor.execute("manage_files", {"action": "delete_file"}, "apague")

    assert "bloqueada" in result.lower()


def test_action_executor_delegates_allowed_tool():
    calls = []

    executor = ActionExecutor(
        allowed_tool_names=frozenset({"search_web"}),
        guardrails=ToolCallGuardrailController(),
        legacy_execute=lambda name, args, user_text: calls.append((name, args, user_text)) or "ok",
    )

    result = executor.execute("search_web", {"query": "tempo"}, "pesquise tempo")

    assert result == "ok"
    assert calls == [("search_web", {"query": "tempo"}, "pesquise tempo")]


def test_action_executor_returns_guardrail_message_for_repeated_call():
    guardrails = ToolCallGuardrailController(exact_repeat_limit=1)
    executor = ActionExecutor(
        allowed_tool_names=frozenset({"search_web"}),
        guardrails=guardrails,
        legacy_execute=lambda name, args, user_text: "ok",
    )

    assert executor.execute("search_web", {"query": "x"}, "x") == "ok"
    result = executor.execute("search_web", {"query": "x"}, "x")

    assert "repetida" in result.lower()
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest tests\test_agent_action_executor.py -q
```

Expected: fail because `src.agent.action_executor` does not exist.

- [ ] **Step 3: Add action executor**

Create `src/agent/action_executor.py`:

```python
from __future__ import annotations

from collections.abc import Callable

from src.agent.tool_guardrails import ToolCallGuardrailController


LegacyExecute = Callable[[str, dict, str], str]


class ActionExecutor:
    def __init__(
        self,
        allowed_tool_names: frozenset[str],
        guardrails: ToolCallGuardrailController,
        legacy_execute: LegacyExecute,
    ) -> None:
        self.allowed_tool_names = allowed_tool_names
        self.guardrails = guardrails
        self.legacy_execute = legacy_execute

    def execute(self, name: str, args: dict | None, user_text: str) -> str:
        args = args or {}
        if self.allowed_tool_names and name not in self.allowed_tool_names:
            return f"Ferramenta bloqueada pelo modo atual: {name}."

        before = self.guardrails.before_call(name, args)
        if not before.allow:
            return before.message

        result = self.legacy_execute(name, args, user_text)
        after = self.guardrails.after_call(name, args, result)
        if not after.allow:
            return after.message
        return result
```

- [ ] **Step 4: Run GREEN**

Run:

```powershell
python -m pytest tests\test_agent_action_executor.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 5**

Run:

```powershell
git add src\agent\action_executor.py tests\test_agent_action_executor.py
git commit -m "feat: add Jarvis action executor"
```

---

### Task 6: Prompt Mode Context

**Files:**
- Modify: `src/agent/prompts.py`
- Create: `tests/test_agent_prompt_runtime_context.py`

- [ ] **Step 1: Write failing prompt context tests**

Create `tests/test_agent_prompt_runtime_context.py`:

```python
from __future__ import annotations

from src.agent.prompts import build_function_calling_system_prompt


def test_function_prompt_includes_active_mode_and_allowed_tools():
    prompt = build_function_calling_system_prompt(
        "Persona base",
        [],
        "",
        active_mode="news",
        allowed_tool_names=frozenset({"nexus_command", "search_web"}),
    )

    assert "Modo ativo: news" in prompt
    assert "nexus_command" in prompt
    assert "search_web" in prompt
    assert "manage_files" not in prompt.split("## Modo ativo e ferramentas")[-1]
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest tests\test_agent_prompt_runtime_context.py -q
```

Expected: fail because `active_mode` is not accepted.

- [ ] **Step 3: Extend prompt builder signature and block**

Modify `build_function_calling_system_prompt` in `src/agent/prompts.py`.

Change the signature to:

```python
def build_function_calling_system_prompt(
    base_persona: str,
    evolution_notes: list[str],
    preferences_summary: str,
    *,
    critical_confirm_enabled: bool = False,
    study_professor_mode: bool = False,
    active_mode: str | None = None,
    allowed_tool_names: frozenset[str] | set[str] | None = None,
) -> str:
```

After `build_persona_section(...)` is appended, add:

```python
    if active_mode or allowed_tool_names is not None:
        tool_list = ", ".join(sorted(allowed_tool_names or [])) or "nenhuma ferramenta de acao"
        parts.append(
            "## Modo ativo e ferramentas\n"
            f"Modo ativo: {active_mode or 'chat'}\n"
            f"Ferramentas disponiveis neste turno: {tool_list}\n"
            "Nao chame ferramentas fora desta lista. Se o pedido exigir uma ferramenta bloqueada, explique brevemente ou peca confirmacao."
        )
```

- [ ] **Step 4: Run GREEN**

Run:

```powershell
python -m pytest tests\test_agent_prompt_runtime_context.py tests\test_gemini_tools.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 6**

Run:

```powershell
git add src\agent\prompts.py tests\test_agent_prompt_runtime_context.py
git commit -m "feat: add active mode context to Jarvis prompt"
```

---

### Task 7: Orchestrator Integration

**Files:**
- Modify: `src/agent/orchestrator.py`
- Create: `tests/test_agent_orchestrator_runtime.py`

- [ ] **Step 1: Write failing integration tests with monkeypatches**

Create `tests/test_agent_orchestrator_runtime.py`:

```python
from __future__ import annotations

from src.agent.orchestrator import AgentOrchestrator


class FakeLLM:
    primary_llm_provider = "nvidia"
    nvidia_client = object()
    nvidia_model = "test-model"

    def wants_gemini_native_tools(self):
        return False

    def wants_nvidia_native_tools(self):
        return True

    def wants_groq_native_tools(self):
        return False

    def generate_embedding(self, text):
        return None

    def chat_with_openai_tools(self, **kwargs):
        self.kwargs = kwargs
        return "feito"


class FakeVision:
    pass


class FakeTools:
    tools = []


class FakeMemory:
    def __init__(self):
        self.short = []

    def add_short_term(self, role, content):
        self.short.append((role, content))

    def maybe_record_persona_note(self, text):
        pass

    def get_recent_short_term(self, limit=10):
        return [{"role": "user", "content": "Abra o modo noticias"}]

    def get_long_term(self, key, default=None):
        return default

    def should_summarize(self):
        return False


def test_orchestrator_filters_openai_tools_for_news_request(monkeypatch):
    llm = FakeLLM()
    orchestrator = AgentOrchestrator(llm, FakeVision(), FakeTools(), FakeMemory())

    monkeypatch.setattr("src.agent.orchestrator.build_proactive_context", lambda: "")
    list(orchestrator.handle_user_message("Abra o modo noticias e procure IA"))

    names = {tool["function"]["name"] for tool in llm.kwargs["tools"]}
    assert "nexus_command" in names
    assert "search_web" in names
    assert "manage_files" not in names
    assert "open_windows_app" not in names
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest tests\test_agent_orchestrator_runtime.py -q
```

Expected: fail because orchestrator does not filter tools by runtime mode.

- [ ] **Step 3: Initialize runtime collaborators**

Modify imports in `src/agent/orchestrator.py`:

```python
from src.agent.action_executor import ActionExecutor
from src.agent.mode_resolver import ModeResolver
from src.agent.tool_guardrails import ToolCallGuardrailController
from src.agent.toolsets import ToolsetSelector
```

Inside `AgentOrchestrator.__init__`, after `self._confirm_bus = confirm_bus`, add:

```python
        self._mode_resolver = ModeResolver()
        self._toolset_selector = ToolsetSelector()
        self._tool_guardrails = ToolCallGuardrailController()
```

- [ ] **Step 4: Resolve runtime context per turn**

In `handle_user_message`, after the short-greeting/function-calling booleans are computed and before `build_function_calling_system_prompt(...)`, add:

```python
        runtime_resolution = self._mode_resolver.resolve(text)
        allowed_tool_names = self._toolset_selector.allowed_tools(runtime_resolution)
        self._tool_guardrails.reset_turn()
```

Update the `build_function_calling_system_prompt(...)` call to pass:

```python
            active_mode=runtime_resolution.mode.value,
            allowed_tool_names=allowed_tool_names,
```

- [ ] **Step 5: Filter dynamic tools and schema builders**

Replace:

```python
        dynamic_tools = [t for t in self.tools.tools if hasattr(t, "parameters")]
```

with:

```python
        dynamic_tools = [
            t for t in self.tools.tools
            if hasattr(t, "parameters") and getattr(t, "name", None) in allowed_tool_names
        ]
```

Change Gemini schema call:

```python
                tools=[build_agent_tool(dynamic_tools, allowed_tool_names=allowed_tool_names)],
```

Change OpenAI/NVIDIA schema calls:

```python
                    tools=build_openai_agent_tools(dynamic_tools, allowed_tool_names=allowed_tool_names),
```

and:

```python
                    tools=build_openai_agent_tools(dynamic_tools, allowed_tool_names=allowed_tool_names),
```

- [ ] **Step 6: Route tool calls through ActionExecutor**

Replace the `on_fc` body:

```python
            out = self._execute_function_tool(name, args, text)
```

with:

```python
            executor = ActionExecutor(
                allowed_tool_names=allowed_tool_names,
                guardrails=self._tool_guardrails,
                legacy_execute=self._execute_function_tool,
            )
            out = executor.execute(name, args, text)
```

- [ ] **Step 7: Run GREEN**

Run:

```powershell
python -m pytest tests\test_agent_orchestrator_runtime.py tests\test_agent_runtime_modes.py tests\test_agent_runtime_tool_schemas.py tests\test_agent_action_executor.py tests\test_agent_tool_guardrails.py -q
```

Expected: all tests pass.

- [ ] **Step 8: Commit Task 7**

Run:

```powershell
git add src\agent\orchestrator.py tests\test_agent_orchestrator_runtime.py
git commit -m "feat: integrate Jarvis runtime mode toolsets"
```

---

### Task 8: Focused Regression Suite

**Files:**
- No new files required.

- [ ] **Step 1: Run focused runtime tests**

Run:

```powershell
python -m pytest tests\test_agent_runtime_modes.py tests\test_agent_runtime_tool_schemas.py tests\test_agent_tool_guardrails.py tests\test_agent_action_executor.py tests\test_agent_prompt_runtime_context.py tests\test_agent_orchestrator_runtime.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Run existing agent/schema tests**

Run:

```powershell
python -m pytest tests\test_gemini_tools.py tests\test_llm_provider_order.py tests\test_prompts_vision.py -q
```

Expected: all tests pass.

- [ ] **Step 3: Run Nexus smoke tests**

Run:

```powershell
python -m pytest tests\test_nexus_life.py tests\test_nexus_window_theme.py -q
```

Expected: all tests pass or only fail for pre-existing unrelated environment/data issues. Any failure touching `nexus_command`, `news_briefing`, or `open_ui` must be fixed before continuing to Phase 2.

- [ ] **Step 4: Commit final verification note if needed**

If verification required small fixes, commit them:

```powershell
git add src\agent tests
git commit -m "test: verify Jarvis runtime phase 1"
```

---

## Phase 1 Completion Criteria

- User greetings use chat mode and do not expose desktop/screen tools.
- PC commands expose PC tools without Nexus/finance/file deletion tools.
- News commands expose News/Nexus/search tools and preserve visible window flow.
- Psych/Coach requests expose safe Nexus/memory tools without desktop mutation.
- Function schemas are filtered for Gemini, NVIDIA/OpenAI-compatible providers, and Groq.
- Repeated exact tool calls are blocked within a turn.
- Repeated no-progress results stop the loop.
- Existing default schema tests still pass when no filter is supplied.

## Handoff To Later Phases

After Phase 1 is verified:

1. Phase 2 can tighten per-action `nexus_command` descriptions by mode.
2. Phase 3 can add the full `psych_coach` persona/memory/diary flow.
3. Phase 4 can improve News window video/transcript handling.
4. Phase 5 can add saved workflows, recording, triggers, and clap activation.
