from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from .base import ToolResult


class FinanceTool:
    name = "finance"
    description = "Adiciona gastos e mostra relatorios diarios."
    critical = False

    def __init__(self, storage_path: str = "data/expenses.json") -> None:
        self.path = Path(storage_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def _load(self) -> list[dict]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, items: list[dict]) -> None:
        self.path.write_text(json.dumps(items, ensure_ascii=True, indent=2), encoding="utf-8")

    def run(self, command: str) -> ToolResult:
        lowered = command.lower()
        add_markers = (
            "adicione gasto",
            "adicionar gasto",
            "registre gasto",
            "registrar gasto",
            "anota gasto",
            "gastei ",
            "despesa ",
        )
        if any(m in lowered for m in add_markers):
            return self._add_expense(command)
        if any(
            x in lowered
            for x in (
                "gastos de hoje",
                "mostre gastos",
                "quanto gast",
                "total do dia",
                "resumo de gasto",
            )
        ):
            return self._report_today()
        return ToolResult(False, "Comando financeiro nao reconhecido.")

    def _add_expense(self, command: str) -> ToolResult:
        amount = self._extract_amount(command)
        if amount is None:
            return ToolResult(False, "Nao achei valor numerico no gasto.")
        entries = self._load()
        entries.append(
            {
                "date": date.today().isoformat(),
                "description": command,
                "amount_brl": amount,
            }
        )
        self._save(entries)
        return ToolResult(True, f"Gasto registrado: R$ {amount:.2f}.")

    def _report_today(self) -> ToolResult:
        today = date.today().isoformat()
        entries = [x for x in self._load() if x.get("date") == today]
        total = sum(float(x.get("amount_brl", 0)) for x in entries)
        return ToolResult(
            True,
            f"Gastos de hoje: {len(entries)} itens, total R$ {total:.2f}.",
        )

    @staticmethod
    def _extract_amount(text: str) -> float | None:
        cleaned = text.replace(",", ".")
        for token in cleaned.split():
            try:
                return float(token)
            except ValueError:
                continue
        return None
