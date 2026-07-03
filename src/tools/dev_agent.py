"""
Dev Agent Tool — Inspirado no Mark-XXXV.
Ferramenta para criar projetos multi-arquivo inteiros a partir de um único prompt.
"""

import json
import os
import re
from pathlib import Path
from typing import Any

from src.tools.base import BaseTool

DEV_AGENT_PROMPT = """Você é um Engenheiro de Software sênior autônomo.
O usuário quer criar um novo projeto.
Objetivo: {goal}

Crie a estrutura completa do projeto.
Retorne APENAS um objeto JSON válido com o seguinte formato:
{{
  "project_name": "nome_da_pasta",
  "files": [
    {{
      "path": "caminho/do/arquivo.py",
      "content": "codigo fonte completo"
    }},
    {{
      "path": "README.md",
      "content": "Instruções de como rodar"
    }}
  ],
  "install_commands": [
    "npm install" ou "pip install -r requirements.txt"
  ]
}}

Regras:
1. NUNCA use marcadores Markdown fora dos valores das strings no JSON.
2. Todo o código deve estar completo e pronto para rodar.
3. Se for web, inclua index.html, script.js, style.css ou o framework pedido.
4. Se for Python, inclua requirements.txt.
"""

class DevAgentTool(BaseTool):
    @property
    def name(self) -> str:
        return "dev_agent"

    @property
    def description(self) -> str:
        return (
            "Cria projetos completos de programação (vários arquivos ao mesmo tempo, "
            "estrutura de pastas, etc). Use quando o usuário pedir 'crie um app', "
            "'crie um site', 'faça um projeto de X'."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "A descrição detalhada do projeto que deve ser construído."
                },
                "destination": {
                    "type": "string",
                    "description": "Pasta de destino (opcional, padrão: Desktop)"
                }
            },
            "required": ["goal"]
        }

    def execute(self, args: dict[str, Any], context: dict[str, Any] = None) -> str:
        goal = args.get("goal")
        if not goal:
            return "O objetivo do projeto é obrigatório."
            
        destination = args.get("destination", "").strip()
        
        llm = context.get("llm") if context else None
        if not llm:
            try:
                from src.services.llm import _global_llm_instance
                llm = _global_llm_instance
            except ImportError:
                pass
                
        if not llm:
            return "Erro: LLM não disponível para o Dev Agent."

        print(f"[DevAgent] 🛠️ Projetando: {goal}")
        
        prompt = DEV_AGENT_PROMPT.format(goal=goal)
        
        try:
            response = llm.chat(
                system_prompt="Você é um expert software architect. Responda apenas com JSON.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Limpa markdown do JSON
            text = response.strip()
            text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
            
            try:
                project_data = json.loads(text)
            except json.JSONDecodeError:
                # Fallback tenta achar o json dentro do texto
                match = re.search(r"\{.*\}", text, re.DOTALL)
                if match:
                    project_data = json.loads(match.group(0))
                else:
                    return f"Falha ao gerar o projeto (JSON inválido retornado):\n{text[:500]}..."
            
            project_name = project_data.get("project_name", "novo_projeto")
            files = project_data.get("files", [])
            install_cmds = project_data.get("install_commands", [])
            
            if not files:
                return "Nenhum arquivo gerado pelo LLM."
                
            # Define o path base
            if destination:
                base_path = Path(destination)
                if not base_path.is_absolute():
                    base_path = Path.home() / "Desktop" / destination
            else:
                base_path = Path.home() / "Desktop" / project_name
                
            base_path.mkdir(parents=True, exist_ok=True)
            
            created_files = []
            for f in files:
                fpath = f.get("path")
                content = f.get("content", "")
                if fpath:
                    full_path = base_path / fpath
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content, encoding="utf-8")
                    created_files.append(fpath)
            
            # Executa comandos de instalação se houver e for seguro? 
            # O ideal é apenas avisar o usuário para executar.
            install_instructions = ""
            if install_cmds:
                install_instructions = "\nPara instalar as dependências, rode:\n" + "\n".join(f"cd {base_path} && {cmd}" for cmd in install_cmds)
                
            return f"Projeto '{project_name}' gerado com sucesso em: {base_path}\nArquivos criados: {', '.join(created_files)}\n{install_instructions}"

        except Exception as e:
            return f"Erro durante a execução do Dev Agent: {e}"
