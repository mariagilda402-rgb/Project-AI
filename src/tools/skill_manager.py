import sys
import importlib.util
from pathlib import Path
from typing import List

from src.tools.base import BaseTool

def load_dynamic_skills() -> List[BaseTool]:
    """Escaneia a pasta src/skills e carrega dinamicamente as classes que herdam de BaseTool."""
    skills_dir = Path("src/skills")
    skills = []
    
    if not skills_dir.exists():
        skills_dir.mkdir(parents=True, exist_ok=True)
        (skills_dir / "__init__.py").touch()
        return skills
        
    for py_file in skills_dir.glob("*.py"):
        if py_file.name in ("__init__.py", "change_voice.py", "system_exit.py"):
            continue
            
        try:
            module_name = f"src.skills.{py_file.stem}"
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                
                # Procura por classes que herdem de BaseTool
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, BaseTool) and attr is not BaseTool:
                        # Ignora se importado de outro lugar
                        if attr.__module__ == module_name:
                            try:
                                tool_instance = attr()
                                skills.append(tool_instance)
                                print(f"[SkillManager] Carregada habilidade dinamica: {tool_instance.name}")
                            except Exception as init_err:
                                print(f"[SkillManager] Erro ao instanciar {attr_name}: {init_err}")
        except Exception as e:
            print(f"[SkillManager] Erro ao carregar o arquivo {py_file.name}: {e}")
            
    return skills
