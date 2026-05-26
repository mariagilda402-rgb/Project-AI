# Nexus Jarvis Command Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 7 MVP that lets Jarvis execute multiple Nexus actions in order and open the requested module with sequence-aware animation payloads.

**Architecture:** Keep orchestration inside `NexusService` and natural-language convenience parsing inside `NexusManagerSkill`. Preserve existing module contracts and use the existing pywebview signal queue, but change it from last-write-wins to ordered draining with optional per-payload hold timing.

**Tech Stack:** Python, pytest, SQLite-backed Nexus service, pywebview desktop windows, existing `nexus_command` tool schema.

---

### Task 1: Ordered Nexus Window Signals

**Files:**
- Modify: `tests/test_nexus_life.py`
- Modify: `src/ui/nexus_signals.py`
- Modify: `src/ui/desktop_app.py`

- [ ] **Step 1: Write failing queue test**

Add a test proving `enqueue_nexus_desktop_open` preserves multiple requests in order:

```python
def test_nexus_window_signal_queue_preserves_sequence(monkeypatch):
    from collections import deque
    import src.ui.desktop_app as desktop_app
    from src.ui.nexus_signals import enqueue_nexus_desktop_open

    class FakeApp:
        def __init__(self):
            import threading
            self._nexus_lock = threading.Lock()
            self._nexus_signal_q = deque(maxlen=16)

    app = FakeApp()
    monkeypatch.setattr(desktop_app, "APP_INSTANCE", app)

    enqueue_nexus_desktop_open("finance", {"step": 1})
    enqueue_nexus_desktop_open("habits", {"step": 2})
    enqueue_nexus_desktop_open("notes", {"step": 3})

    assert list(app._nexus_signal_q) == [
        ("finance", {"step": 1}),
        ("habits", {"step": 2}),
        ("notes", {"step": 3}),
    ]
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest tests\test_nexus_life.py::test_nexus_window_signal_queue_preserves_sequence -q
```

Expected: fail because the queue currently clears previous requests.

- [ ] **Step 3: Implement ordered queue and scheduler hold**

Change `enqueue_nexus_desktop_open` to append without clearing. In `DesktopApp`, add `_nexus_next_open_at` and make `nexus_scheduler_tick` wait until that time before draining the next payload. After opening a module, set `_nexus_next_open_at` from `payload["hold_ms"]` when present.

- [ ] **Step 4: Run GREEN**

Run:

```powershell
python -m pytest tests\test_nexus_life.py::test_nexus_window_signal_queue_preserves_sequence -q
```

Expected: pass.

### Task 2: Complete `open_ui` Mapping

**Files:**
- Modify: `tests/test_nexus_life.py`
- Modify: `src/services/nexus_service.py`

- [ ] **Step 1: Write failing open mapping test**

Add a test proving every current Nexus module can be opened through `open_ui`:

```python
def test_open_ui_maps_all_current_nexus_modules(monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()

    for tab, expected in [
        ("dashboard", "overview"),
        ("overview", "overview"),
        ("habits", "habits"),
        ("finance", "finance"),
        ("notes", "notes"),
        ("study", "study"),
        ("tasks", "tasks"),
        ("progress", "progress"),
        ("goals", "goals"),
        ("rewards", "goals"),
        ("quiz", "quiz"),
    ]:
        msg = svc.handle_structured_command({"action": "open_ui", "tab": tab})
        assert "Abrindo" in msg
        assert calls[-1][0] == expected
        assert calls[-1][1]["animate"] == "open_module"
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest tests\test_nexus_life.py::test_open_ui_maps_all_current_nexus_modules -q
```

Expected: fail on missing module mappings and missing `animate`.

- [ ] **Step 3: Implement mapping and payload**

Expand `open_nexus_ui` to include all current modules and call `enqueue_nexus_desktop_open(mod, {"animate": "open_module", "source": "open_ui", "tab": raw})`.

- [ ] **Step 4: Run GREEN**

Run:

```powershell
python -m pytest tests\test_nexus_life.py::test_open_ui_maps_all_current_nexus_modules -q
```

Expected: pass.

### Task 3: Structured `nexus_batch`

**Files:**
- Modify: `tests/test_nexus_life.py`
- Modify: `src/services/nexus_service.py`

- [ ] **Step 1: Write failing batch test**

Add a test for the user's example sequence:

```python
def test_nexus_batch_executes_steps_and_enqueues_windows_in_order(tmp_path, monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "batch.db"))

    raw = svc.handle_structured_command({
        "action": "nexus_batch",
        "steps": [
            {
                "action": "finance_add",
                "type": "expense",
                "amount": "500",
                "category": "Alimentacao",
                "description": "alimentacao",
            },
            {
                "action": "habit_add",
                "name": "Caminhar",
                "description": "Horario sugerido: 14:00",
                "xp_reward": "50",
            },
            {"action": "open_ui", "tab": "notes"},
        ],
    })

    result = json.loads(raw)
    assert result["ok"] is True
    assert [step["action"] for step in result["steps"]] == ["finance_add", "habit_add", "open_ui"]
    assert [module for module, _ in calls] == ["finance", "habits", "notes"]
    assert all(payload.get("batch_id") for _, payload in calls)
    assert [payload.get("batch_step") for _, payload in calls] == [1, 2, 3]
    assert svc.db.list_finance_transactions()[0]["amount"] == 500.0
    assert any(h["name"] == "Caminhar" for h in svc.db.get_habits())
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest tests\test_nexus_life.py::test_nexus_batch_executes_steps_and_enqueues_windows_in_order -q
```

Expected: fail because `nexus_batch` is unknown.

- [ ] **Step 3: Implement batch execution**

Add `handle_nexus_batch`, `_decorate_nexus_payload`, and active batch metadata in `NexusService`. Ensure nested `nexus_batch` steps are rejected with a per-step error, while normal steps continue in order.

- [ ] **Step 4: Run GREEN**

Run:

```powershell
python -m pytest tests\test_nexus_life.py::test_nexus_batch_executes_steps_and_enqueues_windows_in_order -q
```

Expected: pass.

### Task 4: Natural Compound Command Parsing

**Files:**
- Modify: `tests/test_nexus_life.py`
- Modify: `src/skills/nexus_manager.py`

- [ ] **Step 1: Write failing natural command test**

Add:

```python
def test_nexus_manager_understands_compound_finance_habit_and_open(tmp_path, monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "compound.db"))
    manager = NexusManagerSkill(svc)

    msg = manager.handle_command(
        "jarvis, adicione o gasto de 500 reais em alimentação, "
        "adicione o hábito de caminhar às 14 horas, e abra a janela de estudos"
    )

    assert msg is not None
    assert "3" in msg
    assert [module for module, _ in calls] == ["finance", "habits", "notes"]
    assert svc.db.list_finance_transactions()[0]["category"].lower().startswith("alimenta")
    habit = next(h for h in svc.db.get_habits() if h["name"] == "Caminhar")
    assert "14:00" in habit["description"]
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest tests\test_nexus_life.py::test_nexus_manager_understands_compound_finance_habit_and_open -q
```

Expected: fail because the manager currently executes only the first matching command.

- [ ] **Step 3: Implement parser helpers**

Add helpers in `nexus_manager.py` for:

- cleaning wake words
- mapping panel names to `open_ui` tabs
- extracting one expense step
- extracting one habit step with optional time
- extracting one open-ui step

At the start of `handle_command`, call the compound parser and route generated steps through `nexus_batch` when at least two steps were found.

- [ ] **Step 4: Run GREEN**

Run:

```powershell
python -m pytest tests\test_nexus_life.py::test_nexus_manager_understands_compound_finance_habit_and_open -q
```

Expected: pass.

### Task 5: Tool Schema And Prompt Guidance

**Files:**
- Modify: `tests/test_gemini_tools.py`
- Modify: `src/agent/gemini_tools.py`
- Modify: `src/agent/prompts.py`

- [ ] **Step 1: Write failing schema test**

Extend `test_nexus_command_advertises_flashcard_generation` to assert:

```python
assert "nexus_batch" in nexus.description
assert "steps" in nexus.parameters.properties
assert "habits" in nexus.description
assert "tasks" in nexus.description
assert "quiz" in nexus.description
assert "nexus_batch" in openai_nexus["function"]["description"]
assert "steps" in openai_nexus["function"]["parameters"]["properties"]
```

Add a prompt test:

```python
def test_function_prompt_guides_nexus_batch_for_multi_action_requests():
    from src.agent.prompts import AGENT_SYSTEM_PROMPT_FUNCTION_CALLING

    assert "nexus_batch" in AGENT_SYSTEM_PROMPT_FUNCTION_CALLING
    assert "mais de uma ação" in AGENT_SYSTEM_PROMPT_FUNCTION_CALLING
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest tests\test_gemini_tools.py::test_nexus_command_advertises_flashcard_generation tests\test_gemini_tools.py::test_function_prompt_guides_nexus_batch_for_multi_action_requests -q
```

Expected: fail because the schema/prompt does not advertise batch execution.

- [ ] **Step 3: Update schema and prompt**

Add `nexus_batch` and `steps` to Gemini and OpenAI tool descriptions. Add a concise rule in `AGENT_SYSTEM_PROMPT_FUNCTION_CALLING`: when the user asks for more than one Nexus action in the same request, call one `nexus_command` with `action: nexus_batch` and ordered `steps`.

- [ ] **Step 4: Run GREEN**

Run:

```powershell
python -m pytest tests\test_gemini_tools.py::test_nexus_command_advertises_flashcard_generation tests\test_gemini_tools.py::test_function_prompt_guides_nexus_batch_for_multi_action_requests -q
```

Expected: pass.

### Task 6: Verification

**Files:**
- No new source files expected.

- [ ] **Step 1: Run Nexus behavior tests**

```powershell
python -m pytest tests\test_nexus_life.py tests\test_gemini_tools.py -q
```

- [ ] **Step 2: Run full Nexus suite**

```powershell
python -m pytest tests\test_nexus_life.py tests\test_nexus_quiz.py tests\test_nexus_window_theme.py tests\test_gemini_tools.py -q
```

- [ ] **Step 3: Compile touched Python modules**

```powershell
python -m py_compile src\ui\nexus_signals.py src\ui\desktop_app.py src\services\nexus_service.py src\skills\nexus_manager.py src\agent\gemini_tools.py src\agent\prompts.py
```
