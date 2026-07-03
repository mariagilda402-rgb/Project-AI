from __future__ import annotations

from src.agent.runtime_modes import AgentMode, ModeResolution


BASE_SAFE_TOOLS = frozenset({"save_memory", "manage_memory"})

MODE_TOOLSETS: dict[AgentMode, frozenset[str]] = {
    AgentMode.CHAT: BASE_SAFE_TOOLS,
    AgentMode.PC: frozenset(
        {
            "open_windows_app",
            "manage_apps",
            "open_or_run",
            "run_utility",
            "control_spotify",
            "analyze_screen",
            "search_web",
            "control_visualizer",
        }
    ),
    AgentMode.NEXUS: frozenset(
        {
            "nexus_command",
            "run_finance_command",
            "run_productivity_command",
            "manage_memory",
            "save_memory",
            "control_visualizer",
        }
    ),
    AgentMode.NEWS: frozenset(
        {
            "nexus_command",
            "search_web",
            "manage_memory",
            "save_memory",
            "control_visualizer",
        }
    ),
    AgentMode.PSYCH_COACH: frozenset(
        {
            "nexus_command",
            "manage_memory",
            "save_memory",
            "run_productivity_command",
            "control_visualizer",
        }
    ),
    AgentMode.WORKFLOW: frozenset(
        {
            "nexus_command",
            "open_windows_app",
            "manage_apps",
            "open_or_run",
            "run_utility",
            "control_spotify",
            "analyze_screen",
            "search_web",
            "control_visualizer",
            "manage_memory",
            "save_memory",
        }
    ),
    AgentMode.FILES: frozenset(
        {
            "manage_files",
            "analyze_screen",
            "manage_memory",
            "save_memory",
            "control_visualizer",
        }
    ),
    AgentMode.WEB: frozenset(
        {
            "search_web",
            "manage_memory",
            "save_memory",
            "control_visualizer",
        }
    ),
    AgentMode.VISION: frozenset(
        {
            "analyze_screen",
            "manage_memory",
            "save_memory",
            "control_visualizer",
        }
    ),
}


class ToolsetSelector:
    def allowed_tools(self, resolution: ModeResolution) -> frozenset[str]:
        tools = set(MODE_TOOLSETS.get(resolution.mode, BASE_SAFE_TOOLS))
        if resolution.risky:
            tools.add("control_visualizer")
        return frozenset(tools)
