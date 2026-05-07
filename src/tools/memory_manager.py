"""Gerenciamento de memoria: salvar, buscar, listar e deletar fatos permanentes."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from .base import ToolResult


class MemoryManagerTool:
    name = "memory_manager"
    description = "Salva, busca e lista fatos na memoria de longo prazo."
    critical = False

    def __init__(self, db_path: str = "data/memory.db") -> None:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self._init_facts_table()

    def _init_facts_table(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT DEFAULT 'geral',
                content TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        self.conn.commit()

    def save_fact(self, content: str, category: str = "geral") -> ToolResult:
        if not (content or "").strip():
            return ToolResult(False, "Conteudo vazio.")
        now = datetime.now()
        self.conn.execute(
            "INSERT INTO facts (category, content, created_at) VALUES (?, ?, ?)",
            (category.strip().lower(), content.strip(), now.isoformat()),
        )
        self.conn.commit()
        return ToolResult(
            True,
            f"Salvo na memoria ({category}): '{content.strip()[:80]}' "
            f"em {now.strftime('%d/%m/%Y %H:%M')}.",
        )

    def search_facts(self, query: str) -> ToolResult:
        q = (query or "").strip().lower()
        if not q:
            return ToolResult(False, "Termo de busca vazio.")
        rows = self.conn.execute(
            """
            SELECT id, category, content, created_at FROM facts
            ORDER BY created_at DESC
            """
        ).fetchall()
        matches = [r for r in rows if q in r[2].lower() or q in r[1].lower()]
        if not matches:
            return ToolResult(True, f"Nenhuma memoria encontrada com '{query}'.")
        lines: list[str] = []
        for fid, cat, content, created in matches[:10]:
            dt = created[:16].replace("T", " ")
            lines.append(f"[{fid}] ({cat}, {dt}) {content[:120]}")
        return ToolResult(True, "Memorias encontradas:\n" + "\n".join(lines))

    def list_facts(self, category: str = "") -> ToolResult:
        if category.strip():
            rows = self.conn.execute(
                """
                SELECT id, category, content, created_at FROM facts
                WHERE category = ?
                ORDER BY created_at DESC LIMIT 20
                """,
                (category.strip().lower(),),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """
                SELECT id, category, content, created_at FROM facts
                ORDER BY created_at DESC LIMIT 20
                """
            ).fetchall()
        if not rows:
            return ToolResult(True, "Nenhuma memoria salva" + (f" na categoria '{category}'." if category else "."))
        lines: list[str] = []
        for fid, cat, content, created in rows:
            dt = created[:16].replace("T", " ")
            lines.append(f"[{fid}] ({cat}, {dt}) {content[:120]}")
        return ToolResult(True, "Memorias:\n" + "\n".join(lines))

    def delete_fact(self, fact_id: str) -> ToolResult:
        try:
            fid = int(fact_id)
        except (ValueError, TypeError):
            return ToolResult(False, f"ID invalido: {fact_id}")
        row = self.conn.execute("SELECT content FROM facts WHERE id = ?", (fid,)).fetchone()
        if not row:
            return ToolResult(False, f"Memoria #{fid} nao encontrada.")
        self.conn.execute("DELETE FROM facts WHERE id = ?", (fid,))
        self.conn.commit()
        return ToolResult(True, f"Memoria #{fid} deletada: '{row[0][:60]}'.")

    def run(self, command: str) -> ToolResult:
        lowered = (command or "").lower()
        if any(kw in lowered for kw in ("listar", "todas", "quais")):
            return self.list_facts()
        if any(kw in lowered for kw in ("buscar", "procurar", "encontrar")):
            for kw in ("buscar", "procurar", "encontrar"):
                if kw in lowered:
                    term = command[lowered.index(kw) + len(kw):].strip()
                    if term:
                        return self.search_facts(term)
        if any(kw in lowered for kw in ("deletar", "apagar", "remover")):
            for kw in ("deletar", "apagar", "remover"):
                if kw in lowered:
                    term = command[lowered.index(kw) + len(kw):].strip()
                    if term:
                        return self.delete_fact(term)
        return self.save_fact(command)

    def auto_retrieve(self, user_text: str, limit: int = 2) -> str:
        """Busca automatica de memorias baseada nas palavras do usuario (mini-RAG)."""
        words = set(w.lower() for w in user_text.replace("?", " ").replace(",", " ").split() if len(w) > 3)
        if not words:
            return ""
        
        rows = self.conn.execute("SELECT content FROM facts").fetchall()
        if not rows:
            return ""
            
        scored = []
        for (content,) in rows:
            c_words = set(w.lower() for w in content.replace(",", " ").split())
            score = len(words.intersection(c_words))
            if score > 0:
                scored.append((score, content))
                
        if not scored:
            return ""
            
        scored.sort(key=lambda x: x[0], reverse=True)
        best = [content for score, content in scored[:limit]]
        return " | ".join(best)

