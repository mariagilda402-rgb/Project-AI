from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


class MemoryStore:
    """Memoria com sessoes, resumo automatico e limpeza."""

    # Limite de caracteres por mensagem no historico (trunca resultados longos de tools).
    _MAX_CONTENT_CHARS = 1200
    # Apos atingir este numero de mensagens na sessao, gera um resumo das mais antigas.
    _SUMMARIZE_THRESHOLD = 14
    # Mensagens recentes que ficam intactas (as mais antigas viram resumo).
    _KEEP_RECENT = 6

    def __init__(self, db_path: str = "data/memory.db") -> None:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self._init_schema()
        self._session_id = uuid.uuid4().hex[:12]
        self._session_summary: str = ""
        self._msg_count = 0

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS short_term (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        # Nova coluna session_id — adicionada de forma segura (ignora se ja existe).
        try:
            cur.execute("ALTER TABLE short_term ADD COLUMN session_id TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # coluna ja existe

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS long_term (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        # Tabela de resumos de sessao.
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS session_summaries (
                session_id TEXT PRIMARY KEY,
                summary TEXT NOT NULL,
                message_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        self.conn.commit()

    @property
    def session_id(self) -> str:
        return self._session_id

    def close(self) -> None:
        self.conn.close()

    # ── Short-term (sessao atual) ──

    @staticmethod
    def _truncate(text: str, max_chars: int) -> str:
        """Trunca textos longos (ex.: resultados de web search) para caber no contexto."""
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "... [truncado]"

    def add_short_term(self, role: str, content: str) -> None:
        # Trunca conteudo longo para nao inflar o contexto.
        stored = self._truncate(content, self._MAX_CONTENT_CHARS)
        self.conn.execute(
            "INSERT INTO short_term (role, content, session_id) VALUES (?, ?, ?)",
            (role, stored, self._session_id),
        )
        self.conn.commit()
        self._msg_count += 1

    def get_recent_short_term(self, limit: int = 10) -> list[dict[str, str]]:
        """Retorna mensagens recentes da sessao atual, com resumo de contexto se houver."""
        rows = self.conn.execute(
            """
            SELECT role, content
            FROM short_term
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (self._session_id, limit),
        ).fetchall()
        messages = [{"role": role, "content": content} for role, content in reversed(rows)]

        # Injeta resumo de contexto anterior se existir.
        context: list[dict[str, str]] = []
        if self._session_summary:
            context.append(
                {
                    "role": "system",
                    "content": f"Resumo da conversa anterior (para contexto):\n{self._session_summary}",
                }
            )
        # Busca resumo da ultima sessao salva (continuidade entre execucoes).
        last_session_summary = self._get_last_session_summary()
        if last_session_summary:
            context.append(
                {
                    "role": "system",
                    "content": f"Resumo da sessao anterior:\n{last_session_summary}",
                }
            )
        return context + messages

    def _get_last_session_summary(self) -> str:
        """Busca resumo da sessao mais recente (que nao seja a atual)."""
        row = self.conn.execute(
            """
            SELECT summary FROM session_summaries
            WHERE session_id != ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (self._session_id,),
        ).fetchone()
        return row[0] if row else ""

    # ── Sumarizacao automatica ──

    def should_summarize(self) -> bool:
        """Verifica se ha mensagens suficientes para justificar sumarizacao."""
        return self._msg_count >= self._SUMMARIZE_THRESHOLD

    def get_messages_for_summary(self) -> list[dict[str, str]]:
        """Retorna mensagens antigas da sessao que devem ser sumarizadas."""
        all_rows = self.conn.execute(
            """
            SELECT role, content
            FROM short_term
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (self._session_id,),
        ).fetchall()
        # Pega tudo exceto as ultimas _KEEP_RECENT.
        if len(all_rows) <= self._KEEP_RECENT:
            return []
        old = all_rows[: -self._KEEP_RECENT]
        return [{"role": role, "content": content} for role, content in old]

    def apply_summary(self, summary: str) -> None:
        """Aplica o resumo: salva e remove mensagens antigas da sessao."""
        self._session_summary = summary
        # Salva na tabela de resumos.
        self.conn.execute(
            """
            INSERT INTO session_summaries (session_id, summary, message_count, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(session_id) DO UPDATE SET
                summary = excluded.summary,
                message_count = excluded.message_count,
                updated_at = CURRENT_TIMESTAMP
            """,
            (self._session_id, summary, self._msg_count),
        )
        # Remove mensagens antigas da sessao (so mantem as recentes).
        all_ids = self.conn.execute(
            """
            SELECT id FROM short_term
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (self._session_id,),
        ).fetchall()
        if len(all_ids) > self._KEEP_RECENT:
            ids_to_delete = [row[0] for row in all_ids[: -self._KEEP_RECENT]]
            placeholders = ",".join("?" * len(ids_to_delete))
            self.conn.execute(
                f"DELETE FROM short_term WHERE id IN ({placeholders})",
                ids_to_delete,
            )
        self.conn.commit()
        self._msg_count = self._KEEP_RECENT

    # ── Limpeza de sessoes antigas ──

    def cleanup_old_sessions(self, keep_sessions: int = 5) -> None:
        """Remove mensagens de sessoes muito antigas (mantem so os resumos)."""
        sessions = self.conn.execute(
            """
            SELECT DISTINCT session_id FROM short_term
            WHERE session_id != ?
            ORDER BY id DESC
            """,
            (self._session_id,),
        ).fetchall()
        old_sessions = [s[0] for s in sessions[keep_sessions:]]
        for sid in old_sessions:
            self.conn.execute(
                "DELETE FROM short_term WHERE session_id = ?", (sid,)
            )
        self.conn.commit()

    # ── Long-term ──

    def set_long_term(self, key: str, value: Any) -> None:
        payload = json.dumps(value, ensure_ascii=True)
        self.conn.execute(
            """
            INSERT INTO long_term (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value=excluded.value,
                updated_at=CURRENT_TIMESTAMP
            """,
            (key, payload),
        )
        self.conn.commit()

    def get_long_term(self, key: str, default: Any = None) -> Any:
        row = self.conn.execute(
            "SELECT value FROM long_term WHERE key = ?", (key,)
        ).fetchone()
        if not row:
            return default
        return json.loads(row[0])

    # ── Persona e preferencias ──

    def maybe_record_persona_note(self, user_text: str) -> None:
        """Guarda na memoria ajustes de tom/personalidade quando o usuario pede explicitamente."""
        t = (user_text or "").lower()
        triggers = (
            "prefiro que você",
            "prefiro que voce",
            "quero que você",
            "quero que voce",
            "gostaria que você",
            "gostaria que voce",
            "fale mais",
            "fale menos",
            "seja mais",
            "seja menos",
            "nao seja",
            "não seja",
            "nao fique",
            "não fique",
            "tom mais",
            "tom menos",
            "seja formal",
            "seja informal",
            "respostas curtas",
            "resposta curta",
            "textao",
            "textão",
            "explica em detalhes",
            "me chame de",
            "me trate",
            "personalidade",
            "jeito de falar",
        )
        if not any(x in t for x in triggers):
            return
        line = (user_text or "").strip()[:400]
        if not line:
            return
        notes = self.get_long_term("persona_evolution", default=[])
        if not isinstance(notes, list):
            notes = []
        notes.append(line)
        self.set_long_term("persona_evolution", notes[-40:])

    def maybe_store_preference(
        self, user_text: str, assistant_text: str, consent_for_sensitive: bool = True
    ) -> None:
        text = user_text.lower()
        if "prefiro" in text or "me lembra" in text:
            prefs = self.get_long_term("preferences", default=[])
            prefs.append({"user": user_text, "assistant": assistant_text})
            self.set_long_term("preferences", prefs[-50:])
        if consent_for_sensitive and ("horario" in text or "22h" in text):
            habits = self.get_long_term("habits", default=[])
            habits.append({"note": user_text})
            self.set_long_term("habits", habits[-100:])
