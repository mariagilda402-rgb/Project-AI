import sqlite3
import json
from pathlib import Path
from datetime import datetime, date, timedelta



class NexusHabitsDBMixin:
    def log_habit_completion(self, habit_id, target_date: str = None):
        """Registra conclusão (uma por dia) e recalcula streak por dias consecutivos com log."""
        if target_date:
            from datetime import datetime as dt
            try:
                date_obj = dt.fromisoformat(target_date).date()
            except:
                date_obj = date.today()
            target_iso = date_obj.isoformat()
            ts = f"{target_iso} 12:00:00"
        else:
            target_iso = date.today().isoformat()
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            exists = cursor.execute(
                """
                SELECT 1 FROM habit_logs
                WHERE habit_id = ? AND date(completed_at) = date(?)
            """,
                (habit_id, target_iso),
            ).fetchone()
            if exists:
                conn.commit()
                return False
            cursor.execute(
                "INSERT INTO habit_logs (habit_id, completed_at) VALUES (?, ?)",
                (habit_id, ts),
            )
            conn.commit()

        streak = self._compute_habit_streak(habit_id)
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE habits SET current_streak = ?,
                max_streak = CASE WHEN COALESCE(max_streak, 0) < ? THEN ? ELSE max_streak END
                WHERE id = ?
            """,
                (streak, streak, streak, habit_id),
            )
            conn.commit()
        return True

    def check_habit_completion(self, habit_id, target_date: str = None) -> bool:
        if target_date:
            try:
                from datetime import datetime as dt
                target_iso = dt.fromisoformat(target_date).date().isoformat()
            except:
                target_iso = date.today().isoformat()
        else:
            target_iso = date.today().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            exists = cursor.execute(
                """
                SELECT 1 FROM habit_logs
                WHERE habit_id = ? AND date(completed_at) = date(?)
            """,
                (habit_id, target_iso),
            ).fetchone()
            return bool(exists)

    def unlog_habit_completion(self, habit_id, target_date: str = None):
        """Remove a conclusão do hábito num dia específico (retroativamente ou hoje) e recalcula streak."""
        if target_date:
            try:
                from datetime import datetime as dt
                target_iso = dt.fromisoformat(target_date).date().isoformat()
            except:
                target_iso = date.today().isoformat()
        else:
            target_iso = date.today().isoformat()

        with self._get_connection() as conn:
            conn.execute(
                """
                DELETE FROM habit_logs
                WHERE habit_id = ? AND date(completed_at) = date(?)
                """,
                (habit_id, target_iso),
            )
            conn.commit()

        streak = self._compute_habit_streak(habit_id)
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE habits SET current_streak = ?
                WHERE id = ?
            """,
                (streak, habit_id),
            )
            conn.commit()
        return True

    def _compute_habit_streak(self, habit_id: int) -> int:
        d = date.today()
        streak = 0
        with self._get_connection() as conn:
            while True:
                row = conn.execute(
                    """
                    SELECT 1 FROM habit_logs
                    WHERE habit_id = ? AND date(completed_at) = date(?)
                """,
                    (habit_id, d.isoformat()),
                ).fetchone()
                if row:
                    streak += 1
                    d -= timedelta(days=1)
                else:
                    break
        return streak

    def get_habits(self):
        """Retorna a lista de hábitos e suas estatísticas, incluindo se foi concluído hoje e o histórico de 7 dias."""
        today = date.today()
        today_iso = today.isoformat()
        start_date = (today - timedelta(days=29)).isoformat()
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM habits WHERE active = 1").fetchall()
            habits = []
            for r in rows:
                h = dict(r)
                done = conn.execute(
                    "SELECT 1 FROM habit_logs WHERE habit_id = ? AND date(completed_at) = date(?)",
                    (h["id"], today_iso),
                ).fetchone()
                h["completed_today"] = bool(done)

                logs = conn.execute(
                    "SELECT date(completed_at) as d FROM habit_logs WHERE habit_id = ? AND date(completed_at) >= date(?)",
                    (h["id"], start_date)
                ).fetchall()
                completed_dates = {log["d"] for log in logs}
                history = {}
                for i in range(30):
                    d = (today - timedelta(days=i)).isoformat()
                    history[d] = d in completed_dates
                h["recent_history"] = history
                habits.append(h)
            return habits

    def get_habit_history(self, days: int = 30, year: int = None, month: int = None) -> list[dict]:
        """Retorna dados de atividade diária dos últimos N dias ou de um mês específico para heatmap.
        Cada item contém: date, total (hábitos ativos), completed (feitos)."""
        import calendar
        if year and month:
            start = date(year, month, 1)
            last_day = calendar.monthrange(year, month)[1]
            end = min(date(year, month, last_day), date.today())  # nunca vai além de hoje
            if end < start:
                # Mês futuro: retorna lista vazia
                return []
        else:
            end = date.today()
            start = end - timedelta(days=days - 1)
        with self._get_connection() as conn:
            # Completados por dia
            completed_rows = conn.execute(
                """
                SELECT date(completed_at) as d, COUNT(DISTINCT habit_id) as cnt
                FROM habit_logs
                WHERE date(completed_at) >= date(?) AND date(completed_at) <= date(?)
                GROUP BY date(completed_at)
                ORDER BY d
                """,
                (start.isoformat(), end.isoformat()),
            ).fetchall()
            completed_map = {r[0]: r[1] for r in completed_rows}

            # Total de hábitos ativos por dia (criados antes ou durante o dia)
            habits_rows = conn.execute(
                "SELECT id, created_at, days_of_week FROM habits WHERE active = 1"
            ).fetchall()

            result = []
            d = start
            while d <= end:
                ds = d.isoformat()
                dow = d.weekday()  # 0=Mon ... 6=Sun
                # Python weekday -> JS weekday (0=Sun)
                js_dow = (dow + 1) % 7
                total = 0
                for h in habits_rows:
                    h_created = (h[1] or "2000-01-01")[:10]
                    if ds < h_created:
                        continue
                    h_dow = h[2]
                    if h_dow:
                        try:
                            dow_list = __import__("json").loads(h_dow)
                            if len(dow_list) < 7 and js_dow not in dow_list:
                                continue
                        except Exception:
                            pass
                    total += 1
                completed = completed_map.get(ds, 0)
                result.append({"date": ds, "total": total, "completed": completed, "count": completed})
                d += timedelta(days=1)
            return result

    def add_habit(
        self,
        name: str,
        description: str = "",
        xp_reward: int = 50,
        days_of_week: str | None = None,
    ):
        with self._get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO habits (name, description, xp_reward, days_of_week, active)
                VALUES (?, ?, ?, ?, 1)
            """,
                (name, description, xp_reward, days_of_week or None),
            )
            conn.commit()
            return cur.lastrowid

    def delete_habit(self, habit_id: int):
        with self._get_connection() as conn:
            conn.execute("UPDATE habits SET active = 0 WHERE id = ?", (habit_id,))
            conn.commit()

    def update_habit(
        self,
        habit_id: int,
        name: str | None = None,
        description: str | None = None,
        xp_reward: int | None = None,
        days_of_week: str | None = None,
    ) -> dict | None:
        """Atualiza campos de um hábito existente. Retorna o hábito atualizado."""
        fields = []
        vals = []
        if name is not None:
            fields.append("name = ?")
            vals.append(str(name).strip())
        if description is not None:
            fields.append("description = ?")
            vals.append(str(description).strip())
        if xp_reward is not None:
            fields.append("xp_reward = ?")
            vals.append(int(xp_reward))
        if days_of_week is not None:
            fields.append("days_of_week = ?")
            vals.append(str(days_of_week).strip())
        if not fields:
            with self._get_connection() as conn:
                conn.row_factory = __import__("sqlite3").Row
                row = conn.execute("SELECT * FROM habits WHERE id = ?", (habit_id,)).fetchone()
                return dict(row) if row else None
        vals.append(int(habit_id))
        with self._get_connection() as conn:
            conn.execute(
                f"UPDATE habits SET {', '.join(fields)} WHERE id = ?",
                vals,
            )
            conn.commit()
            conn.row_factory = __import__("sqlite3").Row
            row = conn.execute("SELECT * FROM habits WHERE id = ?", (habit_id,)).fetchone()
            return dict(row) if row else None

