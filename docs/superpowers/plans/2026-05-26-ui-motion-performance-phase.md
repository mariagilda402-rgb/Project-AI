# UI Motion and Performance Phase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve perceived quality with configurable motion, clearer runtime/startup telemetry, smoother panel microinteractions, and shared Nexus animation polish.

**Architecture:** Runtime startup phases are recorded in `RuntimeStatus` and exposed through `get_status`. UI motion preferences live in `Settings`, are saved through `DesktopApi`, and drive CSS data attributes in the panel. Nexus modules get safe shared animation tokens in `nexus_frame.css` without rewriting individual modules.

**Tech Stack:** Python dataclass config, PyWebView API bridge, plain HTML/CSS/JS, pytest, Node script parsing for HTML scripts.

---

### Task 1: Runtime Startup Telemetry

**Files:**
- Modify: `src/runtime_status.py`
- Modify: `src/main.py`

- [ ] Add `mark_startup_phase(name, detail="")` to `RuntimeStatus`.
- [ ] Include `startup_phases` and `startup_total_ms` in `snapshot()`.
- [ ] Mark phases in `main()` after settings, STT, TTS, LLM, Vision, memory/tools/agent, optional services, STT calibration, and UI handoff.
- [ ] Verify with `python -m pytest tests\test_config_defaults.py -q`.

### Task 2: Configurable Motion Preferences

**Files:**
- Modify: `src/config.py`
- Modify: `.env.example`
- Modify: `src/ui/desktop_app.py`
- Modify: `tests/test_config_defaults.py`

- [ ] Add `ui_motion_level` (`reduced`, `balanced`, `expressive`) and `ui_density` (`comfortable`, `compact`) to settings.
- [ ] Expose them in `get_config()`.
- [ ] Add `update_ui_config(data)` to save them in `.env`.
- [ ] Add config tests for env parsing.

### Task 3: Panel Motion and Runtime UX

**Files:**
- Modify: `src/ui/panel.html`

- [ ] Add CSS motion tokens, reduced-motion behavior, card hover lift, nav active indicator, status-badge states, and startup phase list styles.
- [ ] Add appearance controls for motion level and density.
- [ ] Save appearance settings through `update_ui_config`.
- [ ] Render startup phases from `get_status()` in the home dashboard.
- [ ] Update status badge classes based on mic/processing state.

### Task 4: Nexus Shared Animation Polish

**Files:**
- Modify: `src/ui/nexus_modules/nexus_frame.css`

- [ ] Add shared motion variables and reduced-motion media query.
- [ ] Improve chrome/header/button transitions.
- [ ] Add safe content enter animation for module main surfaces.

### Task 5: Validation and Documentation

**Files:**
- Modify: `docs/2026-05-26-revisao-app-melhorias.md`

- [ ] Parse changed HTML scripts with Node.
- [ ] Run focused pytest suites.
- [ ] Compile modified Python files.
- [ ] Append this phase to the review document.
