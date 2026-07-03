import json
from typing import List, Dict, Any
from src.tools.base import Tool, ToolResult
from src.database.nexus_db import NexusDatabase
from src.tools.app_manager import _enum_visible_windows

class WorkflowTool(Tool):
    name = "workflow"
    description = "Grava, edita e executa workflows (modos) compostos por ações no sistema e comandos de janelas. Use comandos textuais ou estruturados. Formatos esperados: 'save|nome|descricao', 'run|nome', 'list'"
    critical = False

    def __init__(self):
        self.db = NexusDatabase()

    def run(self, command: str) -> ToolResult:
        cmd = (command or "").strip()
        if not cmd:
            return ToolResult(False, "Comando vazio.")

        if "|" in cmd:
            parts = [p.strip() for p in cmd.split("|", 2)]
        else:
            parts = [cmd]

        action = parts[0].lower()

        if action == "list":
            wfs = self.db.list_workflows()
            if not wfs:
                return ToolResult(True, "Nenhum workflow salvo.")
            lines = [f"- {w['name']} (ID: {w['id']}): {w['description']}" for w in wfs]
            return ToolResult(True, "Workflows:\n" + "\n".join(lines))

        elif action == "save":
            if len(parts) < 3:
                return ToolResult(False, "Formato invalido. Use save|nome|descricao")
            name = parts[1]
            desc = parts[2]
            
            # Tentar extrair context (apps abertos)
            try:
                windows = _enum_visible_windows()
                apps = list(set([w["title"] for w in windows if w["title"]]))
                steps = [{"tool": "app_manager", "action": "focus_app", "target": app} for app in apps[:5]] # Limita aos 5 principais
                steps_json = json.dumps(steps)
            except Exception:
                steps_json = "[]"
                
            wid = self.db.add_workflow(name, desc, steps_json)
            return ToolResult(True, f"Workflow '{name}' salvo (ID {wid}) com {len(json.loads(steps_json))} passos baseados nas janelas ativas.")

        elif action == "run":
            if len(parts) < 2:
                return ToolResult(False, "Faltando o nome do workflow. Use run|nome")
            name = parts[1].lower()
            wfs = self.db.list_workflows()
            for wf in wfs:
                if wf["name"].lower() == name:
                    self.db.record_workflow_execution(wf["id"])
                    # Retorna instrucao pra LLM executar os passos
                    return ToolResult(True, f"__WORKFLOW_EXEC__:\n{wf['steps_json']}\nPor favor, execute essas ações utilizando as ferramentas disponíveis.")
            return ToolResult(False, f"Workflow '{name}' nao encontrado.")

        return ToolResult(False, f"Ação desconhecida: {action}")
