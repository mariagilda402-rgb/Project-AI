# Nexus Neural Memory Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a visual Neural Memory Graph window backed by local Nexus data.

**Architecture:** `NexusService.build_memory_graph()` creates a compact graph payload. `nexus_desktop_bridge.py`, structured commands, prompts, and schemas expose it. `memory_graph.html` renders a searchable Canvas 2D graph inside the existing Nexus desktop module frame.

**Tech Stack:** Python, SQLite, pytest, pywebview bridge, static HTML/CSS/JS with inline module styling and Canvas 2D.

---

### Task 1: Backend Graph Payload

**Files:**
- Modify: `src/services/nexus_service.py`
- Test: `tests/test_nexus_life.py`

- [ ] Write `test_memory_graph_builds_cross_module_nodes_and_edges` with seeded notes, flashcards, habit, task, goal, reward, and structured memory.
- [ ] Run the test and verify it fails because `build_memory_graph` does not exist.
- [ ] Add helper methods for graph nodes, edges, keyword extraction, Markdown file summaries, structured memory loading, and `build_memory_graph`.
- [ ] Run the targeted test and verify it passes.

### Task 2: Command And Bridge

**Files:**
- Modify: `src/services/nexus_service.py`
- Modify: `src/ui/nexus_desktop_bridge.py`
- Test: `tests/test_nexus_life.py`

- [ ] Write tests for structured `memory_graph` and desktop bridge `memory_graph`.
- [ ] Run the tests and verify they fail because the action and bridge handler are missing.
- [ ] Add structured command and bridge support.
- [ ] Run the targeted tests and verify they pass.

### Task 3: Window Registration And UI Contract

**Files:**
- Modify: `src/services/nexus_service.py`
- Modify: `src/ui/desktop_app.py`
- Create: `src/ui/nexus_modules/memory_graph.html`
- Test: `tests/test_nexus_window_theme.py`

- [ ] Write static tests for module registration, aliases, and UI markers.
- [ ] Run the tests and verify they fail because the module is missing.
- [ ] Register `memory_graph` in allowed modules, titles, aliases, and tool copy.
- [ ] Create `memory_graph.html` with inline CSS, Canvas graph, search, filters, node details, and action buttons.
- [ ] Run the targeted tests and verify they pass.

### Task 4: Agent Schema And Prompts

**Files:**
- Modify: `src/agent/gemini_tools.py`
- Modify: `src/agent/prompts.py`
- Test: `tests/test_gemini_tools.py`

- [ ] Write schema/prompt tests for `memory_graph`.
- [ ] Run the tests and verify they fail because the action is not advertised.
- [ ] Update Gemini/OpenAI descriptions and prompt rules.
- [ ] Run targeted tests and verify they pass.

### Task 5: Verification

- [ ] Run focused Nexus tests.
- [ ] Compile changed Python files.
- [ ] Check inline JS syntax for `memory_graph.html`.
- [ ] Attempt rendered Browser verification if a local pywebview/browser target is reachable; otherwise record the blocker.

### Task 6: Smart Relations And Jarvis Context

**Files:**
- Modify: `src/services/nexus_service.py`
- Modify: `src/ui/nexus_desktop_bridge.py`
- Modify: `src/ui/nexus_modules/memory_graph.html`
- Modify: `src/agent/gemini_tools.py`
- Modify: `src/agent/prompts.py`
- Test: `tests/test_nexus_life.py`
- Test: `tests/test_nexus_window_theme.py`
- Test: `tests/test_gemini_tools.py`

- [x] Write tests for inferred `relates` edges, relevance ranking, `memory_graph_context`, bridge support, UI spotlight, and tool prompt exposure.
- [x] Run the tests and verify they fail because the smart relation/context layer is missing.
- [x] Add keyword preservation, relevance scores, inferred cross-module edges, `ranked_matches`, and `memory_graph_context`.
- [x] Expose `memory_graph_context` through structured commands, bridge, Gemini/OpenAI tool descriptions, and prompt rules.
- [x] Add a relevance spotlight strip to `memory_graph.html`.
- [x] Run the targeted tests and verify they pass.
