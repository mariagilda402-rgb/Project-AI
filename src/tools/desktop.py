from __future__ import annotations

import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path

from .base import ToolResult


class DesktopAutomationTool:
    name = "desktop_automation"
    description = "Abre apps, websites e cria alarmes locais."
    critical = True

    def __init__(self, alarm_path: str = "data/alarms.txt") -> None:
        self.alarm_path = Path(alarm_path)
        self.alarm_path.parent.mkdir(parents=True, exist_ok=True)

    def run_open_app(self, name: str) -> ToolResult:
        name = (name or "").strip()
        if not name:
            return ToolResult(False, "Nome do aplicativo vazio.")
        try:
            subprocess.Popen(["cmd", "/c", "start", "", name], shell=False)  # nosec B603
            return ToolResult(True, f"Comando enviado para abrir: {name}.")
        except OSError as exc:
            return ToolResult(False, f"Nao consegui abrir o app: {exc}")

    def run(self, command: str) -> ToolResult:
        lowered = command.lower()
        if "abra o bloco de notas" in lowered or "abrir bloco de notas" in lowered:
            subprocess.Popen(["notepad.exe"])  # nosec B603
            return ToolResult(True, "Bloco de notas aberto.")

        if "abra o navegador" in lowered or "abrir navegador" in lowered:
            url = "https://www.google.com"
            # tenta extrair a url
            parts = command.split(" ", 3)
            if len(parts) >= 4 and "://" in parts[3]:
                url = parts[3].strip()
            elif "://" in command:
                for word in command.split():
                    if "://" in word:
                        url = word.strip()
                        break
            webbrowser.open(url)
            return ToolResult(True, f"Navegador aberto em: {url}")

        if "pesquisar no navegador:" in lowered or "buscar no google:" in lowered:
            query = command.split(":", 1)[1].strip()
            if query:
                from urllib.parse import quote_plus
                url = f"https://www.google.com/search?q={quote_plus(query)}"
                webbrowser.open(url)
                return ToolResult(True, f"Navegador aberto pesquisando por: {query}")
            
        if "alarme" in lowered:
            hhmm = self._extract_time(lowered)
            if not hhmm:
                return ToolResult(False, "Nao consegui identificar o horario do alarme.")
            self.alarm_path.write_text(
                self.alarm_path.read_text(encoding="utf-8") + f"{hhmm}\n"
                if self.alarm_path.exists()
                else f"{hhmm}\n",
                encoding="utf-8",
            )
            return ToolResult(True, f"Alarme registrado para {hhmm}.")

        return ToolResult(False, "Comando desktop nao suportado ainda.")

    @staticmethod
    def _extract_time(command: str) -> str:
        digits = [token for token in command.replace("h", ":").split() if ":" in token]
        for item in digits:
            try:
                dt = datetime.strptime(item.strip(".,;"), "%H:%M")
                return dt.strftime("%H:%M")
            except ValueError:
                continue
        return ""
