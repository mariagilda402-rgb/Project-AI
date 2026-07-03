import sqlite3
import json
from pathlib import Path
from datetime import datetime, date, timedelta



class NexusAnalyticsDBMixin:
    def get_user_stats(self):
        with self._get_connection() as conn:
            row = conn.execute("SELECT xp, level, points FROM nexus_user WHERE id = 1").fetchone()
            if row:
                return {"xp": row[0], "level": row[1], "points": row[2]}
            return None

