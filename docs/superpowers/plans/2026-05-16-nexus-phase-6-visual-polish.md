# Nexus Phase 6 Visual Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add premium canvas telemetry and restrained neon polish to the Nexus finance, habits, and progress modules while preserving the features already implemented by the previous agent.

**Architecture:** Keep each desktop module self-contained with inline CSS and local JavaScript renderers. Add static contract tests first, then enhance each module without removing existing IDs or bridge calls. Use existing data from `finance_snapshot`, `habit_history`, `habits_list`, `user_stats`, `study_stats_list`, and `study_recommendations`.

**Tech Stack:** Python tests with `pytest`; pywebview module HTML; inline CSS; plain JavaScript Canvas 2D; optional Playwright/Chromium for rendered QA.

---

### Task 1: Static Visual Contracts

**Files:**
- Modify: `tests/test_nexus_window_theme.py`

- [ ] **Step 1: Write failing tests**

Add tests that prove Phase 6 has canvas surfaces and resize-safe renderers:

```python
def test_phase6_finance_declares_canvas_telemetry():
    html = (MODULES / "finance.html").read_text(encoding="utf-8")

    assert 'id="financeTrendCanvas"' in html
    assert 'id="financeCategoryCanvas"' in html
    assert "drawFinanceTrendCanvas" in html
    assert "drawFinanceCategoryCanvas" in html
    assert "ResizeObserver" in html
    assert "<link rel=\"stylesheet\"" not in html


def test_phase6_habits_declares_momentum_canvas():
    html = (MODULES / "habits.html").read_text(encoding="utf-8")

    assert 'id="habitMomentumCanvas"' in html
    assert 'id="habitMomentumStats"' in html
    assert "drawHabitMomentumCanvas" in html
    assert "renderHabitMomentum" in html
    assert "ResizeObserver" in html
    assert "<link rel=\"stylesheet\"" not in html


def test_phase6_progress_declares_canvas_telemetry():
    html = (MODULES / "progress.html").read_text(encoding="utf-8")

    assert 'id="studyTelemetryCanvas"' in html
    assert 'id="studyTelemetryStats"' in html
    assert "drawStudyTelemetryCanvas" in html
    assert "renderStudyTelemetry" in html
    assert "ResizeObserver" in html
    assert "<link rel=\"stylesheet\"" not in html
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest tests\test_nexus_window_theme.py::test_phase6_finance_declares_canvas_telemetry tests\test_nexus_window_theme.py::test_phase6_habits_declares_momentum_canvas tests\test_nexus_window_theme.py::test_phase6_progress_declares_canvas_telemetry -q
```

Expected: fail because the new canvas IDs/functions are not present.

### Task 2: Finance Canvas Telemetry

**Files:**
- Modify: `src/ui/nexus_modules/finance.html`
- Test: `tests/test_nexus_window_theme.py`

- [ ] **Step 1: Add canvas markup without removing existing IDs**

Keep `financeTrendChart` and `financeCategoryChart` as shells. Add:

```html
<div class="telemetry-canvas-shell" id="financeTrendChart">
  <canvas id="financeTrendCanvas" aria-label="Fluxo financeiro diario"></canvas>
  <div class="telemetry-readout" id="financeTrendReadout"></div>
</div>
```

Use the same pattern for `financeCategoryCanvas` inside `financeCategoryChart`.

- [ ] **Step 2: Add inline cockpit styles**

Add `.telemetry-canvas-shell`, `.telemetry-readout`, and reduced-motion styles inside the existing `<style>` block. Use cyan/green/amber accents and avoid the option C stacked colored bars.

- [ ] **Step 3: Add renderers**

Implement:

```javascript
function drawFinanceTrendCanvas(data) { /* daily_series income/expense/net */ }
function drawFinanceCategoryCanvas(data) { /* category_breakdown radial/arc pressure */ }
function resizeFinanceCanvases(data) { drawFinanceTrendCanvas(data); drawFinanceCategoryCanvas(data); }
```

Use `devicePixelRatio`, clear the canvas, draw a subtle grid, and show an empty state when data is missing.

- [ ] **Step 4: Re-render from `load()`**

After `renderFinanceCharts(data)`, call `resizeFinanceCanvases(data)`. Add a `ResizeObserver` that redraws the last finance snapshot.

### Task 3: Habit Momentum Canvas

**Files:**
- Modify: `src/ui/nexus_modules/habits.html`
- Test: `tests/test_nexus_window_theme.py`

- [ ] **Step 1: Add a momentum panel after today progress**

Add:

```html
<div class="momentum-panel">
  <div class="momentum-head">
    <div>
      <div class="receipt-label">Momentum</div>
      <h3>Ritmo dos ultimos 30 dias</h3>
    </div>
    <div class="momentum-stats" id="habitMomentumStats"></div>
  </div>
  <canvas id="habitMomentumCanvas" aria-label="Momentum dos habitos"></canvas>
</div>
```

- [ ] **Step 2: Draw habit rhythm**

Implement:

```javascript
function renderHabitMomentum(history, habits) { /* stats + draw */ }
function drawHabitMomentumCanvas(history, habits) { /* bars + line + target */ }
```

Use `habit_history` counts and `allHabits.length` to compute completion pressure.

- [ ] **Step 3: Re-render from `loadData()`**

After heatmap history is loaded, call `renderHabitMomentum(history, allHabits)`. Add `ResizeObserver` for the canvas shell.

### Task 4: Study Progress Telemetry

**Files:**
- Modify: `src/ui/nexus_modules/progress.html`
- Test: `tests/test_nexus_window_theme.py`

- [ ] **Step 1: Add telemetry panel before the existing DOM chart**

Add:

```html
<section class="chart-card telemetry-study-card">
  <div class="panel-head">
    <div>
      <div class="panel-kicker">Telemetry</div>
      <h2 class="panel-title">Mapa de desempenho e revisao</h2>
    </div>
    <div class="telemetry-stats" id="studyTelemetryStats"></div>
  </div>
  <canvas id="studyTelemetryCanvas" aria-label="Telemetry de estudos"></canvas>
</section>
```

- [ ] **Step 2: Draw subject performance**

Implement:

```javascript
function renderStudyTelemetry(rows, recommendations) { /* stats + draw */ }
function drawStudyTelemetryCanvas(rows, recommendations) { /* radar/columns without option C bars */ }
```

Use subject accuracy, weak subjects, and `flashcards_due`.

- [ ] **Step 3: Keep existing chart**

Do not remove `studyAccuracyChart` or `.chart-bar`, because existing tests assert them.

### Task 5: Verification

**Files:**
- No new source files expected.

- [ ] **Step 1: Run focused tests**

```powershell
python -m pytest tests\test_nexus_window_theme.py -q
```

- [ ] **Step 2: Run Nexus feature tests**

```powershell
python -m pytest tests\test_nexus_life.py tests\test_nexus_quiz.py tests\test_nexus_window_theme.py tests\test_gemini_tools.py -q
```

- [ ] **Step 3: Rendered QA**

Use Browser plugin if available. If Browser tools are unavailable in the active tool list, use Playwright/Chromium as fallback to capture desktop and mobile screenshots of the composed module pages.

- [ ] **Step 4: Manual visual checks**

Confirm:

- Canvas elements are nonblank with seeded data.
- Mobile layout does not overflow.
- Light/dark theme variables still drive colors.
- Existing buttons and bridge calls remain present.
- Motion is disabled or reduced under `prefers-reduced-motion`.
