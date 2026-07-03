import sqlite3
import json
from pathlib import Path
from datetime import datetime, date, timedelta



class NexusFinanceDBMixin:
    def add_transaction(
        self,
        t_type,
        amount,
        category,
        description,
        necessity,
        occurred_at: str | None = None,
        notes: str | None = None,
        is_debt: int = 0,
    ):
        oa = occurred_at or datetime.now().strftime("%Y-%m-%d")
        with self._get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO finance_transactions (
                    type, amount, category, description, necessity_score,
                    occurred_at, notes, is_debt
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    t_type,
                    amount,
                    category,
                    description,
                    necessity,
                    oa,
                    notes,
                    int(is_debt),
                ),
            )
            conn.commit()
            return cur.lastrowid

    def list_finance_transactions(self, date_from: str | None, date_to: str | None):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            q = "SELECT * FROM finance_transactions WHERE 1=1"
            params: list = []
            if date_from:
                q += " AND date(occurred_at) >= date(?)"
                params.append(date_from)
            if date_to:
                q += " AND date(occurred_at) <= date(?)"
                params.append(date_to)
            q += " ORDER BY occurred_at DESC, id DESC"
            rows = conn.execute(q, params).fetchall()
            return [dict(r) for r in rows]

    def get_finance_transaction(self, transaction_id: int):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM finance_transactions WHERE id = ?",
                (transaction_id,),
            ).fetchone()
            return dict(row) if row else None

    def delete_finance_transaction(self, transaction_id: int):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM finance_transactions WHERE id = ?",
                (transaction_id,),
            ).fetchone()
            if not row:
                return None
            deleted = dict(row)
            conn.execute("DELETE FROM finance_transactions WHERE id = ?", (transaction_id,))
            conn.commit()
            return deleted

    def update_finance_transaction(
        self,
        transaction_id: int,
        t_type=None,
        amount=None,
        category=None,
        description=None,
        necessity=None,
        occurred_at: str | None = None,
        notes=None,
        is_debt=None,
    ):
        fields = []
        vals = []
        if t_type is not None:
            fields.append("type = ?")
            vals.append(str(t_type).strip().lower())
        if amount is not None:
            fields.append("amount = ?")
            vals.append(float(amount))
        if category is not None:
            fields.append("category = ?")
            vals.append(str(category).strip())
        if description is not None:
            fields.append("description = ?")
            vals.append(str(description).strip())
        if necessity is not None:
            fields.append("necessity_score = ?")
            vals.append(int(necessity))
        if occurred_at is not None:
            fields.append("occurred_at = ?")
            vals.append(str(occurred_at).strip())
        if notes is not None:
            fields.append("notes = ?")
            vals.append(str(notes).strip() or None)
        if is_debt is not None:
            fields.append("is_debt = ?")
            vals.append(int(is_debt))

        if not fields:
            return self.get_finance_transaction(int(transaction_id))

        vals.append(int(transaction_id))
        with self._get_connection() as conn:
            conn.execute(
                f"UPDATE finance_transactions SET {', '.join(fields)} WHERE id = ?",
                vals,
            )
            conn.commit()
        return self.get_finance_transaction(int(transaction_id))

    def finance_monthly_totals(self, year: int, month: int):
        """Soma income/expense por mes (occurred_at)."""
        from calendar import monthrange

        start = f"{year:04d}-{month:02d}-01"
        last = monthrange(year, month)[1]
        end = f"{year:04d}-{month:02d}-{last:02d}"
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT type, SUM(amount) as total FROM finance_transactions
                WHERE date(occurred_at) >= date(?) AND date(occurred_at) <= date(?)
                GROUP BY type
            """,
                (start, end),
            ).fetchall()
            inc = exp = debt = 0.0
            for t, tot in rows:
                if t == "income":
                    inc = float(tot or 0)
                elif t == "expense":
                    exp = float(tot or 0)
            drow = conn.execute(
                """
                SELECT SUM(amount) FROM finance_transactions
                WHERE date(occurred_at) >= date(?) AND date(occurred_at) <= date(?)
                  AND is_debt = 1
            """,
                (start, end),
            ).fetchone()
            debt = float(drow[0] or 0)
            return {
                "period_start": start,
                "period_end": end,
                "income": inc,
                "expense": exp,
                "debt_payments": debt,
                "net": inc - exp,
            }

