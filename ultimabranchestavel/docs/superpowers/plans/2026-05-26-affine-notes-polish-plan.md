# Affine Notes Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evolve the Nexus notes editor toward a lightweight Notion/Affine-style writing surface without replacing the current markdown-backed storage.

**Architecture:** Keep markdown as the canonical saved value in the hidden textarea, with the visible `contenteditable` acting as the block editor. Add small block helpers, contextual controls, debounced preview/TOC updates, and safer conversion between rich HTML and markdown.

**Tech Stack:** Plain HTML/CSS/JS inside `src/ui/nexus_modules/notes.html`, existing Nexus bridge APIs, Node syntax parsing for scripts.

---

### Task 1: Finish Runtime UI Polish

**Files:**
- Modify: `src/ui/panel.html`
- Modify: `src/ui/nexus_modules/nexus_frame.css`

- [ ] Render `startup_phases` returned by `get_status()` in the dashboard.
- [ ] Add shared Nexus motion tokens, reduced-motion handling, hover transitions, and content enter animation.
- [ ] Preserve existing neon z-index and frame rules covered by `tests/test_nexus_window_theme.py`.

### Task 2: Improve Notes Editor Blocks

**Files:**
- Modify: `src/ui/nexus_modules/notes.html`

- [ ] Add block hover affordance, current-line highlight, block labels, callout/code/table block styles, and better task checkbox interactions.
- [ ] Extend slash commands with paragraph, bullet, numbered list, callout, code block, table, image, and clear-format actions.
- [ ] Add markdown parsing/rendering for numbered lists, callouts, fenced code, simple tables, and pasted URLs/images.
- [ ] Keep all content persisted as markdown through `getEditorMarkdown()`.

### Task 3: Reduce Editor Lag

**Files:**
- Modify: `src/ui/nexus_modules/notes.html`

- [ ] Debounce preview/TOC rendering separately from save calls.
- [ ] Avoid reloading the whole notes nav after every save when only the current title/subject changed.
- [ ] Keep optimistic tab/sidebar labels in sync immediately.

### Task 4: Validate and Document

**Files:**
- Modify: `docs/2026-05-26-revisao-app-melhorias.md`

- [ ] Parse changed HTML scripts with Node.
- [ ] Run focused pytest suites for config, STT, Nexus theme, runtime agents, and Nexus life modules.
- [ ] Compile modified Python files.
- [ ] Document the editor and performance changes in the review document.
