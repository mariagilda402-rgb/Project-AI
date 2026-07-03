import sqlite3
import json
from pathlib import Path
from datetime import datetime, date, timedelta



class NexusTasksDBMixin:
    def get_task_history(self, days: int = 30, year: int = None, month: int = None) -> list[dict]:
        """Retorna histórico de tarefas por dia para heatmap.
        Cada item contém: date, total (tarefas existentes), completed (feitas)."""
        import calendar
        if year and month:
            start = date(year, month, 1)
            last_day = calendar.monthrange(year, month)[1]
            end = min(date(year, month, last_day), date.today())  # nunca vai além de hoje
            if end < start:
                return []
        else:
            end = date.today()
            start = end - timedelta(days=days - 1)
        with self._get_connection() as conn:
            # Tarefas criadas até cada dia - só busca tarefas dentro do período
            all_tasks = conn.execute(
                """
                SELECT id, date(created_at) as created_d, date(done_at) as done_d
                FROM tasks
                WHERE date(created_at) <= date(?)
                """,
                (end.isoformat(),),
            ).fetchall()

            result = []
            d = start
            while d <= end:
                ds = d.isoformat()
                total = 0
                completed = 0
                for t in all_tasks:
                    created_d = t[1] or "2000-01-01"
                    done_d = t[2]
                    # A tarefa existia nesse dia se criada <= d
                    if created_d > ds:
                        continue
                    total += 1
                    # A tarefa foi concluída EXATAMENTE nesse dia (não contamina dias futuros)
                    if done_d and done_d == ds:
                        completed += 1
                result.append({"date": ds, "total": total, "completed": completed})
                d += timedelta(days=1)
            return result

    def list_tasks(self, due: str | None = None, include_done: bool = False):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            q = "SELECT * FROM tasks WHERE 1=1"
            p: list = []
            if due:
                q += " AND date(due_date) = date(?)"
                p.append(due)
            if not include_done:
                q += " AND done_at IS NULL"
            q += " ORDER BY due_date, id"
            return [dict(r) for r in conn.execute(q, p).fetchall()]

    def add_task(self, title: str, due_date: str | None, points_reward: int = 10):
        with self._get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO tasks (title, due_date, points_reward) VALUES (?, ?, ?)",
                (title, due_date, points_reward),
            )
            conn.commit()
            return cur.lastrowid

    def complete_task(self, task_id: int):
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE tasks SET done_at = CURRENT_TIMESTAMP WHERE id = ? AND done_at IS NULL",
                (task_id,),
            )
            conn.commit()

    def uncomplete_task(self, task_id: int):
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE tasks SET done_at = NULL WHERE id = ? AND done_at IS NOT NULL",
                (task_id,),
            )
            conn.commit()

    def delete_task(self, task_id: int):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()

