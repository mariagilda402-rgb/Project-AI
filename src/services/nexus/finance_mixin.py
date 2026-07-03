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




class NexusFinanceMixin:
    def _open_desktop_receipt(self, module: str, payload: dict) -> None:
        try:
            from src.ui.nexus_signals import enqueue_nexus_desktop_open

            enqueue_nexus_desktop_open(module, self._decorate_nexus_payload(payload))
        except Exception:
            pass

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

    def set_finance_budget(self, category: str, limit: float) -> str:
        with self.db._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM finance_budgets WHERE category = ?", (category,))
            row = cur.fetchone()
            if row:
                cur.execute("UPDATE finance_budgets SET monthly_limit = ? WHERE id = ?", (limit, row[0]))
            else:
                cur.execute("INSERT INTO finance_budgets (category, monthly_limit) VALUES (?, ?)", (category, limit))
            conn.commit()
            return f"Budget para '{category}' definido para R$ {limit:.2f}."

    def get_finance_budget_status(self) -> str:
        current_month = date.today().replace(day=1).isoformat()
        with self.db._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT category, monthly_limit FROM finance_budgets")
            budgets = cur.fetchall()
            if not budgets:
                return "Nenhum budget definido."

            status_list = []
            for cat, limit in budgets:
                cur.execute(
                    "SELECT SUM(amount) FROM finance_transactions WHERE type='expense' AND category=? AND occurred_at >= ?",
                    (cat, current_month)
                )
                spent = cur.fetchone()[0] or 0
                status_list.append({"category": cat, "limit": limit, "spent": spent, "remaining": limit - spent})

            return json.dumps(status_list, ensure_ascii=False)

    def add_finance_investment(self, ticker: str, inv_type: str, quantity: float, avg_price: float) -> str:
        with self.db._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO finance_investments (ticker, type, quantity, avg_price) VALUES (?, ?, ?, ?)",
                       (ticker, inv_type, quantity, avg_price))
            conn.commit()
            return f"Investimento {quantity}x {ticker} adicionado."

    def get_finance_portfolio(self) -> str:
        with self.db._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT ticker, type, quantity, avg_price FROM finance_investments")
            invs = cur.fetchall()
            portfolio = [{"ticker": r[0], "type": r[1], "quantity": r[2], "avg_price": r[3]} for r in invs]
            return json.dumps(portfolio, ensure_ascii=False)

