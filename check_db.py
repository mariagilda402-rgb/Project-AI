import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
dsn = os.environ.get('SUPABASE_DB_URL')
conn = psycopg2.connect(dsn)
cur = conn.cursor()
try:
    cur.execute("SELECT * FROM sqlite_master LIMIT 1")
    print("sqlite_master exists")
except Exception as e:
    print(f"Error: {e}")
