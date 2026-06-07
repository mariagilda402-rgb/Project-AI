import sys
sys.path.append(r'd:\Documentos\Projeto AI')
from src.database.pg_wrapper import get_connection

def setup_videos_table():
    conn = get_connection(r'd:\Documentos\Projeto AI\data\nexus.db')
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS nexus_videos (
                id SERIAL PRIMARY KEY,
                url TEXT NOT NULL,
                title TEXT,
                platform TEXT DEFAULT 'youtube',
                xp_reward INTEGER DEFAULT 50,
                is_watched INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        print("Videos table created successfully.")
    except Exception as e:
        print("Error:", e)
        conn.rollback()

if __name__ == '__main__':
    setup_videos_table()
