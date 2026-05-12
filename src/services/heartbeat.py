"""
Heartbeat Service — Inspirado no OmniBot heartbeat_service.
Periodicamente consolida logs e interações recentes na memória de longo prazo.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, date
from pathlib import Path


DAILY_LOGS_DIR = Path("data/logs/daily")
DAILY_LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _today_log_path() -> Path:
    return DAILY_LOGS_DIR / f"{date.today().isoformat()}.md"


def append_daily_log(entry: str) -> None:
    """Adiciona uma entrada ao log diário."""
    path = _today_log_path()
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"- [{timestamp}] {entry.strip()}\n"
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        print(f"[Heartbeat] ⚠️ Falha ao salvar log diário: {e}")


def read_recent_logs(max_lines: int = 50) -> str:
    """Lê as entradas mais recentes dos logs diários."""
    logs = sorted(DAILY_LOGS_DIR.glob("*.md"), reverse=True)[:3]  # Últimos 3 dias
    lines = []
    for log_file in reversed(logs):
        try:
            content = log_file.read_text(encoding="utf-8").strip()
            if content:
                lines.append(f"## {log_file.stem}")
                file_lines = content.splitlines()[-max_lines:]
                lines.extend(file_lines)
        except Exception:
            continue
    return "\n".join(lines) if lines else "(Sem logs recentes)"


def cleanup_old_logs(keep_days: int = 14) -> int:
    """Remove logs com mais de N dias."""
    cutoff = date.today().toordinal() - keep_days
    removed = 0
    for log_file in DAILY_LOGS_DIR.glob("*.md"):
        try:
            log_date = date.fromisoformat(log_file.stem)
            if log_date.toordinal() < cutoff:
                log_file.unlink()
                removed += 1
        except (ValueError, Exception):
            continue
    return removed


class HeartbeatService:
    """
    Serviço que roda em background e periodicamente consolida
    os logs diários na memória estruturada de longo prazo.
    """

    def __init__(self, interval_minutes: int = 30, llm_service=None):
        self.interval_minutes = max(5, interval_minutes)
        self.llm_service = llm_service
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="HeartbeatService"
        )
        self._thread.start()
        print(f"[Heartbeat] ✅ Iniciado (intervalo: {self.interval_minutes}min)")

    def stop(self) -> None:
        self._running = False
        print("[Heartbeat] 🔴 Parado")

    def _loop(self) -> None:
        while self._running:
            try:
                time.sleep(self.interval_minutes * 60)
                if not self._running:
                    break
                self._run_consolidation()
                cleanup_old_logs()
            except Exception as e:
                print(f"[Heartbeat] ⚠️ Erro no loop: {e}")
                time.sleep(30)

    def _run_consolidation(self) -> None:
        """Consolida logs recentes na memória estruturada."""
        if not self.llm_service:
            return

        recent_logs = read_recent_logs(max_lines=30)
        if not recent_logs or recent_logs == "(Sem logs recentes)":
            return

        from src.memory.structured_memory import (
            load_structured_memory,
            format_memory_for_prompt,
            update_structured_memory,
        )

        current_memory = format_memory_for_prompt()

        prompt = (
            f"Você é o módulo de consolidação de memória da Assistente Virtual.\n"
            f"Analise os logs recentes e a memória atual. Extraia NOVOS fatos que devem ser memorizados.\n"
            f"Retorne APENAS JSON válido. Use {{}} se nada novo for encontrado.\n\n"
            f"MEMÓRIA ATUAL:\n{current_memory}\n\n"
            f"LOGS RECENTES:\n{recent_logs}\n\n"
            f"Categorias: identity, preferences, projects, relationships, wishes, notes\n"
            f"Formato: {{\"categoria\": {{\"chave\": {{\"value\": \"valor\"}}}}}}\n\n"
            f"JSON com NOVOS fatos (apenas o que ainda não está na memória):"
        )

        try:
            import re
            import json

            response = self.llm_service.chat(
                system_prompt="Extrator de informações. Responda APENAS com JSON válido.",
                messages=[{"role": "user", "content": prompt}]
            )
            if not response:
                return

            raw = re.sub(r"```(?:json)?", "", response).strip().rstrip("`").strip()
            if raw and raw != "{}":
                data = json.loads(raw)
                if data:
                    update_structured_memory(data)
                    print(f"[Heartbeat] 💾 Memória consolidada: {list(data.keys())}")

        except Exception as e:
            print(f"[Heartbeat] ⚠️ Consolidação falhou: {e}")

    def force_consolidation(self) -> str:
        """Força uma consolidação imediata (para uso manual)."""
        try:
            self._run_consolidation()
            return "Consolidação de memória executada com sucesso."
        except Exception as e:
            return f"Erro na consolidação: {e}"
