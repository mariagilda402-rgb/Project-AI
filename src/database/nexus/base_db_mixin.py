import sqlite3
import json
from pathlib import Path
from datetime import datetime, date, timedelta



class NexusBaseDBMixin:
    def _get_connection(self):
        from src.database.pg_wrapper import get_connection
        return get_connection(self.db_path)

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
            """)
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

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS voice_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    access_level INTEGER DEFAULT 1,
                    voice_embedding TEXT, -- JSON array of floats
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 11. NEW PHASE 1 TABLES
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS finance_budgets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    monthly_limit REAL NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS finance_investments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    type TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    avg_price REAL NOT NULL,
                    currency TEXT DEFAULT 'BRL',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS finance_goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    target_amount REAL NOT NULL,
                    current_amount REAL DEFAULT 0,
                    target_date DATE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workout_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    days_per_week INTEGER,
                    focus TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workout_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id INTEGER,
                    date DATE DEFAULT (date('now', 'localtime')),
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(plan_id) REFERENCES workout_plans(id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workout_sets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    exercise_name TEXT NOT NULL,
                    sets INTEGER,
                    reps INTEGER,
                    weight REAL,
                    rpe REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cron_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    schedule TEXT NOT NULL,
                    command TEXT NOT NULL,
                    active INTEGER DEFAULT 1,
                    last_run DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS calendar_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    date DATE,
                    time TEXT,
                    duration_minutes INTEGER,
                    reminder_minutes INTEGER,
                    google_event_id TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workout_sets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    exercise TEXT NOT NULL,
                    sets INTEGER,
                    reps INTEGER,
                    weight_kg REAL,
                    rpe REAL,
                    FOREIGN KEY(session_id) REFERENCES workout_sessions(id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nutrition_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE DEFAULT (date('now', 'localtime')),
                    meal_name TEXT,
                    calories INTEGER,
                    protein_g INTEGER,
                    carbs_g INTEGER,
                    fat_g INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS body_measurements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE DEFAULT (date('now', 'localtime')),
                    weight_kg REAL,
                    body_fat_pct REAL,
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cron_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    schedule TEXT NOT NULL,
                    command TEXT NOT NULL,
                    active INTEGER DEFAULT 1,
                    last_run DATETIME,
                    next_run DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS calendar_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    event_date DATE NOT NULL,
                    event_time TEXT,
                    duration_minutes INTEGER,
                    reminder_minutes INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            self._migrate_schema(conn)

    def _migrate_schema(self, conn):
        if getattr(conn, 'is_postgres', False):
            return

        def cols(table):
            cur.execute(f"PRAGMA table_info({table})")
            return {row[1] for row in cur.fetchall()}
        cur = conn.cursor()

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

        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='voice_profiles'"
        )
        if not cur.fetchone():
            cur.execute("""
                CREATE TABLE voice_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    access_level INTEGER DEFAULT 1,
                    voice_embedding TEXT, -- JSON array of floats
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

        conn.commit()

    def add_xp(self, amount):
        with self._get_connection() as conn:
            # 1. Adiciona XP e Pontos
            conn.execute("UPDATE nexus_user SET xp = xp + ?, points = points + ? WHERE id = 1", (amount, amount))

            # 2. Recalcula Level (Fórmula: 1 + XP / 1000)
            conn.execute("UPDATE nexus_user SET level = 1 + (xp / 1000) WHERE id = 1")
            conn.commit()

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

    def count_redemptions_on_date(self, d: str) -> int:
        with self._get_connection() as conn:
            r = conn.execute(
                "SELECT COUNT(*) FROM reward_redemptions WHERE redemption_date = ?",
                (d,),
            ).fetchone()
            return int(r[0] or 0)

    def get_shop_items(self):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, name, cost, description FROM nexus_rewards")
            return [dict(row) for row in cur.fetchall()]

    def add_video(self, url: str, title: str = "", platform: str = "youtube", xp_reward: int = 50):
        with self._get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO nexus_videos (url, title, platform, xp_reward) VALUES (?, ?, ?, ?)",
                (url, title, platform, xp_reward)
            )
            conn.commit()
            return cur.lastrowid

    def list_videos(self):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM nexus_videos ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]

    def mark_video_watched(self, video_id: int):
        with self._get_connection() as conn:
            conn.execute("UPDATE nexus_videos SET is_watched = 1 WHERE id = ?", (video_id,))
            conn.commit()

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

