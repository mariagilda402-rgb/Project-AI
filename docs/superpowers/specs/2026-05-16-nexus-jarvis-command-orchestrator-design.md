# Nexus Jarvis Command Orchestrator Design

## Context

The Nexus Life OS already has working modules for finances, habits, tasks, notes, SRS, progress, rewards, and quiz. The missing piece for the next user experience is orchestration: Jarvis should understand multi-action requests, execute each Nexus action in order, and move through windows with visible animation payloads before leaving the final requested panel open.

The current desktop signal queue keeps only the last window-open request, so sequential commands can lose intermediate windows. The `open_ui` action also maps only a subset of modules.

## Approved Direction

Implement the next milestone as Phase 7: Jarvis Command Orchestrator MVP.

This milestone does not attempt the full news briefing system or theme generator yet. It builds the execution rail those features will use.

## Scope

Phase 7 MVP includes:

- Preserve multiple queued Nexus window-open requests instead of replacing earlier ones.
- Space queued windows so temporary receipt animations have time to appear.
- Expand `open_ui` to support all current Nexus modules by natural names.
- Add a structured `nexus_batch` action that runs ordered steps such as finance add, habit add, then open notes.
- Decorate window payloads created during a batch with `batch_id`, `batch_step`, `batch_total`, and `hold_ms`.
- Teach the local `NexusManagerSkill` to parse the example request:
  - add an expense
  - add a habit with time in the description
  - open the studies/MindPalace window
- Update tool descriptions and prompts so LLM function calling knows when to use `nexus_batch`.

## Out Of Scope

These remain for later phases:

- Per-window theme presets and AI-generated theme presets.
- News briefing window with video, transcript lanes, TTS synchronization, and clip selection.
- Rich UI animation redesign inside every module.
- True concurrent multi-window desktop layout. The current desktop shell still opens one Nexus module at a time, so the sequence shows one temporary module after another and ends on the final requested module.

## Data And Flow

`nexus_command` receives either a single action or:

```json
{
  "action": "nexus_batch",
  "steps": [
    {"action": "finance_add", "type": "expense", "amount": "500", "category": "Alimentacao", "description": "alimentacao"},
    {"action": "habit_add", "name": "Caminhar", "description": "Horario sugerido: 14:00", "xp_reward": "50"},
    {"action": "open_ui", "tab": "notes"}
  ]
}
```

The service executes steps synchronously and lets each step emit its normal UI receipt. During the batch, payloads are decorated with sequence metadata. The desktop scheduler drains queued window requests one by one and waits `hold_ms` before opening the next module.

## Testing

Add RED/GREEN tests for:

- queue preservation in `src/ui/nexus_signals.py`
- `open_ui` mapping for all module names
- `nexus_batch` sequential execution and window order
- natural compound command parsing in `NexusManagerSkill`
- tool schema/prompt advertisement of `nexus_batch` and expanded `open_ui` tabs

Run the focused tests first, then the existing Nexus suite.
