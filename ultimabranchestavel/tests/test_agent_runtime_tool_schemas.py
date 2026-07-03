from __future__ import annotations

from src.agent.gemini_tools import build_agent_tool, build_openai_agent_tools


def _gemini_names(allowed: set[str]) -> set[str]:
    tool = build_agent_tool(allowed_tool_names=allowed)
    return {fd.name for fd in (tool.function_declarations or [])}


def _openai_names(allowed: set[str]) -> set[str]:
    return {
        item["function"]["name"]
        for item in build_openai_agent_tools(allowed_tool_names=allowed)
    }


def test_gemini_schema_filters_to_news_tools():
    names = _gemini_names({"nexus_command", "search_web", "save_memory"})

    assert names == {"nexus_command", "search_web", "save_memory"}


def test_openai_schema_filters_to_pc_tools():
    names = _openai_names({"open_windows_app", "run_utility", "control_spotify"})

    assert "open_windows_app" in names
    assert "run_utility" in names
    assert "control_spotify" in names
    assert "nexus_command" not in names
    assert "manage_files" not in names


def test_schema_filter_empty_set_exposes_no_tools():
    assert _openai_names(set()) == set()


def test_schema_filter_none_preserves_default_behavior():
    default_names = {
        item["function"]["name"] for item in build_openai_agent_tools()
    }

    assert "nexus_command" in default_names


def test_news_mode_nexus_schema_only_advertises_news_actions():
    gemini = build_agent_tool(
        allowed_tool_names={"nexus_command"},
        active_mode="news",
    )
    gemini_nexus = next(fd for fd in (gemini.function_declarations or []) if fd.name == "nexus_command")

    assert "news_briefing" in gemini_nexus.description
    assert "news_save_note" in gemini_nexus.description
    assert "finance_delete" not in gemini_nexus.description
    assert "reward_redeem" not in gemini_nexus.description
    assert "ops_dashboard" not in gemini_nexus.description
    assert set(gemini_nexus.parameters.properties) == {
        "action",
        "query",
        "limit",
        "item",
        "briefing",
        "item_index",
        "subject",
        "due_date",
        "max_cards",
        "tab",
    }

    openai_nexus = build_openai_agent_tools(
        allowed_tool_names={"nexus_command"},
        active_mode="news",
    )[0]
    desc = openai_nexus["function"]["description"]
    props = openai_nexus["function"]["parameters"]["properties"]

    assert "news_briefing" in desc
    assert "finance_delete" not in desc
    assert "amount" not in props
    assert "reward_name" not in props


def test_psych_coach_mode_nexus_schema_excludes_unrelated_actions():
    gemini = build_agent_tool(
        allowed_tool_names={"nexus_command"},
        active_mode="psych_coach",
    )
    nexus = next(fd for fd in (gemini.function_declarations or []) if fd.name == "nexus_command")

    assert "habit_add" in nexus.description
    assert "goal_update" in nexus.description
    assert "note_save" in nexus.description
    assert "news_briefing" not in nexus.description
    assert "finance_delete" not in nexus.description
    assert "reward_redeem" not in nexus.description
    assert "ops_dashboard" not in nexus.description
    assert "amount" not in nexus.parameters.properties
    assert "reward_name" not in nexus.parameters.properties
    assert "content" in nexus.parameters.properties


def test_default_nexus_schema_stays_full_when_active_mode_is_missing():
    openai_nexus = next(
        t for t in build_openai_agent_tools(allowed_tool_names={"nexus_command"})
        if t["function"]["name"] == "nexus_command"
    )

    desc = openai_nexus["function"]["description"]
    props = openai_nexus["function"]["parameters"]["properties"]

    assert "finance_delete" in desc
    assert "news_briefing" in desc
    assert "reward_redeem" in desc
    assert "ops_dashboard" in desc
    assert "amount" in props
    assert "reward_name" in props
