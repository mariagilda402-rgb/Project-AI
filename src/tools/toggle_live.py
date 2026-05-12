from typing import Any
from src.tools.base import BaseTool

class ToggleLiveTool(BaseTool):
    @property
    def name(self) -> str:
        return "toggle_live"

    @property
    def description(self) -> str:
        return (
            "Ativa ou desativa o modo de conversa em tempo real de baixa latência (Gemini Live). "
            "Use quando o usuário quiser conversar de forma mais fluida, 'entrar em uma ligação' "
            "ou quando precisar de respostas instantâneas."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "enable": {
                    "type": "boolean",
                    "description": "True para ativar o modo Live, False para desativar e voltar ao modo padrão."
                }
            },
            "required": ["enable"]
        }

    def execute(self, args: dict[str, Any], context: dict[str, Any] = None) -> str:
        enable = args.get("enable", True)
        
        # O orquestrador é passado via contexto
        orchestrator = context.get("orchestrator") if context else None
        if not orchestrator:
            # Tenta encontrar via import circular (fallback)
            try:
                from src.main import agent as global_agent
                orchestrator = global_agent
            except ImportError:
                pass
        
        if orchestrator and hasattr(orchestrator, "toggle_live_mode"):
            return orchestrator.toggle_live_mode(enable)
        
        return "Erro: Orquestrador não encontrado no contexto para alternar o modo Live."
