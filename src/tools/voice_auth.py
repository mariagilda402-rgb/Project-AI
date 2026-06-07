import json
from typing import Any
from src.tools.base import BaseTool
from src.services.nexus_service import get_nexus_service

class VoiceAuthTool(BaseTool):
    @property
    def name(self) -> str:
        return "voice_auth_manager"

    @property
    def description(self) -> str:
        return (
            "Gerencia os perfis de biometria de voz. O agente deve usar isso para "
            "excluir registros de usuários que não são mais necessários ou gerenciar acessos."
            "Nota: O registro ocorre automaticamente quando um usuário fala a palavra passe."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Ação a ser executada: 'delete_profile', 'list_profiles'"
                },
                "name": {
                    "type": "string",
                    "description": "Nome do perfil alvo (ex: 'Ana')"
                }
            },
            "required": ["action"]
        }

    def execute(self, args: dict[str, Any], context: dict[str, Any] = None) -> str:
        action = args.get("action")
        target_name = args.get("name")
        
        try:
            db_conn = get_nexus_service().db._get_connection()
            
            if action == "delete_profile":
                if not target_name:
                    return "Nome não fornecido."
                
                from src.services.voice_biometrics import VoiceBiometrics
                bio = VoiceBiometrics()
                success = bio.remove_profile(db_conn, target_name)
                
                if success:
                    return f"Perfil de voz de '{target_name}' excluído com sucesso."
                else:
                    return f"Perfil de voz de '{target_name}' não encontrado."
                    
            elif action == "list_profiles":
                cursor = db_conn.cursor()
                profiles = cursor.execute("SELECT id, name, access_level FROM voice_profiles").fetchall()
                if not profiles:
                    return "Nenhum perfil de voz cadastrado."
                res = "Perfis de voz cadastrados:\n"
                for p in profiles:
                    res += f"ID: {p[0]} | Nome: {p[1]} | Nível: {p[2]}\n"
                return res
            
            return "Ação não reconhecida."
        except Exception as e:
            return f"Erro ao gerenciar perfis de voz: {e}"
