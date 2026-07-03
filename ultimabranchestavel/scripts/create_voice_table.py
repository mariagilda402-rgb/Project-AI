import sys
sys.path.append(r'd:\Documentos\Projeto AI')
from src.database.pg_wrapper import get_connection

def setup_voice_table():
    conn = get_connection(r'd:\Documentos\Projeto AI\data\nexus.db')
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS voice_profiles (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                access_level INTEGER DEFAULT 1,
                embedding BYTEA
            )
        """)
        # Insert admin
        cur.execute("INSERT INTO voice_profiles (name, access_level) VALUES (%s, %s) ON CONFLICT DO NOTHING", ('Jean', 5))
        conn.commit()
        print("Voice profiles table created and admin inserted.")
    except Exception as e:
        print("Error:", e)
        conn.rollback()

if __name__ == '__main__':
    setup_voice_table()
