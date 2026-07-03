from src.tools.base import BaseTool

class UserManagerTool(BaseTool):
    name = "user_manager"
    description = (
        "Gerencia os usuários e seus níveis de acesso no banco de dados. "
        "Apenas o Administrador (Nível 100) pode usar essa ferramenta para registrar, "
        "excluir ou atualizar usuários. "
        "Ações disponíveis: 'register', 'delete', 'update', 'list'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "A ação a ser executada: 'register', 'delete', 'update', 'list'."
            },
            "name": {
                "type": "string",
                "description": "O nome do usuário alvo."
            },
            "access_level": {
                "type": "integer",
                "description": "O nível de acesso (0-100)."
            }
        },
        "required": ["action"]
    }

    def execute(self, params: dict, context: dict = None) -> str:
        # Recuperamos o access_level atual se for passado (por hora vamos apenas assumir que o prompt
        # já instrui a IA a só usar a ferramenta se for o Admin. Mas podemos verificar por segurança 
        # se passássemos o speaker_level via context. Como não passamos, a barreira principal está na instrução)
        
        action = params.get("action", "").lower()
        name = params.get("name", "").strip()
        access_level = params.get("access_level", 1)

        from src.services.nexus_service import get_nexus_service
        db_conn = get_nexus_service().db._get_connection()
        cursor = db_conn.cursor()

        if action == "list":
            cursor.execute("SELECT name, access_level FROM voice_profiles")
            rows = cursor.fetchall()
            if not rows:
                return "Nenhum usuário registrado."
            result = "Usuários registrados:\n"
            for r in rows:
                result += f"- {r[0]} (Nível {r[1]})\n"
            return result

        if not name:
            return "Erro: O nome do usuário é obrigatório para esta ação."

        if action == "register":
            cursor.execute("SELECT name FROM voice_profiles WHERE name = ?", (name,))
            if cursor.fetchone():
                return f"Erro: Usuário '{name}' já existe."
            
            cursor.execute("INSERT INTO voice_profiles (name, access_level) VALUES (?, ?)", (name, access_level))
            db_conn.commit()
            return f"Usuário '{name}' registrado com sucesso (Nível {access_level})."

        elif action == "update":
            cursor.execute("SELECT name FROM voice_profiles WHERE name = ?", (name,))
            if not cursor.fetchone():
                return f"Erro: Usuário '{name}' não encontrado."
            
            cursor.execute("UPDATE voice_profiles SET access_level = ? WHERE name = ?", (access_level, name))
            db_conn.commit()
            return f"Nível de acesso do usuário '{name}' atualizado para {access_level}."

        elif action == "delete":
            if name.lower() == "admin":
                return "Erro: Não é possível excluir o Administrador principal por aqui."
            
            cursor.execute("SELECT name FROM voice_profiles WHERE name = ?", (name,))
            if not cursor.fetchone():
                return f"Erro: Usuário '{name}' não encontrado."
                
            cursor.execute("DELETE FROM voice_profiles WHERE name = ?", (name,))
            db_conn.commit()
            return f"Usuário '{name}' excluído com sucesso."

        return f"Erro: Ação '{action}' desconhecida."
