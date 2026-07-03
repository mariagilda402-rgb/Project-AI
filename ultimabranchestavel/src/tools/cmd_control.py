"""
CMD Control Tool — Inspirado no Mark-XXXV.
Converte linguagem natural em comandos PowerShell com verificações rigorosas de segurança.
"""

import subprocess
import os
from typing import Any
from pathlib import Path

from src.tools.base import BaseTool

BLOCKLIST = {
    "rm -rf", "del /f /s /q", "format", "diskpart", "shutdown", "restart", "logoff",
    "del *.*", "erase *.*", "attrib -r -s -h", "vssadmin delete shadows", "bcdedit",
    "reg delete", "net user", "icacls", "takeown", "wget", "curl", "Invoke-WebRequest"
}

CMD_PROMPT = """Você é um especialista em terminal Windows (PowerShell/CMD).
O usuário quer executar uma ação no sistema operacional: {intent}
Converta isso para o comando exato de PowerShell correspondente.
Regras:
1. Retorne APENAS o comando, nada mais. Sem backticks, sem markdown.
2. Se a ação for destrutiva ou perigosa (deletar pastas importantes, formatar, etc), retorne a palavra: BLOCKED.
3. Use comandos que funcionem no PowerShell do Windows.
"""

class CmdControlTool(BaseTool):
    @property
    def name(self) -> str:
        return "cmd_control"

    @property
    def description(self) -> str:
        return (
            "Executa ações avançadas no sistema operacional Windows via linha de comando. "
            "Pode ser usado para listar processos pesados, fechar portas de rede, gerenciar serviços, etc. "
            "Traduza a intenção do usuário em linguagem natural. A ferramenta gera e roda o comando com segurança."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "description": "O que você quer que o terminal faça (ex: 'liste processos que mais usam RAM', 'mate o processo do chrome', 'limpe o cache de DNS')."
                }
            },
            "required": ["intent"]
        }

    def _is_safe(self, command: str) -> bool:
        cmd_lower = command.lower()
        if "blocked" in cmd_lower:
            return False
        for blocked_word in BLOCKLIST:
            if blocked_word in cmd_lower:
                return False
        return True

    def execute(self, args: dict[str, Any], context: dict[str, Any] = None) -> str:
        intent = args.get("intent", "").strip()
        if not intent:
            return "Intenção não especificada."

        llm = context.get("llm") if context else None
        if not llm:
            try:
                from src.services.llm import _global_llm_instance
                llm = _global_llm_instance
            except ImportError:
                pass
                
        if not llm:
            return "Erro: LLM não disponível para gerar o comando."

        try:
            prompt = CMD_PROMPT.format(intent=intent)
            command = llm.chat(
                system_prompt="Você é um expert Windows admin. Retorne apenas o comando.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            command = command.strip().replace("```powershell", "").replace("```", "").strip()
            
            if not self._is_safe(command):
                return f"Comando bloqueado por motivos de segurança: {command}"
                
            print(f"[CmdControl] ⚠️ Executando: {command}")
            
            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True,
                text=True,
                timeout=15,
                encoding="utf-8",
                errors="replace"
            )
            
            output = ""
            if result.stdout:
                output += result.stdout.strip()
            if result.stderr:
                output += f"\nErro: {result.stderr.strip()}"
                
            if not output:
                output = "Comando executado sem retorno visual."
                
            return f"Comando executado: {command}\n\nSaída:\n{output[:1500]}"
            
        except subprocess.TimeoutExpired:
            return "O comando demorou muito para responder e foi cancelado (timeout 15s)."
        except Exception as e:
            return f"Erro ao executar comando: {e}"
