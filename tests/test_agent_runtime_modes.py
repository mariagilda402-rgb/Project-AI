from __future__ import annotations

from src.agent.mode_resolver import ModeResolver
from src.agent.runtime_modes import AgentMode
from src.agent.toolsets import ToolsetSelector


def test_mode_resolver_infers_pc_mode_for_app_command():
    result = ModeResolver().resolve("Abra o Spotify e toque uma musica")

    assert result.mode == AgentMode.PC
    assert result.explicit is False
    assert result.confidence >= 0.7


def test_mode_resolver_infers_news_mode_and_visible_window():
    result = ModeResolver().resolve(
        "Abra o modo noticias e procure sobre inteligencia artificial"
    )

    assert result.mode == AgentMode.NEWS
    assert result.explicit is True
    assert result.open_window is True


def test_mode_resolver_infers_psych_coach_mode():
    result = ModeResolver().resolve(
        "Quero conversar sobre meu dia, estou bem desanimado"
    )

    assert result.mode == AgentMode.PSYCH_COACH
    assert result.reason


def test_mode_resolver_marks_destructive_file_request_as_risky():
    result = ModeResolver().resolve("Limpa e apaga essa pasta de downloads")

    assert result.mode == AgentMode.FILES
    assert result.risky is True


def test_mode_resolver_defaults_short_greeting_to_chat():
    result = ModeResolver().resolve("oi")

    assert result.mode == AgentMode.CHAT
    assert result.confidence == 1.0


def test_toolset_selector_limits_chat_tools():
    resolution = ModeResolver().resolve("oi")
    allowed = ToolsetSelector().allowed_tools(resolution)

    assert "analyze_screen" not in allowed
    assert "manage_files" not in allowed
    assert "save_memory" in allowed


def test_toolset_selector_news_keeps_visible_window_path():
    resolution = ModeResolver().resolve("Abra o modo noticias e procure sobre IA")
    allowed = ToolsetSelector().allowed_tools(resolution)

    assert "nexus_command" in allowed
    assert "search_web" in allowed
    assert "manage_files" not in allowed


def test_toolset_selector_pc_exposes_app_and_clipboard_tools():
    resolution = ModeResolver().resolve("Abra o bloco de notas e copie o resumo")
    allowed = ToolsetSelector().allowed_tools(resolution)

    assert "open_windows_app" in allowed
    assert "run_utility" in allowed
    assert "nexus_command" not in allowed


def test_toolset_selector_psych_coach_excludes_desktop_mutation():
    resolution = ModeResolver().resolve("Estou triste, quero conversar como psicologo")
    allowed = ToolsetSelector().allowed_tools(resolution)

    assert "nexus_command" in allowed
    assert "manage_memory" in allowed
    assert "open_windows_app" not in allowed
    assert "whatsapp_send" not in allowed
