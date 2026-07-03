# AGENTS

## Purpose
This file helps AI coding agents understand the repository quickly and make productive, low-risk changes.

## Project overview
- Windows-first personal assistant / automation platform called Nexus AI / Jarvis.
- Python backend in `src/` providing voice, vision, memory, tool orchestration, and agent runtime.
- Android WebView frontend in `mobile/` and mobile APK source in `mobile-apk/`.
- Local data persisted in `data/` and SQLite databases.
- Primary runtime entrypoint: `python -m src.main`.

## Setup and test commands
- `python -m venv .venv`
- Windows shell: `.venv\Scripts\activate`
- `pip install -r requirements.txt`
- Run app: `python -m src.main`
- Run tests: `python -m pytest tests -q`

## Key directories and files
- `src/agent/`: core AI orchestration and runtime
  - `orchestrator.py`: main `AgentOrchestrator`
  - `prompts.py`: system prompts, function-calling and marker-based instructions
  - `gemini_tools.py`: tool definitions exposed to LLM providers
  - `mode_resolver.py`, `toolsets.py`, `tool_guardrails.py`: runtime mode logic and tool filtering
  - `planner.py`: plan execution and chained agent tasks
- `src/tools/`: tool implementations callable by the assistant
- `src/services/`: platform services (LLM, STT, TTS, vision, nexus sync, proactive agent)
- `src/ui/`: desktop app / PyWebView interface and bridge code
- `mobile/`: Android mobile app SPA (HTML/CSS/JS)
- `data/`: runtime state, agent profiles, memory stores

## Important conventions
- The repository is primarily Portuguese for user-facing text and comments. Keep domain terms consistent with the existing app language.
- Agent tool behavior is guarded by `ToolCallGuardrailController` and mode-specific toolsets.
- New tools should be registered in `src/agent/gemini_tools.py` and wired through the tool registry.
- Avoid broad refactors of `AgentOrchestrator` unless the change clearly preserves the existing mode/tool architecture.
- UI behavior changes should usually be localized to `src/ui/desktop_app.py`, `src/ui/nexus_desktop_bridge.py`, and `src/main.py`.

## Helpful documentation
- `README.md`: high-level architecture and user-facing feature summary
- `contexto.md`: project mission, scope, and architecture notes
- `docs/NEXUS_CHAT_HANDOFF_PROMPT_2026-05-26.md`: handoff guidance and product vision for agents
- `docs/superpowers/specs/2026-05-16-nexus-news-memory-mindpalace-design.md`: example of agent-facing design specs

## When contributing
- Preserve or extend existing local-first memory and action safety patterns.
- Prefer explicit, testable tool interfaces over free-form “do anything” prompts.
- Link to docs instead of duplicating long design descriptions.
- Keep changes small when modifying core agent runtime to avoid regressions in tool orchestration.
