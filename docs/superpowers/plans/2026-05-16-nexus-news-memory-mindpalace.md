# Nexus News Memory + MindPalace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add local news briefing history/cache and a one-click path to save selected news stories into MindPalace.

**Architecture:** Extend `NexusService` with JSON-backed briefing history and a note-conversion method. Expose those methods through structured commands, the desktop bridge, tool schemas, prompts, and the News window.

**Tech Stack:** Python service + pytest, pywebview bridge, static HTML/CSS/JS Nexus modules.

---

### Task 1: News History And Cache

**Files:**
- Modify: `src/services/nexus_service.py`
- Test: `tests/test_nexus_life.py`

- [ ] **Step 1: Write failing tests**

Add tests that call `build_news_briefing()` with fixture results, assert a history entry is persisted, then call it again with an empty live provider and assert cached/stale fallback fields are returned.

- [ ] **Step 2: Run targeted tests**

Run: `python -m pytest tests\test_nexus_life.py::test_news_briefing_persists_history_and_reuses_cache -q`

Expected: fail because `list_news_briefings()` and cache fallback do not exist yet.

- [ ] **Step 3: Implement minimal service support**

Add `_news_history_store_path()`, `_load_news_history()`, `_save_news_history()`, `_remember_news_briefing()`, `_cached_news_briefing()`, and `list_news_briefings()`. Update `build_news_briefing()` to persist successful live results and reuse cache when no fresh items exist.

- [ ] **Step 4: Verify targeted tests pass**

Run: `python -m pytest tests\test_nexus_life.py::test_news_briefing_persists_history_and_reuses_cache -q`

Expected: pass.

### Task 2: Save News To MindPalace

**Files:**
- Modify: `src/services/nexus_service.py`
- Modify: `src/ui/nexus_desktop_bridge.py`
- Test: `tests/test_nexus_life.py`

- [ ] **Step 1: Write failing tests**

Add tests for `save_news_item_to_note()`, `handle_structured_command({"action": "news_save_note"})`, and bridge method `news_save_note`.

- [ ] **Step 2: Run targeted tests**

Run the three new tests by name. Expected: fail because the service and bridge methods do not exist yet.

- [ ] **Step 3: Implement minimal service and bridge**

Create `save_news_item_to_note(item=None, briefing=None, item_index=1, subject="Noticias")`, format Markdown content, store media metadata, enqueue a `notes` receipt, and expose it through `news_save_note`.

- [ ] **Step 4: Verify targeted tests pass**

Run the three new tests by name. Expected: pass.

### Task 3: News UI Contract

**Files:**
- Modify: `src/ui/nexus_modules/news.html`
- Test: `tests/test_nexus_window_theme.py`

- [ ] **Step 1: Write failing static UI test**

Assert the News module declares `newsBriefingHistory`, `newsCacheStatus`, `saveCurrentNewsToNote`, `news_history`, and `news_save_note`.

- [ ] **Step 2: Run targeted UI test**

Run: `python -m pytest tests\test_nexus_window_theme.py::test_news_module_declares_history_and_mindpalace_controls -q`

Expected: fail because controls are missing.

- [ ] **Step 3: Implement the UI controls**

Add cache/history status, a "Salvar no MindPalace" button, a compact recent briefing list, and JS functions to load history and save the selected item.

- [ ] **Step 4: Verify targeted UI test passes**

Run the targeted UI test again. Expected: pass.

### Task 4: Agent Schema And Prompts

**Files:**
- Modify: `src/agent/gemini_tools.py`
- Modify: `src/agent/prompts.py`
- Test: `tests/test_gemini_tools.py`

- [ ] **Step 1: Write failing schema/prompt test**

Assert `news_save_note` appears in Gemini/OpenAI tool descriptions and the news prompt mentions saving stories into MindPalace.

- [ ] **Step 2: Run targeted test**

Expected: fail because schemas/prompts only mention `news_briefing`.

- [ ] **Step 3: Update schema and prompt text**

Advertise `news_history` and `news_save_note`, plus `item`, `briefing`, and `item_index` parameters.

- [ ] **Step 4: Verify targeted test passes**

Run: `python -m pytest tests\test_gemini_tools.py -q`

Expected: pass.

### Task 5: Final Verification

- [ ] Run focused Nexus suites.
- [ ] Compile changed Python files.
- [ ] Check inline JS syntax for `news.html`.
- [ ] Attempt Browser/IAB visual verification only if the local app target is reachable; otherwise record the blocker.
