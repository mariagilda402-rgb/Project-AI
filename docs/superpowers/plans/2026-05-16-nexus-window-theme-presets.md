# Nexus Window Theme Presets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add persistent per-window Nexus theme presets that can be applied from the panel or generated/applied through Jarvis commands.

**Architecture:** Store generated presets and module assignments in `nexus_window_themes.json` beside the Nexus database. Keep built-in presets in `NexusService`, expose `theme_list`, `theme_apply`, and `theme_generate`, and have `desktop_app.py` merge module theme boot data into each pywebview window payload.

**Tech Stack:** Python, SQLite-adjacent JSON data file, pywebview HTML composition, inline CSS variables, static HTML tests, pytest.

---

### Task 1: Theme Service Contract

**Files:**
- Modify: `tests/test_nexus_life.py`
- Modify: `src/services/nexus_service.py`

- [ ] **Step 1: Write failing service tests**

Add tests that create a temp `NexusService`, assign a temp `NexusDatabase`, call `list_window_themes()`, `apply_window_theme("finance", "emerald-ledger")`, and `generate_window_theme_preset("notes", "tema neon azul de estudos", "Caderno Neon")`. Assert module assignments persist to the temp JSON file and prompt text is not saved.

- [ ] **Step 2: Run focused tests to verify RED**

Run: `python -m pytest tests\test_nexus_life.py::test_window_theme_apply_persists_and_boot_tokens tests\test_nexus_life.py::test_window_theme_generator_saves_tokens_without_prompt_memory -q`

Expected: failures because the methods do not exist.

- [ ] **Step 3: Implement service methods**

Add module/preset constants, JSON load/save helpers, theme boot builder, apply, list, and deterministic generate methods. Whitelist CSS token keys and never save the raw prompt.

- [ ] **Step 4: Run focused tests to verify GREEN**

Run: `python -m pytest tests\test_nexus_life.py::test_window_theme_apply_persists_and_boot_tokens tests\test_nexus_life.py::test_window_theme_generator_saves_tokens_without_prompt_memory -q`

Expected: both pass.

### Task 2: Window Composition and Main Panel

**Files:**
- Modify: `tests/test_nexus_window_theme.py`
- Modify: `src/ui/desktop_app.py`
- Modify: `src/ui/nexus_modules/nexus_boot.js`
- Modify: `src/ui/nexus_modules/nexus_frame.css`
- Modify: `src/ui/panel.html`

- [ ] **Step 1: Write failing UI contract tests**

Add tests asserting `_compose_nexus_module_html()` emits `data-theme-preset`, inline custom `--accent`, and `window.__NEXUS_BOOT__` theme tokens. Add a panel static test for `nexusThemeModule`, `nexusThemePreset`, `nexusThemePrompt`, `loadNexusThemes`, `nexus_theme_apply`, and `nexus_theme_generate`.

- [ ] **Step 2: Run focused tests to verify RED**

Run: `python -m pytest tests\test_nexus_window_theme.py::test_compose_applies_custom_theme_tokens_and_preset_attribute tests\test_nexus_window_theme.py::test_panel_declares_nexus_window_theme_controls_and_api_calls -q`

Expected: failures because controls and composer attributes are absent.

- [ ] **Step 3: Implement composer and panel UI**

Merge module theme boot data in `open_nexus_module()`, write safe inline CSS variables in `_compose_nexus_module_html()`, expose `DesktopApi.nexus_theme_list/apply/generate`, and add Configuracoes controls plus JS handlers.

- [ ] **Step 4: Run focused tests to verify GREEN**

Run: `python -m pytest tests\test_nexus_window_theme.py::test_compose_applies_custom_theme_tokens_and_preset_attribute tests\test_nexus_window_theme.py::test_panel_declares_nexus_window_theme_controls_and_api_calls -q`

Expected: both pass.

### Task 3: Jarvis Tool Schema and Natural Commands

**Files:**
- Modify: `tests/test_gemini_tools.py`
- Modify: `tests/test_nexus_life.py`
- Modify: `src/services/nexus_service.py`
- Modify: `src/agent/gemini_tools.py`
- Modify: `src/agent/prompts.py`
- Modify: `src/skills/nexus_manager.py`

- [ ] **Step 1: Write failing command/schema tests**

Add tests that `handle_structured_command()` supports `theme_list`, `theme_apply`, and `theme_generate`, and that tool descriptions/prompts mention theme generation for Nexus windows.

- [ ] **Step 2: Run focused tests to verify RED**

Run: `python -m pytest tests\test_nexus_life.py::test_structured_theme_commands_apply_and_generate tests\test_gemini_tools.py::test_nexus_command_schema_exposes_window_theme_actions -q`

Expected: failures because actions are unknown in schema and service.

- [ ] **Step 3: Implement actions and natural parsing**

Route `theme_list`, `theme_apply`, and `theme_generate` in `handle_structured_command()`, update Gemini/OpenAI schemas, add prompt guidance, and teach `NexusManagerSkill` to understand simple phrases like "gere um tema neon azul para estudos".

- [ ] **Step 4: Run focused tests to verify GREEN**

Run: `python -m pytest tests\test_nexus_life.py::test_structured_theme_commands_apply_and_generate tests\test_gemini_tools.py::test_nexus_command_schema_exposes_window_theme_actions -q`

Expected: both pass.

### Task 4: Verification

**Files:**
- Test: `tests/test_nexus_life.py`
- Test: `tests/test_nexus_window_theme.py`
- Test: `tests/test_gemini_tools.py`

- [ ] **Step 1: Run relevant suite**

Run: `python -m pytest tests\test_nexus_life.py tests\test_nexus_window_theme.py tests\test_gemini_tools.py -q`

Expected: all pass.

- [ ] **Step 2: Compile touched Python**

Run: `python -m py_compile src\services\nexus_service.py src\ui\desktop_app.py src\skills\nexus_manager.py src\agent\gemini_tools.py src\agent\prompts.py`

Expected: exit code 0.

- [ ] **Step 3: Browser verification**

Use Browser/IAB on the current local panel URL if available. Open Configuracoes, confirm the theme controls render, and avoid destructive actions. If Browser is unavailable, state the fallback and use a static/rendered verification alternative.
