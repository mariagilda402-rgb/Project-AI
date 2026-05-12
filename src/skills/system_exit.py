from src.tools.base import BaseTool
import os
import time
import threading

class SystemExitTool(BaseTool):
    """
    Permite que a assistente IA desligue/encerre a si mesma quando o usuário pedir.
    """
    name = "turn_off_assistant"
    description = "Encerra o programa da Assistente IA. Use APENAS quando o usuário pedir explicitamente para você se desligar, fechar, ou encerrar o sistema."
    parameters = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Mensagem de despedida antes de desligar."
            }
        },
        "required": ["message"]
    }

    def execute(self, **kwargs):
        msg = kwargs.get("message", "Desligando sistemas.")
        print(f"\n[SystemExitTool] Despedida: {msg}")
        
        def kill_app():
            time.sleep(3)
            os._exit(0)
            
        threading.Thread(target=kill_app, daemon=True).start()
        return f"Sucesso. Sistema será encerrado em 3s."
