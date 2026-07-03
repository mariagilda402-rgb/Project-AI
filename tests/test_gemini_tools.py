from __future__ import annotations

from src.agent.gemini_tools import build_agent_tool, build_openai_agent_tools


def test_schema_filter_none_keeps_existing_static_tools():
    gemini = build_agent_tool()
    gemini_names = {fd.name for fd in (gemini.function_declarations or [])}
    openai_names = {t["function"]["name"] for t in build_openai_agent_tools()}

    assert "nexus_command" in gemini_names
    assert "open_windows_app" in gemini_names
    assert "nexus_command" in openai_names
    assert "open_windows_app" in openai_names


def test_nexus_command_schema_exposes_window_theme_actions():
    from src.agent.prompts import AGENT_SYSTEM_PROMPT_FUNCTION_CALLING

    tool = build_agent_tool()
    nexus = next(fd for fd in (tool.function_declarations or []) if fd.name == "nexus_command")

    assert "theme_generate" in nexus.description
    assert "theme_apply" in nexus.description
    assert "module" in nexus.parameters.properties
    assert "preset_id" in nexus.parameters.properties
    assert "prompt" in nexus.parameters.properties
    assert "temas por janela" in AGENT_SYSTEM_PROMPT_FUNCTION_CALLING.lower()


def test_nexus_command_schema_exposes_news_briefing():
    from src.agent.prompts import AGENT_SYSTEM_PROMPT_FUNCTION_CALLING

    tool = build_agent_tool()
    nexus = next(fd for fd in (tool.function_declarations or []) if fd.name == "nexus_command")

    assert "news_briefing" in nexus.description
    assert "news_history" in nexus.description
    assert "news_save_note" in nexus.description
    assert "news_followup_task" in nexus.description
    assert "news_flashcards_generate" in nexus.description
    assert "item_index" in nexus.parameters.properties
    assert "item" in nexus.parameters.properties
    assert "briefing" in nexus.parameters.properties
    assert "noticias" in AGENT_SYSTEM_PROMPT_FUNCTION_CALLING.lower()
    assert "mindpalace" in AGENT_SYSTEM_PROMPT_FUNCTION_CALLING.lower()
    openai_tools = build_openai_agent_tools()
    openai_nexus = next(t for t in openai_tools if t["function"]["name"] == "nexus_command")
    assert "news_briefing" in openai_nexus["function"]["description"]
    assert "news_save_note" in openai_nexus["function"]["description"]
    assert "news_followup_task" in openai_nexus["function"]["description"]
    assert "news_flashcards_generate" in openai_nexus["function"]["description"]


def test_nexus_command_schema_exposes_memory_graph():
    from src.agent.prompts import AGENT_SYSTEM_PROMPT_FUNCTION_CALLING

    tool = build_agent_tool()
    nexus = next(fd for fd in (tool.function_declarations or []) if fd.name == "nexus_command")

    assert "memory_graph" in nexus.description
    assert "memory_graph_context" in nexus.description
    assert "memory_graph" in nexus.parameters.properties["action"].description
    assert "include_markdown" in nexus.parameters.properties
    assert "grafo neural" in AGENT_SYSTEM_PROMPT_FUNCTION_CALLING.lower()
    assert "memory_graph" in AGENT_SYSTEM_PROMPT_FUNCTION_CALLING
    assert "memory_graph_context" in AGENT_SYSTEM_PROMPT_FUNCTION_CALLING

    openai_tools = build_openai_agent_tools()
    openai_nexus = next(t for t in openai_tools if t["function"]["name"] == "nexus_command")
    assert "memory_graph" in openai_nexus["function"]["description"]
    assert "memory_graph_context" in openai_nexus["function"]["description"]
    assert "include_markdown" in openai_nexus["function"]["parameters"]["properties"]


def test_nexus_command_schema_exposes_memory_graph_obsidian_io():
    from src.agent.prompts import AGENT_SYSTEM_PROMPT_FUNCTION_CALLING

    tool = build_agent_tool()
    nexus = next(fd for fd in (tool.function_declarations or []) if fd.name == "nexus_command")

    assert "memory_graph_export_obsidian" in nexus.description
    assert "memory_graph_import_obsidian" in nexus.description
    assert "folder" in nexus.parameters.properties
    assert "path" in nexus.parameters.properties
    assert "obsidian" in AGENT_SYSTEM_PROMPT_FUNCTION_CALLING.lower()
    assert "memory_graph_export_obsidian" in AGENT_SYSTEM_PROMPT_FUNCTION_CALLING
    assert "memory_graph_import_obsidian" in AGENT_SYSTEM_PROMPT_FUNCTION_CALLING

    openai_tools = build_openai_agent_tools()
    openai_nexus = next(t for t in openai_tools if t["function"]["name"] == "nexus_command")
    assert "memory_graph_export_obsidian" in openai_nexus["function"]["description"]
    assert "memory_graph_import_obsidian" in openai_nexus["function"]["description"]
    assert "folder" in openai_nexus["function"]["parameters"]["properties"]
    assert "path" in openai_nexus["function"]["parameters"]["properties"]


def test_nexus_command_schema_exposes_ops_dashboard():
    from src.agent.prompts import AGENT_SYSTEM_PROMPT_FUNCTION_CALLING

    tool = build_agent_tool()
    nexus = next(fd for fd in (tool.function_declarations or []) if fd.name == "nexus_command")

    assert "ops_dashboard" in nexus.description
    assert "ops_metric_set" in nexus.description
    assert "key" in nexus.parameters.properties
    assert "value" in nexus.parameters.properties
    assert "target" in nexus.parameters.properties
    assert "business" in AGENT_SYSTEM_PROMPT_FUNCTION_CALLING.lower()
    assert "ops_dashboard" in AGENT_SYSTEM_PROMPT_FUNCTION_CALLING

    openai_tools = build_openai_agent_tools()
    openai_nexus = next(t for t in openai_tools if t["function"]["name"] == "nexus_command")
    assert "ops_dashboard" in openai_nexus["function"]["description"]
    assert "ops_metric_set" in openai_nexus["function"]["description"]
    assert "key" in openai_nexus["function"]["parameters"]["properties"]
    assert "value" in openai_nexus["function"]["parameters"]["properties"]
    assert "target" in openai_nexus["function"]["parameters"]["properties"]


def test_build_agent_tool_has_declarations():
    tool = build_agent_tool()
    fds = tool.function_declarations or []
    names = {fd.name for fd in fds}
    assert "analyze_screen" in names
    assert "open_windows_app" in names


def test_control_visualizer_schema_advertises_particle_core_states():
    tool = build_agent_tool()
    visualizer = next(fd for fd in (tool.function_declarations or []) if fd.name == "control_visualizer")

    assert "estado visual" in visualizer.description.lower()
    assert "executando" in visualizer.parameters.properties["command"].description.lower()
    assert "emocao" in visualizer.parameters.properties["command"].description.lower()

    openai_tools = build_openai_agent_tools()
    openai_visualizer = next(t for t in openai_tools if t["function"]["name"] == "control_visualizer")
    assert "estado visual" in openai_visualizer["function"]["description"].lower()
    assert "executando" in openai_visualizer["function"]["parameters"]["properties"]["command"]["description"].lower()
    assert "emocao" in openai_visualizer["function"]["parameters"]["properties"]["command"]["description"].lower()

    from src.agent.prompts import AGENT_SYSTEM_PROMPT_FUNCTION_CALLING

    prompt = AGENT_SYSTEM_PROMPT_FUNCTION_CALLING.lower()
    assert "control_visualizer" in prompt
    assert "estado visual" in prompt


def test_openai_tools_count():
    tools = build_openai_agent_tools()
    assert len(tools) == 16
    assert tools[0]["function"]["name"]


def test_nexus_command_advertises_flashcard_generation():
    tool = build_agent_tool()
    nexus = next(fd for fd in (tool.function_declarations or []) if fd.name == "nexus_command")
    assert "flashcards_generate" in nexus.description
    assert "note_summarize" in nexus.description
    assert "note_teach" in nexus.description
    assert "subject_teach" in nexus.description
    assert "note_attach_media" in nexus.description
    assert "quiz_attempt_review" in nexus.description
    assert "quiz_flashcards_generate" in nexus.description
    assert "finance_delete" in nexus.description
    assert "finance_update" in nexus.description
    assert "nexus_batch" in nexus.description
    assert "habits" in nexus.description
    assert "tasks" in nexus.description
    assert "quiz" in nexus.description
    assert "reward_redeem" in nexus.description
    assert "goal_update" in nexus.description
    assert "theme_list" in nexus.description
    assert "theme_apply" in nexus.description
    assert "theme_generate" in nexus.description
    assert "news_briefing" in nexus.description
    assert "news_history" in nexus.description
    assert "news_save_note" in nexus.description
    assert "news_followup_task" in nexus.description
    assert "news_flashcards_generate" in nexus.description
    assert "steps" in nexus.parameters.properties
    assert "module" in nexus.parameters.properties
    assert "preset_id" in nexus.parameters.properties
    assert "prompt" in nexus.parameters.properties
    assert "max_cards" in nexus.parameters.properties
    assert "append_summary" in nexus.parameters.properties
    assert "question" in nexus.parameters.properties
    assert "media_url" in nexus.parameters.properties
    assert "caption" in nexus.parameters.properties
    assert "attempt_id" in nexus.parameters.properties
    assert "only_wrong" in nexus.parameters.properties
    assert "transaction_id" in nexus.parameters.properties
    assert "target_description" in nexus.parameters.properties
    assert "new_amount" in nexus.parameters.properties
    assert "new_notes" in nexus.parameters.properties
    assert "reward_name" in nexus.parameters.properties
    assert "progress" in nexus.parameters.properties
    assert "item" in nexus.parameters.properties
    assert "briefing" in nexus.parameters.properties
    assert "item_index" in nexus.parameters.properties

    openai_tools = build_openai_agent_tools()
    openai_nexus = next(t for t in openai_tools if t["function"]["name"] == "nexus_command")
    assert "flashcards_generate" in openai_nexus["function"]["description"]
    assert "note_summarize" in openai_nexus["function"]["description"]
    assert "note_teach" in openai_nexus["function"]["description"]
    assert "subject_teach" in openai_nexus["function"]["description"]
    assert "note_attach_media" in openai_nexus["function"]["description"]
    assert "quiz_attempt_review" in openai_nexus["function"]["description"]
    assert "quiz_flashcards_generate" in openai_nexus["function"]["description"]
    assert "finance_delete" in openai_nexus["function"]["description"]
    assert "finance_update" in openai_nexus["function"]["description"]
    assert "nexus_batch" in openai_nexus["function"]["description"]
    assert "reward_redeem" in openai_nexus["function"]["description"]
    assert "goal_update" in openai_nexus["function"]["description"]
    assert "theme_list" in openai_nexus["function"]["description"]
    assert "theme_apply" in openai_nexus["function"]["description"]
    assert "theme_generate" in openai_nexus["function"]["description"]
    assert "news_briefing" in openai_nexus["function"]["description"]
    assert "news_history" in openai_nexus["function"]["description"]
    assert "news_save_note" in openai_nexus["function"]["description"]
    assert "news_followup_task" in openai_nexus["function"]["description"]
    assert "news_flashcards_generate" in openai_nexus["function"]["description"]
    assert "steps" in openai_nexus["function"]["parameters"]["properties"]
    assert "module" in openai_nexus["function"]["parameters"]["properties"]
    assert "preset_id" in openai_nexus["function"]["parameters"]["properties"]
    assert "prompt" in openai_nexus["function"]["parameters"]["properties"]
    assert "max_cards" in openai_nexus["function"]["parameters"]["properties"]
    assert "append_summary" in openai_nexus["function"]["parameters"]["properties"]
    assert "question" in openai_nexus["function"]["parameters"]["properties"]
    assert "media_url" in openai_nexus["function"]["parameters"]["properties"]
    assert "caption" in openai_nexus["function"]["parameters"]["properties"]
    assert "attempt_id" in openai_nexus["function"]["parameters"]["properties"]
    assert "only_wrong" in openai_nexus["function"]["parameters"]["properties"]
    assert "transaction_id" in openai_nexus["function"]["parameters"]["properties"]
    assert "target_description" in openai_nexus["function"]["parameters"]["properties"]
    assert "new_amount" in openai_nexus["function"]["parameters"]["properties"]
    assert "new_notes" in openai_nexus["function"]["parameters"]["properties"]
    assert "reward_name" in openai_nexus["function"]["parameters"]["properties"]
    assert "progress" in openai_nexus["function"]["parameters"]["properties"]
    assert "item" in openai_nexus["function"]["parameters"]["properties"]
    assert "briefing" in openai_nexus["function"]["parameters"]["properties"]
    assert "item_index" in openai_nexus["function"]["parameters"]["properties"]


def test_function_prompt_guides_nexus_batch_for_multi_action_requests():
    from src.agent.prompts import AGENT_SYSTEM_PROMPT_FUNCTION_CALLING

    assert "nexus_batch" in AGENT_SYSTEM_PROMPT_FUNCTION_CALLING
    assert "mais de uma ação" in AGENT_SYSTEM_PROMPT_FUNCTION_CALLING
