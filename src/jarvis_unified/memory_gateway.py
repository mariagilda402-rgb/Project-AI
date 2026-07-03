from __future__ import annotations

from typing import Any


class MemoryGateway:
    def __init__(
        self,
        memory_store: Any = None,
        vector_memory: Any = None,
        structured_memory: Any = None,
        nexus_service: Any = None,
    ) -> None:
        self.memory_store = memory_store
        self.vector_memory = vector_memory
        self.structured_memory = structured_memory
        self.nexus_service = nexus_service

    def query(self, query: str, limit: int = 8) -> dict[str, Any]:
        sources: list[dict[str, Any]] = []
        lim = max(1, int(limit or 8))
        if self.memory_store and hasattr(self.memory_store, "get_recent_short_term"):
            try:
                sources.append({
                    "source": "short_term",
                    "items": self.memory_store.get_recent_short_term(limit=lim),
                })
            except Exception:
                pass
        if self.nexus_service and hasattr(self.nexus_service, "build_memory_graph_context"):
            try:
                sources.append({
                    "source": "nexus_graph",
                    "items": self.nexus_service.build_memory_graph_context(query=query, limit=lim),
                })
            except Exception:
                pass
        elif self.nexus_service and hasattr(self.nexus_service, "get_study_recommendations"):
            try:
                sources.append({
                    "source": "nexus_study",
                    "items": self.nexus_service.get_study_recommendations(lim),
                })
            except Exception:
                pass
        return {
            "ok": True,
            "query": query,
            "sources": sources,
        }

    def merge_mobile_event(self, event: dict[str, Any]) -> dict[str, Any]:
        kind = str(event.get("kind") or event.get("type") or "unknown")
        return {
            "ok": True,
            "kind": kind,
            "stored": False,
            "summary": event.get("summary") or event.get("title") or "",
        }

