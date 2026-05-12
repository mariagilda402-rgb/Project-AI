"""
Settings Manager Tool — Inspirado no ADA Local.
Permite à IA ou ao usuário alterar configurações em tempo de execução, como trocar o modelo de LLM ou alterar volumes globais.
"""

from typing import Any

from src.tools.base import BaseTool

class SettingsManagerTool(BaseTool):
    @property
    def name(self) -> str:
        return "manage_settings"

    @property
    def description(self) -> str:
        return (
            "Permite alterar configurações do sistema em tempo de execução. "
            "Ações suportadas: 'change_llm' (troca o provedor de IA entre gemini, groq, nvidia, ollama) "
            "ou 'toggle_vision' (ativa/desativa rastreamento MediaPipe para poupar CPU)."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Ex: change_llm ou toggle_vision"
                },
                "provider": {
                    "type": "string",
                    "description": "(Apenas para change_llm) O novo provedor (gemini, groq, nvidia, ollama)"
                },
                "model": {
                    "type": "string",
                    "description": "(Apenas para change_llm) Nome do modelo (opcional)"
                },
                "enable": {
                    "type": "boolean",
                    "description": "(Apenas para toggle_vision) True para ativar, False para pausar."
                }
            },
            "required": ["action"]
        }

    def execute(self, args: dict[str, Any], context: dict[str, Any] = None) -> str:
        action = args.get("action", "").lower()
        
        if action == "change_llm":
            provider = args.get("provider", "")
            model = args.get("model", "")
            
            llm = context.get("llm") if context else None
            if not llm:
                try:
                    from src.services.llm import _global_llm_instance
                    llm = _global_llm_instance
                except ImportError:
                    pass
                    
            if not llm:
                return "Erro: LLM não disponível no contexto."
                
            try:
                result = llm.change_provider(provider, model)
                print(f"[SettingsManager] ⚙️ {result}")
                return result
            except Exception as e:
                return f"Falha ao trocar o provedor LLM: {e}"
                
        if action == "toggle_vision":
            enable = args.get("enable", True)
            try:
                # O VisionTracker foi instanciado globalmente no main.py, mas precisamos acessá-lo.
                # Como ele envia para a task_queue, a forma mais segura é sinalizar que ativou e ele pega na próxima rodada, ou importamos.
                from src.main import vision_tracker
                if enable:
                    vision_tracker.resume()
                    return "Módulo de Visão Contínua (Gestos/Face) ATIVADO."
                else:
                    vision_tracker.pause()
                    return "Módulo de Visão Contínua (Gestos/Face) DESATIVADO."
            except Exception as e:
                return f"Falha ao alternar Módulo de Visão: {e}"
                
        return f"Ação desconhecida: {action}"
