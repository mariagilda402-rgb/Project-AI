from src.jarvis_unified.memory_gateway import MemoryGateway


class FakeNexusService:
    def get_study_recommendations(self, limit):
        return [{"title": "Matematica", "limit": limit}]


def test_memory_gateway_returns_compact_context():
    gateway = MemoryGateway(nexus_service=FakeNexusService())

    result = gateway.query("matematica", limit=3)

    assert result["query"] == "matematica"
    assert result["sources"][0]["source"] == "nexus_study"


def test_memory_gateway_accepts_mobile_event():
    gateway = MemoryGateway(nexus_service=FakeNexusService())

    merged = gateway.merge_mobile_event({
        "kind": "note_saved",
        "title": "Raiz quadrada",
        "summary": "Resumo curto",
    })

    assert merged["ok"] is True
    assert merged["kind"] == "note_saved"

