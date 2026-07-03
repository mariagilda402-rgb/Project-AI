from src.database.nexus_db import NexusDatabase
from src.utils.nexus_notifier import broadcast_nexus_state, log_nexus_event
import logging
from datetime import datetime, date, timedelta
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

_SUBJECT_ALIASES = {
    "geral": "Geral",
    "matemática": "Matemática",
    "matematica": "Matemática",
    "português": "Português",
    "portugues": "Português",
    "natureza": "Ciências da Natureza",
    "ciências da natureza": "Ciências da Natureza",
    "humanas": "Ciências Humanas",
    "ciências humanas": "Ciências Humanas",
}

_NEXUS_WINDOW_MODULES = {
    "overview": "Visao geral",
    "habits": "Habitos",
    "finance": "Financas",
    "notes": "MindPalace",
    "memory_graph": "Grafo neural",
    "study": "SRS",
    "tasks": "Tarefas",
    "progress": "Progresso",
    "goals": "Metas e recompensas",
    "quiz": "Quiz",
    "news": "Noticias",
    "ops": "Operacoes",
}

_NEXUS_WINDOW_MODULE_ALIASES = {
    "dashboard": "overview",
    "home": "overview",
    "inicio": "overview",
    "visao geral": "overview",
    "habito": "habits",
    "habitos": "habits",
    "rotina": "habits",
    "financa": "finance",
    "financas": "finance",
    "financeiro": "finance",
    "aether": "finance",
    "nota": "notes",
    "notas": "notes",
    "mindpalace": "notes",
    "grafo": "memory_graph",
    "grafo neural": "memory_graph",
    "memoria": "memory_graph",
    "memorias": "memory_graph",
    "rede neural": "memory_graph",
    "neural": "memory_graph",
    "estudo": "notes",
    "estudos": "notes",
    "flashcard": "study",
    "flashcards": "study",
    "srs": "study",
    "board": "tasks",
    "tarefa": "tasks",
    "tarefas": "tasks",
    "progresso": "progress",
    "meta": "goals",
    "metas": "goals",
    "loja": "goals",
    "recompensa": "goals",
    "recompensas": "goals",
    "simulado": "quiz",
    "simulados": "quiz",
    "news": "news",
    "noticia": "news",
    "noticias": "news",
    "manchete": "news",
    "manchetes": "news",
    "jornal": "news",
    "ops": "ops",
    "business": "ops",
    "negocios": "ops",
    "negócios": "ops",
    "operacoes": "ops",
    "operações": "ops",
    "dashboard ops": "ops",
    "painel ops": "ops",
}

_NEXUS_THEME_TOKEN_KEYS = {
    "--bg",
    "--bg-panel",
    "--surface",
    "--surface-hover",
    "--border",
    "--border-accent",
    "--text",
    "--text-dim",
    "--text-muted",
    "--muted",
    "--accent",
    "--accent-hover",
    "--accent-glow",
    "--accent-subtle",
    "--danger",
    "--success",
    "--warning",
    "--sidebar",
    "--shadow",
}

_DEFAULT_WINDOW_THEME_ID = "dark-neon"

_DEFAULT_WINDOW_THEME_PRESETS = {
    "dark-neon": {
        "id": "dark-neon",
        "name": "Dark Neon",
        "mode": "dark",
        "description": "Base escura Nexus com roxo e ciano.",
        "tokens": {
            "--bg": "#0a0a0a",
            "--bg-panel": "#111111",
            "--surface": "rgba(255,255,255,0.04)",
            "--surface-hover": "rgba(255,255,255,0.08)",
            "--border": "rgba(255,255,255,0.08)",
            "--border-accent": "rgba(139,92,246,0.35)",
            "--text": "#e4e4e7",
            "--text-dim": "#71717a",
            "--text-muted": "#52525b",
            "--muted": "#71717a",
            "--accent": "#8b5cf6",
            "--accent-hover": "#7c3aed",
            "--accent-glow": "rgba(139,92,246,0.30)",
            "--accent-subtle": "rgba(139,92,246,0.08)",
            "--sidebar": "#080808",
            "--shadow": "0 0 25px rgba(0,0,0,0.80)",
        },
    },
    "light-crystal": {
        "id": "light-crystal",
        "name": "Light Crystal",
        "mode": "light",
        "description": "Tema claro limpo com acento violeta.",
        "tokens": {
            "--bg": "#f6f8fc",
            "--bg-panel": "#ffffff",
            "--surface": "rgba(15,23,42,0.045)",
            "--surface-hover": "rgba(15,23,42,0.08)",
            "--border": "rgba(15,23,42,0.12)",
            "--border-accent": "rgba(6,182,212,0.34)",
            "--text": "#111827",
            "--text-dim": "#5b6475",
            "--text-muted": "#7a8496",
            "--muted": "#6b7280",
            "--accent": "#7c3aed",
            "--accent-hover": "#6d28d9",
            "--accent-glow": "rgba(6,182,212,0.24)",
            "--accent-subtle": "rgba(124,58,237,0.08)",
            "--sidebar": "#eef2ff",
            "--shadow": "0 22px 55px rgba(15,23,42,0.20)",
        },
    },
    "emerald-ledger": {
        "id": "emerald-ledger",
        "name": "Emerald Ledger",
        "mode": "dark",
        "description": "Verde financeiro para Aether e rotinas de dinheiro.",
        "tokens": {
            "--bg": "#03130f",
            "--bg-panel": "#071b16",
            "--surface": "rgba(16,185,129,0.08)",
            "--surface-hover": "rgba(16,185,129,0.14)",
            "--border": "rgba(110,231,183,0.14)",
            "--border-accent": "rgba(16,185,129,0.46)",
            "--text": "#e6fff5",
            "--text-dim": "#8dcfba",
            "--text-muted": "#5f8f81",
            "--muted": "#7bb09f",
            "--accent": "#10b981",
            "--accent-hover": "#059669",
            "--accent-glow": "rgba(16,185,129,0.32)",
            "--accent-subtle": "rgba(16,185,129,0.10)",
            "--sidebar": "#020b08",
            "--shadow": "0 0 34px rgba(16,185,129,0.16)",
        },
    },
    "study-cyan": {
        "id": "study-cyan",
        "name": "Study Cyan",
        "mode": "dark",
        "description": "Azul frio para foco, SRS e MindPalace.",
        "tokens": {
            "--bg": "#06111f",
            "--bg-panel": "#091827",
            "--surface": "rgba(56,189,248,0.08)",
            "--surface-hover": "rgba(56,189,248,0.14)",
            "--border": "rgba(125,211,252,0.15)",
            "--border-accent": "rgba(56,189,248,0.46)",
            "--text": "#eef8ff",
            "--text-dim": "#9cc9df",
            "--text-muted": "#6f93a6",
            "--muted": "#8ab2c6",
            "--accent": "#38bdf8",
            "--accent-hover": "#0ea5e9",
            "--accent-glow": "rgba(56,189,248,0.30)",
            "--accent-subtle": "rgba(56,189,248,0.10)",
            "--sidebar": "#030914",
            "--shadow": "0 0 34px rgba(14,165,233,0.16)",
        },
    },
    "solar-premium": {
        "id": "solar-premium",
        "name": "Solar Premium",
        "mode": "light",
        "description": "Claro dourado para revisoes e planejamento calmo.",
        "tokens": {
            "--bg": "#fbfaf5",
            "--bg-panel": "#fffdf7",
            "--surface": "rgba(180,83,9,0.055)",
            "--surface-hover": "rgba(180,83,9,0.095)",
            "--border": "rgba(120,53,15,0.14)",
            "--border-accent": "rgba(245,158,11,0.48)",
            "--text": "#231a10",
            "--text-dim": "#6d5a43",
            "--text-muted": "#927f66",
            "--muted": "#78644d",
            "--accent": "#f59e0b",
            "--accent-hover": "#d97706",
            "--accent-glow": "rgba(245,158,11,0.28)",
            "--accent-subtle": "rgba(245,158,11,0.12)",
            "--sidebar": "#f7efe0",
            "--shadow": "0 22px 55px rgba(120,53,15,0.16)",
        },
    },
}




class NexusGoalsMixin:
    def get_rewards(self):
        """Lista todas as recompensas disponíveis."""
        return self.db.list_rewards()

    def add_reward(self, name: str, cost: int, description: str = "") -> int:
        rid = self.db.add_reward(name, cost, description)
        from src.utils.nexus_notifier import broadcast_nexus_state
        broadcast_nexus_state(self)
        return rid

    def update_reward(self, reward_id: int, name: str | None = None, cost: int | None = None, description: str | None = None) -> dict | None:
        updated = self.db.update_reward(reward_id, name, cost, description)
        from src.utils.nexus_notifier import broadcast_nexus_state
        broadcast_nexus_state(self)
        return updated

    def delete_reward(self, reward_id: int) -> None:
        self.db.delete_reward(reward_id)
        from src.utils.nexus_notifier import broadcast_nexus_state
        broadcast_nexus_state(self)

    def process_reward(self, reward_name):
        """Resgata recompensa; no máximo 1 resgate por dia (calendário)."""
        today = date.today().isoformat()

        with self.db._get_connection() as conn:
            row = conn.execute(
                "SELECT id, cost FROM nexus_rewards WHERE name LIKE ?",
                (f"%{reward_name}%",),
            ).fetchone()
            if not row:
                return False, f"Não encontrei a recompensa '{reward_name}', Sir."
            rid, cost = int(row[0]), int(row[1])
            stats = self.db.get_user_stats()
            if stats["points"] < cost:
                return False, f"Saldo insuficiente, Sir."
            import sqlite3

            try:
                conn.execute(
                    "INSERT INTO reward_redemptions (redemption_date, reward_id) VALUES (?, ?)",
                    (today, rid),
                )
            except sqlite3.IntegrityError:
                return False, "Ja resgatou uma recompensa hoje, Sir."
            conn.execute("UPDATE nexus_user SET points = points - ? WHERE id = 1", (cost,))
            conn.commit()
        log_nexus_event(f"REWARD: {reward_name} Resgatada")
        broadcast_nexus_state(self)
        return True, f"Recompensa '{reward_name}' liberada! Aproveite, Sir."

    def get_reward_status(self, limit: int = 7) -> dict:
        """Estado da loja: pontos, resgate de hoje e historico recente."""
        today_date = date.today()
        today = today_date.isoformat()
        tomorrow = (today_date + timedelta(days=1)).isoformat()
        stats = self.db.get_user_stats() or {"points": 0}
        with self.db._get_connection() as conn:
            conn.row_factory = __import__("sqlite3").Row
            today_row = conn.execute(
                """
                SELECT rr.redemption_date, r.name, r.cost, r.description
                FROM reward_redemptions rr
                JOIN nexus_rewards r ON r.id = rr.reward_id
                WHERE rr.redemption_date = ?
                """,
                (today,),
            ).fetchone()
            rows = conn.execute(
                """
                SELECT rr.redemption_date, rr.created_at, r.name, r.cost, r.description
                FROM reward_redemptions rr
                JOIN nexus_rewards r ON r.id = rr.reward_id
                ORDER BY rr.redemption_date DESC, rr.id DESC
                LIMIT ?
                """,
                (max(1, min(30, int(limit or 7))),),
            ).fetchall()
        redeemed_today = bool(today_row)
        return {
            "date": today,
            "points": int(stats.get("points") or 0),
            "daily_limit": 1,
            "remaining_today": 0 if redeemed_today else 1,
            "next_available_date": tomorrow if redeemed_today else today,
            "reset_at": f"{tomorrow}T00:00:00",
            "redeemed_today": redeemed_today,
            "today_reward": dict(today_row) if today_row else None,
            "history": [dict(r) for r in rows],
        }

    def _goal_keyword_key(self, goals) -> str:
        if isinstance(goals, str):
            text = goals
        else:
            text = " ".join(str(g) for g in (goals or []))
        key = unicodedata.normalize("NFKD", text.lower())
        key = "".join(ch for ch in key if not unicodedata.combining(ch))
        return " ".join(key.replace("-", " ").split())

    def _goal_preset_name(self, key: str, preset_name: str | None = None) -> str:
        if preset_name and preset_name.strip():
            return preset_name.strip()
        tags = []
        if any(word in key for word in ("enem", "vestibular", "estudo", "estudar")):
            tags.append("ENEM")
        if any(word in key for word in ("dinheiro", "invest", "finance", "econom", "juntar")):
            tags.append("Financas")
        if any(word in key for word in ("shape", "treino", "muscul", "corpo", "academia")):
            tags.append("Shape")
        return "Plano IA - " + " + ".join(tags or ["Objetivos"])

    def build_lifestyle_preset_from_goals(self, goals, preset_name: str | None = None) -> str:
        """Cria e aplica um preset inicial a partir de objetivos de alto nivel."""
        try:
            key = self._goal_keyword_key(goals)
            name = self._goal_preset_name(key, preset_name)
            habits = self._goal_habit_candidates(goals)
            config = json.dumps(
                [self._preset_habit_config(h) for h in habits],
                ensure_ascii=False,
            )
            with self.db._get_connection() as conn:
                row = conn.execute(
                    "SELECT id FROM lifestyle_presets WHERE name = ?",
                    (name,),
                ).fetchone()
                if row:
                    preset_id = row[0]
                    conn.execute(
                        """
                        UPDATE lifestyle_presets
                        SET config_json = ?, created_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (config, preset_id),
                    )
                else:
                    cur = conn.execute(
                        """
                        INSERT INTO lifestyle_presets (name, config_json)
                        VALUES (?, ?)
                        """,
                        (name, config),
                    )
                    preset_id = cur.lastrowid
                conn.execute("UPDATE lifestyle_presets SET is_active = 0")
                conn.execute("UPDATE lifestyle_presets SET is_active = 1 WHERE id = ?", (preset_id,))
                conn.commit()

            habit_count = self._replace_active_habits(habits)
            msg = f"{name} criado e ativado com {habit_count} habitos, Sir."
            log_nexus_event(f"STRATEGY: {name} gerado por objetivos.")
            broadcast_nexus_state(self)
            self._open_desktop_receipt(
                "habits",
                {
                    "animate": "preset",
                    "toast": msg,
                    "receipt": {
                        "kind": "preset",
                        "action": "preset_apply_goals",
                        "name": name,
                        "habit_count": habit_count,
                    },
                },
            )
            return msg
        except Exception as e:
            logger.error("Erro ao gerar preset por objetivos: %s", e)
            return "Falha ao gerar preset pelos objetivos."

    def add_goal(self, name, target_date=None):
        """Adiciona um grande objetivo de longo prazo."""
        try:
            with self.db._get_connection() as conn:
                conn.execute("""
                    INSERT INTO nexus_goals (name, target_date)
                    VALUES (?, ?)
                """, (name, target_date))
                conn.commit()
            log_nexus_event(f"GOAL: '{name}' Estabelecido.")
            broadcast_nexus_state(self)
            return f"Meta '{name}' registrada no horizonte estratégico, Sir."
        except Exception as e:
            logger.error(f"Erro ao adicionar meta: {e}")
            return "Falha ao registrar objetivo."

    def update_goal_progress(self, name, progress):
        """Atualiza o progresso (0-100) de uma meta de forma precisa."""
        try:
            with self.db._get_connection() as conn:
                # Busca a meta que melhor coincide
                row = conn.execute("SELECT name FROM nexus_goals WHERE name LIKE ? ORDER BY length(name) ASC", (f"%{name}%",)).fetchone()
                if not row:
                    return f"Não encontrei nenhuma meta parecida com '{name}', Sir."

                real_name = row[0]
                conn.execute("""
                    UPDATE nexus_goals SET progress = ? WHERE name = ?
                """, (progress, real_name))
                conn.commit()

            log_nexus_event(f"GOAL UPDATE: {real_name} ({progress}%)")
            broadcast_nexus_state(self)
            return f"Meta '{real_name}' avançou para {progress}%. Mantenha o ritmo, Sir."
        except Exception as e:
            logger.error(f"Erro ao atualizar meta: {e}")
            return "Falha ao sincronizar progresso."

    def get_goals(self):
        """Retorna a lista de metas ativas."""
        import sqlite3
        with self.db._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM nexus_goals WHERE status = 'active'").fetchall()
            return [dict(r) for r in rows]

