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


class NexusService:
    def __init__(self):
        self.db = NexusDatabase()
        self.db.seed_quiz_if_empty()
        self._last_created_note_id: int | None = None
        self._last_created_finance_id: int | None = None
        self._active_nexus_batch: dict | None = None

    def _decorate_nexus_payload(self, payload: dict | None) -> dict:
        out = dict(payload or {})
        batch = self._active_nexus_batch
        if batch:
            out.setdefault("batch_id", batch.get("id"))
            out.setdefault("batch_step", batch.get("step"))
            out.setdefault("batch_total", batch.get("total"))
            out.setdefault("hold_ms", batch.get("hold_ms", 1400))
        return out

    def _open_desktop_receipt(self, module: str, payload: dict) -> None:
        try:
            from src.ui.nexus_signals import enqueue_nexus_desktop_open

            enqueue_nexus_desktop_open(module, self._decorate_nexus_payload(payload))
        except Exception:
            pass

    def handle_nexus_batch(self, steps, hold_ms: int = 1400) -> str:
        if isinstance(steps, str):
            try:
                steps = json.loads(steps)
            except json.JSONDecodeError:
                steps = []
        if not isinstance(steps, list) or not steps:
            return json.dumps(
                {"ok": False, "error": "nexus_batch requer uma lista steps."},
                ensure_ascii=False,
            )

        batch_id = "nx-" + datetime.now().strftime("%Y%m%d%H%M%S%f")
        previous = self._active_nexus_batch
        results = []
        total = len(steps)
        try:
            for idx, raw_step in enumerate(steps, 1):
                if not isinstance(raw_step, dict):
                    results.append(
                        {
                            "step": idx,
                            "action": "",
                            "ok": False,
                            "message": "Passo ignorado: formato invalido.",
                        }
                    )
                    continue
                step = dict(raw_step)
                action = (step.get("action") or "").strip().lower()
                if action == "nexus_batch":
                    results.append(
                        {
                            "step": idx,
                            "action": action,
                            "ok": False,
                            "message": "Batch aninhado ignorado.",
                        }
                    )
                    continue
                self._active_nexus_batch = {
                    "id": batch_id,
                    "step": idx,
                    "total": total,
                    "hold_ms": hold_ms,
                }
                message = self.handle_structured_command(step)
                ok = not str(message).startswith(("Erro Nexus:", "Acao desconhecida:"))
                results.append(
                    {
                        "step": idx,
                        "action": action,
                        "ok": ok,
                        "message": message,
                    }
                )
        finally:
            self._active_nexus_batch = previous

        return json.dumps(
            {
                "ok": all(item.get("ok") for item in results),
                "batch_id": batch_id,
                "steps": results,
            },
            ensure_ascii=False,
        )

    def _normalize_date_alias(self, value: str | None) -> str | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            return date.fromisoformat(raw[:10]).isoformat()
        except ValueError:
            pass
        key = unicodedata.normalize("NFKD", raw.lower())
        key = "".join(ch for ch in key if not unicodedata.combining(ch))
        key = " ".join(key.replace("-", " ").split())
        offsets = {
            "hoje": 0,
            "ontem": 1,
            "anteontem": 2,
            "ante ontem": 2,
            "antes de ontem": 2,
            "ontem de ontem": 2,
            "amanha": -1,
        }
        if key in offsets:
            return (date.today() - timedelta(days=offsets[key])).isoformat()
        return raw

    def add_expense(
        self,
        amount,
        category,
        description,
        necessity=5,
        occurred_at: str | None = None,
        notes: str | None = None,
        is_debt: int = 0,
    ):
        """Registra um gasto e atualiza o estado financeiro."""
        self._last_created_finance_id = None
        try:
            tx_id = self.db.add_transaction(
                "expense",
                amount,
                category,
                description,
                necessity,
                occurred_at=occurred_at,
                notes=notes,
                is_debt=is_debt,
            )
            try:
                self._last_created_finance_id = int(tx_id)
            except (TypeError, ValueError):
                self._last_created_finance_id = None
            log_nexus_event(f"Gasto registrado: R$ {amount:.2f} ({category})")
            broadcast_nexus_state(self)
            return f"Gasto de R$ {amount:.2f} em '{category}' registrado, Sir."
        except Exception as e:
            logger.error(f"Erro ao adicionar gasto: {e}")
            return "Houve um erro ao processar a transação financeira."

    def add_income(
        self,
        amount,
        category,
        description,
        occurred_at: str | None = None,
        notes: str | None = None,
    ):
        """Registra um ganho."""
        self._last_created_finance_id = None
        try:
            tx_id = self.db.add_transaction(
                "income",
                amount,
                category,
                description,
                10,
                occurred_at=occurred_at,
                notes=notes,
                is_debt=0,
            )
            try:
                self._last_created_finance_id = int(tx_id)
            except (TypeError, ValueError):
                self._last_created_finance_id = None
            log_nexus_event(f"Lucro registrado: R$ {amount:.2f}")
            broadcast_nexus_state(self)
            return f"Entrada de R$ {amount:.2f} registrada com sucesso."
        except Exception as e:
            logger.error(f"Erro ao adicionar ganho: {e}")
            return "Erro ao registrar lucro."

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
                    from src.telemetry.events import log_event
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


    def get_summary(self):
        """Retorna um resumo rápido para o Jarvis falar."""
        stats = self.db.get_user_stats()
        return f"Sir, seu nível atual é {stats['level']} com {stats['points']} pontos disponíveis para troca."

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

    def set_focus_mode(self, active=True):
        """Ativa ou desativa o ambiente de foco (Silêncio + Música)."""
        import subprocess
        try:
            status = "ATIVADO" if active else "DESATIVADO"
            val = 0 if active else 1
            # Garante que a chave existe antes de setar
            setup_cmd = 'if (!(Test-Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings")) { New-Item -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings" -Force }'
            set_cmd = f'Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings" -Name "NOC_GLOBAL_SETTING_TOASTS_ENABLED" -Value {val}'

            subprocess.run(["powershell", "-Command", f"{setup_cmd}; {set_cmd}"], capture_output=True)

            if active:
                from src.tools.spotify import SpotifyTool
                sp = SpotifyTool()
                sp.search_and_play("Lofi Study Focus")

            log_nexus_event(f"PROTOCOL: Focus Mode {status}")
            broadcast_nexus_state(self)

            return f"Modo de Foco {status}, Sir. Ambiente preparado."
        except Exception as e:
            logger.error(f"Erro no modo foco: {e}")
            return "Falha ao ajustar o protocolo de foco."

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

    def _fold_text(self, value: str | None) -> str:
        raw = str(value or "").strip().lower()
        folded = unicodedata.normalize("NFKD", raw)
        return "".join(ch for ch in folded if not unicodedata.combining(ch))

    def _parse_finance_amount(self, value) -> float | None:
        if value in (None, ""):
            return None
        return float(str(value).replace(",", ".").strip())

    def _find_finance_transaction(
        self,
        transaction_id: int | None = None,
        description: str | None = None,
        category: str | None = None,
        tx_type: str | None = None,
        occurred_at: str | None = None,
        amount: float | None = None,
    ) -> dict | None:
        if transaction_id:
            return self.db.get_finance_transaction(int(transaction_id))

        od = self._normalize_date_alias(occurred_at)
        rows = (
            self.db.list_finance_transactions(od, od)
            if od
            else self.db.list_finance_transactions(None, None)
        )
        desc_key = self._fold_text(description)
        cat_key = self._fold_text(category)
        type_key = (tx_type or "").strip().lower()
        for row in rows:
            if type_key and (row.get("type") or "").lower() != type_key:
                continue
            if desc_key and desc_key not in self._fold_text(row.get("description")):
                continue
            if cat_key and cat_key not in self._fold_text(row.get("category")):
                continue
            if amount is not None and abs(float(row.get("amount") or 0) - float(amount)) > 0.009:
                continue
            return row
        return None

    def update_finance_transaction(
        self,
        transaction_id: int | None = None,
        target_description: str | None = None,
        target_category: str | None = None,
        target_type: str | None = None,
        target_occurred_at: str | None = None,
        target_amount: float | None = None,
        tx_type: str | None = None,
        amount=None,
        category: str | None = None,
        description: str | None = None,
        occurred_at: str | None = None,
        necessity: int | None = None,
        notes: str | None = None,
        is_debt: int | None = None,
    ) -> dict:
        """Atualiza uma transacao por id ou pelo melhor match de texto/data."""
        target = self._find_finance_transaction(
            transaction_id=transaction_id,
            description=target_description,
            category=target_category,
            tx_type=target_type,
            occurred_at=target_occurred_at,
            amount=target_amount,
        )
        if not target:
            return {
                "ok": False,
                "message": "Nao encontrei uma transacao financeira compativel para atualizar.",
                "updated": None,
            }

        new_amount = self._parse_finance_amount(amount)
        new_date = self._normalize_date_alias(occurred_at) if occurred_at is not None else None
        updated = self.db.update_finance_transaction(
            int(target["id"]),
            t_type=tx_type,
            amount=new_amount,
            category=category,
            description=description,
            necessity=necessity,
            occurred_at=new_date,
            notes=notes,
            is_debt=is_debt,
        )
        if not updated:
            return {
                "ok": False,
                "message": "Transacao financeira nao encontrada.",
                "updated": None,
            }

        log_nexus_event(f"FINANCE UPDATE: #{updated['id']} {updated.get('description') or updated.get('category')}")
        broadcast_nexus_state(self)
        self._open_desktop_receipt(
            "finance",
            {
                "animate": "finance_update",
                "toast": f"Movimento atualizado: {updated.get('description') or updated.get('category') or updated['id']}",
                "receipt": {
                    "kind": "finance",
                    "action": "finance_update",
                    "id": updated.get("id"),
                    "type": updated.get("type"),
                    "amount": updated.get("amount"),
                    "category": updated.get("category"),
                    "description": updated.get("description"),
                    "occurred_at": updated.get("occurred_at"),
                    "notes": updated.get("notes"),
                    "is_debt": updated.get("is_debt"),
                },
            },
        )
        return {
            "ok": True,
            "message": f"Movimento financeiro #{updated['id']} atualizado, Sir.",
            "updated": updated,
        }

    def delete_finance_transaction(
        self,
        transaction_id: int | None = None,
        description: str | None = None,
        category: str | None = None,
        tx_type: str | None = None,
        occurred_at: str | None = None,
        amount: float | None = None,
    ) -> dict:
        """Remove uma transacao por id ou pelo melhor match de texto/data."""
        target = None
        if transaction_id:
            target = self.db.get_finance_transaction(int(transaction_id))
        else:
            od = self._normalize_date_alias(occurred_at)
            rows = (
                self.db.list_finance_transactions(od, od)
                if od
                else self.db.list_finance_transactions(None, None)
            )
            desc_key = self._fold_text(description)
            cat_key = self._fold_text(category)
            type_key = (tx_type or "").strip().lower()
            for row in rows:
                if type_key and (row.get("type") or "").lower() != type_key:
                    continue
                if desc_key and desc_key not in self._fold_text(row.get("description")):
                    continue
                if cat_key and cat_key not in self._fold_text(row.get("category")):
                    continue
                if amount is not None and abs(float(row.get("amount") or 0) - float(amount)) > 0.009:
                    continue
                target = row
                break

        if not target:
            return {
                "ok": False,
                "message": "Nao encontrei uma transacao financeira compatível para remover.",
                "deleted": None,
            }

        deleted = self.db.delete_finance_transaction(int(target["id"]))
        if not deleted:
            return {
                "ok": False,
                "message": "Transacao financeira nao encontrada.",
                "deleted": None,
            }

        log_nexus_event(f"FINANCE DELETE: #{deleted['id']} {deleted.get('description') or deleted.get('category')}")
        broadcast_nexus_state(self)
        self._open_desktop_receipt(
            "finance",
            {
                "animate": "finance_delete",
                "toast": f"Movimento removido: {deleted.get('description') or deleted.get('category') or deleted['id']}",
                "receipt": {
                    "kind": "finance",
                    "action": "finance_delete",
                    "id": deleted.get("id"),
                    "type": deleted.get("type"),
                    "amount": deleted.get("amount"),
                    "category": deleted.get("category"),
                    "description": deleted.get("description"),
                    "occurred_at": deleted.get("occurred_at"),
                    "notes": deleted.get("notes"),
                    "is_debt": deleted.get("is_debt"),
                },
            },
        )
        return {
            "ok": True,
            "message": f"Movimento financeiro #{deleted['id']} removido, Sir.",
            "deleted": deleted,
        }

    # --- MINDPALACE (ESTUDOS) ---

    def create_note(self, subject, title, content, media=None, color=None):
        """Cria uma nova nota de estudo."""
        self._last_created_note_id = None
        try:
            with self.db._get_connection() as conn:
                cur = conn.execute(
                    """
                    INSERT INTO study_notes (subject, title, content, media_links, color)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (subject, title, content, json.dumps(media or []), color),
                )
                conn.commit()
                try:
                    self._last_created_note_id = int(cur.lastrowid)
                except (TypeError, ValueError):
                    self._last_created_note_id = None
            log_nexus_event(f"MINDPALACE: Nota '{title}' arquivada.")
            broadcast_nexus_state(self)
            return f"Nota '{title}' sobre {subject} foi salva no seu MindPalace, Sir."
        except Exception as e:
            logger.error(f"Erro ao criar nota: {e}")
            return "Erro ao arquivar nota."

    def capture_note(self, title: str, content: str, url: str | None = None, subject: str | None = None) -> int:
        """Captura conteúdo externo e transforma em nota no MindPalace."""
        final_content = content.strip()
        if url:
            final_content += f"\n\n---\n**Fonte:** {url.strip()}"

        self.create_note(subject or "Captura", title.strip(), final_content)
        return self._last_created_note_id or -1

    def _note_media_list(self, note: dict | None) -> list[dict]:
        if not note:
            return []
        try:
            media = json.loads(note.get("media_links") or "[]")
            return media if isinstance(media, list) else []
        except (TypeError, json.JSONDecodeError):
            return []

    def attach_media_to_note(
        self,
        note_id: int,
        media_url: str,
        caption: str | None = None,
        alt: str | None = None,
        append_markdown: bool = True,
    ) -> dict:
        """Anexa uma imagem/link na nota e opcionalmente insere um bloco markdown."""
        note = self.db.get_study_note(int(note_id))
        if not note:
            return {
                "note_id": int(note_id),
                "attached": None,
                "media": [],
                "content_appended": False,
                "error": "Nota nao encontrada.",
            }

        url = re.sub(r"\s+", " ", str(media_url or "")).strip()
        if not url:
            return {
                "note_id": int(note_id),
                "attached": None,
                "media": self._note_media_list(note),
                "content_appended": False,
                "error": "URL ou caminho da midia vazio.",
            }

        label = re.sub(r"\s+", " ", str(caption or alt or "Imagem da nota")).strip()
        item = {
            "url": url,
            "caption": label,
            "alt": re.sub(r"\s+", " ", str(alt or caption or label)).strip(),
        }
        media = self.db.append_study_note_media(int(note_id), item) or []

        content_appended = False
        if append_markdown:
            current = note.get("content") or ""
            block = f"![{label}]({url})"
            if block not in current:
                new_content = f"{current.rstrip()}\n\n{block}".strip()
                self.db.update_study_note(int(note_id), content=new_content)
                content_appended = True

        msg = f"Midia anexada em {note.get('title') or 'nota'}."
        log_nexus_event(f"MINDPALACE: {msg}")
        broadcast_nexus_state(self)
        self._open_desktop_receipt(
            "notes",
            {
                "highlight_id": int(note_id),
                "animate": "note_media_attach",
                "toast": msg,
                "receipt": {
                    "kind": "note",
                    "action": "note_attach_media",
                    "id": int(note_id),
                    "title": note.get("title") or "",
                    "url": url,
                    "caption": label,
                },
            },
        )
        return {
            "note_id": int(note_id),
            "attached": item,
            "media": media,
            "content_appended": content_appended,
        }

    def add_flashcard(self, note_id, front, back):
        """Adiciona um flashcard a uma nota específica."""
        try:
            with self.db._get_connection() as conn:
                conn.execute("""
                    INSERT INTO flashcards (note_id, front, back)
                    VALUES (?, ?, ?)
                """, (note_id, front, back))
                conn.commit()
            log_nexus_event(f"MINDPALACE: Flashcard gerado.")
            return "Flashcard adicionado com sucesso."
        except Exception as e:
            logger.error(f"Erro ao adicionar flashcard: {e}")
            return "Erro ao criar flashcard."

    def _summary_sentences_from_note(self, content: str, max_sentences: int = 4) -> list[str]:
        body = re.sub(r"(?is)\n## Resumo IA\b.*$", "", content or "").strip()
        lines = self._study_lines(body)
        candidates: list[str] = []
        seen: set[str] = set()
        for kind, text in lines:
            if kind == "heading":
                continue
            for sentence in re.split(r"(?<=[.!?])\s+", text):
                cleaned = re.sub(r"\s+", " ", sentence).strip(" -*")
                if len(cleaned) < 24:
                    continue
                key = cleaned.lower()
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(cleaned.rstrip(".;:") + ".")
        if not candidates and body:
            fallback = re.sub(r"\s+", " ", body).strip()
            if fallback:
                candidates.append(fallback[:520].rstrip(".;:") + ".")
        limit = max(1, min(8, int(max_sentences or 4)))
        return candidates[:limit]

    def summarize_note(self, note_id: int, append: bool = True, max_sentences: int = 4) -> dict:
        """Cria um resumo curto e opcionalmente grava na nota."""
        note = self.db.get_study_note(int(note_id))
        if not note:
            return {"note_id": note_id, "summary": "", "appended": False, "error": "Nota nao encontrada."}

        sentences = self._summary_sentences_from_note(note.get("content") or "", max_sentences)
        summary = "\n".join(f"- {sentence}" for sentence in sentences)
        if not summary:
            summary = "- Sem conteudo suficiente para resumir."

        appended = False
        if append:
            current = re.sub(r"(?is)\n## Resumo IA\b.*$", "", note.get("content") or "").rstrip()
            new_content = f"{current}\n\n## Resumo IA\n{summary}".strip()
            self.db.update_study_note(int(note_id), content=new_content)
            appended = True

        msg = f"Resumo IA gerado para {note.get('title') or 'nota'}."
        log_nexus_event(f"MINDPALACE: {msg}")
        broadcast_nexus_state(self)
        self._open_desktop_receipt(
            "notes",
            {
                "highlight_id": int(note_id),
                "animate": "note_summarize",
                "toast": msg,
                "receipt": {
                    "kind": "note",
                    "action": "note_summarize",
                    "id": int(note_id),
                    "title": note.get("title") or "",
                    "appended": appended,
                },
            },
        )
        return {"note_id": int(note_id), "summary": summary, "appended": appended}

    def teach_note(self, note_id: int, question: str | None = None, max_points: int = 4) -> dict:
        """Gera uma explicacao estilo professor a partir de uma nota salva."""
        note = self.db.get_study_note(int(note_id))
        if not note:
            return {
                "note_id": note_id,
                "mode": "professor",
                "question": (question or "").strip(),
                "lesson": "",
                "key_points": [],
                "check_questions": [],
                "error": "Nota nao encontrada.",
            }

        limit = max(2, min(8, int(max_points or 4)))
        title = (note.get("title") or "Nota").strip()
        subject = (note.get("subject") or "Geral").strip()
        key_points = self._summary_sentences_from_note(note.get("content") or "", limit)
        if not key_points:
            key_points = ["Revise a nota completa e destaque as ideias principais antes de praticar."]

        asked = re.sub(r"\s+", " ", (question or "").strip())
        first_point = key_points[0].rstrip(".")
        lesson_parts = [
            f"Modo Professor: {title} ({subject}).",
            f"Comece pela ideia central: {first_point}.",
        ]
        if asked:
            lesson_parts.append(
                f"Sobre sua pergunta, conecte a duvida com este ponto da nota e explique usando um exemplo simples."
            )
        if len(key_points) > 1:
            lesson_parts.append(
                "Depois organize o raciocinio nestes passos: "
                + " ".join(f"{idx + 1}. {point}" for idx, point in enumerate(key_points[1:]))
            )
        lesson_parts.append("Feche tentando responder sem olhar e marque o que ainda ficou fraco para revisar depois.")

        check_questions: list[str] = []
        for point in key_points:
            topic = self._topic_from_fact(point, title)
            check_questions.append(f"Explique com suas palavras: {topic}.")
            if len(check_questions) >= 3:
                break
        while len(check_questions) < 2:
            check_questions.append(f"Qual exemplo voce usaria para lembrar {title}?")

        msg = f"Modo Professor preparado para {title}."
        log_nexus_event(f"MINDPALACE: {msg}")
        broadcast_nexus_state(self)
        self._open_desktop_receipt(
            "notes",
            {
                "highlight_id": int(note_id),
                "animate": "teacher_mode",
                "toast": msg,
                "receipt": {
                    "kind": "note",
                    "action": "note_teach",
                    "id": int(note_id),
                    "title": title,
                    "question": asked,
                    "point_count": len(key_points),
                },
            },
        )
        return {
            "note_id": int(note_id),
            "title": title,
            "subject": subject,
            "mode": "professor",
            "question": asked,
            "lesson": "\n".join(lesson_parts),
            "key_points": key_points,
            "check_questions": check_questions,
            "next_step": "Gerar flashcards ou revisar as perguntas de checagem.",
        }

    def teach_subject(self, subject: str | None, question: str | None = None, max_points: int = 6) -> dict:
        """Gera uma aula curta usando todas as notas de uma materia."""
        subject_name = re.sub(r"\s+", " ", str(subject or "").strip())
        subject_label = subject_name or "Todas as materias"
        raw_notes = self.db.list_study_notes(subject_name or None)
        notes = sorted(
            [
                note
                for note in raw_notes
                if not subject_name or (note.get("subject") or "").strip() == subject_name
            ],
            key=lambda note: int(note.get("id") or 0),
        )
        asked = re.sub(r"\s+", " ", (question or "").strip())
        if not notes:
            return {
                "subject": subject_label,
                "mode": "professor_subject",
                "question": asked,
                "lesson": "",
                "key_points": [],
                "check_questions": [],
                "note_count": 0,
                "note_ids": [],
                "error": "Materia sem notas salvas.",
            }

        limit = max(2, min(10, int(max_points or 6)))
        key_points: list[str] = []
        for note in notes[:8]:
            title = (note.get("title") or "Nota").strip()
            for sentence in self._summary_sentences_from_note(note.get("content") or "", 2):
                key_points.append(f"{title}: {sentence}")
                if len(key_points) >= limit:
                    break
            if len(key_points) >= limit:
                break
        if not key_points:
            key_points = [
                f"{(notes[0].get('title') or subject_label).strip()}: Revise as ideias principais e transforme cada topico em pergunta."
            ]

        titles = [(note.get("title") or "Nota").strip() for note in notes]
        first_point = key_points[0].rstrip(".")
        lesson_parts = [
            f"Modo Professor da materia: {subject_label}.",
            f"Base de leitura: {len(notes)} nota(s) - {', '.join(titles[:4])}.",
            f"Comece conectando a ideia central: {first_point}.",
        ]
        if asked:
            lesson_parts.append(
                "Para responder sua pergunta, atravesse as notas como uma trilha: conceito, exemplo, armadilha comum e exercicio."
            )
        if len(key_points) > 1:
            lesson_parts.append(
                "Roteiro de revisao: "
                + " ".join(f"{idx + 1}. {point}" for idx, point in enumerate(key_points[1:]))
            )
        lesson_parts.append("Finalize criando flashcards da materia e revisando os pontos que voce nao conseguir explicar em voz alta.")

        check_questions: list[str] = []
        for point in key_points:
            topic = self._topic_from_fact(point, subject_label)
            check_questions.append(f"Explique sem consultar: {topic}.")
            if len(check_questions) >= 4:
                break
        while len(check_questions) < 2:
            check_questions.append(f"Qual exemplo pratico voce usaria para lembrar {subject_label}?")

        first_note_id = int(notes[0].get("id") or 0)
        msg = f"Modo Professor da materia preparado para {subject_label}."
        log_nexus_event(f"MINDPALACE: {msg}")
        broadcast_nexus_state(self)
        self._open_desktop_receipt(
            "notes",
            {
                "highlight_id": first_note_id,
                "animate": "subject_teacher_mode",
                "toast": msg,
                "receipt": {
                    "kind": "note",
                    "action": "subject_teach",
                    "subject": subject_label,
                    "question": asked,
                    "note_count": len(notes),
                    "point_count": len(key_points),
                },
            },
        )
        return {
            "subject": subject_label,
            "mode": "professor_subject",
            "question": asked,
            "lesson": "\n".join(lesson_parts),
            "key_points": key_points,
            "check_questions": check_questions,
            "note_count": len(notes),
            "note_ids": [int(note.get("id") or 0) for note in notes],
            "next_step": "Gerar flashcards da materia e responder as perguntas de checagem.",
        }

    def _study_lines(self, content: str) -> list[tuple[str, str]]:
        lines: list[tuple[str, str]] = []
        for raw in (content or "").splitlines():
            text = raw.strip()
            if not text:
                continue
            if text.startswith("#"):
                heading = text.lstrip("#").strip()
                if heading:
                    lines.append(("heading", heading))
                continue
            chunks = re.split(r"\s+-\s+", text)
            for chunk in chunks:
                item = chunk.strip().lstrip("-*").strip()
                if item:
                    kind = "bullet" if text.startswith(("-", "*")) or chunk != chunks[0] else "text"
                    lines.append((kind, item))
        return lines

    def _topic_from_fact(self, text: str, fallback: str) -> str:
        cleaned = re.sub(r"\s+", " ", (text or "")).strip(" .;:")
        if not cleaned:
            return fallback
        parts = re.split(
            r"\b(e|eh|sao|significa|converte|produz|fixa|marca|marcou|derrubou|absorve|gera|usa)\b",
            cleaned,
            maxsplit=1,
            flags=re.IGNORECASE,
        )
        topic = (parts[0] if parts else cleaned).strip(" .;:")
        if len(topic.split()) > 6 or len(topic) < 3:
            topic = " ".join(cleaned.split()[:6]).strip(" .;:")
        return topic or fallback

    def _flashcard_candidates_from_note(self, note: dict, max_cards: int = 8) -> list[dict]:
        title = (note.get("title") or "Nota").strip()
        lines = self._study_lines(note.get("content") or "")
        cards: list[dict] = []
        seen: set[str] = set()

        def add(front: str, back: str) -> None:
            front = re.sub(r"\s+", " ", front).strip()
            back = re.sub(r"\s+", " ", back).strip()
            key = front.lower()
            if not front or not back or key in seen or len(cards) >= max_cards:
                return
            seen.add(key)
            cards.append({"front": front[:220], "back": back[:600]})

        for idx, (kind, text) in enumerate(lines):
            if len(cards) >= max_cards:
                break
            if kind == "heading":
                answer = next((line for k, line in lines[idx + 1 :] if k != "heading"), title)
                add(f"O que estudar em {text}?", answer)
                continue
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
            for sentence in sentences or [text]:
                topic = self._topic_from_fact(sentence, title)
                if kind == "bullet":
                    add(f"O que lembrar sobre {topic}?", sentence)
                else:
                    add(f"Qual e a ideia central de {topic}?", sentence)
                if len(cards) >= max_cards:
                    break

        if not cards and title:
            add(f"Qual e o resumo de {title}?", note.get("content") or f"Revisar {title}.")
        return cards

    def _insert_flashcards(self, note_id: int | None, cards: list[dict]) -> list[dict]:
        created: list[dict] = []
        with self.db._get_connection() as conn:
            if note_id is None:
                rows = conn.execute("SELECT front FROM flashcards WHERE note_id IS NULL").fetchall()
            else:
                rows = conn.execute(
                    "SELECT front FROM flashcards WHERE note_id = ?",
                    (note_id,),
                ).fetchall()
            existing = {row[0] for row in rows}
            for card in cards:
                if card["front"] in existing:
                    continue
                cur = conn.execute(
                    """
                    INSERT INTO flashcards (note_id, front, back)
                    VALUES (?, ?, ?)
                    """,
                    (note_id, card["front"], card["back"]),
                )
                created.append({**card, "id": cur.lastrowid, "note_id": note_id})
                existing.add(card["front"])
            conn.commit()
        return created

    def generate_flashcards_from_note(self, note_id: int, max_cards: int = 8) -> dict:
        """Gera flashcards SRS a partir do conteudo de uma nota."""
        note = self.db.get_study_note(int(note_id))
        if not note:
            return {"note_id": note_id, "created": 0, "cards": [], "error": "Nota nao encontrada."}
        limit = max(1, min(20, int(max_cards or 8)))
        cards = self._flashcard_candidates_from_note(note, limit)
        created = self._insert_flashcards(int(note_id), cards)
        msg = f"{len(created)} flashcards gerados para {note.get('title') or 'nota'}."
        log_nexus_event(f"MINDPALACE: {msg}")
        if created:
            broadcast_nexus_state(self)
        self._open_desktop_receipt(
            "study",
            {
                "animate": "flashcards_generate",
                "toast": msg,
                "note_id": int(note_id),
                "created": len(created),
            },
        )
        return {"note_id": int(note_id), "created": len(created), "cards": created}

    def generate_flashcards_from_subject(self, subject: str, max_cards: int = 20) -> dict:
        """Gera flashcards para todas as notas de uma materia/assunto."""
        subject_name = (subject or "").strip()
        notes = self.db.list_study_notes(subject_name or None)
        total = 0
        created_cards: list[dict] = []
        remaining = max(1, min(50, int(max_cards or 20)))
        for note in notes:
            if subject_name and (note.get("subject") or "") != subject_name:
                continue
            result = self.generate_flashcards_from_note(note["id"], remaining)
            total += int(result.get("created") or 0)
            created_cards.extend(result.get("cards") or [])
            remaining -= int(result.get("created") or 0)
            if remaining <= 0:
                break
        return {"subject": subject_name or None, "created": total, "cards": created_cards}

    def get_review_count(self):
        """Retorna quantos flashcards precisam de revisão hoje."""
        with self.db._get_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM flashcards WHERE datetime(next_review) <= datetime('now')"
            ).fetchone()[0]
            return count

    def log_study_result(self, subject, correct=True):
        """Registra o resultado de uma questão de estudo."""
        key = (subject or "Geral").strip().lower()
        subject_db = _SUBJECT_ALIASES.get(key, subject)
        try:
            with self.db._get_connection() as conn:
                conn.execute("""
                    INSERT OR IGNORE INTO study_stats (subject, total_questions, correct_answers)
                    VALUES (?, 0, 0)
                """, (subject_db,))

                if correct:
                    conn.execute("""
                        UPDATE study_stats
                        SET total_questions = total_questions + 1, correct_answers = correct_answers + 1, last_attempt = CURRENT_TIMESTAMP
                        WHERE subject = ?
                    """, (subject_db,))
                else:
                    conn.execute("""
                        UPDATE study_stats
                        SET total_questions = total_questions + 1, last_attempt = CURRENT_TIMESTAMP
                        WHERE subject = ?
                    """, (subject_db,))
                conn.commit()

            xp = 30 if correct else 10
            self.db.add_xp(xp)

            status = "ACERTOU" if correct else "ERROU"
            log_nexus_event(f"ESTUDO: {subject_db} ({status})")
            broadcast_nexus_state(self)

            return f"Resultado registrado, Sir. +{xp} XP em {subject_db}."
        except Exception as e:
            logger.error(f"Erro ao registrar estudo: {e}")
            return "Falha ao salvar desempenho."

    def get_study_stats(self):
        """Retorna as estatísticas de estudo para o HUD."""
        import sqlite3
        with self.db._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM study_stats").fetchall()
            return [dict(r) for r in rows]

    def get_study_recommendations(self, limit: int = 4) -> dict:
        """Analisa desempenho e devolve proximas acoes de estudo."""
        stats = self.get_study_stats()
        total_questions = sum(int(s.get("total_questions") or 0) for s in stats)
        correct_answers = sum(int(s.get("correct_answers") or 0) for s in stats)
        overall_accuracy = round((correct_answers / total_questions) * 100) if total_questions else 0
        due_cards = self.db.list_flashcards_due(50)

        candidates = []
        for stat in stats:
            subject = stat.get("subject") or "Geral"
            total = int(stat.get("total_questions") or 0)
            correct = int(stat.get("correct_answers") or 0)
            accuracy = round((correct / total) * 100) if total else 0
            if total == 0:
                bucket = 1
                reason = "Ainda sem simulado registrado."
                action = f"Fazer 5 questoes diagnosticas de {subject}."
            elif accuracy < 50:
                bucket = 0
                reason = "Taxa de acerto critica."
                action = f"Revisar teoria e fazer uma lista curta de {subject}."
            elif accuracy < 70:
                bucket = 0
                reason = "Abaixo da meta de 70%."
                action = f"Refazer erros recentes de {subject}."
            else:
                bucket = 2
                reason = "Manter ritmo."
                action = f"Manter revisao leve de {subject}."
            candidates.append(
                {
                    "subject": subject,
                    "total": total,
                    "correct": correct,
                    "accuracy": accuracy,
                    "priority": "high" if bucket == 0 else "medium" if bucket == 1 else "low",
                    "reason": reason,
                    "suggested_action": action,
                    "_sort": (bucket, accuracy if total else 101, -total),
                }
            )

        candidates.sort(key=lambda item: item["_sort"])
        weak_subjects = []
        for item in candidates:
            item = dict(item)
            item.pop("_sort", None)
            if item["priority"] != "low" or len(weak_subjects) < limit:
                weak_subjects.append(item)
            if len(weak_subjects) >= limit:
                break

        next_actions = []
        if due_cards:
            next_actions.append(f"Revisar {len(due_cards)} flashcards pendentes hoje.")
        for item in weak_subjects[:3]:
            next_actions.append(item["suggested_action"])
        if not next_actions:
            next_actions.append("Fazer um simulado curto para atualizar o diagnostico.")

        return {
            "overall": {
                "questions": total_questions,
                "correct": correct_answers,
                "accuracy": overall_accuracy,
            },
            "flashcards_due": len(due_cards),
            "weak_subjects": weak_subjects,
            "next_actions": next_actions,
        }

    def review_quiz_attempt(self, attempt_id: int, emit_receipt: bool = True) -> dict:
        """Monta revisao do simulado com explicacao, resposta correta e acoes."""
        attempt = self.db.get_quiz_attempt(int(attempt_id))
        rows = self.db.list_quiz_attempt_answers(int(attempt_id))
        total = len(rows)
        correct_count = sum(1 for row in rows if int(row.get("correct") or 0))
        score_pct = round((correct_count / total) * 100) if total else 0
        if attempt and attempt.get("score_pct") is not None:
            try:
                score_pct = round(float(attempt.get("score_pct") or 0))
            except (TypeError, ValueError):
                pass

        items = []
        weak_skills: dict[str, int] = {}
        weak_areas: dict[str, int] = {}
        for row in rows:
            try:
                options = json.loads(row.get("options_json") or "[]")
            except (TypeError, json.JSONDecodeError):
                options = []
            chosen = int(row.get("chosen_index") or 0)
            correct_idx = int(row.get("correct_index") or 0)
            area = row.get("area") or "Geral"
            skill = row.get("skill") or area
            is_correct = bool(int(row.get("correct") or 0))
            if not is_correct:
                weak_skills[skill] = weak_skills.get(skill, 0) + 1
                weak_areas[area] = weak_areas.get(area, 0) + 1
            items.append(
                {
                    "question_id": row.get("question_id"),
                    "area": area,
                    "skill": skill,
                    "difficulty": row.get("difficulty") or "media",
                    "stem": row.get("stem") or "",
                    "chosen_index": chosen,
                    "chosen_option": options[chosen] if 0 <= chosen < len(options) else "",
                    "correct_index": correct_idx,
                    "correct_option": options[correct_idx] if 0 <= correct_idx < len(options) else "",
                    "correct": is_correct,
                    "explanation": row.get("explanation")
                    or "Revise o conceito central desta questao e tente explicar o raciocinio em voz alta.",
                    "source": row.get("source") or "",
                }
            )

        wrong_count = total - correct_count
        top_skills = sorted(weak_skills.items(), key=lambda item: (-item[1], item[0]))
        top_areas = sorted(weak_areas.items(), key=lambda item: (-item[1], item[0]))
        next_actions = []
        for skill, count in top_skills[:3]:
            next_actions.append(f"Revisar {skill} e criar flashcards dos {count} erro(s).")
        if wrong_count:
            next_actions.append("Refazer apenas as questoes erradas antes de iniciar outro simulado.")
        else:
            next_actions.append("Aumentar a dificuldade ou fazer um simulado com mais questoes.")

        breakdown = {}
        for item in items:
            area = item["area"]
            if area not in breakdown:
                breakdown[area] = {"total": 0, "correct": 0, "pct": 0}
            breakdown[area]["total"] += 1
            if item["correct"]:
                breakdown[area]["correct"] += 1

        for area, data in breakdown.items():
            data["pct"] = round((data["correct"] / data["total"]) * 100) if data["total"] else 0

        review = {
            "attempt_id": int(attempt_id),
            "area": (attempt or {}).get("area"),
            "score_pct": score_pct,
            "total": total,
            "correct_count": correct_count,
            "wrong_count": wrong_count,
            "weak_skills": [{"skill": skill, "misses": count} for skill, count in top_skills],
            "weak_areas": [{"area": area, "misses": count} for area, count in top_areas],
            "items": items,
            "breakdown": breakdown,
            "next_actions": next_actions,
        }
        if emit_receipt:
            log_nexus_event(f"QUIZ REVIEW: tentativa #{attempt_id} {score_pct}%")
            self._open_desktop_receipt(
                "quiz",
                {
                    "animate": "quiz_review",
                    "toast": f"Revisao do simulado pronta: {score_pct}%",
                    "receipt": {
                        "kind": "quiz",
                        "action": "quiz_review",
                        "attempt_id": int(attempt_id),
                        "score_pct": score_pct,
                        "wrong_count": wrong_count,
                    },
                },
            )
        return review

    def generate_flashcards_from_quiz_attempt(
        self,
        attempt_id: int,
        only_wrong: bool = True,
        max_cards: int = 8,
    ) -> dict:
        """Cria flashcards SRS a partir da revisao de um simulado."""
        if isinstance(only_wrong, str):
            only_wrong = only_wrong.strip().lower() not in ("0", "false", "no", "nao")
        limit = max(1, min(20, int(max_cards or 8)))
        review = self.review_quiz_attempt(int(attempt_id), emit_receipt=False)
        source_items = [
            item
            for item in (review.get("items") or [])
            if (not only_wrong or not item.get("correct"))
        ]

        cards: list[dict] = []
        for item in source_items[:limit]:
            skill = item.get("skill") or item.get("area") or "Geral"
            stem = " ".join(str(item.get("stem") or "").split())
            correct_option = str(item.get("correct_option") or "").strip()
            explanation = str(item.get("explanation") or "").strip()
            front = f"Quiz ENEM - {skill}: {stem}"[:220]
            back_parts = []
            if correct_option:
                back_parts.append(f"Resposta correta: {correct_option}")
            if explanation:
                back_parts.append(f"Explicacao: {explanation}")
            back_parts.append(f"Skill: {skill}")
            cards.append(
                {
                    "front": front,
                    "back": "\n\n".join(back_parts)[:600],
                    "question_id": item.get("question_id"),
                    "skill": skill,
                    "area": item.get("area") or "Geral",
                    "correct_option": correct_option,
                }
            )

        created = self._insert_flashcards(None, cards)
        msg = f"{len(created)} flashcards dos erros do simulado criados."
        log_nexus_event(f"QUIZ FLASHCARDS: tentativa #{attempt_id} {len(created)} card(s)")
        if created:
            broadcast_nexus_state(self)
        self._open_desktop_receipt(
            "quiz",
            {
                "animate": "quiz_flashcards_generate",
                "toast": msg,
                "attempt_id": int(attempt_id),
                "created": len(created),
                "only_wrong": bool(only_wrong),
            },
        )
        return {
            "attempt_id": int(attempt_id),
            "created": len(created),
            "source_count": len(source_items),
            "only_wrong": bool(only_wrong),
            "cards": created,
        }

    # --- STRATEGY ENGINE (PRESETS) ---

    def _normalize_days_of_week(self, value) -> str | None:
        if value in (None, "", []):
            return None
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return None
            if raw.startswith("["):
                try:
                    value = json.loads(raw)
                except json.JSONDecodeError:
                    return raw
            else:
                return raw
        if isinstance(value, (list, tuple)):
            days = []
            for day in value:
                try:
                    day_int = int(day)
                except (TypeError, ValueError):
                    continue
                if 0 <= day_int <= 6 and day_int not in days:
                    days.append(day_int)
            return json.dumps(days) if days else None
        return None

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

    def save_lifestyle_preset(self, name):
        """Salva o estado atual de hábitos como um preset."""
        try:
            preset_name = (name or "").strip() or "Preset Nexus"
            habits = self.db.get_habits()
            config = json.dumps(
                [self._preset_habit_config(h) for h in habits],
                ensure_ascii=False,
            )
            with self.db._get_connection() as conn:
                row = conn.execute(
                    "SELECT id FROM lifestyle_presets WHERE name = ?",
                    (preset_name,),
                ).fetchone()
                if row:
                    conn.execute(
                        """
                        UPDATE lifestyle_presets
                        SET config_json = ?, created_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (config, row[0]),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO lifestyle_presets (name, config_json)
                        VALUES (?, ?)
                        """,
                        (preset_name, config),
                    )
                conn.commit()
            log_nexus_event(f"STRATEGY: Preset '{preset_name}' salvo.")
            return f"Preset de vida '{preset_name}' foi imortalizado, Sir."
        except Exception as e:
            logger.error(f"Erro ao salvar preset: {e}")
            return "Falha ao salvar configuração estratégica."

    def list_lifestyle_presets(self) -> list[dict]:
        """Lista presets salvos com contagem resumida para UI/IA."""
        with self.db._get_connection() as conn:
            conn.row_factory = __import__("sqlite3").Row
            rows = conn.execute(
                """
                SELECT id, name, config_json, is_active, created_at
                FROM lifestyle_presets
                ORDER BY is_active DESC, datetime(created_at) DESC, id DESC
                """
            ).fetchall()
        presets = []
        for row in rows:
            try:
                habits = json.loads(row["config_json"] or "[]")
            except json.JSONDecodeError:
                habits = []
            presets.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "habit_count": len(habits) if isinstance(habits, list) else 0,
                    "is_active": bool(row["is_active"]),
                    "created_at": row["created_at"],
                }
            )
        return presets

    def load_lifestyle_preset(self, name):
        """Carrega um preset de vida, substituindo os hábitos atuais."""
        try:
            search_name = (name or "").strip()
            with self.db._get_connection() as conn:
                row = conn.execute(
                    """
                    SELECT id, name, config_json
                    FROM lifestyle_presets
                    WHERE name LIKE ?
                    ORDER BY length(name) ASC, datetime(created_at) DESC
                    LIMIT 1
                    """,
                    (f"%{search_name}%",),
                ).fetchone()
                if not row:
                    return f"Não encontrei o preset '{search_name}', Sir."

                preset_id, preset_name, config_json = row
                new_habits = json.loads(config_json or "[]")
                conn.execute("UPDATE lifestyle_presets SET is_active = 0")
                conn.execute("UPDATE lifestyle_presets SET is_active = 1 WHERE id = ?", (preset_id,))
                conn.commit()

            habit_count = self._replace_active_habits(new_habits if isinstance(new_habits, list) else [])
            msg = f"Protocolo '{preset_name}' ativado. Todos os sistemas reconfigurados."
            log_nexus_event(f"STRATEGY: Preset '{preset_name}' ativado.")
            broadcast_nexus_state(self)
            self._open_desktop_receipt(
                "habits",
                {
                    "animate": "preset",
                    "toast": msg,
                    "receipt": {
                        "kind": "preset",
                        "action": "preset_apply",
                        "name": preset_name,
                        "habit_count": habit_count,
                    },
                },
            )
            return msg
        except Exception as e:
            logger.error(f"Erro ao carregar preset: {e}")
            return "Falha na reconfiguração estratégica."

    # --- GRAND OBJECTIVES (METAS) ---

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

    # --- WINDOW THEME PRESETS ---

    def _window_theme_store_path(self) -> Path:
        db_path = Path(getattr(self.db, "db_path", "data/nexus.db"))
        return db_path.parent / "nexus_window_themes.json"

    def _fold_key(self, value: str | None) -> str:
        folded = unicodedata.normalize("NFKD", (value or "").lower())
        folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
        return " ".join(re.sub(r"[^a-z0-9]+", " ", folded).split())

    def _slug_theme_id(self, value: str | None, fallback: str = "tema-nexus") -> str:
        folded = self._fold_key(value)
        slug = re.sub(r"[^a-z0-9]+", "-", folded).strip("-")
        return (slug or fallback)[:64]

    def _normalize_window_module(self, module: str | None) -> str | None:
        raw = self._fold_key(module)
        if raw in _NEXUS_WINDOW_MODULES:
            return raw
        if raw in _NEXUS_WINDOW_MODULE_ALIASES:
            return _NEXUS_WINDOW_MODULE_ALIASES[raw]
        for key, value in _NEXUS_WINDOW_MODULE_ALIASES.items():
            if key and key in raw:
                return value
        return None

    def _clean_theme_tokens(self, tokens: dict | None) -> dict:
        if not isinstance(tokens, dict):
            return {}
        clean = {}
        for key in sorted(_NEXUS_THEME_TOKEN_KEYS):
            if key not in tokens:
                continue
            value = str(tokens.get(key) or "").strip()
            if not value:
                continue
            if any(ch in value for ch in ['"', "'", "<", ">", "{", "}"]):
                continue
            if len(value) > 96:
                continue
            clean[key] = value
        return clean

    def _normalize_theme_preset(self, preset: dict, custom: bool = False) -> dict:
        pid = self._slug_theme_id(preset.get("id") or preset.get("name"))
        mode = str(preset.get("mode") or "dark").strip().lower()
        return {
            "id": pid,
            "name": str(preset.get("name") or pid).strip()[:80],
            "mode": "light" if mode == "light" else "dark",
            "description": str(preset.get("description") or "").strip()[:180],
            "tokens": self._clean_theme_tokens(preset.get("tokens")),
            "custom": bool(custom),
        }

    def _load_window_theme_store(self) -> dict:
        path = self._window_theme_store_path()
        raw = {}
        if path.is_file():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                raw = {}
        modules = {}
        for module, preset_id in dict(raw.get("modules") or {}).items():
            mod = self._normalize_window_module(module)
            if mod:
                modules[mod] = self._slug_theme_id(str(preset_id or ""))
        custom_presets = {}
        for pid, preset in dict(raw.get("presets") or {}).items():
            if isinstance(preset, dict):
                normalized = self._normalize_theme_preset({**preset, "id": pid}, custom=True)
                custom_presets[normalized["id"]] = normalized
        presets = {
            pid: self._normalize_theme_preset(preset, custom=False)
            for pid, preset in _DEFAULT_WINDOW_THEME_PRESETS.items()
        }
        presets.update(custom_presets)
        modules = {
            module: preset_id
            for module, preset_id in modules.items()
            if preset_id in presets
        }
        return {
            "version": 1,
            "modules": modules,
            "custom_presets": custom_presets,
            "presets": presets,
        }

    def _save_window_theme_store(self, modules: dict, custom_presets: dict) -> None:
        path = self._window_theme_store_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "modules": {
                module: preset_id
                for module, preset_id in sorted(modules.items())
                if module in _NEXUS_WINDOW_MODULES
            },
            "presets": {
                pid: {
                    "id": preset["id"],
                    "name": preset["name"],
                    "mode": preset["mode"],
                    "description": preset.get("description") or "",
                    "tokens": self._clean_theme_tokens(preset.get("tokens")),
                }
                for pid, preset in sorted(custom_presets.items())
            },
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def list_window_themes(self) -> dict:
        store = self._load_window_theme_store()
        assignments = dict(store["modules"])
        presets = list(store["presets"].values())
        presets.sort(key=lambda item: (item.get("custom", False), item["name"].lower()))
        modules = []
        for module_id, label in _NEXUS_WINDOW_MODULES.items():
            preset_id = assignments.get(module_id, _DEFAULT_WINDOW_THEME_ID)
            preset = store["presets"].get(preset_id) or store["presets"][_DEFAULT_WINDOW_THEME_ID]
            modules.append(
                {
                    "id": module_id,
                    "label": label,
                    "preset_id": preset["id"],
                    "preset_name": preset["name"],
                }
            )
        return {
            "modules": modules,
            "presets": presets,
            "assignments": assignments,
        }

    def get_window_theme_boot(self, module: str | None) -> dict:
        mod = self._normalize_window_module(module) or "overview"
        store = self._load_window_theme_store()
        preset_id = store["modules"].get(mod, _DEFAULT_WINDOW_THEME_ID)
        preset = store["presets"].get(preset_id) or store["presets"][_DEFAULT_WINDOW_THEME_ID]
        return {
            "module": mod,
            "theme": preset["mode"],
            "theme_preset": preset["id"],
            "theme_name": preset["name"],
            "theme_tokens": self._clean_theme_tokens(preset.get("tokens")),
        }

    def apply_window_theme(self, module: str | None, preset_id: str | None) -> dict:
        mod = self._normalize_window_module(module)
        if not mod:
            return {"ok": False, "error": f"Modulo Nexus invalido: {module}"}
        store = self._load_window_theme_store()
        pid = self._slug_theme_id(preset_id)
        preset = store["presets"].get(pid)
        if not preset:
            return {"ok": False, "error": f"Preset de tema nao encontrado: {preset_id}"}
        modules = dict(store["modules"])
        modules[mod] = pid
        self._save_window_theme_store(modules, store["custom_presets"])
        broadcast_nexus_state(self)
        boot = self.get_window_theme_boot(mod)
        msg = f"Tema '{preset['name']}' aplicado em {_NEXUS_WINDOW_MODULES[mod]}."
        self._open_desktop_receipt(
            mod,
            {
                **boot,
                "animate": "theme_apply",
                "toast": msg,
                "receipt": {
                    "kind": "theme",
                    "action": "theme_apply",
                    "module": mod,
                    "preset_id": pid,
                    "name": preset["name"],
                },
            },
        )
        log_nexus_event(f"THEME: {mod} -> {pid}")
        return {
            "ok": True,
            "module": mod,
            "preset": preset,
            "assignment": {mod: pid},
            "boot": boot,
            "message": msg,
        }

    def _generated_theme_tokens(self, accent: str, mode: str) -> dict:
        palettes = {
            "#10b981": ("16,185,129", "#059669"),
            "#38bdf8": ("56,189,248", "#0ea5e9"),
            "#f59e0b": ("245,158,11", "#d97706"),
            "#f472b6": ("244,114,182", "#db2777"),
            "#ef4444": ("239,68,68", "#dc2626"),
            "#8b5cf6": ("139,92,246", "#7c3aed"),
        }
        rgb, hover = palettes.get(accent, palettes["#8b5cf6"])
        if mode == "light":
            return {
                "--bg": "#fbfcff",
                "--bg-panel": "#ffffff",
                "--surface": f"rgba({rgb},0.055)",
                "--surface-hover": f"rgba({rgb},0.095)",
                "--border": "rgba(15,23,42,0.12)",
                "--border-accent": f"rgba({rgb},0.42)",
                "--text": "#111827",
                "--text-dim": "#5b6475",
                "--text-muted": "#7a8496",
                "--muted": "#6b7280",
                "--accent": accent,
                "--accent-hover": hover,
                "--accent-glow": f"rgba({rgb},0.26)",
                "--accent-subtle": f"rgba({rgb},0.10)",
                "--sidebar": "#eef2ff",
                "--shadow": f"0 22px 55px rgba({rgb},0.14)",
            }
        return {
            "--bg": "#06070b",
            "--bg-panel": "#0d1118",
            "--surface": f"rgba({rgb},0.08)",
            "--surface-hover": f"rgba({rgb},0.14)",
            "--border": f"rgba({rgb},0.16)",
            "--border-accent": f"rgba({rgb},0.46)",
            "--text": "#f4f7fb",
            "--text-dim": "#9aa9ba",
            "--text-muted": "#667487",
            "--muted": "#8b98a8",
            "--accent": accent,
            "--accent-hover": hover,
            "--accent-glow": f"rgba({rgb},0.32)",
            "--accent-subtle": f"rgba({rgb},0.10)",
            "--sidebar": "#030509",
            "--shadow": f"0 0 34px rgba({rgb},0.16)",
        }

    def generate_window_theme_preset(self, module: str | None, prompt: str | None, name: str | None = None) -> dict:
        mod = self._normalize_window_module(module)
        if not mod:
            return {"ok": False, "error": f"Modulo Nexus invalido: {module}"}
        folded = self._fold_key(prompt)
        mode = "light" if any(word in folded for word in ["claro", "light", "clean", "branco", "solar"]) else "dark"
        if any(word in folded for word in ["verde", "financa", "dinheiro", "invest", "emerald"]):
            accent = "#10b981"
            mood = "Emerald"
        elif any(word in folded for word in ["azul", "estudo", "foco", "srs", "nota", "cyan"]):
            accent = "#38bdf8"
            mood = "Cyan"
        elif any(word in folded for word in ["dourado", "gold", "luxo", "premium", "solar"]):
            accent = "#f59e0b"
            mood = "Solar"
        elif any(word in folded for word in ["rosa", "pink", "anime", "magenta"]):
            accent = "#f472b6"
            mood = "Rose"
        elif any(word in folded for word in ["vermelho", "red", "stark"]):
            accent = "#ef4444"
            mood = "Redline"
        else:
            accent = "#8b5cf6"
            mood = "Neon"
        preset_name = (name or "").strip() or f"{mood} {_NEXUS_WINDOW_MODULES[mod]}"
        pid = self._slug_theme_id(preset_name)
        store = self._load_window_theme_store()
        if pid in _DEFAULT_WINDOW_THEME_PRESETS:
            pid = f"{pid}-custom"
        preset = {
            "id": pid,
            "name": preset_name[:80],
            "mode": mode,
            "description": f"Preset gerado para {_NEXUS_WINDOW_MODULES[mod]}.",
            "tokens": self._generated_theme_tokens(accent, mode),
            "custom": True,
        }
        custom_presets = dict(store["custom_presets"])
        custom_presets[pid] = preset
        modules = dict(store["modules"])
        modules[mod] = pid
        self._save_window_theme_store(modules, custom_presets)
        broadcast_nexus_state(self)
        boot = self.get_window_theme_boot(mod)
        msg = f"Tema '{preset_name}' gerado e aplicado em {_NEXUS_WINDOW_MODULES[mod]}."
        self._open_desktop_receipt(
            mod,
            {
                **boot,
                "animate": "theme_apply",
                "toast": msg,
                "receipt": {
                    "kind": "theme",
                    "action": "theme_generate",
                    "module": mod,
                    "preset_id": pid,
                    "name": preset_name,
                },
            },
        )
        log_nexus_event(f"THEME: generated {pid} for {mod}")
        return {
            "ok": True,
            "module": mod,
            "preset": preset,
            "assignment": {mod: pid},
            "boot": boot,
            "message": msg,
        }

    # --- NEURAL MEMORY GRAPH ---

    def _graph_node(
        self,
        nodes: dict[str, dict],
        node_id: str,
        node_type: str,
        label: str,
        subtitle: str = "",
        cluster: str = "nexus",
        weight: float = 1.0,
        details: str = "",
        source: dict | None = None,
    ) -> None:
        if not node_id or node_id in nodes:
            return
        nodes[node_id] = {
            "id": node_id,
            "type": node_type,
            "label": str(label or node_type).strip()[:120],
            "subtitle": str(subtitle or "").strip()[:180],
            "cluster": str(cluster or node_type).strip()[:80],
            "weight": float(weight or 1.0),
            "details": str(details or "").strip()[:900],
            "source": source or {},
        }

    def _graph_edge(
        self,
        edges: dict[str, dict],
        source: str,
        target: str,
        edge_type: str,
        label: str = "",
        weight: float = 1.0,
    ) -> None:
        if not source or not target or source == target:
            return
        edge_id = f"{source}->{target}:{edge_type}"
        if edge_id in edges:
            return
        edges[edge_id] = {
            "id": edge_id,
            "source": source,
            "target": target,
            "type": edge_type,
            "label": str(label or edge_type).strip()[:80],
            "weight": float(weight or 1.0),
        }

    def _graph_text_summary(self, text: str | None, limit: int = 220) -> str:
        clean = re.sub(r"\s+", " ", str(text or "")).strip()
        if len(clean) <= limit:
            return clean
        return clean[: limit - 1].rstrip() + "..."

    def _graph_slug(self, value: str | None, fallback: str = "item") -> str:
        key = self._fold_key(value)
        if not key:
            key = self._fold_key(fallback)
        return key.replace(" ", "-") or "item"

    def _graph_keywords(self, *texts: str, limit: int = 5) -> list[str]:
        stop = {
            "sobre", "para", "como", "mais", "com", "uma", "que", "por", "dos", "das",
            "de", "da", "do", "em", "no", "na", "os", "as", "um", "ao", "aos", "e",
            "o", "a", "the", "and", "with", "from", "this", "that", "sem", "ser",
            "ter", "esta", "este", "isso", "essa", "esse", "todo", "todos",
        }
        raw = self._fold_key(" ".join(str(t or "") for t in texts))
        counts: dict[str, int] = {}
        for word in raw.split():
            if len(word) < 4 or word in stop:
                continue
            counts[word] = counts.get(word, 0) + 1
        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return [word for word, _ in ranked[: max(1, int(limit or 5))]]

    def _graph_semantic_topics(self, *texts: str) -> list[str]:
        folded = self._fold_key(" ".join(str(t or "") for t in texts))
        if not folded:
            return []
        topic_map = {
            "energia_solar": {
                "solar", "solares", "fotovoltaica", "fotovoltaicas", "placas",
                "radiacao", "renovavel", "eletricidade", "energia",
            },
            "enem_estudos": {
                "enem", "simulado", "simulados", "redacao", "vestibular",
                "questoes", "revisao", "revisoes", "flashcards", "estudo",
            },
            "ia_tecnologia": {
                "ia", "inteligencia", "artificial", "modelo", "modelos",
                "software", "digital", "algoritmo", "neural",
            },
            "financas": {
                "gasto", "gastos", "receita", "dinheiro", "orcamento",
                "divida", "cartao", "mercado", "investimento",
            },
            "saude_rotina": {
                "saude", "sono", "treino", "academia", "caminhar",
                "meditar", "habito", "rotina",
            },
        }
        topics = []
        words = set(folded.split())
        for topic, aliases in topic_map.items():
            if words & aliases:
                topics.append(topic)
        return topics

    def _graph_local_embedding(self, *texts: str, dimensions: int = 32) -> list[float]:
        terms = self._graph_keywords(*texts, limit=16) + self._graph_semantic_topics(*texts)
        if not terms:
            return []
        dims = max(8, min(96, int(dimensions or 32)))
        vec = [0.0] * dims
        for term in terms:
            slot = sum(ord(ch) for ch in term) % dims
            vec[slot] += 1.0 + min(1.0, len(term) / 14.0)
        norm = sum(value * value for value in vec) ** 0.5 or 1.0
        return [round(value / norm, 4) for value in vec]

    def _graph_vector_similarity(self, left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        return sum(a * b for a, b in zip(left, right))

    def _graph_node_search_text(self, node: dict) -> str:
        source = node.get("source") if isinstance(node.get("source"), dict) else {}
        source_text = " ".join(str(v) for v in source.values() if isinstance(v, (str, int, float)))
        return " ".join(
            str(part or "")
            for part in (
                node.get("label"),
                node.get("subtitle"),
                node.get("details"),
                node.get("type"),
                node.get("cluster"),
                source_text,
            )
        )

    def _graph_query_terms(self, query: str | None) -> list[str]:
        return self._graph_keywords(query or "", limit=8) if str(query or "").strip() else []

    def _graph_relevance_score(self, node: dict, query: str, terms: list[str]) -> float:
        if not terms:
            return 0.0
        text = self._fold_key(self._graph_node_search_text(node))
        label = self._fold_key(node.get("label"))
        folded_query = self._fold_key(query)
        keywords = set(node.get("keywords") or [])
        score = 0.0
        if folded_query and folded_query in label:
            score += 8.0
        elif folded_query and folded_query in text:
            score += 5.0
        for term in terms:
            if term in keywords:
                score += 2.4
            if term in label:
                score += 2.0
            elif term in text:
                score += 1.0
        type_bias = {
            "note": 1.8,
            "memory": 1.4,
            "markdown": 1.2,
            "flashcard": 0.9,
            "subject": 0.6,
            "task": 0.5,
            "habit": 0.4,
            "goal": 0.4,
            "reward": 0.2,
        }
        if score > 0:
            score += type_bias.get(str(node.get("type") or ""), 0.0)
        return round(score, 2)

    def _graph_match_payload(self, node: dict) -> dict:
        return {
            "id": node.get("id"),
            "type": node.get("type"),
            "label": node.get("label"),
            "subtitle": node.get("subtitle"),
            "details": node.get("details"),
            "cluster": node.get("cluster"),
            "source": node.get("source") or {},
            "keywords": list(node.get("keywords") or [])[:8],
            "relevance": float(node.get("relevance") or 0),
        }

    def _graph_add_semantic_edges(
        self,
        nodes: dict[str, dict],
        edges: dict[str, dict],
        query_terms: list[str],
        limit: int = 90,
    ) -> int:
        skip_types = {"core", "subject", "tag", "memory_category"}
        candidates = [
            node for node in nodes.values()
            if node.get("type") not in skip_types and node.get("keywords")
        ]
        existing_pairs = {
            frozenset((edge["source"], edge["target"]))
            for edge in edges.values()
            if edge.get("source") and edge.get("target")
        }
        scored: list[tuple[float, dict, dict, list[str]]] = []
        q_terms = set(query_terms or [])
        for idx, left in enumerate(candidates):
            left_terms = set(left.get("keywords") or [])
            left_topics = set(left.get("semantic_topics") or [])
            if not left_terms:
                continue
            for right in candidates[idx + 1:]:
                pair = frozenset((left["id"], right["id"]))
                if pair in existing_pairs:
                    continue
                right_terms = set(right.get("keywords") or [])
                right_topics = set(right.get("semantic_topics") or [])
                common = sorted(left_terms & right_terms)
                common_topics = sorted(left_topics & right_topics)
                vector_score = self._graph_vector_similarity(
                    left.get("_semantic_vector") or [],
                    right.get("_semantic_vector") or [],
                )
                if not common and not common_topics and vector_score < 0.52:
                    continue
                score = len(common) * 0.55
                score += len(common_topics) * 1.05
                score += max(0.0, vector_score - 0.38)
                if q_terms and (q_terms & set(common)):
                    score += 0.6
                if q_terms and common_topics:
                    score += 0.4
                if left.get("type") != right.get("type"):
                    score += 0.25
                if left.get("cluster") != right.get("cluster"):
                    score += 0.15
                if score < 0.95:
                    continue
                label_terms = common[:3] or common_topics[:2] or ["vetor-local"]
                edge_type = "semantic" if common_topics or (not common and vector_score >= 0.52) else "relates"
                scored.append((score, left, right, label_terms, edge_type))
        scored.sort(key=lambda row: (-row[0], row[1]["id"], row[2]["id"]))
        added = 0
        for score, left, right, common, edge_type in scored[: max(1, int(limit or 90))]:
            label = ", ".join(common[:3])
            before = len(edges)
            self._graph_edge(
                edges,
                left["id"],
                right["id"],
                edge_type,
                label or ("semantica local" if edge_type == "semantic" else "relacionado"),
                min(2.6, 0.75 + score),
            )
            if len(edges) > before:
                added += 1
        return added

    def _graph_structured_memory_path(self) -> Path:
        db_path = Path(getattr(self.db, "db_path", "data/nexus.db"))
        local = db_path.parent / "structured_memory.json"
        if local.exists():
            return local
        return Path("data/structured_memory.json")

    def _load_graph_structured_memory(self) -> dict:
        path = self._graph_structured_memory_path()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _graph_markdown_files(self, limit: int = 8) -> list[Path]:
        db_path = Path(getattr(self.db, "db_path", "data/nexus.db"))
        roots = [db_path.parent, Path("data/persona"), Path("docs"), Path(".")]
        seen: set[str] = set()
        out: list[Path] = []
        blocked = {".git", ".pytest_cache", "node_modules", "venv", ".venv", "ProjetosGithub"}
        for root in roots:
            try:
                root = root.resolve()
            except Exception:
                continue
            if not root.exists():
                continue
            for path in root.rglob("*.md"):
                parts = set(path.parts)
                if blocked & parts:
                    continue
                key = str(path.resolve()).lower()
                if key in seen:
                    continue
                seen.add(key)
                out.append(path)
                if len(out) >= limit:
                    return out
        return out

    def _graph_flashcards(self, limit: int) -> list[dict]:
        try:
            with self.db._get_connection() as conn:
                conn.row_factory = __import__("sqlite3").Row
                rows = conn.execute(
                    """
                    SELECT f.id, f.note_id, f.front, f.back, f.next_review,
                           n.title AS note_title, n.subject
                    FROM flashcards f
                    LEFT JOIN study_notes n ON n.id = f.note_id
                    ORDER BY datetime(f.next_review) ASC, f.id DESC
                    LIMIT ?
                    """,
                    (max(1, int(limit or 30)),),
                ).fetchall()
                return [dict(r) for r in rows]
        except Exception:
            return []

    def build_memory_graph(
        self,
        query: str | None = None,
        limit: int = 120,
        include_markdown: bool = True,
    ) -> dict:
        lim = max(20, min(240, int(limit or 120)))
        q = str(query or "").strip()
        nodes: dict[str, dict] = {}
        edges: dict[str, dict] = {}
        self._graph_node(
            nodes,
            "nexus:core",
            "core",
            "Nexus Life OS",
            "Memoria operacional local",
            "core",
            4.0,
            "Centro do grafo: notas, flashcards, memoria, rotinas e objetivos.",
        )

        notes = self.db.list_study_notes(None)[:lim]
        for note in notes:
            note_id = int(note.get("id") or 0)
            if not note_id:
                continue
            subject = (note.get("subject") or "Geral").strip() or "Geral"
            subject_id = f"subject:{self._graph_slug(subject)}"
            node_id = f"note:{note_id}"
            self._graph_node(nodes, subject_id, "subject", subject, "Materia / area", "study", 2.0)
            self._graph_edge(edges, "nexus:core", subject_id, "contains", "area", 1.5)
            self._graph_node(
                nodes,
                node_id,
                "note",
                note.get("title") or "Nota",
                subject,
                "study",
                2.4,
                self._graph_text_summary(note.get("content"), 420),
                {"note_id": note_id, "module": "notes"},
            )
            self._graph_edge(edges, subject_id, node_id, "contains", "nota", 2.0)
            for keyword in self._graph_keywords(note.get("title"), note.get("content"), limit=4):
                tag_id = f"tag:{keyword}"
                self._graph_node(nodes, tag_id, "tag", keyword, "Conceito recorrente", "tags", 1.2)
                self._graph_edge(edges, node_id, tag_id, "mentions", "menciona", 0.8)

        for card in self._graph_flashcards(max(10, lim // 3)):
            card_id = int(card.get("id") or 0)
            if not card_id:
                continue
            node_id = f"flashcard:{card_id}"
            note_id = int(card.get("note_id") or 0)
            self._graph_node(
                nodes,
                node_id,
                "flashcard",
                card.get("front") or "Flashcard",
                card.get("subject") or "SRS",
                "srs",
                1.6,
                self._graph_text_summary(card.get("back"), 260),
                {"card_id": card_id, "note_id": note_id, "module": "study"},
            )
            self._graph_edge(edges, f"note:{note_id}" if note_id else "nexus:core", node_id, "generates", "card", 1.2)

        for habit in self.db.get_habits()[: max(6, lim // 6)]:
            hid = int(habit.get("id") or 0)
            node_id = f"habit:{hid}"
            self._graph_node(
                nodes,
                node_id,
                "habit",
                habit.get("name") or "Habito",
                f"+{int(habit.get('xp_reward') or 0)} XP",
                "routine",
                1.8,
                habit.get("description") or "",
                {"habit_id": hid, "module": "habits"},
            )
            self._graph_edge(edges, "nexus:core", node_id, "drives", "rotina", 1.0)

        for task in self.db.list_tasks(include_done=False)[: max(6, lim // 6)]:
            tid = int(task.get("id") or 0)
            node_id = f"task:{tid}"
            self._graph_node(
                nodes,
                node_id,
                "task",
                task.get("title") or "Tarefa",
                task.get("due_date") or "Sem prazo",
                "tasks",
                1.7,
                f"Recompensa: {int(task.get('points_reward') or 0)} pontos",
                {"task_id": tid, "module": "tasks"},
            )
            self._graph_edge(edges, "nexus:core", node_id, "queues", "acao", 1.0)

        for goal in self.get_goals()[: max(5, lim // 8)]:
            gid = int(goal.get("id") or 0)
            node_id = f"goal:{gid}"
            self._graph_node(
                nodes,
                node_id,
                "goal",
                goal.get("name") or "Meta",
                f"{int(goal.get('progress') or 0)}% concluido",
                "goals",
                2.0,
                f"Data alvo: {goal.get('target_date') or 'sem data'}",
                {"goal_id": gid, "module": "goals"},
            )
            self._graph_edge(edges, "nexus:core", node_id, "aims", "meta", 1.2)

        for reward in self.get_rewards()[: max(5, lim // 8)]:
            rid = int(reward.get("id") or 0)
            node_id = f"reward:{rid}"
            self._graph_node(
                nodes,
                node_id,
                "reward",
                reward.get("name") or "Recompensa",
                f"{int(reward.get('cost') or 0)} pontos",
                "rewards",
                1.4,
                reward.get("description") or "",
                {"reward_id": rid, "module": "goals"},
            )
            self._graph_edge(edges, "nexus:core", node_id, "unlocks", "loja", 0.9)

        memory = self._load_graph_structured_memory()
        for category, rows in list(memory.items())[:10]:
            if not isinstance(rows, dict):
                continue
            category_id = f"memory-category:{self._graph_slug(category)}"
            self._graph_node(nodes, category_id, "memory_category", str(category), "Memoria estruturada", "memory", 1.6)
            self._graph_edge(edges, "nexus:core", category_id, "remembers", "memoria", 1.0)
            for key, value in list(rows.items())[:12]:
                if isinstance(value, dict):
                    detail = str(value.get("value") or "")
                    updated = str(value.get("updated") or "")
                else:
                    detail = str(value)
                    updated = ""
                memory_id = f"memory:{self._graph_slug(category)}:{self._graph_slug(key)}"
                self._graph_node(
                    nodes,
                    memory_id,
                    "memory",
                    str(key).replace("_", " "),
                    updated,
                    "memory",
                    1.7,
                    self._graph_text_summary(detail, 360),
                    {"category": category, "key": key},
                )
                self._graph_edge(edges, category_id, memory_id, "stores", "fato", 1.0)

        if include_markdown:
            for path in self._graph_markdown_files(max(4, lim // 12)):
                try:
                    content = path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                rel = str(path)
                node_id = f"markdown:{self._graph_slug(rel)}"
                title = path.stem.replace("_", " ").replace("-", " ")
                first = next((line.strip("# ").strip() for line in content.splitlines() if line.strip()), "")
                self._graph_node(
                    nodes,
                    node_id,
                    "markdown",
                    title,
                    rel,
                    "markdown",
                    1.5,
                    self._graph_text_summary(first or content, 280),
                    {"path": rel},
                )
                self._graph_edge(edges, "nexus:core", node_id, "documents", "md", 0.8)

        query_terms = self._graph_query_terms(q)
        for node in nodes.values():
            search_text = self._graph_node_search_text(node)
            folded_text = self._fold_key(search_text)
            keywords = self._graph_keywords(search_text, limit=10)
            for term in query_terms:
                if term in folded_text and term not in keywords:
                    keywords.append(term)
            node["keywords"] = keywords
            node["semantic_topics"] = self._graph_semantic_topics(search_text)
            node["_semantic_vector"] = self._graph_local_embedding(search_text)
            node["relevance"] = self._graph_relevance_score(node, q, query_terms)
        smart_edges = self._graph_add_semantic_edges(nodes, edges, query_terms, max(30, lim))

        utility_types = {"core", "tag", "subject", "memory_category"}
        ranked_nodes = sorted(
            (
                node for node in nodes.values()
                if float(node.get("relevance") or 0) > 0 and node.get("type") not in utility_types
            ),
            key=lambda node: (-float(node.get("relevance") or 0), -float(node.get("weight") or 0), str(node.get("label") or "")),
        )
        ranked_matches = [self._graph_match_payload(node) for node in ranked_nodes[:12]]
        if ranked_nodes:
            ranked_ids = {node["id"] for node in ranked_nodes}
            ordered_nodes = [nodes["nexus:core"]] + ranked_nodes + [
                node for node in nodes.values()
                if node["id"] != "nexus:core" and node["id"] not in ranked_ids
            ]
        else:
            ordered_nodes = list(nodes.values())

        node_list = ordered_nodes[:lim]
        node_ids = {node["id"] for node in node_list}
        edge_list = [
            edge for edge in edges.values()
            if edge["source"] in node_ids and edge["target"] in node_ids
        ]
        smart_edges = sum(1 for edge in edge_list if edge.get("type") == "relates")
        semantic_edges = sum(1 for edge in edge_list if edge.get("type") == "semantic")
        for node in node_list:
            node.pop("_semantic_vector", None)
        type_counts: dict[str, int] = {}
        cluster_counts: dict[str, int] = {}
        for node in node_list:
            type_counts[node["type"]] = type_counts.get(node["type"], 0) + 1
            cluster_counts[node["cluster"]] = cluster_counts.get(node["cluster"], 0) + 1
        return {
            "ok": True,
            "query": q,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "nodes": node_list,
            "edges": edge_list,
            "clusters": cluster_counts,
            "ranked_matches": ranked_matches,
            "stats": {
                "nodes": len(node_list),
                "edges": len(edge_list),
                "smart_edges": smart_edges,
                "semantic_edges": semantic_edges,
                "semantic_mode": "local",
                "types": type_counts,
                "clusters": cluster_counts,
            },
        }

    def _obsidian_safe_filename(self, value: str | None, fallback: str = "Nexus Note") -> str:
        base = re.sub(r"[\\/:*?\"<>|]+", " ", str(value or fallback)).strip()
        base = re.sub(r"\s+", " ", base)[:90].strip(" .")
        return base or fallback

    def export_memory_graph_obsidian(
        self,
        folder,
        query: str | None = "",
        include_markdown: bool = True,
        limit: int = 160,
    ) -> dict:
        target = Path(folder).expanduser()
        if target.exists() and not target.is_dir():
            return {"ok": False, "count": 0, "files": [], "error": "Destino nao e uma pasta."}
        target.mkdir(parents=True, exist_ok=True)
        graph = self.build_memory_graph(query=query, limit=limit, include_markdown=include_markdown)
        utility = {"core", "tag", "subject", "memory_category"}
        export_nodes = [node for node in graph.get("nodes", []) if node.get("type") not in utility]
        filename_by_id: dict[str, str] = {}
        used: set[str] = set()
        for node in export_nodes:
            base = self._obsidian_safe_filename(node.get("label") or node.get("id"), "Nexus Note")
            name = base
            suffix = 2
            while name.lower() in used:
                name = f"{base} {suffix}"
                suffix += 1
            used.add(name.lower())
            filename_by_id[node["id"]] = name

        files: list[str] = []
        index_lines = [
            "# Nexus Memory Graph",
            "",
            f"- Query: {query or 'tudo'}",
            f"- Gerado em: {datetime.now().isoformat(timespec='seconds')}",
            f"- Nos exportados: {len(export_nodes)}",
            "",
            "## Nos",
        ]
        for node in export_nodes:
            file_stem = filename_by_id[node["id"]]
            index_lines.append(f"- [[{file_stem}]] - {node.get('type')} - {node.get('subtitle') or ''}")
        index_path = target / "Nexus Memory Graph.md"
        index_path.write_text("\n".join(index_lines).strip() + "\n", encoding="utf-8")
        files.append(str(index_path))

        edge_map: dict[str, list[dict]] = {}
        for edge in graph.get("edges", []):
            if edge.get("source") in filename_by_id and edge.get("target") in filename_by_id:
                edge_map.setdefault(edge["source"], []).append(edge)
                edge_map.setdefault(edge["target"], []).append(edge)

        for node in export_nodes:
            file_stem = filename_by_id[node["id"]]
            path = target / f"{file_stem}.md"
            source = node.get("source") if isinstance(node.get("source"), dict) else {}
            topics = ", ".join(node.get("semantic_topics") or [])
            lines = [
                "---",
                f'nexus_id: "{node.get("id")}"',
                f'type: "{node.get("type")}"',
                f'cluster: "{node.get("cluster")}"',
                f'semantic_topics: "{topics}"',
                "---",
                "",
                f"# {node.get('label') or file_stem}",
                "",
                node.get("details") or node.get("subtitle") or "Sem detalhes.",
                "",
                "## Origem",
            ]
            for key, value in source.items():
                lines.append(f"- {key}: {value}")
            lines.extend(["", "## Conexoes"])
            connections = edge_map.get(node["id"], [])
            if connections:
                for edge in connections[:24]:
                    other = edge["target"] if edge.get("source") == node["id"] else edge.get("source")
                    other_name = filename_by_id.get(other)
                    if other_name:
                        lines.append(f"- [[{other_name}]] ({edge.get('type')}: {edge.get('label')})")
            else:
                lines.append("- Sem conexoes exportadas.")
            path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
            files.append(str(path))

        return {
            "ok": True,
            "folder": str(target),
            "count": len(export_nodes),
            "files": files,
            "message": f"{len(export_nodes)} notas exportadas para Obsidian.",
        }

    def import_obsidian_markdown(
        self,
        folder,
        subject: str | None = "Obsidian",
        limit: int = 80,
    ) -> dict:
        root = Path(folder).expanduser()
        if not root.exists() or not root.is_dir():
            return {"ok": False, "count": 0, "note_ids": [], "error": "Pasta Obsidian nao encontrada."}
        note_ids: list[int] = []
        imported = 0
        for path in sorted(root.rglob("*.md"))[: max(1, min(200, int(limit or 80)))]:
            if path.name.lower() == "nexus memory graph.md":
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="ignore").strip()
            except OSError:
                continue
            if not content:
                continue
            title = path.stem
            for line in content.splitlines():
                clean = line.strip()
                if clean.startswith("# "):
                    title = clean.lstrip("#").strip() or title
                    break
            body = content + f"\n\n---\nFonte Obsidian: {path}"
            self.create_note(subject or "Obsidian", title[:180], body)
            if self._last_created_note_id:
                note_ids.append(int(self._last_created_note_id))
                imported += 1
        if imported:
            broadcast_nexus_state(self)
        return {
            "ok": True,
            "count": imported,
            "note_ids": note_ids,
            "subject": subject or "Obsidian",
            "message": f"{imported} arquivos Markdown importados para o MindPalace.",
        }

    def build_memory_graph_context(
        self,
        query: str | None,
        limit: int = 8,
        include_markdown: bool = True,
    ) -> dict:
        q = str(query or "").strip()
        match_limit = max(1, min(12, int(limit or 8)))
        graph = self.build_memory_graph(
            query=q,
            limit=max(80, match_limit * 24),
            include_markdown=include_markdown,
        )
        node_by_id = {node["id"]: node for node in graph.get("nodes", [])}
        ranked = graph.get("ranked_matches") or [
            self._graph_match_payload(node)
            for node in sorted(
                graph.get("nodes", []),
                key=lambda node: (-float(node.get("weight") or 0), str(node.get("label") or "")),
            )
            if node.get("type") != "core"
        ]
        matches: list[dict] = []
        suggested_modules: set[str] = set()
        for match in ranked[:match_limit]:
            node_id = match.get("id")
            related: list[dict] = []
            for edge in graph.get("edges", []):
                other_id = ""
                if edge.get("source") == node_id:
                    other_id = edge.get("target") or ""
                elif edge.get("target") == node_id:
                    other_id = edge.get("source") or ""
                if not other_id or other_id == "nexus:core" or other_id not in node_by_id:
                    continue
                other = node_by_id[other_id]
                related.append(
                    {
                        "id": other.get("id"),
                        "type": other.get("type"),
                        "label": other.get("label"),
                        "subtitle": other.get("subtitle"),
                        "details": other.get("details"),
                        "source": other.get("source") or {},
                        "edge_type": edge.get("type"),
                        "edge_label": edge.get("label"),
                        "weight": float(edge.get("weight") or 1),
                    }
                )
            related.sort(key=lambda item: (-float(item.get("weight") or 0), str(item.get("label") or "")))
            source = match.get("source") or {}
            if source.get("module"):
                suggested_modules.add(str(source["module"]))
            for item in related[:4]:
                module = (item.get("source") or {}).get("module")
                if module:
                    suggested_modules.add(str(module))
            enriched = dict(match)
            enriched["related"] = related[:5]
            matches.append(enriched)

        lines = [f"Contexto do grafo para '{q or 'visao geral'}':"]
        for match in matches:
            title = match.get("label") or match.get("id")
            node_type = match.get("type") or "item"
            detail = match.get("details") or match.get("subtitle") or ""
            lines.append(f"- {title} ({node_type}): {self._graph_text_summary(detail, 180)}")
            for item in match.get("related", [])[:3]:
                rel = item.get("edge_label") or item.get("edge_type") or "relacionado"
                lines.append(f"  conectado a {item.get('label')}: {rel}")

        return {
            "ok": True,
            "query": q,
            "generated_at": graph.get("generated_at"),
            "matches": matches,
            "suggested_modules": sorted(suggested_modules),
            "context_text": "\n".join(lines)[:5000],
            "graph_stats": graph.get("stats") or {},
        }

    # --- NEWS BRIEFING STUDIO ---

    def _news_sentences(self, text: str | None) -> list[str]:
        clean = re.sub(r"\s+", " ", str(text or "")).strip()
        if not clean:
            return []
        parts = re.split(r"(?<=[.!?])\s+", clean)
        return [p.strip(" .") for p in parts if p.strip(" .")]

    def _fetch_news_results(self, query: str, limit: int) -> list[dict]:
        try:
            from duckduckgo_search import DDGS
        except Exception:
            return []
        rows = []
        try:
            with DDGS() as ddgs:
                for item in ddgs.news(query, max_results=limit):
                    rows.append(item)
        except Exception as e:
            logger.warning("News search failed: %s", e)
        return rows

    def _news_history_store_path(self) -> Path:
        db_path = Path(getattr(self.db, "db_path", "data/nexus.db"))
        return db_path.parent / "nexus_news_briefings.json"

    def _load_news_history(self) -> list[dict]:
        path = self._news_history_store_path()
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        rows = raw.get("briefings") if isinstance(raw, dict) else raw
        if not isinstance(rows, list):
            return []
        return [row for row in rows if isinstance(row, dict)]

    def _save_news_history(self, rows: list[dict]) -> None:
        path = self._news_history_store_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"version": 1, "briefings": rows[:12]}
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as e:
            logger.warning("Could not save Nexus news history: %s", e)

    def _remember_news_briefing(self, briefing: dict) -> None:
        if not briefing.get("ok") or not briefing.get("items") or briefing.get("from_cache"):
            return
        query = (briefing.get("query") or "top news Brasil").strip()
        generated_at = briefing.get("generated_at") or datetime.now().isoformat(timespec="seconds")
        first_title = (briefing.get("items") or [{}])[0].get("title") or "noticias"
        record_id = f"{self._slug_theme_id(query, 'noticias')}-{self._slug_theme_id(first_title, 'briefing')}-{generated_at}"
        record = {
            "id": record_id,
            "query": query,
            "query_key": self._fold_key(query),
            "generated_at": generated_at,
            "items": briefing.get("items") or [],
            "narration": briefing.get("narration") or "",
        }
        history = [
            row
            for row in self._load_news_history()
            if row.get("id") != record_id
        ]
        history.insert(0, record)
        self._save_news_history(history)

    def _cached_news_briefing(self, query: str) -> dict | None:
        history = self._load_news_history()
        if not history:
            return None
        key = self._fold_key(query)
        for row in history:
            if row.get("query_key") == key:
                return json.loads(json.dumps(row, ensure_ascii=False))
        return json.loads(json.dumps(history[0], ensure_ascii=False))

    def list_news_briefings(self, limit: int = 8) -> list[dict]:
        try:
            lim = max(1, min(20, int(limit or 8)))
        except (TypeError, ValueError):
            lim = 8
        briefings = []
        for row in self._load_news_history()[:lim]:
            items = row.get("items") if isinstance(row.get("items"), list) else []
            first = items[0] if items and isinstance(items[0], dict) else {}
            briefings.append(
                {
                    "id": row.get("id") or "",
                    "query": row.get("query") or "",
                    "generated_at": row.get("generated_at") or "",
                    "item_count": len(items),
                    "top_title": first.get("title") or "",
                    "top_source": first.get("source") or "",
                }
            )
        return briefings

    def _news_impact_tags(self, title: str, body: str, query: str | None = None) -> list[str]:
        folded = self._fold_key(" ".join([query or "", title or "", body or ""]))
        tags: list[str] = []
        keyword_map = {
            "educacao": ["educacao", "ensino", "escola", "professor", "estudo", "enem"],
            "tecnologia": ["tecnologia", "ia", "digital", "plataforma", "software", "neural"],
            "economia": ["economia", "mercado", "consumo", "juros", "inflacao", "indicador"],
            "saude": ["saude", "hospital", "medico", "triagem", "paciente"],
            "politica": ["politica", "governo", "congresso", "eleicao", "regra"],
            "privacidade": ["privacidade", "dados", "seguranca"],
        }
        for tag, words in keyword_map.items():
            if any(word in folded for word in words):
                tags.append(tag)
        qtag = self._slug_theme_id(query or "", fallback="")
        if qtag and qtag not in tags:
            tags.insert(0, qtag)
        return tags[:5] or ["atualidades"]

    def _news_timeline(self, title: str, source: str, sentences: list[str]) -> list[dict]:
        context = sentences[0] if sentences else f"A noticia foi publicada por {source}."
        next_step = (
            sentences[2]
            if len(sentences) > 2
            else "Acompanhar a fonte original e observar os proximos desdobramentos."
        )
        return [
            {"label": "Contexto", "text": context},
            {"label": "Agora", "text": title},
            {"label": "Proximo passo", "text": next_step},
        ]

    def _news_actions(self) -> list[dict]:
        return [
            {"id": "save_note", "label": "Salvar no MindPalace", "action": "news_save_note"},
            {"id": "flashcards", "label": "Criar flashcards", "action": "news_flashcards_generate"},
            {"id": "follow_up", "label": "Criar tarefa", "action": "news_followup_task"},
            {"id": "deep_dive", "label": "Fale mais", "action": "expand_spotlight"},
        ]

    def _build_news_deck(self, query: str, items: list[dict]) -> dict:
        segments = []
        for idx, item in enumerate(items, 1):
            item_index = int(item.get("index") or idx)
            cue = f"[Noticia {item_index}]"
            title = str(item.get("title") or "Noticia").strip()
            source = str(item.get("source") or "Fonte desconhecida").strip()
            why = str(item.get("why_it_matters") or item.get("summary") or "").strip()
            summary = str(item.get("summary") or "").strip()
            script = (
                f"{cue} {title}. "
                f"Fonte: {source}. "
                f"{summary} "
                f"Por que importa: {why}"
            ).strip()
            word_count = max(1, len(script.split()))
            duration = max(10, min(45, int(round(word_count / 2.7))))
            segments.append(
                {
                    "cue": cue,
                    "item_index": item_index,
                    "title": title,
                    "source": source,
                    "script": script,
                    "duration_sec": duration,
                }
            )
        script = " ".join(seg["script"] for seg in segments).strip()
        first = items[0] if items else {}
        actions = first.get("actions") if isinstance(first.get("actions"), list) else []
        primary_action = next(
            (
                str(action.get("label") or "").strip()
                for action in actions
                if isinstance(action, dict) and action.get("id") == "save_note"
            ),
            "Salvar no MindPalace",
        )
        video = first.get("video") if isinstance(first.get("video"), dict) else {}
        sources = {
            str(item.get("source") or "").strip().lower()
            for item in items
            if str(item.get("source") or "").strip()
        }
        return {
            "mode": "spotlight",
            "spotlight_index": 1 if items else 0,
            "item_count": len(items),
            "source_count": len(sources),
            "estimated_duration_sec": sum(int(seg.get("duration_sec") or 0) for seg in segments),
            "segments": segments,
            "spotlight": {
                "item_index": int(first.get("index") or 0) if first else 0,
                "title": first.get("title") or "",
                "source": first.get("source") or "",
                "published_at": first.get("published_at") or "",
                "summary": first.get("summary") or "",
                "why_it_matters": first.get("why_it_matters") or "",
                "primary_action": primary_action,
                "source_url": first.get("url") or "",
                "video_url": video.get("url") or "",
            },
            "briefing_script": script,
            "next_action": "Escolha uma noticia para aprofundar, salvar ou acompanhar.",
            "query": query,
        }

    def _normalize_news_item(self, idx: int, raw: dict, query: str | None = None) -> dict:
        title = str(raw.get("title") or raw.get("headline") or "Sem titulo").strip()
        source = str(raw.get("source") or raw.get("publisher") or "Fonte desconhecida").strip()
        published = str(raw.get("date") or raw.get("published_at") or raw.get("published") or "").strip()
        url = str(raw.get("url") or raw.get("link") or raw.get("href") or "").strip()
        body = str(raw.get("body") or raw.get("snippet") or raw.get("description") or "").strip()
        sentences = self._news_sentences(body)
        summary = ". ".join(sentences[:2]).strip()
        if summary and not summary.endswith("."):
            summary += "."
        if not summary:
            summary = f"{title}. Fonte: {source}."
        past = sentences[0] if sentences else f"Fonte: {source}"
        future = sentences[1] if len(sentences) > 1 else "Proximo passo: abrir a fonte e acompanhar os desdobramentos."
        detail_lines = sentences[:4] or [summary.strip(" .")]
        deep_dive = (
            "Pontos principais: "
            + " ".join(line.strip(" .") + "." for line in detail_lines if line)
            + f" Fonte original: {source}."
        ).strip()
        why = (
            "Importa porque "
            + (sentences[1] if len(sentences) > 1 else summary).strip(" .")
            + "."
        )
        video_query = f"{title} {source} video"
        return {
            "index": idx,
            "title": title,
            "source": source,
            "published_at": published,
            "url": url,
            "body": body,
            "summary": summary,
            "deep_dive": deep_dive,
            "why_it_matters": why,
            "impact_tags": self._news_impact_tags(title, body, query),
            "timeline": self._news_timeline(title, source, sentences),
            "actions": self._news_actions(),
            "video": {
                "provider": "youtube-search",
                "url": "https://www.youtube.com/results?search_query=" + quote_plus(video_query),
                "query": video_query,
            },
            "transcript": {
                "past": past,
                "present": title,
                "future": future,
            },
        }

    def _coerce_news_payload(self, value) -> dict:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return {}
        return value if isinstance(value, dict) else {}

    def _select_news_item(self, item=None, briefing=None, item_index: int = 1) -> dict:
        item_data = self._coerce_news_payload(item)
        if item_data:
            return item_data
        briefing_data = self._coerce_news_payload(briefing)
        items = briefing_data.get("items") if isinstance(briefing_data.get("items"), list) else []
        try:
            idx = max(0, int(item_index or 1) - 1)
        except (TypeError, ValueError):
            idx = 0
        if 0 <= idx < len(items) and isinstance(items[idx], dict):
            return items[idx]
        return {}

    def save_news_item_to_note(
        self,
        item=None,
        briefing=None,
        item_index: int = 1,
        subject: str | None = "Noticias",
    ) -> dict:
        news_item = self._select_news_item(item=item, briefing=briefing, item_index=item_index)
        if not news_item:
            return {"ok": False, "note_id": None, "error": "Noticia nao encontrada."}
        title = str(news_item.get("title") or "Noticia").strip()[:180]
        source = str(news_item.get("source") or "Fonte desconhecida").strip()
        url = str(news_item.get("url") or "").strip()
        video = news_item.get("video") if isinstance(news_item.get("video"), dict) else {}
        video_url = str(video.get("url") or "").strip()
        video_query = str(video.get("query") or title).strip()
        summary = str(news_item.get("summary") or "").strip()
        deep_dive = str(news_item.get("deep_dive") or news_item.get("body") or "").strip()
        content_parts = [
            f"# {title}",
            "## Resumo",
            summary or f"Fonte: {source}.",
            "## Por que importa",
            str(news_item.get("why_it_matters") or "A noticia pode impactar decisoes e estudos futuros.").strip(),
            "## Detalhes para revisar",
            deep_dive or "Abra a fonte original para aprofundar.",
            "## Linha do tempo",
            "\n".join(
                f"- **{row.get('label', 'Etapa')}:** {row.get('text', '')}"
                for row in (news_item.get("timeline") if isinstance(news_item.get("timeline"), list) else [])
                if isinstance(row, dict)
            )
            or "- Contexto indisponivel.",
            "## Fonte",
            f"- Veiculo: {source}",
        ]
        if url:
            content_parts.append(f"- Link: {url}")
        if video_url:
            content_parts.append(f"- Video sugerido: {video_url}")
        if video_query:
            content_parts.append(f"- Consulta de video: {video_query}")
        media = []
        if url:
            media.append({"type": "source", "url": url, "caption": source, "alt": title})
        if video_url:
            media.append({"type": "video_search", "url": video_url, "caption": video_query, "alt": title})
        note_subject = (subject or "Noticias").strip() or "Noticias"
        self.create_note(note_subject, title, "\n\n".join(content_parts), media=media)
        note_id = self._last_created_note_id or -1
        ok = note_id > 0
        if ok:
            msg = f"Noticia '{title}' salva no MindPalace."
            self._open_desktop_receipt(
                "notes",
                {
                    "highlight_id": note_id,
                    "animate": "news_save_note",
                    "toast": msg,
                    "receipt": {
                        "kind": "note",
                        "action": "news_save_note",
                        "id": note_id,
                        "title": title,
                        "source": source,
                    },
                },
            )
            return {
                "ok": True,
                "note_id": note_id,
                "title": title,
                "subject": note_subject,
                "message": msg,
            }
        return {"ok": False, "note_id": None, "error": "Erro ao salvar noticia no MindPalace."}

    def create_news_followup_task(
        self,
        item=None,
        briefing=None,
        item_index: int = 1,
        due_date: str | None = None,
    ) -> dict:
        news_item = self._select_news_item(item=item, briefing=briefing, item_index=item_index)
        if not news_item:
            return {"ok": False, "task_id": None, "error": "Noticia nao encontrada."}
        title = str(news_item.get("title") or "noticia").strip()
        source = str(news_item.get("source") or "fonte").strip()
        url = str(news_item.get("url") or "").strip()
        due = due_date or (date.today() + timedelta(days=1)).isoformat()
        task_title = f"Acompanhar noticia: {title}"
        if url:
            task_title += f" | {url}"
        task_id = self.db.add_task(task_title[:220], due, 15)
        broadcast_nexus_state(self)
        msg = f"Tarefa de acompanhamento criada para '{title}'."
        self._open_desktop_receipt(
            "tasks",
            {
                "highlight_id": task_id,
                "animate": "news_followup_task",
                "toast": msg,
                "receipt": {
                    "kind": "task",
                    "action": "news_followup_task",
                    "id": task_id,
                    "title": title,
                    "source": source,
                },
            },
        )
        return {
            "ok": True,
            "task_id": int(task_id),
            "title": task_title[:220],
            "due_date": due,
            "message": msg,
        }

    def create_news_flashcards(
        self,
        item=None,
        briefing=None,
        item_index: int = 1,
        subject: str | None = "Noticias",
        max_cards: int = 4,
    ) -> dict:
        news_item = self._select_news_item(item=item, briefing=briefing, item_index=item_index)
        if not news_item:
            return {"ok": False, "note_id": None, "created": 0, "cards": [], "error": "Noticia nao encontrada."}

        saved = self.save_news_item_to_note(
            item=news_item,
            subject=(subject or "Noticias").strip() or "Noticias",
        )
        if not saved.get("ok"):
            return {
                "ok": False,
                "note_id": saved.get("note_id"),
                "created": 0,
                "cards": [],
                "error": saved.get("error") or "Nao consegui salvar a noticia antes dos flashcards.",
            }

        limit = max(1, min(12, int(max_cards or 4)))
        generated = self.generate_flashcards_from_note(int(saved["note_id"]), limit)
        created = int(generated.get("created") or 0)
        msg = f"{created} flashcards criados a partir da noticia '{saved.get('title')}'."
        self._open_desktop_receipt(
            "study",
            {
                "highlight_id": saved["note_id"],
                "animate": "news_flashcards_generate",
                "toast": msg,
                "note_id": int(saved["note_id"]),
                "created": created,
                "receipt": {
                    "kind": "study",
                    "action": "news_flashcards_generate",
                    "title": saved.get("title"),
                    "note_id": int(saved["note_id"]),
                    "created": created,
                },
            },
        )
        return {
            "ok": True,
            "note_id": int(saved["note_id"]),
            "title": saved.get("title"),
            "subject": saved.get("subject"),
            "created": created,
            "cards": generated.get("cards") or [],
            "message": msg,
        }

    def build_news_briefing(
        self,
        query: str | None = "",
        limit: int = 3,
        results: list[dict] | str | None = None,
        open_window: bool = True,
    ) -> dict:
        q = (query or "").strip() or "top news Brasil"
        try:
            lim = max(1, min(5, int(limit or 3)))
        except (TypeError, ValueError):
            lim = 3
        if isinstance(results, str):
            try:
                results = json.loads(results)
            except json.JSONDecodeError:
                results = []
        rows = results if isinstance(results, list) else self._fetch_news_results(q, lim)
        items = [
            self._normalize_news_item(idx, raw, q)
            for idx, raw in enumerate(rows[:lim], 1)
            if isinstance(raw, dict)
        ]
        generated_at = datetime.now().isoformat(timespec="seconds")
        if not items:
            cached = self._cached_news_briefing(q)
            if cached:
                items = cached.get("items") if isinstance(cached.get("items"), list) else []
                deck = self._build_news_deck(cached.get("query") or q, items)
                narration = deck["briefing_script"] or cached.get("narration") or ""
                briefing = {
                    "ok": bool(items),
                    "query": cached.get("query") or q,
                    "generated_at": cached.get("generated_at") or generated_at,
                    "cached_generated_at": cached.get("generated_at") or "",
                    "from_cache": True,
                    "stale": True,
                    "items": items,
                    "deck": deck,
                    "narration": narration,
                    "error": "" if items else "Nenhuma noticia encontrada agora.",
                }
            else:
                briefing = {
                    "ok": False,
                    "query": q,
                    "generated_at": generated_at,
                    "from_cache": False,
                    "stale": False,
                    "items": [],
                    "deck": self._build_news_deck(q, []),
                    "narration": "",
                    "error": "Nenhuma noticia encontrada agora.",
                }
        else:
            deck = self._build_news_deck(q, items)
            narration = deck["briefing_script"]
            briefing = {
                "ok": True,
                "query": q,
                "generated_at": generated_at,
                "from_cache": False,
                "stale": False,
                "items": items,
                "deck": deck,
                "narration": narration,
                "error": "",
            }
            self._remember_news_briefing(briefing)
        if open_window:
            self._open_desktop_receipt(
                "news",
                {
                    "animate": "news_briefing",
                    "toast": "Briefing de noticias atualizado." if items else briefing["error"],
                    "briefing": briefing,
                    "receipt": {
                        "kind": "news",
                        "action": "news_briefing",
                        "query": q,
                        "count": len(items),
                    },
                },
            )
        return briefing

    def change_aura(self, color_name):
        """Muda a cor do HUD (Aura)."""
        mapping = {
            "ciano": "cyan",
            "vermelho": "red",
            "roxo": "purple",
            "esmeralda": "emerald",
            "verde": "emerald",
            "stark": "red"
        }
        theme = mapping.get(color_name.lower(), "cyan")
        payload = {
            "type": "theme_change",
            "theme": theme
        }
        from src.utils.nexus_notifier import notify_nexus_update
        notify_nexus_update(payload)
        log_nexus_event(f"AURA: Mudança para {theme.upper()}")
        return f"Aura alterada para {color_name}, Sir. Sistemas recalibrados."
    def change_hud_tab(self, tab_name):
        """Sincroniza aba (HUD web opcional) e abre módulo desktop correspondente."""
        try:
            from src.ui.nexus_signals import enqueue_nexus_desktop_open

            mp = {
                "dashboard": "overview",
                "notes": "notes",
                "memory_graph": "memory_graph",
                "grafo": "memory_graph",
                "grafo neural": "memory_graph",
                "memoria": "memory_graph",
                "rede neural": "memory_graph",
                "board": "tasks",
                "finance": "finance",
                "study": "study",
                "progress": "progress",
                "goals": "goals",
                "rewards": "goals",
                "quiz": "quiz",
                "news": "news",
                "noticias": "news",
                "ops": "ops",
                "business": "ops",
                "negocios": "ops",
                "operacoes": "ops",
            }
            enqueue_nexus_desktop_open(mp.get(str(tab_name).lower(), "overview"), {})
        except Exception:
            pass
        payload = {
            "type": "tab_change",
            "tab": tab_name,
        }
        from src.utils.nexus_notifier import notify_nexus_update

        notify_nexus_update(payload)
        log_nexus_event(f"NAV: Alternado para aba {str(tab_name).upper()}")
        return True

    def open_nexus_ui(self, tab: str | None = None):
        """Abre janela Nexus no desktop (pywebview); fallback para HUD web se necessário."""
        raw = (tab or "dashboard").strip().lower()
        mp = {
            "dashboard": "overview",
            "overview": "overview",
            "home": "overview",
            "inicio": "overview",
            "início": "overview",
            "habits": "habits",
            "habitos": "habits",
            "hábitos": "habits",
            "notes": "notes",
            "note": "notes",
            "notas": "notes",
            "mindpalace": "notes",
            "memory_graph": "memory_graph",
            "memory graph": "memory_graph",
            "grafo": "memory_graph",
            "grafo neural": "memory_graph",
            "memoria": "memory_graph",
            "memorias": "memory_graph",
            "rede neural": "memory_graph",
            "neural": "memory_graph",
            "board": "tasks",
            "tasks": "tasks",
            "tarefas": "tasks",
            "finance": "finance",
            "financas": "finance",
            "finanças": "finance",
            "study": "study",
            "srs": "study",
            "flashcards": "study",
            "progress": "progress",
            "progresso": "progress",
            "goals": "goals",
            "metas": "goals",
            "rewards": "goals",
            "loja": "goals",
            "recompensas": "goals",
            "quiz": "quiz",
            "simulado": "quiz",
            "simulados": "quiz",
            "news": "news",
            "noticias": "news",
            "notÃ­cias": "news",
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
        mod = mp.get(raw, "overview")
        try:
            from src.ui.nexus_signals import enqueue_nexus_desktop_open

            enqueue_nexus_desktop_open(
                mod,
                self._decorate_nexus_payload(
                    {"animate": "open_module", "source": "open_ui", "tab": raw}
                ),
            )
            log_nexus_event(f"SYSTEM: Janela Nexus desktop ({mod}).")
            return f"Abrindo Nexus ({mod}), Sir."
        except Exception as e:
            logger.warning("Nexus desktop indisponível: %s", e)
        import webbrowser

        webbrowser.open("http://localhost:5123/nexus/")
        log_nexus_event("SYSTEM: Interface Nexus (navegador) como fallback.")
        return "Abrindo a interface Nexus no navegador, Sir."

    def get_finance_snapshot(self, year: int | None = None, month: int | None = None) -> dict:
        today = date.today()
        y = year if year is not None else today.year
        m = month if month is not None else today.month
        monthly = self.db.finance_monthly_totals(y, m)
        from calendar import monthrange

        last = monthrange(y, m)[1]
        start = f"{y:04d}-{m:02d}-01"
        end = f"{y:04d}-{m:02d}-{last:02d}"
        rows = self.db.list_finance_transactions(start, end)
        daily = {
            f"{y:04d}-{m:02d}-{day:02d}": {"date": f"{y:04d}-{m:02d}-{day:02d}", "income": 0.0, "expense": 0.0, "net": 0.0}
            for day in range(1, last + 1)
        }
        categories: dict[str, float] = {}
        for tx in rows:
            day_key = str(tx.get("occurred_at") or "")[:10]
            if day_key in daily:
                amount = float(tx.get("amount") or 0)
                if tx.get("type") == "income":
                    daily[day_key]["income"] += amount
                else:
                    daily[day_key]["expense"] += amount
                    cat = (tx.get("category") or "Geral").strip() or "Geral"
                    categories[cat] = categories.get(cat, 0.0) + amount
                daily[day_key]["net"] = daily[day_key]["income"] - daily[day_key]["expense"]
        daily_series = list(daily.values())
        category_breakdown = [
            {"category": cat, "expense": total}
            for cat, total in sorted(categories.items(), key=lambda item: item[1], reverse=True)
        ]
        with self.db._get_connection() as conn:
            drow = conn.execute(
                "SELECT COALESCE(SUM(amount),0) FROM finance_transactions WHERE is_debt = 1"
            ).fetchone()
            total_debts = float(drow[0] or 0)
        income = float(monthly.get("income") or 0)
        expense = float(monthly.get("expense") or 0)
        debt_payments = float(monthly.get("debt_payments") or 0)
        net = float(monthly.get("net") or 0)
        finance_insights = {
            "cash_after_debt": income - debt_payments,
            "non_debt_expense": max(0.0, expense - debt_payments),
            "debt_ratio_pct": round((debt_payments / income) * 100) if income > 0 else 0,
            "expense_ratio_pct": round((expense / income) * 100) if income > 0 else 0,
            "free_after_all_expenses": net,
        }
        return {
            "monthly": monthly,
            "transactions": rows,
            "daily_series": daily_series,
            "category_breakdown": category_breakdown,
            "finance_insights": finance_insights,
            "total_marked_debt": total_debts,
            "global_streak": self.db.compute_global_streak(),
        }

    # --- BUSINESS / OPS DASHBOARD ---

    def _ops_store_path(self) -> Path:
        db_path = Path(getattr(self.db, "db_path", "data/nexus.db"))
        return db_path.parent / "nexus_ops_dashboard.json"

    def _ops_metric_key(self, value: str | None) -> str:
        folded = self._fold_key(value)
        slug = re.sub(r"[^a-z0-9]+", "_", folded).strip("_")
        return (slug or "metric")[:64]

    def _parse_ops_number(self, value) -> float:
        if value in (None, ""):
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        raw = str(value).strip().replace("R$", "").replace("%", "")
        raw = re.sub(r"[^0-9,.\-]", "", raw)
        if "," in raw and raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", ".")
        return float(raw or 0)

    def _ops_metric_sort_key(self, metric: dict) -> tuple[int, str]:
        order = {
            "mrr": 0,
            "revenue": 1,
            "downloads": 2,
            "roas": 3,
            "refunds": 4,
            "churn": 5,
        }
        return (order.get(metric.get("key"), 50), str(metric.get("label") or metric.get("key") or ""))

    def _ops_format_value(self, value: float, unit: str | None) -> str:
        unit_key = (unit or "").strip().lower()
        if unit_key in ("brl", "r$", "real", "reais"):
            return "R$ " + f"{float(value):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
        if unit_key in ("percent", "pct", "%"):
            return f"{float(value):.1f}%".replace(".", ",")
        if unit_key in ("ratio", "roas", "x"):
            return f"{float(value):.2f}x".replace(".", ",")
        if abs(float(value) - round(float(value))) < 0.0001:
            return str(int(round(float(value))))
        return f"{float(value):.2f}".replace(".", ",")

    def _normalize_ops_metric(self, metric: dict) -> dict:
        key = self._ops_metric_key(str(metric.get("key") or metric.get("label") or "metric"))
        value = self._parse_ops_number(metric.get("value"))
        target_raw = metric.get("target")
        target = self._parse_ops_number(target_raw) if target_raw not in (None, "") else None
        label = str(metric.get("label") or key.replace("_", " ").title()).strip()[:80]
        unit = str(metric.get("unit") or "").strip()[:24]
        trend = str(metric.get("trend") or "flat").strip().lower()[:24]
        period = str(metric.get("period") or "atual").strip()[:48]
        notes = str(metric.get("notes") or metric.get("note") or "").strip()[:240]
        lower_is_better = key in {"refunds", "reembolsos", "churn", "cac", "bugs", "crashes"} or (
            trend == "down" and key not in {"downloads"}
        )
        target_hit = False
        progress = 0
        gap = 0.0
        if target is not None:
            if lower_is_better:
                target_hit = value <= target
                if target <= 0:
                    progress = 100 if value <= 0 else 0
                    gap = max(0.0, value - target)
                else:
                    progress = round(max(0.0, min(100.0, (1 - max(0.0, value - target) / target) * 100)))
                    gap = max(0.0, value - target)
            else:
                target_hit = value >= target
                progress = round(max(0.0, min(160.0, (value / target) * 100))) if target > 0 else 0
                gap = max(0.0, target - value)
        return {
            "key": key,
            "label": label,
            "value": value,
            "value_label": self._ops_format_value(value, unit),
            "unit": unit,
            "target": target,
            "target_label": self._ops_format_value(target, unit) if target is not None else "",
            "target_hit": target_hit,
            "lower_is_better": lower_is_better,
            "progress": progress,
            "gap": gap,
            "gap_label": self._ops_format_value(gap, unit),
            "trend": trend if trend in {"up", "down", "flat"} else "flat",
            "period": period,
            "notes": notes,
            "updated_at": str(metric.get("updated_at") or datetime.now().isoformat(timespec="seconds")),
        }

    def _load_ops_store(self) -> dict:
        path = self._ops_store_path()
        raw = {}
        if path.is_file():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                raw = {}
        metrics = {}
        for key, metric in dict(raw.get("metrics") or {}).items():
            if isinstance(metric, dict):
                normalized = self._normalize_ops_metric({**metric, "key": key})
                metrics[normalized["key"]] = normalized
        events = [e for e in list(raw.get("events") or []) if isinstance(e, dict)][-80:]
        return {"version": 1, "metrics": metrics, "events": events}

    def _save_ops_store(self, store: dict) -> None:
        path = self._ops_store_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "metrics": {
                key: metric
                for key, metric in sorted(dict(store.get("metrics") or {}).items())
            },
            "events": list(store.get("events") or [])[-80:],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _default_ops_metrics(self) -> list[dict]:
        return [
            self._normalize_ops_metric({"key": "mrr", "label": "MRR", "value": 0, "unit": "BRL", "target": 0, "period": "mes"}),
            self._normalize_ops_metric({"key": "downloads", "label": "Downloads", "value": 0, "unit": "count", "target": 0, "period": "7 dias"}),
            self._normalize_ops_metric({"key": "roas", "label": "ROAS anuncios", "value": 0, "unit": "ratio", "target": 1.2, "period": "7 dias"}),
            self._normalize_ops_metric({"key": "refunds", "label": "Reembolsos", "value": 0, "unit": "count", "target": 0, "trend": "down", "period": "7 dias"}),
        ]

    def _build_ops_recommendations(self, metrics: list[dict]) -> list[dict]:
        by_key = {m["key"]: m for m in metrics}
        recs: list[dict] = []
        mrr = by_key.get("mrr") or by_key.get("revenue")
        if mrr:
            if mrr.get("target_hit"):
                recs.append(
                    {
                        "priority": "alta",
                        "title": "Meta de receita batida",
                        "action": "Aumentar a proxima meta e proteger retencao antes de escalar mais aquisicao.",
                        "reason": f"{mrr['label']} esta em {mrr['value_label']} contra alvo de {mrr.get('target_label') or 'sem alvo'}.",
                    }
                )
            elif mrr.get("target") is not None:
                recs.append(
                    {
                        "priority": "alta",
                        "title": "Receita abaixo do alvo",
                        "action": f"Priorizar ofertas e canais que cubram {mrr['gap_label']} restantes.",
                        "reason": f"{mrr['label']} esta em {mrr['progress']}% da meta.",
                    }
                )
        roas = by_key.get("roas")
        if roas:
            if roas.get("value", 0) >= max(1.2, float(roas.get("target") or 1.2)):
                recs.append(
                    {
                        "priority": "media",
                        "title": "Anuncios com retorno positivo",
                        "action": "Dobrar ou aumentar gradualmente o budget do criativo vencedor e monitorar payback.",
                        "reason": f"ROAS atual em {roas['value_label']}.",
                    }
                )
            elif roas.get("value", 0) > 0:
                recs.append(
                    {
                        "priority": "media",
                        "title": "ROAS precisa de ajuste",
                        "action": "Pausar variacoes fracas e testar novo angulo de criativo antes de subir budget.",
                        "reason": f"ROAS atual em {roas['value_label']}.",
                    }
                )
        downloads = by_key.get("downloads")
        if downloads and downloads.get("value", 0) > 0:
            recs.append(
                {
                    "priority": "media",
                    "title": "Aquisicao em movimento",
                    "action": "Transformar o canal vencedor em checklist semanal de criativos e landing page.",
                    "reason": f"{downloads['value_label']} downloads no periodo {downloads.get('period') or 'atual'}.",
                }
            )
        refunds = by_key.get("refunds") or by_key.get("reembolsos")
        if refunds and refunds.get("target_hit"):
            recs.append(
                {
                    "priority": "baixa",
                    "title": "Qualidade operacional estavel",
                    "action": "Manter monitoramento de suporte e coletar depoimentos enquanto reembolsos estao zerados.",
                    "reason": f"Reembolsos em {refunds['value_label']}.",
                }
            )
        for metric in metrics:
            if len(recs) >= 6:
                break
            if metric.get("target") is not None and not metric.get("target_hit") and metric["key"] not in {"mrr", "revenue", "roas"}:
                recs.append(
                    {
                        "priority": "media",
                        "title": f"Ajustar {metric['label']}",
                        "action": f"Criar uma tarefa de acompanhamento para fechar gap de {metric['gap_label']}.",
                        "reason": f"{metric['label']} esta em {metric['progress']}% da meta.",
                    }
                )
        if not recs:
            recs.append(
                {
                    "priority": "baixa",
                    "title": "Sem dados suficientes",
                    "action": "Registrar MRR, downloads, ROAS e reembolsos para o Jarvis montar uma leitura executiva.",
                    "reason": "O painel Ops ainda esta vazio.",
                }
            )
        return recs[:6]

    def build_ops_dashboard(self, open_window: bool = True) -> dict:
        store = self._load_ops_store()
        metrics = list(store["metrics"].values()) or self._default_ops_metrics()
        metrics.sort(key=self._ops_metric_sort_key)
        targets = [m for m in metrics if m.get("target") is not None]
        targets_hit = sum(1 for m in targets if m.get("target_hit"))
        avg_progress = round(sum(float(m.get("progress") or 0) for m in targets) / len(targets)) if targets else 0
        focus_metric = next((m for m in metrics if m["key"] == "mrr"), metrics[0] if metrics else {})
        recommendations = self._build_ops_recommendations(metrics)
        metric_line = ", ".join(f"{m['label']}: {m['value_label']}" for m in metrics[:4])
        narrative = (
            f"Status operacional: {metric_line}. "
            f"{targets_hit}/{len(targets)} metas estao no alvo. "
            f"Minha recomendacao principal: {recommendations[0]['action']}"
        )
        dashboard = {
            "ok": True,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "metrics": metrics,
            "focus_metric": focus_metric,
            "recommendations": recommendations,
            "narrative": narrative,
            "events": list(store.get("events") or [])[-8:],
            "stats": {
                "metric_count": len(metrics),
                "targets": len(targets),
                "targets_hit": targets_hit,
                "avg_progress": avg_progress,
            },
        }
        if open_window:
            self._open_desktop_receipt(
                "ops",
                {
                    "animate": "ops_dashboard",
                    "toast": "Painel Business/Ops atualizado.",
                    "dashboard": dashboard,
                },
            )
        return dashboard

    def set_ops_metric(
        self,
        key: str | None,
        value,
        label: str | None = None,
        unit: str | None = None,
        target=None,
        trend: str | None = None,
        period: str | None = None,
        notes: str | None = None,
    ) -> dict:
        store = self._load_ops_store()
        metric = self._normalize_ops_metric(
            {
                "key": key or label or "metric",
                "label": label,
                "value": value,
                "unit": unit,
                "target": target,
                "trend": trend,
                "period": period,
                "notes": notes,
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
        store["metrics"][metric["key"]] = metric
        store.setdefault("events", []).append(
            {
                "type": "metric_set",
                "key": metric["key"],
                "label": metric["label"],
                "value_label": metric["value_label"],
                "created_at": metric["updated_at"],
            }
        )
        self._save_ops_store(store)
        log_nexus_event(f"OPS: {metric['label']} = {metric['value_label']}")
        return {
            "ok": True,
            "metric": metric,
            "message": f"Metrica {metric['label']} atualizada, Sir.",
        }

    def review_flashcard_sm2(self, card_id: int, quality: int) -> str:
        """quality 0-5 (SM-2 simplificado)."""
        with self.db._get_connection() as conn:
            conn.row_factory = __import__("sqlite3").Row
            row = conn.execute("SELECT * FROM flashcards WHERE id = ?", (card_id,)).fetchone()
            if not row:
                return "Flashcard nao encontrado."
            r = dict(row)
        q = max(0, min(5, int(quality)))
        ef = float(r.get("ease_factor") or 2.5)
        reps = int(r.get("repetitions") or 0)
        interval = int(r.get("interval") or 0)
        if q < 3:
            reps = 0
            interval = 0
        else:
            if reps == 0:
                interval = 1
            elif reps == 1:
                interval = 6
            else:
                interval = max(1, round(interval * ef))
            reps += 1
        ef = max(1.3, ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)))
        next_d = (date.today() + timedelta(days=max(1, interval))).isoformat() + "T09:00:00"
        self.db.update_flashcard_srs(card_id, ef, interval, reps, next_d)
        broadcast_nexus_state(self)
        return f"Revisao gravada. Proxima em {interval} dia(s), Sir."

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

    def handle_structured_command(self, data: dict) -> str:
        act = (data.get("action") or "").strip().lower()
        try:
            if act == "nexus_batch":
                try:
                    hold_ms = int(data.get("hold_ms") or 1400)
                except (TypeError, ValueError):
                    hold_ms = 1400
                return self.handle_nexus_batch(data.get("steps"), hold_ms=hold_ms)
            if act == "finance_add":
                t = (data.get("type") or "expense").lower()
                raw_amt = data.get("amount")
                if isinstance(raw_amt, str):
                    amount = float(raw_amt.replace(",", ".").strip() or 0)
                else:
                    amount = float(raw_amt or 0)
                cat = (data.get("category") or "Geral").strip()
                desc = (data.get("description") or "").strip() or "Via nexus_command"
                od = self._normalize_date_alias(data.get("occurred_at"))
                notes = (data.get("notes") or "").strip() or None
                is_debt = int(data.get("is_debt") or 0)
                if t == "income":
                    msg = self.add_income(amount, cat, desc, occurred_at=od, notes=notes)
                else:
                    msg = self.add_expense(
                        amount, cat, desc, necessity=int(data.get("necessity") or 5),
                        occurred_at=od, notes=notes, is_debt=is_debt,
                    )
                self._open_desktop_receipt(
                    "finance",
                    {
                        "highlight_id": self._last_created_finance_id,
                        "animate": "finance_add",
                        "toast": (msg or "")[:120],
                        "receipt": {
                            "kind": "finance",
                            "action": "finance_add",
                            "id": self._last_created_finance_id,
                            "type": t,
                            "amount": amount,
                            "category": cat,
                            "description": desc,
                            "occurred_at": od or date.today().isoformat(),
                            "notes": notes,
                            "is_debt": is_debt,
                        },
                    },
                )
                return msg
            if act == "finance_list":
                od = data.get("date_from")
                do = data.get("date_to")
                rows = self.db.list_finance_transactions(od, do)
                return json.dumps(rows, ensure_ascii=False)[:8000]
            if act == "finance_update":
                has_id = bool(data.get("transaction_id"))
                target_amount = self._parse_finance_amount(data.get("target_amount") or data.get("match_amount"))
                new_amount = data.get("new_amount")
                if new_amount in (None, "") and has_id:
                    new_amount = data.get("amount")
                new_notes = data.get("new_notes") if "new_notes" in data else (data.get("notes") if has_id and "notes" in data else None)
                new_is_debt = data.get("new_is_debt") if "new_is_debt" in data else (data.get("is_debt") if has_id and "is_debt" in data else None)
                new_necessity = data.get("new_necessity") if "new_necessity" in data else (data.get("necessity") if has_id and "necessity" in data else None)
                result = self.update_finance_transaction(
                    transaction_id=int(data["transaction_id"]) if has_id else None,
                    target_description=(
                        data.get("target_description")
                        or data.get("match_description")
                        or (None if has_id else data.get("description") or data.get("text"))
                    ),
                    target_category=(
                        data.get("target_category")
                        or data.get("match_category")
                        or (None if has_id else data.get("category"))
                    ),
                    target_type=data.get("target_type") or data.get("match_type") or (None if has_id else data.get("type")),
                    target_occurred_at=(
                        data.get("target_occurred_at")
                        or data.get("target_date")
                        or data.get("match_date")
                        or (None if has_id else data.get("occurred_at") or data.get("date"))
                    ),
                    target_amount=target_amount,
                    tx_type=data.get("new_type") or (data.get("type") if has_id else None),
                    amount=new_amount,
                    category=data.get("new_category") or (data.get("category") if has_id else None),
                    description=data.get("new_description") or (data.get("description") if has_id else None),
                    occurred_at=data.get("new_occurred_at") or data.get("new_date") or (data.get("occurred_at") if has_id else None),
                    necessity=int(new_necessity) if new_necessity not in (None, "") else None,
                    notes=new_notes,
                    is_debt=int(new_is_debt) if new_is_debt not in (None, "") else None,
                )
                return result["message"]
            if act == "finance_delete":
                raw_amount = data.get("amount")
                amount = None
                if raw_amount not in (None, ""):
                    amount = float(str(raw_amount).replace(",", "."))
                result = self.delete_finance_transaction(
                    transaction_id=int(data["transaction_id"]) if data.get("transaction_id") else None,
                    description=data.get("description") or data.get("text"),
                    category=data.get("category"),
                    tx_type=data.get("type"),
                    occurred_at=data.get("occurred_at") or data.get("date"),
                    amount=amount,
                )
                return result["message"]
            if act == "habit_complete":
                return self.complete_habit((data.get("habit_name") or "").strip())
            if act == "habit_add":
                dow = data.get("days_of_week")
                if isinstance(dow, list):
                    dow_s = json.dumps(dow)
                elif isinstance(dow, str) and dow.strip().startswith("["):
                    dow_s = dow.strip()
                else:
                    dow_s = None
                hid = self.db.add_habit(
                    (data.get("name") or "").strip(),
                    (data.get("description") or "").strip(),
                    int(data.get("xp_reward") or 50),
                    dow_s,
                )
                broadcast_nexus_state(self)
                self._open_desktop_receipt(
                    "habits",
                    {
                        "highlight_id": hid,
                        "animate": "habit_add",
                        "toast": f"Hábito criado: {(data.get('name') or '').strip()}",
                        "receipt": {
                            "kind": "habit",
                            "action": "habit_add",
                            "id": hid,
                            "name": (data.get("name") or "").strip(),
                            "description": (data.get("description") or "").strip(),
                            "xp": int(data.get("xp_reward") or 50),
                            "days_of_week": dow_s,
                        },
                    },
                )
                return f"Habito criado id={hid}, Sir."
            if act == "task_add":
                tid = self.db.add_task(
                    (data.get("title") or "").strip(),
                    (data.get("due_date") or "").strip() or None,
                    int(data.get("points_reward") or 10),
                )
                broadcast_nexus_state(self)
                try:
                    from src.ui.nexus_signals import enqueue_nexus_desktop_open

                    enqueue_nexus_desktop_open("tasks", {"highlight_id": tid, "animate": "add"})
                except Exception:
                    pass
                return f"Tarefa #{tid} criada, Sir."
            if act == "task_complete":
                self.db.complete_task(int(data.get("task_id")))
                broadcast_nexus_state(self)
                return "Tarefa concluida."
            if act == "task_delete":
                self.db.delete_task(int(data.get("task_id")))
                broadcast_nexus_state(self)
                return "Tarefa removida."
            if act == "task_list":
                inc = data.get("include_done")
                if isinstance(inc, str):
                    inc = inc.lower() in ("1", "true", "yes")
                rows = self.db.list_tasks(data.get("due_date"), include_done=bool(inc))
                return json.dumps(rows, ensure_ascii=False)
            if act == "goal_add":
                return self.add_goal(
                    (data.get("name") or data.get("goal") or "").strip(),
                    (data.get("target_date") or "").strip() or None,
                )
            if act == "goal_update":
                return self.update_goal_progress(
                    (data.get("name") or data.get("goal") or "").strip(),
                    int(data.get("progress") or 0),
                )
            if act == "reward_redeem":
                ok_flag, msg = self.process_reward((data.get("reward_name") or data.get("name") or "").strip())
                return json.dumps({"ok": ok_flag, "message": msg}, ensure_ascii=False)
            if act == "reward_status":
                return json.dumps(
                    self.get_reward_status(int(data.get("limit") or 7)),
                    default=str,
                    ensure_ascii=False,
                )
            if act == "preset_apply_json":
                habits = data.get("habits")
                if isinstance(habits, str):
                    habits = json.loads(habits)
                return self.apply_preset_habits_json(habits or [])
            if act == "preset_save":
                return self.save_lifestyle_preset((data.get("name") or "").strip())
            if act == "preset_apply":
                return self.load_lifestyle_preset((data.get("name") or "").strip())
            if act == "preset_from_goals":
                goals = data.get("goals") or data.get("objectives") or data.get("goal") or ""
                return self.build_lifestyle_preset_from_goals(
                    goals,
                    (data.get("name") or data.get("preset_name") or "").strip() or None,
                )
            if act == "presets_list":
                return json.dumps(self.list_lifestyle_presets(), ensure_ascii=False)
            if act == "theme_list":
                return json.dumps(self.list_window_themes(), ensure_ascii=False)
            if act == "theme_apply":
                result = self.apply_window_theme(
                    data.get("module") or data.get("tab") or data.get("window"),
                    data.get("preset_id") or data.get("preset") or data.get("name"),
                )
                return json.dumps(result, ensure_ascii=False)
            if act == "theme_generate":
                result = self.generate_window_theme_preset(
                    data.get("module") or data.get("tab") or data.get("window"),
                    data.get("prompt") or data.get("description") or data.get("text") or "",
                    name=(data.get("name") or data.get("preset_name") or "").strip() or None,
                )
                return json.dumps(result, ensure_ascii=False)
            if act == "news_history":
                return json.dumps(
                    self.list_news_briefings(int(data.get("limit") or 8)),
                    ensure_ascii=False,
                )
            if act == "news_briefing":
                return json.dumps(
                    self.build_news_briefing(
                        data.get("query") or data.get("topic") or "",
                        limit=int(data.get("limit") or data.get("max_results") or 3),
                        results=data.get("results"),
                    ),
                    ensure_ascii=False,
                )
            if act == "news_save_note":
                return json.dumps(
                    self.save_news_item_to_note(
                        item=data.get("item"),
                        briefing=data.get("briefing"),
                        item_index=int(data.get("item_index") or data.get("index") or 1),
                        subject=data.get("subject") or "Noticias",
                    ),
                    ensure_ascii=False,
                )
            if act == "news_followup_task":
                return json.dumps(
                    self.create_news_followup_task(
                        item=data.get("item"),
                        briefing=data.get("briefing"),
                        item_index=int(data.get("item_index") or data.get("index") or 1),
                        due_date=data.get("due_date"),
                    ),
                    ensure_ascii=False,
                )
            if act == "news_flashcards_generate":
                return json.dumps(
                    self.create_news_flashcards(
                        item=data.get("item"),
                        briefing=data.get("briefing"),
                        item_index=int(data.get("item_index") or data.get("index") or 1),
                        subject=data.get("subject") or "Noticias",
                        max_cards=int(data.get("max_cards") or data.get("limit") or 4),
                    ),
                    ensure_ascii=False,
                )
            if act == "memory_graph":
                include_markdown = data.get("include_markdown", True)
                if isinstance(include_markdown, str):
                    include_markdown = include_markdown.strip().lower() not in ("0", "false", "no", "nao")
                return json.dumps(
                    self.build_memory_graph(
                        query=data.get("query") or data.get("text") or "",
                        limit=int(data.get("limit") or 120),
                        include_markdown=bool(include_markdown),
                    ),
                    default=str,
                    ensure_ascii=False,
                )
            if act in ("memory_graph_context", "memory_context"):
                include_markdown = data.get("include_markdown", True)
                if isinstance(include_markdown, str):
                    include_markdown = include_markdown.strip().lower() not in ("0", "false", "no", "nao")
                return json.dumps(
                    self.build_memory_graph_context(
                        query=data.get("query") or data.get("text") or data.get("question") or "",
                        limit=int(data.get("limit") or 8),
                        include_markdown=bool(include_markdown),
                    ),
                    default=str,
                    ensure_ascii=False,
                )
            if act == "memory_graph_export_obsidian":
                include_markdown = data.get("include_markdown", True)
                if isinstance(include_markdown, str):
                    include_markdown = include_markdown.strip().lower() not in ("0", "false", "no", "nao")
                return json.dumps(
                    self.export_memory_graph_obsidian(
                        data.get("folder") or data.get("path") or "",
                        query=data.get("query") or "",
                        include_markdown=bool(include_markdown),
                        limit=int(data.get("limit") or 160),
                    ),
                    default=str,
                    ensure_ascii=False,
                )
            if act == "memory_graph_import_obsidian":
                return json.dumps(
                    self.import_obsidian_markdown(
                        data.get("folder") or data.get("path") or "",
                        subject=data.get("subject") or "Obsidian",
                        limit=int(data.get("limit") or 80),
                    ),
                    default=str,
                    ensure_ascii=False,
                )
            if act == "ops_dashboard":
                open_window = data.get("open_window", True)
                if isinstance(open_window, str):
                    open_window = open_window.strip().lower() not in ("0", "false", "no", "nao")
                return json.dumps(
                    self.build_ops_dashboard(open_window=bool(open_window)),
                    default=str,
                    ensure_ascii=False,
                )
            if act in ("ops_metric_set", "ops_metric_update"):
                return json.dumps(
                    self.set_ops_metric(
                        data.get("key") or data.get("metric") or data.get("name"),
                        data.get("value") or data.get("amount"),
                        label=data.get("label") or data.get("name"),
                        unit=data.get("unit"),
                        target=data.get("target"),
                        trend=data.get("trend"),
                        period=data.get("period"),
                        notes=data.get("notes") or data.get("description"),
                    ),
                    default=str,
                    ensure_ascii=False,
                )
            if act == "open_ui":
                tab = (data.get("tab") or "dashboard").strip()
                return self.open_nexus_ui(tab)
            if act == "note_list":
                rows = self.db.list_study_notes(data.get("subject"))
                return json.dumps(rows, default=str, ensure_ascii=False)[:12000]
            if act == "note_get":
                n = self.db.get_study_note(int(data.get("note_id")))
                return json.dumps(n, default=str, ensure_ascii=False) if n else "Nao encontrado."
            if act == "note_save":
                msg = self.create_note(
                    (data.get("subject") or "Geral").strip(),
                    (data.get("title") or "Sem titulo").strip(),
                    (data.get("content") or "").strip(),
                    data.get("media"),
                )
                nid = getattr(self, "_last_created_note_id", None)
                try:
                    from src.ui.nexus_signals import enqueue_nexus_desktop_open

                    enqueue_nexus_desktop_open(
                        "notes", {"highlight_id": nid, "animate": "add"}
                    )
                except Exception:
                    pass
                return msg
            if act == "note_append":
                nid = int(data.get("note_id"))
                n = self.db.get_study_note(nid)
                if not n:
                    return "Nota nao encontrada."
                newc = (n.get("content") or "") + "\n\n" + (data.get("text") or "")
                self.db.update_study_note(nid, content=newc)
                broadcast_nexus_state(self)
                return "Nota atualizada."
            if act == "note_summarize":
                append = data.get("append_summary", data.get("append", True))
                if isinstance(append, str):
                    append = append.strip().lower() not in ("0", "false", "nao", "não", "no")
                return json.dumps(
                    self.summarize_note(
                        int(data.get("note_id")),
                        append=bool(append),
                        max_sentences=int(data.get("max_sentences") or 4),
                    ),
                    default=str,
                    ensure_ascii=False,
                )
            if act == "note_teach":
                return json.dumps(
                    self.teach_note(
                        int(data.get("note_id")),
                        question=data.get("question") or data.get("text") or "",
                        max_points=int(data.get("max_points") or data.get("limit") or 4),
                    ),
                    default=str,
                    ensure_ascii=False,
                )
            if act == "subject_teach":
                return json.dumps(
                    self.teach_subject(
                        data.get("subject") or data.get("materia") or "",
                        question=data.get("question") or data.get("text") or "",
                        max_points=int(data.get("max_points") or data.get("limit") or 6),
                    ),
                    default=str,
                    ensure_ascii=False,
                )
            if act == "note_attach_media":
                return json.dumps(
                    self.attach_media_to_note(
                        int(data.get("note_id")),
                        data.get("media_url") or data.get("url") or data.get("path") or "",
                        caption=data.get("caption"),
                        alt=data.get("alt"),
                    ),
                    default=str,
                    ensure_ascii=False,
                )
            if act == "flashcard_review":
                return self.review_flashcard_sm2(int(data["card_id"]), int(data.get("quality", 4)))
            if act == "flashcards_due":
                rows = self.db.list_flashcards_due(int(data.get("limit") or 20))
                return json.dumps(rows, default=str, ensure_ascii=False)
            if act == "flashcards_generate":
                limit = int(data.get("max_cards") or data.get("limit") or 8)
                if data.get("note_id"):
                    return json.dumps(
                        self.generate_flashcards_from_note(int(data["note_id"]), limit),
                        default=str,
                        ensure_ascii=False,
                    )
                return json.dumps(
                    self.generate_flashcards_from_subject((data.get("subject") or "").strip(), limit),
                    default=str,
                    ensure_ascii=False,
                )
            if act == "quiz_random":
                self.db.seed_quiz_if_empty()
                rows = self.db.random_quiz_questions(int(data.get("n") or 5), data.get("area"))
                return json.dumps(rows, default=str, ensure_ascii=False)
            if act == "quiz_attempt_review":
                return json.dumps(
                    self.review_quiz_attempt(int(data.get("attempt_id"))),
                    default=str,
                    ensure_ascii=False,
                )
            if act == "quiz_flashcards_generate":
                only_wrong = data.get("only_wrong", True)
                if isinstance(only_wrong, str):
                    only_wrong = only_wrong.strip().lower() not in ("0", "false", "no", "nao")
                return json.dumps(
                    self.generate_flashcards_from_quiz_attempt(
                        int(data.get("attempt_id")),
                        only_wrong=bool(only_wrong),
                        max_cards=int(data.get("max_cards") or data.get("limit") or 8),
                    ),
                    default=str,
                    ensure_ascii=False,
                )
            if act == "study_recommendations":
                return json.dumps(
                    self.get_study_recommendations(int(data.get("limit") or 4)),
                    default=str,
                    ensure_ascii=False,
                )
        except Exception as e:
            logger.exception("nexus_command")
            return f"Erro Nexus: {e}"
        return f"Acao desconhecida: {act}"


_nexus_singleton: NexusService | None = None


def get_nexus_service() -> NexusService:
    global _nexus_singleton
    if _nexus_singleton is None:
        _nexus_singleton = NexusService()
    return _nexus_singleton
