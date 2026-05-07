from __future__ import annotations

from src.integrations.super_productivity import SuperProductivityConnector

from .base import ToolResult


class ProductivityTool:
    name = "productivity"
    description = "Adiciona habitos e atualiza tarefas."
    critical = False

    def __init__(self, connector: SuperProductivityConnector) -> None:
        self.connector = connector

    def run(self, command: str) -> ToolResult:
        lowered = command.lower()
        if "habito" in lowered or "hábito" in lowered:
            return ToolResult(True, self.connector.add_habit(command))
        if "tarefa" in lowered:
            return ToolResult(True, self.connector.update_task(command))
        return ToolResult(False, "Comando de produtividade nao reconhecido.")
