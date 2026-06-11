import threading
import time
import os
import sqlite3
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

TABLES_TO_SYNC = [
    "nexus_user",
    "habits",
    "tasks",
    "finance_transactions",
    "nexus_rewards",
    "study_notes",
    "nexus_goals",
    "fitness_workouts"
]

class SyncService:
    def __init__(self, sqlite_path="data/nexus.db"):
        self.sqlite_path = sqlite_path
        self.pg_url = os.getenv("SUPABASE_DB_URL")
        self.sync_interval = 60  # seconds
        self._stop_event = threading.Event()
        self.thread = None

    def start(self):
        if not self.pg_url:
            print("[SyncService] SUPABASE_DB_URL not found. Offline mode active.")
            return
            
        self.thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.thread.start()
        print("[SyncService] Started background sync thread.")

    def stop(self):
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)

    def _sync_loop(self):
        while not self._stop_event.is_set():
            try:
                self.perform_sync()
            except Exception as e:
                print(f"[SyncService] Error during sync: {e}")
            self._stop_event.wait(self.sync_interval)

    def perform_sync(self):
        # 1. Connect to local SQLite
        with sqlite3.connect(self.sqlite_path) as local_conn:
            local_conn.row_factory = sqlite3.Row
            # Try to get last sync time
            local_cur = local_conn.cursor()
            local_cur.execute("CREATE TABLE IF NOT EXISTS sync_meta (key TEXT PRIMARY KEY, value TEXT)")
            row = local_cur.execute("SELECT value FROM sync_meta WHERE key = 'last_sync'").fetchone()
            last_sync = row["value"] if row else "1970-01-01 00:00:00"

            # 2. Connect to remote Supabase via psycopg2
            with psycopg2.connect(self.pg_url) as remote_conn:
                remote_cur = remote_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                
                new_last_sync = last_sync

                for table in TABLES_TO_SYNC:
                    # Pull from remote
                    remote_cur.execute(f"SELECT * FROM {table} WHERE updated_at > %s ORDER BY updated_at ASC", (last_sync,))
                    remote_changes = remote_cur.fetchall()
                    
                    for r_row in remote_changes:
                        remote_dict = dict(r_row)
                        # Check local version
                        local_row = local_cur.execute(f"SELECT * FROM {table} WHERE id = ?", (remote_dict["id"],)).fetchone()
                        
                        if not local_row or str(remote_dict.get("updated_at", "")) > str(local_row.get("updated_at", "")):
                            # Upsert local
                            cols = list(remote_dict.keys())
                            vals = list(remote_dict.values())
                            placeholders = ",".join(["?"] * len(cols))
                            
                            update_cols = ",".join([f"{c} = EXCLUDED.{c}" for c in cols])
                            # SQLite UPSERT
                            local_cur.execute(f"""
                                INSERT INTO {table} ({','.join(cols)})
                                VALUES ({placeholders})
                                ON CONFLICT(id) DO UPDATE SET {update_cols}
                            """, vals)
                            if str(remote_dict.get("updated_at", "")) > new_last_sync:
                                new_last_sync = str(remote_dict.get("updated_at", ""))

                    # Push to remote
                    local_changes = local_cur.execute(f"SELECT * FROM {table} WHERE updated_at > ?", (last_sync,)).fetchall()
                    for l_row in local_changes:
                        local_dict = dict(l_row)
                        remote_cur.execute(f"SELECT updated_at FROM {table} WHERE id = %s", (local_dict["id"],))
                        r_row = remote_cur.fetchone()
                        
                        if not r_row or str(local_dict.get("updated_at", "")) > str(r_row["updated_at"]):
                            # Upsert remote
                            cols = list(local_dict.keys())
                            vals = list(local_dict.values())
                            placeholders = ",".join(["%s"] * len(cols))
                            update_cols = ",".join([f"{c} = EXCLUDED.{c}" for c in cols])
                            
                            remote_cur.execute(f"""
                                INSERT INTO {table} ({','.join(cols)})
                                VALUES ({placeholders})
                                ON CONFLICT (id) DO UPDATE SET {update_cols}
                            """, vals)
                            if str(local_dict.get("updated_at", "")) > new_last_sync:
                                new_last_sync = str(local_dict.get("updated_at", ""))

            # Save new last_sync
            if new_last_sync > last_sync:
                local_cur.execute("INSERT INTO sync_meta (key, value) VALUES ('last_sync', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (new_last_sync,))
                local_conn.commit()

# Expose a singleton instance
_sync_service = SyncService()
def start_sync():
    _sync_service.start()
