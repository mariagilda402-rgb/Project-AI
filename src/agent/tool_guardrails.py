from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ToolGuardrailDecision:
    allow: bool
    message: str = ""


class ToolCallGuardrailController:
    def __init__(self, exact_repeat_limit: int = 3, no_progress_limit: int = 3) -> None:
        self.exact_repeat_limit = max(1, exact_repeat_limit)
        self.no_progress_limit = max(1, no_progress_limit)
        self._call_counts: dict[str, int] = {}
        self._result_counts: dict[tuple[str, str], int] = {}

    def reset_turn(self) -> None:
        self._call_counts.clear()
        self._result_counts.clear()

    def before_call(
        self, tool_name: str, args: Mapping[str, Any] | None
    ) -> ToolGuardrailDecision:
        key = self._call_key(tool_name, args)
        count = self._call_counts.get(key, 0)
        if count >= self.exact_repeat_limit:
            return ToolGuardrailDecision(
                False, f"Chamada repetida bloqueada: {tool_name}."
            )
        self._call_counts[key] = count + 1
        return ToolGuardrailDecision(True)

    def after_call(
        self, tool_name: str, args: Mapping[str, Any] | None, result: Any
    ) -> ToolGuardrailDecision:
        text = self._normalize_result(result)
        result_key = (tool_name, text)
        count = self._result_counts.get(result_key, 0) + 1
        self._result_counts[result_key] = count
        if count >= self.no_progress_limit and self._looks_no_progress(text):
            return ToolGuardrailDecision(
                False,
                f"Ferramenta interrompida por resultado sem progresso: {tool_name}.",
            )
        return ToolGuardrailDecision(True)

    @staticmethod
    def _call_key(tool_name: str, args: Mapping[str, Any] | None) -> str:
        try:
            payload = json.dumps(args or {}, sort_keys=True, ensure_ascii=False)
        except TypeError:
            payload = repr(args)
        return f"{tool_name}:{payload}"

    @staticmethod
    def _normalize_result(result: Any) -> str:
        return " ".join(str(result or "").strip().lower().split())[:500]

    @staticmethod
    def _looks_no_progress(text: str) -> bool:
        if not text:
            return True
        markers = [
            "sem mudanca",
            "sem mudança",
            "sem resultados",
            "nenhum resultado",
            "nao executado",
            "não executado",
            "falhou",
            "erro",
        ]
        return any(marker in text for marker in markers)
