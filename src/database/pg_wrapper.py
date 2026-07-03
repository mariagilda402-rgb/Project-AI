import re
import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

class PgCursorWrapper:
    def __init__(self, cursor):
        self._cursor = cursor
        self._lastrowid = None
        
    def execute(self, query, params=None):
        q = query.replace("?", "%s")
        
        # SQLite specific syntax translation
        if "INSERT OR IGNORE" in q:
            q = q.replace("INSERT OR IGNORE", "INSERT")
            q += " ON CONFLICT DO NOTHING"
            
        # Translate datetime/date
        q = re.sub(r"datetime\('now'.*?\)", "CURRENT_TIMESTAMP", q)
        q = re.sub(r"date\('now'.*?\)", "CURRENT_DATE", q)
        q = q.replace("datetime(f.next_review)", "f.next_review")

        if "CREATE TABLE" in q.upper():
            q = q.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
            q = q.replace("DATETIME", "TIMESTAMP")
            q = q.replace("REAL", "DOUBLE PRECISION")
            q = q.replace("(date('now', 'localtime'))", "CURRENT_DATE")
            
        # Add RETURNING id for INSERTs to support lastrowid
        is_insert = q.lstrip().upper().startswith("INSERT")
        if is_insert and "RETURNING id" not in q:
            q += " RETURNING id"
            
        # Convert params if necessary (e.g. lists to tuples for IN clauses)
        # But sqlite3 uses ? for each element, so params is just a tuple.
        if params is not None:
            self._cursor.execute(q, params)
        else:
            self._cursor.execute(q)
            
        if is_insert:
            try:
                row = self._cursor.fetchone()
                self._lastrowid = row[0] if row else None
            except Exception:
                self._lastrowid = None
                
    def fetchone(self): return self._cursor.fetchone()
    def fetchall(self): return self._cursor.fetchall()
    def fetchmany(self, size): return self._cursor.fetchmany(size)
    def close(self): self._cursor.close()
    
    @property
    def lastrowid(self):
        return self._lastrowid
        
class PgConnectionWrapper:
    def __init__(self, dsn):
        self.conn = psycopg2.connect(dsn)
        self.is_postgres = True
        
    def __enter__(self):
        self.conn.__enter__()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.conn.__exit__(exc_type, exc_val, exc_tb)
        
    def cursor(self):
        return PgCursorWrapper(self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor))
        
    def execute(self, query, params=None):
        cur = self.cursor()
        cur.execute(query, params)
        return cur
        
    def commit(self): self.conn.commit()
    def rollback(self): self.conn.rollback()
    def close(self): self.conn.close()
    
    @property
    def row_factory(self): return None
    @row_factory.setter
    def row_factory(self, value): pass

def get_connection(db_path):
    pg_url = os.getenv("SUPABASE_DB_URL")
    if pg_url:
        return PgConnectionWrapper(pg_url)
    import sqlite3
    return sqlite3.connect(db_path, check_same_thread=False)
