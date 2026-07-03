"""
Persona Framework — Inspirado no OmniBot.
Gerencia os arquivos markdown que definem a identidade e alma da IA.
A própria IA pode ler e modificar esses arquivos.
"""

from pathlib import Path
from typing import Any

from src.tools.base import BaseTool

PERSONA_DIR = Path("data/persona")

# Defaults para caso os arquivos não existam
DEFAULT_IDENTITY = """# Identidade da Assistente
Você é uma assistente pessoal avançada baseada em IA, executando localmente no Windows.
Sua comunicação deve ser:
- Direta e natural (Português do Brasil).
- Sem uso de formatações excessivas (evite markdown complexo ou textões).
- Amigável, mas extremamente focada na eficiência.
"""

DEFAULT_SOUL = """# Núcleo / Valores
- Privacidade: Você roda localmente, priorizando a segurança dos dados do usuário.
- Autonomia: Você tem a capacidade de aprender, se reescrever e executar tarefas complexas sozinha.
- Evolução Constante: Você busca se otimizar e expandir suas próprias "skills" através do Hacker Mode.
"""

def setup_persona_files():
    PERSONA_DIR.mkdir(parents=True, exist_ok=True)
    identity_file = PERSONA_DIR / "IDENTITY.md"
    if not identity_file.exists():
        identity_file.write_text(DEFAULT_IDENTITY, encoding="utf-8")
        
    soul_file = PERSONA_DIR / "SOUL.md"
    if not soul_file.exists():
        soul_file.write_text(DEFAULT_SOUL, encoding="utf-8")

def get_persona_context() -> str:
    """Lê os arquivos de persona para injetar no System Prompt."""
    setup_persona_files()
    
    identity = (PERSONA_DIR / "IDENTITY.md").read_text(encoding="utf-8").strip()
    soul = (PERSONA_DIR / "SOUL.md").read_text(encoding="utf-8").strip()
    
    context = []
    if identity:
        context.append(f"[IDENTITY]\n{identity}")
    if soul:
        context.append(f"[SOUL]\n{soul}")
        
    return "\n\n".join(context)

class PersonaManagerTool(BaseTool):
    @property
    def name(self) -> str:
        return "manage_persona"
        
    @property
    def description(self) -> str:
        return (
            "Permite que você reescreva, atualize ou leia sua própria personalidade (IDENTITY) "
            "e seus valores centrais (SOUL). Use isso para evoluir seu comportamento ou se adaptar "
            "ao que o usuário pede. Arquivos: IDENTITY.md ou SOUL.md."
        )
        
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "read | update"
                },
                "file": {
                    "type": "string",
                    "description": "IDENTITY.md ou SOUL.md"
                },
                "content": {
                    "type": "string",
                    "description": "O novo conteúdo completo do arquivo (obrigatório se action=update)"
                }
            },
            "required": ["action", "file"]
        }
        
    def execute(self, args: dict[str, Any], context: dict[str, Any] = None) -> str:
        action = args.get("action", "read").lower()
        filename = args.get("file", "").upper()
        content = args.get("content", "")
        
        if not filename.endswith(".MD"):
            filename += ".MD"
            
        if filename not in ("IDENTITY.MD", "SOUL.MD"):
            return "Apenas IDENTITY.md ou SOUL.md são permitidos."
            
        filepath = PERSONA_DIR / filename
        
        if action == "read":
            if not filepath.exists():
                setup_persona_files()
            return filepath.read_text(encoding="utf-8")
            
        elif action == "update":
            if not content:
                return "O campo 'content' é obrigatório para update."
            
            # Salva backup da versão anterior
            if filepath.exists():
                backup = PERSONA_DIR / f"{filename}.bak"
                backup.write_text(filepath.read_text(encoding="utf-8"), encoding="utf-8")
                
            filepath.write_text(content, encoding="utf-8")
            return f"[{filename}] atualizado com sucesso. Minha personalidade/alma foi alterada."
            
        return f"Ação desconhecida: {action}"
