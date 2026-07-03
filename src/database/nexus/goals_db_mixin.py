import sqlite3
import json
from pathlib import Path
from datetime import datetime, date, timedelta



class NexusGoalsDBMixin:
    def buy_reward(self, reward_id: int) -> bool:
        """Tentativa de compra de um item. Retorna True se sucesso, False se saldo insuficiente."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT cost FROM nexus_rewards WHERE id = ?", (reward_id,))
            reward = cur.fetchone()
            if not reward:
                return False
            cost = reward["cost"]

            cur.execute("SELECT points FROM nexus_user WHERE id = 1")
            user = cur.fetchone()
            if not user or user["points"] < cost:
                return False
            
            # Deduct points
            cur.execute("UPDATE nexus_user SET points = points - ? WHERE id = 1", (cost,))
            
            # Record redemption
            from datetime import datetime
            d = datetime.now().isoformat()
            cur.execute(
                "INSERT INTO reward_redemptions (redemption_date, reward_id) VALUES (?, ?)",
                (d, reward_id),
            )
            return True

    def add_reward_redemption(self, reward_id: int, d: str):
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO reward_redemptions (redemption_date, reward_id) VALUES (?, ?)",
                (d, reward_id),
            )
            conn.commit()

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

