"""Anotacoes rapidas persistidas em JSON."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .base import ToolResult


class NotesTool:
    name = "notes"
    description = "Anotacoes rapidas (salvar, listar, buscar, deletar)."
    critical = False

    def __init__(self, storage_path: str = "data/notes.json") -> None:
        self.path = Path(storage_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def _load(self) -> list[dict]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, notes: list[dict]) -> None:
        self.path.write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, title: str, content: str) -> ToolResult:
        notes = self._load()
        notes.append(
            {
                "title": title.strip(),
                "content": content.strip(),
                "created_at": datetime.now().isoformat(),
            }
        )
        self._save(notes)
        return ToolResult(True, f"Nota salva: '{title.strip()}'.")

    def list_all(self) -> ToolResult:
        notes = self._load()
        if not notes:
            return ToolResult(True, "Nenhuma nota salva.")
        lines: list[str] = []
        for i, n in enumerate(notes, 1):
            dt = n.get("created_at", "?")[:16].replace("T", " ")
            lines.append(f"{i}. {n['title']} ({dt})")
        return ToolResult(True, "Notas:\n" + "\n".join(lines))

    def search(self, query: str) -> ToolResult:
        q = query.lower()
        matches = [
            n for n in self._load() if q in n["title"].lower() or q in n["content"].lower()
        ]
        if not matches:
            return ToolResult(True, f"Nenhuma nota encontrada com '{query}'.")
        lines = [f"- {n['title']}: {n['content'][:120]}" for n in matches]
        return ToolResult(True, "\n".join(lines))

    def delete(self, title: str) -> ToolResult:
        notes = self._load()
        before = len(notes)
        notes = [n for n in notes if n["title"].lower() != title.strip().lower()]
        if len(notes) == before:
            return ToolResult(False, f"Nota '{title}' nao encontrada.")
        self._save(notes)
        return ToolResult(True, f"Nota '{title}' deletada.")

    def run(self, command: str) -> ToolResult:
        lowered = (command or "").lower()
        if any(kw in lowered for kw in ("listar", "todas", "quais", "ver notas")):
            return self.list_all()
        if any(kw in lowered for kw in ("buscar", "procurar", "encontrar")):
            for kw in ("buscar", "procurar", "encontrar"):
                if kw in lowered:
                    term = command[lowered.index(kw) + len(kw) :].strip()
                    if term:
                        return self.search(term)
            return ToolResult(False, "Informe o termo de busca.")
        if any(kw in lowered for kw in ("deletar", "apagar", "remover")):
            for kw in ("deletar", "apagar", "remover"):
                if kw in lowered:
                    term = command[lowered.index(kw) + len(kw) :].strip()
                    if term:
                        return self.delete(term)
            return ToolResult(False, "Informe o titulo da nota a deletar.")
        # Default: salvar com titulo auto.
        return self.add(command[:60], command)
