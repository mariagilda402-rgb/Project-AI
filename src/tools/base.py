from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ToolResult:
    ok: bool
    message: str


class Tool(Protocol):
    name: str
    description: str
    critical: bool

    def run(self, command: str) -> ToolResult:
        ...

class BaseTool:
    @property
    def name(self) -> str:
        raise NotImplementedError
        
    @property
    def description(self) -> str:
        return ""
        
    @property
    def critical(self) -> bool:
        return False
        
    @property
    def parameters(self) -> dict:
        return {}
        
    def execute(self, args: dict, context: dict = None) -> str:
        raise NotImplementedError
        
    def run(self, command: str) -> ToolResult:
        # Fallback to keep compatibility with old Tool Protocol
        try:
            import json
            # Tenta parsear JSON se possível
            if command.startswith("{"):
                args = json.loads(command)
            else:
                args = {"argument": command}
            res = self.execute(args)
            return ToolResult(True, str(res))
        except Exception as e:
            return ToolResult(False, f"Erro ao executar tool {self.name}: {e}")
