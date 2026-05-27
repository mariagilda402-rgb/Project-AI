import sqlite3
import json
from pathlib import Path
from datetime import datetime, date, timedelta

class NexusDatabase:
    def __init__(self, db_path="data/nexus.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. ECONOMY & USER (XP, Levels)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nexus_user (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    points INTEGER DEFAULT 0,
                    last_update DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Insere usuário padrão se não existir
            cursor.execute("INSERT OR IGNORE INTO nexus_user (id, xp, level, points) VALUES (1, 0, 1, 0)")

            # 2. FINANCE (Aether)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS finance_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL, -- 'income' or 'expense'
                    amount REAL NOT NULL,
                    category TEXT,
                    description TEXT,
                    necessity_score INTEGER DEFAULT 5,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 3. HABITS & ROUTINE (Chronos)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS habits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    days_of_week TEXT, -- JSON list: [0,1,2,3,4,5,6]
                    target_time TEXT,
                    xp_reward INTEGER DEFAULT 50,
                    current_streak INTEGER DEFAULT 0,
                    max_streak INTEGER DEFAULT 0,
                    active INTEGER DEFAULT 1
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS habit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    habit_id INTEGER,
                    completed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(habit_id) REFERENCES habits(id)
                )
            """)

            # 4. STUDIES & NOTES (MindPalace)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS study_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT,
                    title TEXT NOT NULL,
                    content TEXT, -- Rich Text / Markdown
                    media_links TEXT, -- JSON list of file paths/URLs
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS flashcards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    note_id INTEGER,
                    front TEXT NOT NULL,
                    back TEXT NOT NULL,
                    ease_factor REAL DEFAULT 2.5,
                    interval INTEGER DEFAULT 0,
                    repetitions INTEGER DEFAULT 0,
                    next_review DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(note_id) REFERENCES study_notes(id)
                )
            """)

            # 5. STRATEGY PRESETS (unico esquema; evita duplicata de CREATE)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lifestyle_presets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    config_json TEXT NOT NULL,
                    is_active INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 6. REWARDS STORE
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nexus_rewards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    cost INTEGER NOT NULL,
                    description TEXT
                )
            """)

            # Insere recompensas iniciais
            cursor.execute("INSERT OR IGNORE INTO nexus_rewards (id, name, cost, description) VALUES (1, 'Episódio de Anime', 300, 'Assista a um episódio de anime sem culpa.')")
            cursor.execute("INSERT OR IGNORE INTO nexus_rewards (id, name, cost, description) VALUES (2, 'Noite de Rodízio', 2000, 'Recompensa máxima por uma semana de elite.')")
            cursor.execute("INSERT OR IGNORE INTO nexus_rewards (id, name, cost, description) VALUES (3, '1h de Games', 500, 'Tempo livre para jogos.')")

            # Insere hábitos iniciais
            cursor.execute("INSERT OR IGNORE INTO habits (id, name, description, xp_reward) VALUES (1, 'Academia', 'Treino físico diário', 100)")
            cursor.execute("INSERT OR IGNORE INTO habits (id, name, description, xp_reward) VALUES (2, 'Estudo ENEM', 'Sessão de estudos intensiva', 150)")

            # 7. ENEM QUESTIONS & STATS
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS study_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL UNIQUE,
                    total_questions INTEGER DEFAULT 0,
                    correct_answers INTEGER DEFAULT 0,
                    last_attempt DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("INSERT OR IGNORE INTO study_stats (id, subject) VALUES (1, 'Matemática')")
            cursor.execute("INSERT OR IGNORE INTO study_stats (id, subject) VALUES (2, 'Português')")
            cursor.execute("INSERT OR IGNORE INTO study_stats (id, subject) VALUES (3, 'Ciências da Natureza')")
            cursor.execute("INSERT OR IGNORE INTO study_stats (id, subject) VALUES (4, 'Ciências Humanas')")

            # 8. GRAND OBJECTIVES (Metas)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nexus_goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    target_date DATE,
                    progress INTEGER DEFAULT 0, -- 0 a 100
                    status TEXT DEFAULT 'active' -- active, achieved, failed
                )
            # 9. HEALTH & FITNESS
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fitness_workouts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE DEFAULT (date('now', 'localtime')),
                    type TEXT NOT NULL,
                    duration_minutes INTEGER,
                    calories_burned INTEGER,
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fitness_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE DEFAULT (date('now', 'localtime')),
                    weight REAL,
                    body_fat_percentage REAL,
                    calories_consumed INTEGER,
                    protein_grams INTEGER,
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 10. JOURNAL & MOOD
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS journal_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE DEFAULT (date('now', 'localtime')),
                    content TEXT NOT NULL,
                    psychologist_feedback TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mood_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE DEFAULT (date('now', 'localtime')),
                    mood_score INTEGER, -- 1 to 10
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            self._migrate_schema(conn)

    def _migrate_schema(self, conn):
        """ALTER TABLE leves para colunas novas (idempotente)."""
        cur = conn.cursor()

        def cols(table):
            cur.execute(f"PRAGMA table_info({table})")
            return {row[1] for row in cur.fetchall()}

        ft = "finance_transactions"
        if ft in [r[0] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]:
            c = cols(ft)
            if "occurred_at" not in c:
                cur.execute(f"ALTER TABLE {ft} ADD COLUMN occurred_at DATE")
                cur.execute(
                    f"UPDATE {ft} SET occurred_at = date(created_at) WHERE occurred_at IS NULL"
                )
            if "notes" not in c:
                cur.execute(f"ALTER TABLE {ft} ADD COLUMN notes TEXT")
            if "is_debt" not in c:
                cur.execute(
                    f"ALTER TABLE {ft} ADD COLUMN is_debt INTEGER NOT NULL DEFAULT 0"
                )

        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='study_notes'"
        )
        if cur.fetchone():
            c = cols("study_notes")
            if "media_links" not in c:
                cur.execute("ALTER TABLE study_notes ADD COLUMN media_links TEXT")
            if "color" not in c:
                cur.execute("ALTER TABLE study_notes ADD COLUMN color TEXT")

        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'"
        )
        if not cur.fetchone():
            cur.execute("""
                CREATE TABLE tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    due_date DATE,
                    done_at DATETIME,
                    habit_id INTEGER,
                    points_reward INTEGER DEFAULT 10,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(habit_id) REFERENCES habits(id)
                )
            """)

        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='habits'")
        if cur.fetchone():
            c = cols("habits")
            if "created_at" not in c:
                cur.execute("ALTER TABLE habits ADD COLUMN created_at DATETIME")
                cur.execute("UPDATE habits SET created_at = COALESCE((SELECT MIN(completed_at) FROM habit_logs WHERE habit_id = habits.id), CURRENT_TIMESTAMP)")

        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='reward_redemptions'"
        )
        if not cur.fetchone():
            cur.execute("""
                CREATE TABLE reward_redemptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    redemption_date DATE NOT NULL UNIQUE,
                    reward_id INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(reward_id) REFERENCES nexus_rewards(id)
                )
            """)

        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='quiz_questions'"
        )
        if not cur.fetchone():
            cur.execute("""
                CREATE TABLE quiz_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    area TEXT NOT NULL,
                    stem TEXT NOT NULL,
                    options_json TEXT NOT NULL,
                    correct_index INTEGER NOT NULL,
                    explanation TEXT,
                    skill TEXT,
                    difficulty TEXT,
                    source TEXT DEFAULT 'seed'
                )
            """)
            cur.execute("""
                CREATE TABLE quiz_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    finished_at DATETIME,
                    area TEXT,
                    score_pct REAL
                )
            """)
            cur.execute("""
                CREATE TABLE quiz_answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attempt_id INTEGER NOT NULL,
                    question_id INTEGER NOT NULL,
                    chosen_index INTEGER NOT NULL,
                    correct INTEGER NOT NULL,
                    FOREIGN KEY(attempt_id) REFERENCES quiz_attempts(id),
                    FOREIGN KEY(question_id) REFERENCES quiz_questions(id)
                )
            """)
        else:
            c = cols("quiz_questions")
            if "explanation" not in c:
                cur.execute("ALTER TABLE quiz_questions ADD COLUMN explanation TEXT")
            if "skill" not in c:
                cur.execute("ALTER TABLE quiz_questions ADD COLUMN skill TEXT")
            if "difficulty" not in c:
                cur.execute("ALTER TABLE quiz_questions ADD COLUMN difficulty TEXT")

        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='workflows'"
        )
        if not cur.fetchone():
            cur.execute("""
                CREATE TABLE workflows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    steps_json TEXT NOT NULL,
                    tags TEXT,
                    risk_level TEXT DEFAULT 'low',
                    last_executed DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

        conn.commit()

    # --- Métodos de Utilidade Básica ---

    def add_xp(self, amount):
        with self._get_connection() as conn:
            # 1. Adiciona XP e Pontos
            conn.execute("UPDATE nexus_user SET xp = xp + ?, points = points + ? WHERE id = 1", (amount, amount))

            # 2. Recalcula Level (Fórmula: 1 + XP / 1000)
            conn.execute("UPDATE nexus_user SET level = 1 + (xp / 1000) WHERE id = 1")
            conn.commit()
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

    def compute_global_streak(self) -> int:
        """Dias consecutivos (a partir de hoje) em que todos os hábitos ativos tiveram log."""
        habits = self.get_habits()
        if not habits:
            return 0
        ids = [h["id"] for h in habits]
        d = date.today()
        streak = 0
        with self._get_connection() as conn:
            while True:
                ok = True
                for hid in ids:
                    r = conn.execute(
                        """
                        SELECT 1 FROM habit_logs
                        WHERE habit_id = ? AND date(completed_at) = date(?)
                    """,
                        (hid, d.isoformat()),
                    ).fetchone()
                    if not r:
                        ok = False
                        break
                if not ok:
                    break
                streak += 1
                d -= timedelta(days=1)
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

    def get_user_stats(self):
        with self._get_connection() as conn:
            row = conn.execute("SELECT xp, level, points FROM nexus_user WHERE id = 1").fetchone()
            if row:
                return {"xp": row[0], "level": row[1], "points": row[2]}
            return None

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

    def count_redemptions_on_date(self, d: str) -> int:
        with self._get_connection() as conn:
            r = conn.execute(
                "SELECT COUNT(*) FROM reward_redemptions WHERE redemption_date = ?",
                (d,),
            ).fetchone()
            return int(r[0] or 0)

    def add_reward_redemption(self, reward_id: int, d: str):
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO reward_redemptions (redemption_date, reward_id) VALUES (?, ?)",
                (d, reward_id),
            )
            conn.commit()

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

    def list_study_notes(self, subject: str | None = None):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            if subject:
                rows = conn.execute(
                    "SELECT * FROM study_notes WHERE subject = ? ORDER BY updated_at DESC",
                    (subject,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM study_notes ORDER BY updated_at DESC"
                ).fetchall()
            return [dict(r) for r in rows]

    def get_study_note(self, note_id: int):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM study_notes WHERE id = ?", (note_id,)).fetchone()
            return dict(row) if row else None

    def update_study_note(self, note_id: int, title=None, content=None, subject=None, color=None):
        fields = []
        vals = []
        if title is not None:
            fields.append("title = ?")
            vals.append(title)
        if content is not None:
            fields.append("content = ?")
            vals.append(content)
        if subject is not None:
            fields.append("subject = ?")
            vals.append(subject)
        if color is not None:
            fields.append("color = ?")
            vals.append(color)
        if not fields:
            return
        fields.append("updated_at = CURRENT_TIMESTAMP")
        vals.append(note_id)
        with self._get_connection() as conn:
            conn.execute(
                f"UPDATE study_notes SET {', '.join(fields)} WHERE id = ?",
                vals,
            )
            conn.commit()

    def append_study_note_media(self, note_id: int, media_item: dict):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT media_links FROM study_notes WHERE id = ?", (note_id,)
            ).fetchone()
            if not row:
                return None
            try:
                media = json.loads(row["media_links"] or "[]")
                if not isinstance(media, list):
                    media = []
            except (TypeError, json.JSONDecodeError):
                media = []
            media.append(media_item)
            conn.execute(
                """
                UPDATE study_notes
                SET media_links = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (json.dumps(media, ensure_ascii=False), note_id),
            )
            conn.commit()
            return media

    def delete_study_note(self, note_id: int):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM flashcards WHERE note_id = ?", (note_id,))
            conn.execute("DELETE FROM study_notes WHERE id = ?", (note_id,))
            conn.commit()

    def list_flashcards_due(self, limit: int = 50):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT f.*, n.subject, n.title as note_title FROM flashcards f
                LEFT JOIN study_notes n ON n.id = f.note_id
                WHERE datetime(f.next_review) <= datetime('now')
                ORDER BY datetime(f.next_review) LIMIT ?
            """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def update_flashcard_srs(
        self,
        card_id: int,
        ease_factor: float,
        interval: int,
        repetitions: int,
        next_review: str,
    ):
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE flashcards SET ease_factor=?, interval=?, repetitions=?, next_review=?
                WHERE id=?
            """,
                (ease_factor, interval, repetitions, next_review, card_id),
            )
            conn.commit()

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

    # ── Reward CRUD ─────────────────────────────────────────────

    def list_rewards(self) -> list[dict]:
        """Lista todas as recompensas."""
        with self._get_connection() as conn:
            conn.row_factory = __import__("sqlite3").Row
            rows = conn.execute("SELECT * FROM nexus_rewards ORDER BY cost ASC").fetchall()
            return [dict(r) for r in rows]

    def add_reward(self, name: str, cost: int, description: str = "") -> int:
        """Cria uma recompensa customizada. Retorna o ID."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO nexus_rewards (name, cost, description) VALUES (?, ?, ?)",
                (name.strip(), int(cost), (description or "").strip()),
            )
            conn.commit()
            return cur.lastrowid

    def update_reward(
        self,
        reward_id: int,
        name: str | None = None,
        cost: int | None = None,
        description: str | None = None,
    ) -> dict | None:
        """Atualiza campos de uma recompensa. Retorna a recompensa atualizada."""
        fields, vals = [], []
        if name is not None:
            fields.append("name = ?")
            vals.append(str(name).strip())
        if cost is not None:
            fields.append("cost = ?")
            vals.append(int(cost))
        if description is not None:
            fields.append("description = ?")
            vals.append(str(description).strip())
        if not fields:
            with self._get_connection() as conn:
                conn.row_factory = __import__("sqlite3").Row
                row = conn.execute("SELECT * FROM nexus_rewards WHERE id = ?", (reward_id,)).fetchone()
                return dict(row) if row else None
        vals.append(int(reward_id))
        with self._get_connection() as conn:
            conn.execute(f"UPDATE nexus_rewards SET {', '.join(fields)} WHERE id = ?", vals)
            conn.commit()
            conn.row_factory = __import__("sqlite3").Row
            row = conn.execute("SELECT * FROM nexus_rewards WHERE id = ?", (reward_id,)).fetchone()
            return dict(row) if row else None

    def delete_reward(self, reward_id: int):
        """Remove uma recompensa."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM nexus_rewards WHERE id = ?", (int(reward_id),))
            conn.commit()



    def seed_quiz_if_empty(self):
        """Banco inicial ENEM-like, idempotente, com explicacoes para revisao."""
        samples = [
            {
                "area": "Matemática",
                "stem": "Uma família reduziu o consumo mensal de energia de 240 kWh para 204 kWh. Qual foi a redução percentual?",
                "options": ["12%", "15%", "18%", "36%"],
                "correct_index": 1,
                "skill": "Porcentagem",
                "difficulty": "media",
                "explanation": "A reducao foi de 36 kWh. Dividindo 36 por 240, obtemos 0,15, ou seja, 15%.",
            },
            {
                "area": "Matemática",
                "stem": "Em uma função afim f(x)=2x+3, qual é o valor de f(5)?",
                "options": ["10", "11", "13", "15"],
                "correct_index": 2,
                "skill": "Função afim",
                "difficulty": "facil",
                "explanation": "Substitua x por 5: f(5)=2*5+3=13.",
            },
            {
                "area": "Matemática",
                "stem": "Um reservatório comporta 1200 litros e está com 35% da capacidade. Quantos litros faltam para enchê-lo?",
                "options": ["420", "650", "780", "900"],
                "correct_index": 2,
                "skill": "Grandezas e porcentagem",
                "difficulty": "media",
                "explanation": "35% de 1200 sao 420 litros. Faltam 1200-420=780 litros.",
            },
            {
                "area": "Português",
                "stem": "Na frase 'Ela estudou muito, portanto foi bem na prova', a palavra 'portanto' indica:",
                "options": ["oposição", "conclusão", "adição", "condição"],
                "correct_index": 1,
                "skill": "Conectivos argumentativos",
                "difficulty": "facil",
                "explanation": "'Portanto' introduz uma consequencia/conclusao em relacao ao que foi dito antes.",
            },
            {
                "area": "Português",
                "stem": "Em textos dissertativo-argumentativos, a tese é:",
                "options": ["um exemplo secundário", "a opinião central defendida", "a citação obrigatória", "o resumo final"],
                "correct_index": 1,
                "skill": "Tese e argumentação",
                "difficulty": "facil",
                "explanation": "A tese e o ponto de vista central que o texto defende com argumentos.",
            },
            {
                "area": "Português",
                "stem": "A expressão 'chuva de ideias' é um exemplo de linguagem:",
                "options": ["literal", "figurada", "técnica", "jurídica"],
                "correct_index": 1,
                "skill": "Figuras de linguagem",
                "difficulty": "media",
                "explanation": "A expressao nao descreve chuva real; usa sentido figurado para indicar muitas ideias.",
            },
            {
                "area": "Ciências da Natureza",
                "stem": "Durante a fotossíntese, a fase clara produz principalmente:",
                "options": ["glicose e oxigênio", "ATP e NADPH", "DNA e RNA", "sais minerais"],
                "correct_index": 1,
                "skill": "Fotossíntese",
                "difficulty": "media",
                "explanation": "A fase clara transforma energia luminosa em ATP e NADPH, usados no ciclo de Calvin.",
            },
            {
                "area": "Ciências da Natureza",
                "stem": "Ao ligar vários aparelhos em uma mesma tomada, o risco de aquecimento aumenta principalmente por causa:",
                "options": ["da queda da gravidade", "do aumento da corrente elétrica", "da redução da frequência", "da ausência de tensão"],
                "correct_index": 1,
                "skill": "Eletricidade",
                "difficulty": "media",
                "explanation": "Mais aparelhos demandam maior corrente; o efeito Joule aumenta o aquecimento dos condutores.",
            },
            {
                "area": "Ciências da Natureza",
                "stem": "A mitocôndria é associada principalmente à:",
                "options": ["digestão intracelular", "respiração celular", "fotossíntese", "síntese de proteínas"],
                "correct_index": 1,
                "skill": "Citologia",
                "difficulty": "facil",
                "explanation": "Mitocondrias participam da respiracao celular e produzem ATP.",
            },
            {
                "area": "Ciências Humanas",
                "stem": "A Revolução Industrial intensificou a urbanização porque:",
                "options": ["eliminou todas as fábricas", "concentrou empregos nas cidades", "proibiu o comércio", "reduziu a produção"],
                "correct_index": 1,
                "skill": "Industrialização e urbanização",
                "difficulty": "facil",
                "explanation": "A concentracao de fabricas e empregos atraiu trabalhadores para os centros urbanos.",
            },
            {
                "area": "Ciências Humanas",
                "stem": "No Brasil, a política do café com leite na Primeira República relacionava-se ao predomínio de elites de:",
                "options": ["São Paulo e Minas Gerais", "Amazonas e Pará", "Bahia e Pernambuco", "Rio Grande do Sul e Ceará"],
                "correct_index": 0,
                "skill": "Primeira República",
                "difficulty": "media",
                "explanation": "Cafe remete a Sao Paulo e leite a Minas Gerais, estados com forte influencia politica no periodo.",
            },
            {
                "area": "Ciências Humanas",
                "stem": "O conceito de cidadania envolve, além de deveres, o acesso a direitos:",
                "options": ["apenas privados", "civis, políticos e sociais", "somente comerciais", "exclusivos de governantes"],
                "correct_index": 1,
                "skill": "Cidadania",
                "difficulty": "facil",
                "explanation": "Cidadania inclui direitos civis, politicos e sociais, alem da participacao na vida coletiva.",
            },
        ]
        with self._get_connection() as conn:
            for item in samples:
                row = conn.execute(
                    "SELECT id FROM quiz_questions WHERE stem = ?", (item["stem"],)
                ).fetchone()
                options_json = json.dumps(item["options"], ensure_ascii=False)
                if row:
                    conn.execute(
                        """
                        UPDATE quiz_questions
                        SET area=?, options_json=?, correct_index=?,
                            explanation=COALESCE(NULLIF(explanation, ''), ?),
                            skill=COALESCE(NULLIF(skill, ''), ?),
                            difficulty=COALESCE(NULLIF(difficulty, ''), ?),
                            source=COALESCE(NULLIF(source, ''), ?)
                        WHERE id=?
                    """,
                        (
                            item["area"],
                            options_json,
                            int(item["correct_index"]),
                            item["explanation"],
                            item["skill"],
                            item["difficulty"],
                            "ENEM-like seed",
                            row[0],
                        ),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO quiz_questions
                        (area, stem, options_json, correct_index, explanation, skill, difficulty, source)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            item["area"],
                            item["stem"],
                            options_json,
                            int(item["correct_index"]),
                            item["explanation"],
                            item["skill"],
                            item["difficulty"],
                            "ENEM-like seed",
                        ),
                    )
            conn.commit()

    def start_quiz_attempt(self, area: str | None):
        with self._get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO quiz_attempts (area) VALUES (?)", (area,)
            )
            conn.commit()
            return cur.lastrowid

    def finish_quiz_attempt(self, attempt_id: int, score_pct: float):
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE quiz_attempts SET finished_at = CURRENT_TIMESTAMP, score_pct = ?
                WHERE id = ?
            """,
                (score_pct, attempt_id),
            )
            conn.commit()

    def add_quiz_answer(self, attempt_id, question_id, chosen_index, correct: int):
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO quiz_answers (attempt_id, question_id, chosen_index, correct)
                VALUES (?, ?, ?, ?)
            """,
                (attempt_id, question_id, chosen_index, correct),
            )
            conn.commit()

    def get_quiz_attempt(self, attempt_id: int):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM quiz_attempts WHERE id = ?", (attempt_id,)
            ).fetchone()
            return dict(row) if row else None

    def list_quiz_attempt_answers(self, attempt_id: int):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT
                    a.id AS answer_id,
                    a.attempt_id,
                    a.question_id,
                    a.chosen_index,
                    a.correct,
                    q.area,
                    q.stem,
                    q.options_json,
                    q.correct_index,
                    q.explanation,
                    q.skill,
                    q.difficulty,
                    q.source
                FROM quiz_answers a
                JOIN quiz_questions q ON q.id = a.question_id
                WHERE a.attempt_id = ?
                ORDER BY a.id
            """,
                (attempt_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def random_quiz_questions(self, n: int, area: str | None):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            if area:
                rows = conn.execute(
                    "SELECT * FROM quiz_questions WHERE area = ? ORDER BY RANDOM() LIMIT ?",
                    (area, n),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM quiz_questions ORDER BY RANDOM() LIMIT ?", (n,)
                ).fetchall()
            return [dict(r) for r in rows]

    _VALID_RESET_SECTIONS = ('finance', 'habits', 'study', 'tasks', 'workflows', 'all')

    def reset_data(self, section: str):
        """Limpa dados de uma sessão específica ou todos."""
        section = (section or "all").strip().lower()
        if section not in self._VALID_RESET_SECTIONS:
            raise ValueError(f"Seção inválida para reset: {section}. Válidas: {self._VALID_RESET_SECTIONS}")
        with self._get_connection() as conn:
            if section in ('finance', 'all'):
                conn.execute("DELETE FROM finance_transactions")
            if section in ('habits', 'all'):
                conn.execute("DELETE FROM habits")
                conn.execute("DELETE FROM habit_logs")
            if section in ('study', 'all'):
                conn.execute("DELETE FROM study_notes")
                conn.execute("DELETE FROM flashcards")
                conn.execute("DELETE FROM quiz_attempts")
                conn.execute("DELETE FROM quiz_answers")
                conn.execute("DELETE FROM study_stats")
            if section in ('tasks', 'all'):
                conn.execute("DELETE FROM tasks")
            if section in ('workflows', 'all'):
                conn.execute("DELETE FROM workflows")
            if section == 'all':
                conn.execute("DELETE FROM nexus_goals")
                conn.execute("DELETE FROM nexus_rewards")
                conn.execute("DELETE FROM reward_redemptions")
                conn.execute("UPDATE nexus_user SET xp=0, level=1, points=0 WHERE id=1")
            conn.commit()
        return True

    # --- Workflows ---

    def list_workflows(self):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM workflows ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]

    def add_workflow(self, name: str, description: str, steps_json: str, tags: str = None, risk_level: str = 'low'):
        with self._get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO workflows (name, description, steps_json, tags, risk_level) VALUES (?, ?, ?, ?, ?)",
                (name, description, steps_json, tags, risk_level),
            )
            conn.commit()
            return cur.lastrowid

    def get_workflow(self, workflow_id: int):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
            return dict(row) if row else None

    def update_workflow(self, workflow_id: int, name=None, description=None, steps_json=None, tags=None, risk_level=None):
        fields = []
        vals = []
        if name is not None:
            fields.append("name = ?")
            vals.append(str(name))
        if description is not None:
            fields.append("description = ?")
            vals.append(str(description))
        if steps_json is not None:
            fields.append("steps_json = ?")
            vals.append(str(steps_json))
        if tags is not None:
            fields.append("tags = ?")
            vals.append(str(tags))
        if risk_level is not None:
            fields.append("risk_level = ?")
            vals.append(str(risk_level))

        if not fields:
            return self.get_workflow(workflow_id)

        vals.append(workflow_id)
        with self._get_connection() as conn:
            conn.execute(f"UPDATE workflows SET {', '.join(fields)} WHERE id = ?", vals)
            conn.commit()
        return self.get_workflow(workflow_id)

    def delete_workflow(self, workflow_id: int):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
            conn.commit()

    def record_workflow_execution(self, workflow_id: int):
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE workflows SET last_executed = CURRENT_TIMESTAMP WHERE id = ?",
                (workflow_id,)
            )
            conn.commit()

    # ==========================================
    # HEALTH & FITNESS API
    # ==========================================
    def add_fitness_workout(self, w_type: str, duration: int, calories: int, notes: str = ""):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO fitness_workouts (type, duration_minutes, calories_burned, notes)
                VALUES (?, ?, ?, ?)
            """, (w_type, duration, calories, notes))
            conn.commit()
            return cur.lastrowid

    def list_fitness_workouts(self, limit: int = 50):
        with self._get_connection() as conn:
            conn.row_factory = dict_factory
            return conn.execute("""
                SELECT * FROM fitness_workouts ORDER BY date DESC, id DESC LIMIT ?
            """, (limit,)).fetchall()

    def add_fitness_metrics(self, weight: float, bf: float, calories: int, protein: int, notes: str = ""):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO fitness_metrics (weight, body_fat_percentage, calories_consumed, protein_grams, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (weight, bf, calories, protein, notes))
            conn.commit()
            return cur.lastrowid

    def get_latest_fitness_metrics(self):
        with self._get_connection() as conn:
            conn.row_factory = dict_factory
            return conn.execute("SELECT * FROM fitness_metrics ORDER BY date DESC, id DESC LIMIT 1").fetchone()
            
    def list_fitness_metrics(self, limit: int = 30):
        with self._get_connection() as conn:
            conn.row_factory = dict_factory
            return conn.execute("SELECT * FROM fitness_metrics ORDER BY date DESC, id DESC LIMIT ?", (limit,)).fetchall()

    # ==========================================
    # JOURNAL & MOOD API
    # ==========================================
    def add_journal_entry(self, content: str, psycho_feedback: str = ""):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO journal_entries (content, psychologist_feedback)
                VALUES (?, ?)
            """, (content, psycho_feedback))
            conn.commit()
            return cur.lastrowid

    def update_journal_feedback(self, entry_id: int, feedback: str):
        with self._get_connection() as conn:
            conn.execute("UPDATE journal_entries SET psychologist_feedback = ? WHERE id = ?", (feedback, entry_id))
            conn.commit()

    def list_journal_entries(self, limit: int = 20):
        with self._get_connection() as conn:
            conn.row_factory = dict_factory
            return conn.execute("SELECT * FROM journal_entries ORDER BY date DESC, id DESC LIMIT ?", (limit,)).fetchall()

    def add_mood_log(self, score: int, notes: str = ""):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO mood_logs (mood_score, notes)
                VALUES (?, ?)
            """, (score, notes))
            conn.commit()
            return cur.lastrowid
            
    def list_mood_logs(self, limit: int = 30):
        with self._get_connection() as conn:
            conn.row_factory = dict_factory
            return conn.execute("SELECT * FROM mood_logs ORDER BY date DESC, id DESC LIMIT ?", (limit,)).fetchall()

