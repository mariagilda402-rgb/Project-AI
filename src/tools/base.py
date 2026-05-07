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
