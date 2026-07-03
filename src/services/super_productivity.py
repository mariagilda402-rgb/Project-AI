from __future__ import annotations

import json
from pathlib import Path


class SuperProductivityConnector:
    """
    Conector MVP:
    - guarda dados em JSON local para validar fluxo end-to-end.
    - pode ser trocado depois por integracao direta com API/DB do app.
    """

    def __init__(self, storage_path: str = "data/super_productivity_mock.json") -> None:
        self.path = Path(storage_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(
                json.dumps({"habits": [], "tasks": []}, ensure_ascii=True, indent=2),
                encoding="utf-8",
            )

    def _load(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, data: dict) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")

    def add_habit(self, raw_text: str) -> str:
        data = self._load()
        data["habits"].append({"description": raw_text})
        self._save(data)
        return "Habito adicionado no conector Super Productivity (mock)."

    def update_task(self, raw_text: str) -> str:
        data = self._load()
        data["tasks"].append({"update_request": raw_text})
        self._save(data)
        return "Pedido de atualizacao de tarefa registrado no conector Super Productivity (mock)."
