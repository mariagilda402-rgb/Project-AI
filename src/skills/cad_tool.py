import os
import json
import asyncio
from datetime import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv
from typing import Any
import tempfile
import re
import subprocess
import sys

from src.tools.base import BaseTool

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

class CadTool(BaseTool):
    @property
    def name(self) -> str:
        return "generate_cad_3d"
        
    @property
    def description(self) -> str:
        return "Gera um modelo 3D (CAD em formato .stl) com base em uma descrição de texto. Use para criar peças mecânicas, engrenagens, parafusos, formas 3D e objetos paramétricos. Retorna o caminho do arquivo STL gerado."
        
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Descrição detalhada da peça 3D para gerar (ex: 'Crie uma caixa 10x10x10 com cantos arredondados')"
                }
            },
            "required": ["prompt"]
        }
        
    def execute(self, args: dict[str, Any], context: dict[str, Any] = None) -> str:
        prompt = args.get("prompt")
        if not prompt:
            return "Erro: Prompt não informado."
            
        print(f"[CAD] Iniciando geração 3D para: {prompt}")
        
        try:
            return asyncio.run(self._generate_prototype(prompt))
        except Exception as e:
            return f"Falha ao gerar modelo 3D: {e}"

    async def _generate_prototype(self, prompt: str) -> str:
        client = genai.Client(api_key=API_KEY)
        model = "gemini-2.5-pro"
        
        system_instruction = """
You are a Python-based 3D CAD Engineer using the `build123d` library.
Your goal is to write a Python script that generates a 3D model based on the user's request.

Requirements:
1. Start with `from build123d import *`.
2. Include `import numpy as np` if needed.
3. You MUST assign the final object to a variable named `result_part`.
4. If you create a sketch or line, extrude it to make it a solid `Part`.
5. The model should be centered at (0,0,0) and have reasonable dimensions (mm).
6. **IMPORTANT**: Do NOT use old or PascalCase function names for core operations.
   - Use `make_face()` instead of `MakeFace()`.
   - Use `extrude()` instead of `Extrude()`.
   - Use `fillet()` instead of `Fillet()`.
   - Use `chamfer()` instead of `Chamfer()`.
   - generally prefer lowercase builder methods inside contexts.

7. **Vector Access**: Do NOT access vector components like `v.X`, `v.Y`, `v.Z` unless you are sure they exist.
8. **Final Output**: The script MUST end by exporting the final part to an STL file named 'output.stl'.
   - `export_stl(result_part, 'output.stl')`

9. **Robustness**: Operations like `fillet()` and `chamfer()` will crash if the radius is too large. Keep values conservative.

Example Script:
```python
from build123d import *

with BuildPart() as p:
    Box(10, 10, 10)
    Fillet(p.edges(), radius=1)

result_part = p.part
export_stl(result_part, 'output.stl')
```
"""
        # Ensure output directory exists
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        output_dir = os.path.join(base_dir, "data", "cad_outputs")
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_stl = os.path.join(output_dir, f"model_{timestamp}.stl")
        script_path = os.path.join(output_dir, f"script_{timestamp}.py")

        max_retries = 3
        current_prompt = f"Write a generic python script to create a 3D model of: {prompt}. Ensure you export to 'output.stl'. Unscaled."
        
        for attempt in range(max_retries):
            print(f"[CAD] Tentativa {attempt + 1}/{max_retries}...")
            
            response = await client.aio.models.generate_content(
                model=model,
                contents=current_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                )
            )
            
            raw_content = response.text
            if not raw_content:
                continue

            code_match = re.search(r'```python(.*?)```', raw_content, re.DOTALL)
            if code_match:
                code = code_match.group(1).strip()
            else:
                if "import build123d" in raw_content: code = raw_content
                else: continue
            
            safe_output_path = output_stl.replace("\\", "\\\\")
            code_with_path = code.replace("output.stl", safe_output_path)
            
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code_with_path)
                
            print(f"[CAD] Script gerado, executando build123d...")
            
            proc = await asyncio.to_thread(
                subprocess.run,
                [sys.executable, script_path],
                capture_output=True,
                text=True
            )
            
            if proc.returncode != 0:
                print(f"[CAD] Erro no script: {proc.stderr[:200]}")
                current_prompt = f"The script failed to execute with error:\n{proc.stderr}\nPlease fix the code and return the full corrected script. Request: {prompt}"
                continue
            
            if os.path.exists(output_stl):
                print(f"[CAD] Sucesso! STL salvo em: {output_stl}")
                return f"Modelo 3D gerado com sucesso! Arquivo salvo em: {output_stl}"
            else:
                current_prompt = "The script executed successfully but 'output.stl' was not found. Call export_stl(result_part, 'output.stl')."
                continue
                
        return "Falha ao gerar o modelo 3D após várias tentativas."
