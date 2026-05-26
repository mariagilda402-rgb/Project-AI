from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AgentMode(str, Enum):
    CHAT = "chat"
    PC = "pc"
    NEXUS = "nexus"
    NEWS = "news"
    PSYCH_COACH = "psych_coach"
    WORKFLOW = "workflow"
    FILES = "files"
    WEB = "web"
    VISION = "vision"


@dataclass(frozen=True)
class ModeResolution:
    mode: AgentMode
    confidence: float
    reason: str
    explicit: bool = False
    risky: bool = False
    open_window: bool = False


@dataclass(frozen=True)
class RuntimeContext:
    resolution: ModeResolution
    allowed_tool_names: frozenset[str] = field(default_factory=frozenset)

    @property
    def mode(self) -> AgentMode:
        return self.resolution.mode
