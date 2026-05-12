import sqlite3
import json
from pathlib import Path
from datetime import datetime

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

            # 5. STRATEGY PRESETS
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lifestyle_presets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    config_json TEXT NOT NULL, -- Full snapshot of habits/goals
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

            # 9. LIFESTYLE PRESETS
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lifestyle_presets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    config_json TEXT NOT NULL,
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
    def log_habit_completion(self, habit_id):
        """Registra a conclusão de um hábito e atualiza a streak."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 1. Registra o log
            cursor.execute("INSERT INTO habit_logs (habit_id) VALUES (?)", (habit_id,))
            
            # 2. Atualiza a streak (lógica simplificada: +1 se hoje)
            # Nota: Em um sistema real, checaríamos se o último log foi ontem
            cursor.execute("UPDATE habits SET current_streak = current_streak + 1 WHERE id = ?", (habit_id,))
            
            # 3. Atualiza recorde máximo se necessário
            cursor.execute("UPDATE habits SET max_streak = current_streak WHERE id = ? AND current_streak > max_streak", (habit_id,))
            conn.commit()

    def get_habits(self):
        """Retorna a lista de hábitos e suas estatísticas."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM habits WHERE active = 1").fetchall()
            return [dict(r) for r in rows]

    def get_user_stats(self):
        with self._get_connection() as conn:
            row = conn.execute("SELECT xp, level, points FROM nexus_user WHERE id = 1").fetchone()
            if row:
                return {"xp": row[0], "level": row[1], "points": row[2]}
            return None

    def add_transaction(self, t_type, amount, category, description, necessity):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO finance_transactions (type, amount, category, description, necessity_score)
                VALUES (?, ?, ?, ?, ?)
            """, (t_type, amount, category, description, necessity))
            conn.commit()
