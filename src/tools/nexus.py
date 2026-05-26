import json

from src.tools.base import Tool, ToolResult
from src.services.nexus_service import get_nexus_service
from src.skills.nexus_manager import NexusManagerSkill


class NexusTool(Tool):
    name = "nexus"
    description = "Gerencia o ecossistema Nexus: Metas (Kanban/Board), Notas (MindPalace/Notion), Hábitos (Chronos), Finanças (Aether), Temas (Aura) e Presets de rotina. Use para abrir o quadro de metas, gerenciar progresso e anotações."
    critical = False

    def __init__(self):
        self.service = get_nexus_service()
        self.skill = NexusManagerSkill(self.service)

    def run(self, command: str) -> ToolResult:
        cmd = (command or "").strip()
        if cmd.startswith("__NEXUS_JSON__"):
            try:
                payload = json.loads(cmd.replace("__NEXUS_JSON__", "", 1).strip())
                out = self.service.handle_structured_command(payload)
                return ToolResult(True, out)
            except Exception as e:
                return ToolResult(False, f"Nexus JSON invalido: {e}")

        # Tenta processar via Skill de voz primeiro
        result_text = self.skill.handle_command(command)
        if result_text:
            return ToolResult(True, result_text)
        
        # Fallback para consultas de status
        if "nexus" in command.lower():
            return ToolResult(True, self.service.get_summary())
            
        return ToolResult(False, "Comando Nexus não processado.")
