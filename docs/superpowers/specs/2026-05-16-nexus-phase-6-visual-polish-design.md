# Nexus Phase 6 Visual Polish Design

## Context

The handoff file still lists six implementation priorities. The current codebase already contains evidence for the first five priority slices:

- SRS due flashcards can create a review task from `progress.html`.
- Habits can be edited through UI, bridge, database update methods, and natural language manager handling.
- Custom rewards can be created/deleted through the store UI, with update support in backend/bridge.
- MindPalace has a web capture panel that saves pasted content with source URL.
- Quiz supports quick/medium/full modes, live timer, and result breakdown by area.

The remaining near-term priority is Phase 6: visual polish and real charting. The broader product backlog from the handoff still exists, but it is outside this phase.

## Approved Visual Direction

Use the "Telemetry Cockpit" look from option A as the visual language:

- Dense, useful dashboard surfaces.
- Dark neon glassmorphism without excessive decoration.
- Canvas-driven telemetry panels for money, habits, and study progress.
- Subtle grid, glow, scanline, and reveal motion.
- Cyan, green, amber, and magenta accents, balanced so the UI does not become one-note purple.
- No colored progress-bar stack from option C.

Include the information density from all three concepts where it helps the real workflow:

- Finance should show trend, income/expense/net signal, category pressure, debt impact, and quick insight.
- Habits should show momentum, streak signal, weekly cadence, completion heat, and XP movement.
- Progress should show study accuracy, weak areas, pending SRS load, and next actions.
- Overview should feel like a command center summary, not a marketing page.

## Scope

### Finance

Add a real canvas chart while preserving existing DOM contracts and IDs used by tests. The chart should render monthly telemetry from existing snapshot data:

- Income, expense, and net result over the selected period.
- Debt-aware visual cues using existing finance insight fields.
- Empty states that still look intentional.
- Resize-safe rendering with device pixel ratio handling.

### Habits

Add a canvas-based momentum panel alongside the existing heatmap:

- Last 30 days completion rhythm.
- Expected-vs-completed signal where the available data supports it.
- Streak/XP visual reinforcement without replacing current controls.
- Keep habit edit, preset, and completion workflows unchanged.

### Progress

Upgrade the study chart surface while keeping current SRS task creation intact:

- Visualize subject performance and pending review pressure.
- Preserve weak-subject recommendations and action panel.
- Avoid the option C colored-bar style.

### Overview

Apply light polish only if shared CSS or component motifs naturally improve the dashboard:

- Better module summary cards.
- Subtle motion and visual consistency with the new telemetry language.
- No major dashboard rewrite in this phase.

## Out Of Scope

This phase will not implement:

- Monthly category budgets.
- Recurring expenses, installment debts, or multi-wallet finance.
- Rich Markdown/Notion editor blocks.
- Real ENEM open dataset import.
- New natural language command families beyond what already exists.
- A full layout personalization system.

## Architecture

Keep each Nexus module self-contained:

- No new external CSS files.
- No new `<link rel="stylesheet">` inside module HTML.
- Module CSS stays inline inside each `.html` file.
- Use `#nx-app-wrapper` specificity for styles that must win over the frame.
- Avoid breaking existing element IDs expected by static tests.

Canvas helpers should stay inside the module scripts unless duplication becomes painful. Each canvas renderer should:

- Read from existing bridge responses.
- Handle missing or sparse data gracefully.
- Scale for high-DPI screens.
- Re-render on resize and data refresh.
- Respect `prefers-reduced-motion` for decorative animation.

## Testing

Use TDD for the implementation:

- Add static tests that require the new canvas IDs, renderer functions, resize hooks, and no external module CSS.
- Run the focused window tests first.
- Run the Nexus feature tests after implementation.
- Run a rendered UI check with Browser or Playwright, including desktop and mobile viewports.

## Acceptance Criteria

- Finance, habits, and progress expose canvas chart surfaces backed by real app data.
- Existing workflows still work: finance add/edit/delete, habit edit/complete, SRS task creation, quiz review.
- No removed IDs or broken bridge method names.
- The visual result follows option A while carrying the useful information from B/C, excluding option C colored bars.
- Theme variables still support dark and light modes.
- Motion is subtle, purposeful, and reduced when the user prefers reduced motion.
