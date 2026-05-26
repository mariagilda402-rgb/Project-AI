# Nexus News Briefing Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reliable Nexus news briefing window with structured headline research, video-search slots, transcript lanes, narration, and Jarvis routing.

**Architecture:** Implement briefing construction in `NexusService`, expose it through `nexus_desktop_bridge.py` and `nexus_command`, add `news.html` as a self-contained Nexus module, and extend desktop module routing.

**Tech Stack:** Python service logic, DuckDuckGo news at runtime, pywebview bridge, static HTML/CSS/JS module, pytest.

---

### Task 1: Service Briefing Contract

**Files:**
- Modify: `tests/test_nexus_life.py`
- Modify: `src/services/nexus_service.py`

- [ ] **Step 1: Write failing service test**

Add a fixture-based test for `build_news_briefing("tecnologia", limit=2, results=[...])`. Assert `items`, `video.provider`, `transcript.past/present/future`, `summary`, and `narration`.

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests\test_nexus_life.py::test_news_briefing_builds_video_transcript_and_narration -q`

Expected: method missing.

- [ ] **Step 3: Implement service**

Add helpers to fetch/normalize news results, split summary sentences, build YouTube search URLs, and optionally enqueue the news window.

- [ ] **Step 4: Run GREEN**

Run: `python -m pytest tests\test_nexus_life.py::test_news_briefing_builds_video_transcript_and_narration -q`

Expected: pass.

### Task 2: Window and Bridge

**Files:**
- Modify: `tests/test_nexus_window_theme.py`
- Modify: `tests/test_nexus_life.py`
- Create: `src/ui/nexus_modules/news.html`
- Modify: `src/ui/nexus_desktop_bridge.py`
- Modify: `src/ui/desktop_app.py`
- Modify: `src/services/nexus_service.py`
- Modify: `src/skills/nexus_manager.py`
- Modify: `src/ui/panel.html`

- [ ] **Step 1: Write failing UI/bridge tests**

Add tests for static markers in `news.html`, bridge `news_briefing`, `open_ui` mapping for news, and natural language opening.

- [ ] **Step 2: Run RED**

Run focused tests for the new names.

- [ ] **Step 3: Implement UI and routing**

Add module file, bridge method, desktop allowed/titles, panel button, open-ui aliases, and manager mapping.

- [ ] **Step 4: Run GREEN**

Run the same focused tests.

### Task 3: Tool Schema

**Files:**
- Modify: `tests/test_gemini_tools.py`
- Modify: `src/agent/gemini_tools.py`
- Modify: `src/agent/prompts.py`

- [ ] **Step 1: Write failing schema test**

Assert `news_briefing` appears in Gemini/OpenAI descriptions and the prompt tells Jarvis to use it for latest news.

- [ ] **Step 2: Implement schema/prompt**

Add action name and argument guidance.

- [ ] **Step 3: Run GREEN**

Run the schema tests.

### Task 4: Verification

- [ ] **Step 1: Run full Nexus suite**

Run: `python -m pytest tests\test_nexus_life.py tests\test_nexus_quiz.py tests\test_nexus_window_theme.py tests\test_gemini_tools.py -q`

- [ ] **Step 2: Compile touched Python**

Run: `python -m py_compile src\services\nexus_service.py src\ui\desktop_app.py src\ui\nexus_desktop_bridge.py src\skills\nexus_manager.py src\agent\gemini_tools.py src\agent\prompts.py`

- [ ] **Step 3: Check JS syntax**

Run: `node --check src\ui\nexus_modules\nexus_boot.js` and extract/check inline scripts from `news.html` and `panel.html`.
