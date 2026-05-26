from __future__ import annotations

from .base import ToolResult


class FinanceTool:
    name = "finance"
    description = "Financas Nexus (Aether); alias para o mesmo motor que nexus/fin."
    critical = False

    def run(self, command: str) -> ToolResult:
        from src.tools.nexus import NexusTool

        return NexusTool().run(command or "")
