from typing import Any
from pathlib import Path
from src.tools.base import BaseTool

class HackerModeTool(BaseTool):
    @property
    def name(self) -> str:
        return "create_python_skill"
        
    @property
    def description(self) -> str:
        return (
            "Entra no MODO HACKER / PROGRAMADOR. Usado para se auto-adaptar, criando, lendo, listando ou modificando "
            "habilidades (Skills) em Python na pasta src/skills. O código DEVE herdar de BaseTool e definir "
            "`name`, `description`, `parameters` e `execute(self, args: dict, context=None)`. "
            "A operacao 'read' retorna o conteudo do arquivo. A operacao 'list' lista todas as skills existentes. "
            "As operacoes 'create' ou 'update' salvam o codigo e recarregam o sistema instantaneamente."
        )
        
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["read", "create", "update", "list", "delete"],
                    "description": "Ação a ser realizada: 'list' lista skills, 'read' lê uma skill, 'create'/'update' salva código, 'delete' remove uma skill."
                },
                "filename": {
                    "type": "string",
                    "description": "O nome do arquivo .py na pasta src/skills (ex: weather_tool.py). Obrigatório para read, create, update, delete."
                },
                "code": {
                    "type": "string",
                    "description": "O código Python completo da Tool (obrigatório para create e update)."
                }
            },
            "required": ["action"]
        }
        
    def execute(self, args: dict[str, Any], context: dict[str, Any] = None) -> str:
        action = args.get("action", "create")
        filename = args.get("filename", "")
        code = args.get("code", "")
        
        skills_dir = Path("src/skills")
        skills_dir.mkdir(parents=True, exist_ok=True)
        
        # ── LIST ──
        if action == "list":
            files = sorted(skills_dir.glob("*.py"))
            files = [f for f in files if f.name != "__init__.py"]
            if not files:
                return "Nenhuma skill dinâmica encontrada em src/skills."
            lines = [f"📦 Skills disponíveis ({len(files)}):"]
            for f in files:
                lines.append(f"  - {f.name} ({f.stat().st_size} bytes)")
            return "\n".join(lines)
        
        # Validação de filename para as demais ações
        if not filename:
            return "Erro: filename é obrigatório para essa ação."
            
        if not filename.endswith(".py"):
            filename += ".py"
            
        filepath = skills_dir / filename
        
        # ── READ ──
        if action == "read":
            if not filepath.exists():
                return f"Erro: Arquivo '{filename}' não encontrado em src/skills."
            try:
                content = filepath.read_text(encoding="utf-8")
                return f"Conteúdo de {filename}:\n\n```python\n{content}\n```"
            except Exception as e:
                return f"Falha ao ler {filename}: {e}"
        
        # ── DELETE ──
        if action == "delete":
            if not filepath.exists():
                return f"Erro: Arquivo '{filename}' não encontrado em src/skills."
            try:
                filepath.unlink()
                try:
                    from src.main import task_queue
                    task_queue.put(("/reload_skills", "System"))
                except ImportError:
                    pass
                return f"Skill '{filename}' removida com sucesso."
            except Exception as e:
                return f"Falha ao deletar {filename}: {e}"
        
        # ── CREATE / UPDATE ──
        if action in ("create", "update"):
            if not code:
                return "Erro: O parâmetro 'code' é obrigatório para create e update."
            try:
                filepath.write_text(code, encoding="utf-8")
                
                # Dispara o evento de recarregar skills dinamicamente
                try:
                    from src.main import task_queue
                    task_queue.put(("/reload_skills", "System"))
                except ImportError:
                    pass
                
                try:
                    import src.ui.desktop_app
                    if src.ui.desktop_app.APP_INSTANCE:
                        pass  # Opcional: popup de confirmação
                except Exception:
                    pass
                    
                return f"Sucesso! Arquivo '{filename}' salvo e recarregado instantaneamente. A habilidade já está pronta para uso!"
            except Exception as e:
                return f"Falha ao salvar a skill: {e}"
        
        return f"Ação desconhecida: '{action}'. Use list, read, create, update ou delete."

