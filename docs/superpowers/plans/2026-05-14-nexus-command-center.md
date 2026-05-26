# Nexus Command Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first Nexus visual foundation: theme-aware neon window chrome and a dense Command Center overview using existing data bridges.

**Architecture:** Keep the pywebview module composition model. Add theme control in `desktop_app.py`, shared variables in `nexus_frame.css`, persistent browser-side theme logic in `nexus_boot.js`, and redesign `overview.html` as the first flagship surface.

**Tech Stack:** Python, pytest, pywebview HTML composition, vanilla HTML/CSS/JS, SQLite-backed bridge APIs.

---

### Task 1: Theme Contract Tests

**Files:**
- Create: `tests/test_nexus_window_theme.py`
- Modify later: `src/ui/desktop_app.py`
- Modify later: `src/ui/nexus_modules/nexus_boot.js`
- Modify later: `src/ui/nexus_modules/nexus_frame.css`

- [ ] **Step 1: Write failing tests**

Create tests that assert `_compose_nexus_module_html()` emits a theme-aware wrapper and theme toggle, invalid themes fall back to dark, `nexus_boot.js` exposes persistent theme helpers, and `nexus_frame.css` contains the light-theme selector and toggle styles.

- [ ] **Step 2: Run the tests and verify RED**

Run: `python -m pytest tests/test_nexus_window_theme.py -q`

Expected before implementation: failures mentioning missing `data-theme`, `data-nx-theme-toggle`, `nxToggleTheme`, and light theme CSS.

- [ ] **Step 3: Implement frame theme support**

Add a small theme normalizer in `desktop_app.py`, include `data-theme` on `#nx-app-wrapper`, add a theme toggle button next to the close button, add persistent theme helpers in `nexus_boot.js`, and add dark/light token contracts plus `.nx-theme-toggle` styles in `nexus_frame.css`.

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests/test_nexus_window_theme.py -q`

Expected after implementation: all tests pass.

### Task 2: Command Center Contract Tests

**Files:**
- Modify: `tests/test_nexus_window_theme.py`
- Modify later: `src/ui/nexus_modules/overview.html`

- [ ] **Step 1: Write failing overview structure test**

Assert that `overview.html` contains the Command Center root, sidebar, signal feed, study queue, rewards/goals panels, and bridge calls needed for the requested vision.

- [ ] **Step 2: Run the test and verify RED**

Run: `python -m pytest tests/test_nexus_window_theme.py::test_overview_declares_command_center_contract -q`

Expected before implementation: failure because the current overview is a simpler dashboard.

- [ ] **Step 3: Redesign `overview.html`**

Replace the simple dashboard with a dense cockpit: sidebar navigation, status deck, XP bar, finance and habit panels, study/review queue, goals/rewards, and AI signal feed. Keep module CSS inline and selectors specific enough to win over the frame.

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests/test_nexus_window_theme.py -q`

Expected after implementation: all tests pass.

### Task 3: Regression And Render Sanity

**Files:**
- Verify: `tests/test_nexus_life.py`
- Verify: generated pywebview module composition through unit tests

- [ ] **Step 1: Run Nexus tests**

Run: `python -m pytest tests/test_nexus_life.py tests/test_nexus_window_theme.py -q`

Expected: all selected tests pass.

- [ ] **Step 2: Run browser/render QA if a web target is available**

Use the Browser plugin when the target is a browser-served page. For pywebview-only module HTML, verify composition through tests and inspect the generated HTML contract; record if full browser screenshots are blocked by the desktop-only runtime.
