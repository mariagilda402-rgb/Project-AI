from __future__ import annotations

from src.agent.orchestrator import AgentOrchestrator


class FakeLLM:
    primary_llm_provider = "nvidia"
    nvidia_client = object()
    nvidia_model = "test-model"

    def wants_gemini_native_tools(self):
        return False

    def wants_nvidia_native_tools(self):
        return True

    def wants_groq_native_tools(self):
        return False

    def generate_embedding(self, text):
        return None

    def chat_with_openai_tools(self, **kwargs):
        self.kwargs = kwargs
        return "feito"


class FakeVision:
    pass


class FakeTools:
    tools = []


class FakeMemory:
    def __init__(self):
        self.short = []

    def add_short_term(self, role, content):
        self.short.append((role, content))

    def maybe_record_persona_note(self, text):
        pass

    def get_recent_short_term(self, limit=10):
        return [{"role": "user", "content": "Abra o modo noticias"}]

    def get_long_term(self, key, default=None):
        return default

    def should_summarize(self):
        return False


class FakeSemanticMemory:
    enabled = False


def test_orchestrator_filters_openai_tools_for_news_request(monkeypatch):
    monkeypatch.setattr("src.agent.orchestrator.SemanticMemory", FakeSemanticMemory)
    monkeypatch.setattr("src.agent.orchestrator.build_proactive_context", lambda: "")
    monkeypatch.setattr(
        AgentOrchestrator,
        "_post_process_async",
        lambda self, text, final: None,
    )

    llm = FakeLLM()
    orchestrator = AgentOrchestrator(llm, FakeVision(), FakeTools(), FakeMemory())

    list(orchestrator.handle_user_message("Abra o modo noticias e procure IA"))

    names = {tool["function"]["name"] for tool in llm.kwargs["tools"]}
    nexus_tool = next(
        tool for tool in llm.kwargs["tools"]
        if tool["function"]["name"] == "nexus_command"
    )
    nexus_desc = nexus_tool["function"]["description"]
    assert "nexus_command" in names
    assert "search_web" in names
    assert "manage_files" not in names
    assert "open_windows_app" not in names
    assert "news_briefing" in nexus_desc
    assert "finance_delete" not in nexus_desc
    assert "reward_redeem" not in nexus_desc
    assert "Modo ativo: news" in llm.kwargs["system_instruction"]
