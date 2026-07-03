# Jarvis Agent Runtime, Toolsets, And Workflows Design

## Context

Jarvis/Nexus already has working foundations: native LLM providers, voice, screen vision, desktop tools, Nexus modules, structured `nexus_command`, `nexus_batch`, a dedicated News window, and agent profiles. The current weak point is not lack of features. It is that the assistant can be exposed to too many tools and instructions at once, which increases the chance of random commands, wrong tool calls, repeated tool use, or confused context.

The `hermes-agent-main` project in the repository is useful as an architecture reference. It should not replace Jarvis, because Hermes is a large general CLI/gateway agent while Jarvis is a Windows/Nexus desktop assistant. The patterns worth adapting are scoped toolsets, tool-call guardrails, layered prompts, provider profiles, scheduler/workflow concepts, and command approval boundaries.

## Approved Direction

Keep Jarvis/Nexus as the main product and adapt Hermes-style runtime patterns into the existing codebase.

The experience should feel automatic like Jarvis:

- The user speaks naturally most of the time.
- The system infers the active mode from intent.
- Explicit mode commands still work when the user wants focus, such as "enter PC mode" or "open News mode".
- Ambiguous or risky requests ask for confirmation before execution.
- Workflows can be recorded from real actions and saved as reusable routines.
- Workflows can be triggered by voice, buttons, keyboard shortcuts, schedules, mobile, or configurable clap patterns.

## Product Principles

1. Natural language first. The user should not need to memorize modes.
2. Modes are internal execution contexts, not separate products.
3. Only expose tools that match the current request, active mode, and risk level.
4. Mutating actions require stricter guardrails than read-only actions.
5. Workflows store structured actions, not raw mouse movements, whenever possible.
6. News remains a visible on-demand window, not only a hidden chat answer.
7. The psychologist/coach experience is allowed as a real conversational mode, but with safety boundaries.

## Phase 1: Agent Runtime Stabilization

Phase 1 introduces a small runtime layer around the current `AgentOrchestrator`.

### ModeResolver

`ModeResolver` classifies each user message into one or more modes:

- `chat`: normal conversation.
- `pc`: apps, windows, clipboard, screen, browser, Spotify, local utilities.
- `nexus`: habits, study, finance, notes, flashcards, quiz, progress, goals, rewards, workout.
- `news`: current news, briefings, source tracking, video search, saved stories.
- `psych_coach`: daily reflection, mood, motivation, accountability, emotional memory.
- `workflow`: create, record, save, run, edit, or schedule workflows.
- `files`: file read/write/search/move/delete operations.
- `web`: invisible research without opening a visible browser window.
- `vision`: screen analysis.

The resolver should support three levels:

- Automatic inference from the user message.
- Explicit mode activation, such as "open News mode".
- Confirmation mode when the intent is ambiguous or risky.

The first implementation can be heuristic and deterministic. It does not need another LLM call.

### ToolsetSelector

`ToolsetSelector` maps the resolved mode to allowed tool names.

Examples:

- `chat`: no mutating desktop tools.
- `pc`: `open_windows_app`, `run_utility`, `control_spotify`, `analyze_screen`, selected browser actions.
- `nexus`: `nexus_command`, `run_finance_command`, safe memory/context actions.
- `news`: `nexus_command` actions for `news_briefing`, `news_history`, `news_save_note`, `news_followup_task`, `news_flashcards_generate`, and `open_ui` for the `news` tab.
- `psych_coach`: diary, mood, goals, habits, safe memory, reflection prompts. No file deletion, WhatsApp send, finance mutation, or smart-home mutation by default.
- `workflow`: workflow create/record/save/run/list/edit plus the exact toolsets needed by each step.
- `files`: file manager tools, with destructive actions requiring confirmation.

The selector should default to the smallest useful toolset. If a request clearly needs multiple contexts, it can compose them. Example: "open News mode and save the top story to MindPalace" uses `news` plus the narrow Nexus note-save path.

### PromptBuilder

Split the function-calling prompt into layers:

- Stable identity/persona.
- Active agent profile.
- Active mode and available toolset.
- Safety/confirmation instructions.
- Long-term memory and preferences.
- Volatile context such as current time, active window, screen hints, and recent conversation.

The existing prompt can remain as the source text, but Phase 1 should stop presenting every capability as equally available on every request.

### ToolGuardrails

Introduce a guardrail controller around function calls:

- Block exact repeated tool calls with the same arguments after a threshold.
- Warn or stop when an idempotent tool returns no progress repeatedly.
- Treat mutating tools differently from read-only tools.
- Require confirmation for destructive file operations, message sending, purchases, smart-home control, or reward changes above configured thresholds.
- Stop tool loops and return a concise explanation instead of continuing to call tools.

This should be independent of provider. Gemini, NVIDIA, Groq, and marker fallback should share the same guardrail policy when possible.

### ActionExecutor

Centralize tool execution decisions before reaching `_execute_function_tool`.

The executor should:

- Check whether the selected tool is allowed in the current toolset.
- Check guardrails before and after the call.
- Route to the existing `_execute_function_tool` implementation for compatibility.
- Return normalized results that can be summarized by the assistant.

## Phase 2: Mode-Aware Tool Schemas

Update Gemini/OpenAI tool schema builders so they receive the selected toolset and only emit relevant tools. This follows the Hermes pattern of dynamic tool definitions.

Target behavior:

- A greeting should not expose screen analysis or desktop control.
- A News request should not expose file deletion or finance mutation.
- A psychologist/coach conversation should not expose desktop automation unless the user explicitly asks for it.
- A PC command can expose app/window/clipboard tools without exposing every Nexus module.

## Phase 3: Psychologist And Motivational Coach Mode

The user wants this mode to genuinely act as psychologist and motivational coach.

The design should preserve that experience while adding safety boundaries:

- Deep supportive conversation is allowed.
- It can ask reflective questions and help reframe situations.
- It can create action plans, habit changes, goals, and accountability tasks.
- It can record mood, diary entries, emotional patterns, and insights.
- It can use memory to notice patterns over days or weeks.
- It should not claim to be a licensed professional, diagnose disorders, prescribe treatment, or replace emergency help.
- If the user expresses immediate self-harm risk or danger, it should pause normal coaching and direct the user to immediate human help/emergency resources.

The toolset is narrow by default: diary, mood, goals, habits, safe memory, and optionally workout/study actions when relevant.

## Phase 4: News Mode With Visible Window

News remains a dedicated Nexus window opened on demand.

Example command:

```text
Open News mode and search the latest news about AI.
```

Expected flow:

1. Resolve mode as `news`.
2. Build a narrow News/Nexus toolset.
3. Run `news_briefing` with the requested query.
4. Open the Nexus `news` window if requested or implied by "open mode".
5. Show cards, sources, summary, timeline, video-search slot, and saved actions.
6. Later upgrades can replace video search with selected live videos and real transcript/caption extraction when a reliable source exists.

The chat may control the window, but the visual News experience stays available.

## Phase 5: Workflow Engine

Evolve `nexus_batch` into saved workflows.

### Workflow Model

Each workflow stores:

- `id`
- `name`
- `description`
- `steps`
- `triggers`
- `required_toolsets`
- `risk_level`
- `confirmation_policy`
- `created_at`
- `updated_at`

Steps should be structured actions:

```json
{
  "action": "open_app",
  "app": "Spotify"
}
```

or:

```json
{
  "action": "nexus_command",
  "payload": {"action": "open_ui", "tab": "study"}
}
```

Avoid storing raw mouse coordinates unless there is no structured alternative.

### Workflow Recording

The user can say:

```text
Start recording a workflow.
```

Then Jarvis records successful structured actions during the session. When the user says:

```text
Save this as Study Mode.
```

Jarvis creates a named workflow from the recorded action log.

The user can also ask:

```text
Save the apps and windows I currently opened as a workflow.
```

For this MVP, Jarvis should save detectable structured state, such as known opened apps, URLs it opened, Nexus tabs, timers, playlists, and commands it executed. Exact third-party app layout restoration can be a later enhancement.

### Workflow Triggers

Supported trigger types:

- Voice command.
- Button in the Nexus/desktop panel.
- Keyboard shortcut.
- Schedule/time.
- Mobile command.
- Clap pattern.

Clap triggers should be configurable:

- disabled by default or opt-in.
- pattern such as two claps or three claps.
- optional confirmation phrase for risky workflows.
- cooldown to avoid accidental repeated activation.
- confidence threshold and noise calibration.

Safe workflows such as "Focus Mode" can run directly after a clap. Risky workflows should ask for confirmation.

## Data Flow

```text
User message
-> ModeResolver
-> ToolsetSelector
-> PromptBuilder
-> LLM function calling
-> ActionExecutor
-> ToolGuardrails before/after call
-> Existing tools/Nexus services
-> Normalized result
-> User-facing reply or UI update
```

For workflows:

```text
User action request
-> ActionExecutor
-> successful structured action log
-> optional WorkflowRecorder
-> saved WorkflowDefinition
-> TriggerRegistry
-> WorkflowRunner
-> ActionExecutor for each step
```

## Implementation Order

1. Add runtime data models for modes, toolsets, and tool-call context.
2. Add deterministic `ModeResolver` tests and implementation.
3. Add `ToolsetSelector` tests and implementation.
4. Filter dynamic tools before schema generation in `AgentOrchestrator`.
5. Add guardrail tests and a provider-neutral guardrail controller.
6. Route function calls through `ActionExecutor`.
7. Refactor prompt construction to include active mode/toolset context.
8. Add `psych_coach` mode prompt/toolset.
9. Add `news` mode routing that preserves the visible window behavior.
10. Add workflow definitions, recording, listing, saving, and running.
11. Add trigger registry with voice/button/schedule first.
12. Add clap-trigger detector behind opt-in configuration.

## Testing Strategy

Focused tests should cover:

- Mode inference for representative commands.
- Explicit mode activation.
- Ambiguous/risky request confirmation.
- Toolset selection for chat, PC, Nexus, News, Psych/Coach, Workflow, Files, Web, and Vision.
- Schema builders only exposing allowed tools.
- Guardrail blocking repeated no-progress calls.
- Mutating tools requiring stricter confirmation.
- News commands opening the visible News window when requested.
- Psych/Coach mode excluding unrelated toolsets by default.
- Workflow recording only successful structured actions.
- Workflow run executing steps in order.
- Clap trigger config parsing and cooldown behavior.

## Out Of Scope For The First Implementation

- Replacing `AgentOrchestrator` entirely.
- Importing the full Hermes runtime.
- Full live YouTube transcript extraction for every news video.
- Pixel-perfect app/window layout replay.
- Smart-home automation beyond a future protected toolset.
- Mobile app implementation.

## Open Decisions

- Exact UI controls for editing saved workflows can be designed after the backend model exists.
- The first clap detection implementation can be lightweight and local; production-quality noise handling may need a separate audio calibration pass.
- Provider-specific schema quirks should be handled after the generic toolset filter is in place.
