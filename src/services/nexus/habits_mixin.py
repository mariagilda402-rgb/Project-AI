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




class NexusHabitsMixin:
    def complete_habit(self, habit_name, target_date: str = None):
        """Marca (ou desmarca) um hábito como concluído e ajusta XP + streak."""
        try:
            habits = self.db.get_habits()
            target = next((h for h in habits if habit_name.lower() in h["name"].lower()), None)

            if not target:
                return f"Não encontrei o hábito '{habit_name}' na sua lista, Sir."

            # Toggle behavior
            is_done = self.db.check_habit_completion(target["id"], target_date)
            base_xp = target.get("xp_reward", 50)

            if is_done:
                # Uncheck
                self.db.unlog_habit_completion(target["id"], target_date)
                # Recover new streak
                habits = self.db.get_habits()
                new_target = next((h for h in habits if h["id"] == target["id"]), target)
                streak = int(new_target.get("current_streak") or 0)
                bonus = min(base_xp, int(base_xp * (streak * 0.1)))
                total_xp = base_xp + bonus

                # Deduct XP
                self.db.add_xp(-total_xp)
                log_nexus_event(f"HABIT UNDONE: {target['name']} (-{total_xp} XP)")
                broadcast_nexus_state(self)
                return f"Hábito '{target['name']}' desmarcado. XP revertido (Streak: {streak})."
            else:
                # Check
                added = self.db.log_habit_completion(target["id"], target_date)
                habits = self.db.get_habits()
                new_target = next((h for h in habits if h["id"] == target["id"]), target)
                streak = int(new_target.get("current_streak") or 0)

                bonus = min(base_xp, int(base_xp * (streak * 0.1)))
                total_xp = base_xp + bonus

                self.db.add_xp(total_xp)
                log_nexus_event(f"HABIT DONE: {target['name']} (+{total_xp} XP)")
                try:
                    from src.utils.telemetry import log_event
                    log_event("nexus_habit", {"habit": target["name"], "streak": streak})
                except Exception:
                    pass
                broadcast_nexus_state(self)
                self._open_desktop_receipt(
                    "habits",
                    {
                        "highlight_id": target["id"],
                        "animate": "habit_complete",
                        "toast": f"Hábito concluído: {target['name']}",
                        "receipt": {
                            "kind": "habit",
                            "action": "habit_complete",
                            "id": target["id"],
                            "name": target["name"],
                            "xp": total_xp,
                            "streak": streak,
                        },
                    },
                )

                return (
                    f"Hábito '{target['name']}' concluído! +{total_xp} XP (Streak: {streak}). Muito bem, Sir."
                )
        except Exception as e:
            logger.error(f"Erro ao concluir/desmarcar hábito: {e}")
            return "Falha ao registrar/remover conclusão do hábito."

    def _preset_habit_config(self, habit: dict) -> dict:
        return {
            "name": habit.get("name") or "Habito",
            "description": habit.get("description") or "",
            "xp_reward": int(habit.get("xp_reward") or 50),
            "days_of_week": self._normalize_days_of_week(habit.get("days_of_week")),
        }

    def _replace_active_habits(self, habits_list: list[dict]) -> int:
        with self.db._get_connection() as conn:
            conn.execute("UPDATE habits SET active = 0")
            count = 0
            for habit in habits_list:
                h = self._preset_habit_config(habit)
                conn.execute(
                    """
                    INSERT INTO habits (name, description, xp_reward, days_of_week, active)
                    VALUES (?, ?, ?, ?, 1)
                    """,
                    (h["name"], h["description"], h["xp_reward"], h["days_of_week"]),
                )
                count += 1
            conn.commit()
            return count

    def _goal_habit_candidates(self, goals) -> list[dict]:
        key = self._goal_keyword_key(goals)
        habits: list[dict] = []
        if any(word in key for word in ("enem", "vestibular", "estudo", "estudar")):
            habits.extend(
                [
                    {
                        "name": "Redacao ENEM",
                        "description": "Escrever, corrigir ou revisar uma redacao com repertorio.",
                        "xp_reward": 120,
                        "days_of_week": [1, 3, 5],
                    },
                    {
                        "name": "Questoes ENEM",
                        "description": "Resolver questoes cronometradas e registrar acertos.",
                        "xp_reward": 90,
                        "days_of_week": [1, 2, 3, 4, 5],
                    },
                    {
                        "name": "Revisao ativa",
                        "description": "Revisar flashcards e anotar pontos fracos.",
                        "xp_reward": 70,
                        "days_of_week": [2, 4, 6],
                    },
                ]
            )
        if any(word in key for word in ("dinheiro", "invest", "finance", "econom", "juntar")):
            habits.extend(
                [
                    {
                        "name": "Revisar gastos",
                        "description": "Registrar gastos, ganhos e uma observacao financeira do dia.",
                        "xp_reward": 60,
                        "days_of_week": None,
                    },
                    {
                        "name": "Estudar investimentos",
                        "description": "Ler ou resumir um conteudo de educacao financeira.",
                        "xp_reward": 70,
                        "days_of_week": [2, 4],
                    },
                ]
            )
        if any(word in key for word in ("shape", "treino", "muscul", "corpo", "academia")):
            habits.extend(
                [
                    {
                        "name": "Treino de forca",
                        "description": "Executar o treino principal e registrar carga ou repeticoes.",
                        "xp_reward": 110,
                        "days_of_week": [1, 3, 5],
                    },
                    {
                        "name": "Cardio leve",
                        "description": "Fazer cardio, mobilidade ou caminhada focada.",
                        "xp_reward": 70,
                        "days_of_week": [2, 4, 6],
                    },
                    {
                        "name": "Sono e proteina",
                        "description": "Checar sono, agua e meta minima de proteina.",
                        "xp_reward": 60,
                        "days_of_week": None,
                    },
                ]
            )
        if not habits:
            habits.append(
                {
                    "name": "Planejamento estrategico",
                    "description": "Definir a proxima acao mensuravel para o objetivo.",
                    "xp_reward": 50,
                    "days_of_week": None,
                }
            )
        seen = set()
        unique = []
        for habit in habits:
            name_key = habit["name"].lower()
            if name_key in seen:
                continue
            seen.add(name_key)
            unique.append(habit)
        return unique

    def apply_preset_habits_json(self, habits_list: list) -> str:
        """Substitui hábitos ativos por lista de dicts {name, description, xp_reward, days_of_week?}."""
        try:
            habit_count = self._replace_active_habits(habits_list)
            log_nexus_event("STRATEGY: Preset IA aplicado.")
            broadcast_nexus_state(self)
            self._open_desktop_receipt(
                "habits",
                {
                    "animate": "preset",
                    "toast": "Preset de habitos aplicado com sucesso, Sir.",
                    "receipt": {
                        "kind": "preset",
                        "action": "preset_apply_json",
                        "name": "Preset IA",
                        "habit_count": habit_count,
                    },
                },
            )
            return "Preset de habitos aplicado com sucesso, Sir."
        except Exception as e:
            logger.error(e)
            return "Falha ao aplicar preset."

    def get_habit_stats(self, habit_id: int) -> str:
        with self.db._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT name, current_streak, max_streak, xp_reward FROM habits WHERE id = ?", (habit_id,))
            row = cur.fetchone()
            if not row:
                return "Hábito não encontrado."

            cur.execute("SELECT COUNT(*) FROM habit_logs WHERE habit_id = ?", (habit_id,))
            total_completions = cur.fetchone()[0]

            stats = {
                "name": row[0],
                "current_streak": row[1],
                "max_streak": row[2],
                "xp_reward": row[3],
                "total_completions": total_completions
            }
            return json.dumps(stats, ensure_ascii=False)

    def get_habit_heatmap(self, year: int) -> str:
        with self.db._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT date(completed_at), COUNT(*) FROM habit_logs WHERE strftime('%Y', completed_at) = ? GROUP BY date(completed_at)", (str(year),))
            rows = cur.fetchall()
            heatmap = {row[0]: row[1] for row in rows}
            return json.dumps(heatmap, ensure_ascii=False)

