from src.tools.base import Tool, ToolResult
from src.services.nexus_service import get_nexus_service
import json

class HabitTrackerTool(Tool):
    name = "habit_tracker"
    description = "Gerencia os hábitos e cria Presets Estratégicos de Vida. Use isso quando o usuário quiser criar uma nova rotina (ex: 'Preset Shape dos Sonhos', 'Foco no ENEM'). A ferramenta substitui os hábitos atuais por uma rotina completa gamificada."
    critical = False

    def __init__(self):
        self.service = get_nexus_service()

    def run(self, command: str) -> ToolResult:
        # A intenção primária desta tool é ser invocada pela IA
        # passando um payload JSON com os hábitos sugeridos.
        try:
            # Esperamos que a IA passe um JSON dentro do comando
            import re
            json_match = re.search(r'\[.*\]', command, re.DOTALL)
            if json_match:
                habits = json.loads(json_match.group(0))
                if isinstance(habits, list) and len(habits) > 0 and 'name' in habits[0]:
                    res = self.service.apply_preset_habits_json(habits)
                    return ToolResult(True, res)
        except Exception as e:
            return ToolResult(False, f"Erro ao processar o Preset JSON: {e}. Certifique-se de retornar uma lista de objetos JSON [{{\"name\": \"...\", \"description\": \"...\", \"xp_reward\": 50}}].")

        return ToolResult(False, "Comando não reconhecido. Forneça uma lista JSON de hábitos para aplicar o Preset.")
