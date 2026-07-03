"""
Ferramenta para criar novas skills (ferramentas) dinamicamente.
"""

import os
import json
import re
from pathlib import Path
from typing import Any

from src.tools.base import BaseTool

SKILL_CREATOR_PROMPT = """Você é um Desenvolvedor Python especialista.
O objetivo é criar uma nova 'Tool' (ferramenta/skill) para o assistente Jarvis.
Objetivo da Tool: {goal}

Retorne APENAS um objeto JSON com o seguinte formato:
{{
  "file_name": "nome_da_tool.py",
  "content": "código fonte completo da tool em Python"
}}

Regras do código da Tool:
1. Deve herdar de `BaseTool` (from src.tools.base import BaseTool).
2. Deve implementar os métodos/propriedades `name`, `description`, `parameters` (se precisar) e `execute(self, args: dict, context: dict = None) -> str`.
3. Para acessar o LLM, use `llm = context.get('llm')`.
4. O código deve ser seguro, tratar erros com try/except e retornar strings claras.
5. Se precisar de imports adicionais, inclua-os no topo.
6. NUNCA use markdown no valor do JSON. Responda APENAS com o JSON válido.
"""

class SkillCreatorTool(BaseTool):
    @property
    def name(self) -> str:
        return "create_skill"

    @property
    def description(self) -> str:
        return (
            "Cria uma nova habilidade/ferramenta (código Python) para o Jarvis dinamicamente. "
            "Use quando o usuário pedir para você 'aprender', 'criar uma ferramenta' ou 'fazer uma skill'."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "Descrição clara do que a nova ferramenta deve fazer."
                }
            },
            "required": ["goal"]
        }

    def execute(self, args: dict[str, Any], context: dict[str, Any] = None) -> str:
        goal = args.get("goal")
        if not goal:
            return "O objetivo da skill é obrigatório."
            
        llm = context.get("llm") if context else None
        if not llm:
            try:
                from src.services.llm import _global_llm_instance
                llm = _global_llm_instance
            except ImportError:
                pass
                
        if not llm:
            return "Erro: LLM não disponível para o Skill Creator."

        registry = context.get("registry") if context else None

        print(f"[SkillCreator] 🧠 Projetando nova skill: {goal}")
        
        prompt = SKILL_CREATOR_PROMPT.format(goal=goal)
        
        try:
            response = llm.chat(
                system_prompt="Você é um expert Python dev. Responda apenas com JSON válido.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Limpa markdown do JSON
            text = response.strip()
            text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
            
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                match = re.search(r"\{.*\}", text, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                else:
                    return f"Falha ao gerar a skill (JSON inválido): {text[:200]}..."
            
            file_name = data.get("file_name", "nova_skill.py")
            if not file_name.endswith(".py"):
                file_name += ".py"
            content = data.get("content", "")
            
            if not content:
                return "Nenhum código gerado pelo LLM."
                
            skills_dir = Path("src/skills")
            skills_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = skills_dir / file_name
            file_path.write_text(content, encoding="utf-8")
            
            msg = f"Skill '{file_name}' criada com sucesso em src/skills/!"
            
            # Tentativa de carregar a skill dinamicamente no mesmo momento
            if registry:
                try:
                    import importlib.util
                    import sys
                    
                    module_name = f"src.skills.{file_path.stem}"
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[module_name] = module
                        spec.loader.exec_module(module)
                        
                        loaded = False
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if isinstance(attr, type) and issubclass(attr, BaseTool) and attr is not BaseTool:
                                if attr.__module__ == module_name:
                                    tool_instance = attr()
                                    # Adiciona a ferramenta no registry ativo
                                    registry.tools.append(tool_instance)
                                    msg += f" Ferramenta '{tool_instance.name}' carregada em tempo real."
                                    loaded = True
                                    break
                        if not loaded:
                            msg += " Nenhuma classe válida (herdando de BaseTool) foi encontrada no arquivo."
                except Exception as load_err:
                    msg += f" Aviso: A skill foi criada, mas ocorreu um erro ao carregá-la: {load_err} (Pode exigir reinicialização)."
            else:
                msg += " O ToolRegistry não estava disponível no contexto para carregar a skill dinamicamente. Necessário reiniciar."

            return msg

        except Exception as e:
            return f"Erro durante a execução do Skill Creator: {e}"
