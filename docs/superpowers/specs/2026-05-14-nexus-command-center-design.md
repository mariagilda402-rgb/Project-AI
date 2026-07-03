# Nexus Command Center Design

## Decision

The user authorized Codex to choose the best option and order without further questions unless a decision is important. The selected direction is A1: a dense Command Center that feels like the Nexus panel, with rounded neon borders, dark/light themes, compact operational cards, and direct access to finance, habits, study, notes, goals, rewards, quiz, and progress.

## Scope For This Package

This package builds the visual foundation and first cockpit pass. It does not replace the existing Python/SQLite/pywebview architecture; it makes the existing modules feel like one product and prepares later packages for deeper AI workflows.

## Architecture

The existing `desktop_app.py` composition remains the single chrome/frame entry point for module windows. It will add a theme-aware wrapper and a compact theme control to every Nexus module. `nexus_frame.css` will own shared window chrome tokens, dark/light variables, neon border behavior, and common control polish.

Each module keeps its own inline `<style>` rules, following `docs/NEXUS_WINDOW_STYLING_GUIDE.md`. The first major surface is `overview.html`, redesigned as the Command Center. It reads existing bridge methods only, so this package avoids schema changes.

## Components

- Frame shell: rounded pywebview frame, neon border, close button, theme toggle, dark/light variables.
- Boot helper: persistent local theme through `localStorage`, exposed through `nxToggleTheme()`.
- Command Center overview: sidebar navigation, status strip, XP/streak/points/balance, today habits, monthly finances, study queue, goals/rewards, and AI signal feed.
- Empty/error states: panels remain useful when bridge data is missing or empty.

## Data Flow

`overview.html` calls existing bridge methods: `user_stats`, `global_streak`, `habits_list`, `finance_snapshot`, `flashcards_due`, `goals_list`, `rewards_list`, and `study_stats_list`. Navigation continues through `pywebview.api.jump(module, "{}")`. Finance and habits still write through their existing module-specific forms and AI structured commands.

## Error Handling

Each overview panel renders a short empty state if its bridge call fails or returns no rows. Theme initialization must never break pywebview startup; invalid theme values fall back to dark mode.

## Testing

Add Python tests for the frame composition contract, theme fallback, persistent theme API presence, frame CSS light-theme selectors, and overview Command Center structure. Run the targeted tests first red, then implement, then run the full Nexus life test slice.

## Later Packages

1. AI command receipts for finance and habits, including animated "adding" states and date interpretation receipts.
2. Habit preset workflow from goals, richer streak charts, and shop redemption history.
3. MindPalace study workspace with note tabs, flashcard generation, spaced repetition reminders, quizzes/simulado progress, and teacher mode.
