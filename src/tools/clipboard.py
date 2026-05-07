"""Leitura e escrita no clipboard do Windows (sem dependencias extras)."""
from __future__ import annotations

import logging
import subprocess

from .base import ToolResult

logger = logging.getLogger(__name__)


class ClipboardTool:
    name = "clipboard"
    description = "Le e escreve no clipboard do Windows."
    critical = False

    def read(self) -> ToolResult:
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Get-Clipboard"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            content = (result.stdout or "").strip()
            if not content:
                return ToolResult(True, "(Clipboard vazio)")
            return ToolResult(True, f"Conteudo do clipboard:\n{content}")
        except Exception as exc:
            return ToolResult(False, f"Erro ao ler clipboard: {exc}")

    def write(self, text: str) -> ToolResult:
        if not text:
            return ToolResult(False, "Texto vazio para clipboard.")
        try:
            # Usa clip.exe via stdin para evitar problemas com caracteres especiais.
            subprocess.run(
                ["clip"],
                input=text,
                text=True,
                timeout=5,
                check=True,
            )
            return ToolResult(True, f"Texto copiado para o clipboard ({len(text)} caracteres).")
        except Exception as exc:
            return ToolResult(False, f"Erro ao escrever no clipboard: {exc}")

    def run(self, command: str) -> ToolResult:
        lowered = (command or "").lower()
        if any(kw in lowered for kw in ("ler", "read", "conteudo", "conteúdo", "ver", "mostrar")):
            return self.read()
        return self.write(command)
