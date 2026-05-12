"""
Code Helper Tool — Inspirado no Mark-XXXV code_helper.
Escreve, edita, executa, debugga e otimiza código em qualquer linguagem.
Inclui um loop build que escreve → executa → corrige → executa (até 3x).
"""

from typing import Any
from pathlib import Path
import subprocess
import sys
import re
import time

from src.tools.base import BaseTool


class CodeHelperTool(BaseTool):
    @property
    def name(self) -> str:
        return "code_helper"
        
    @property
    def description(self) -> str:
        return (
            "Ferramenta avançada para escrever, editar, executar e debugar código. "
            "Ações: 'write' (gera código novo), 'edit' (modifica arquivo existente), "
            "'run' (executa script), 'build' (escreve→executa→corrige loop), "
            "'explain' (explica código), 'optimize' (otimiza código existente). "
            "Use quando o usuário pedir algo de programação que não seja uma Skill."
        )
        
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "write | edit | run | build | explain | optimize"
                },
                "description": {
                    "type": "string",
                    "description": "O que o código deve fazer ou que mudança aplicar"
                },
                "language": {
                    "type": "string",
                    "description": "Linguagem de programação (default: python)"
                },
                "file_path": {
                    "type": "string",
                    "description": "Caminho do arquivo existente para edit/run/explain/optimize"
                },
                "code": {
                    "type": "string",
                    "description": "Código fonte para explain/optimize (se não houver arquivo)"
                },
                "output_path": {
                    "type": "string",
                    "description": "Onde salvar o arquivo gerado"
                }
            },
            "required": ["action"]
        }
        
    def execute(self, args: dict[str, Any], context: dict[str, Any] = None) -> str:
        action = args.get("action", "write").lower().strip()
        description = args.get("description", "").strip()
        language = args.get("language", "python").strip()
        file_path = args.get("file_path", "").strip()
        code = args.get("code", "").strip()
        output_path = args.get("output_path", "").strip()
        
        if action == "write":
            return self._write(description, language, output_path)
        elif action == "edit":
            return self._edit(file_path, description)
        elif action == "run":
            return self._run(file_path)
        elif action == "build":
            return self._build(description, language, output_path)
        elif action == "explain":
            return self._explain(file_path, code)
        elif action == "optimize":
            return self._optimize(file_path, code, language, output_path)
        else:
            return f"Ação desconhecida: '{action}'. Use write, edit, run, build, explain ou optimize."

    def _get_llm(self):
        """Obtém o LLMService globalmente."""
        try:
            from src.services.llm import _global_llm_instance
            return _global_llm_instance
        except Exception:
            return None

    def _resolve_path(self, output_path: str, language: str) -> Path:
        ext_map = {
            "python": ".py", "py": ".py",
            "javascript": ".js", "js": ".js",
            "typescript": ".ts", "ts": ".ts",
            "html": ".html", "css": ".css",
            "java": ".java", "cpp": ".cpp", "c": ".c",
            "bash": ".sh", "shell": ".sh", "powershell": ".ps1",
        }
        desktop = Path.home() / "Desktop"
        if output_path:
            p = Path(output_path)
            return p if p.is_absolute() else desktop / p
        ext = ext_map.get(language.lower(), ".py")
        return desktop / f"assistente_code{ext}"

    def _clean_code(self, text: str) -> str:
        text = text.strip()
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        return text.strip()

    def _has_error(self, output: str) -> bool:
        signals = ["error", "exception", "traceback", "syntaxerror",
                    "nameerror", "typeerror", "stderr", "failed"]
        return any(s in output.lower() for s in signals)

    def _run_file(self, path: Path, timeout: int = 30) -> str:
        interpreters = {
            ".py": [sys.executable],
            ".js": ["node"],
            ".sh": ["bash"],
            ".ps1": ["powershell", "-File"],
        }
        interp = interpreters.get(path.suffix.lower())
        if not interp:
            return f"Sem interpretador para {path.suffix}."
        try:
            result = subprocess.run(
                interp + [str(path)],
                capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=timeout, cwd=str(path.parent)
            )
            parts = []
            if result.stdout.strip():
                parts.append(f"Output:\n{result.stdout.strip()}")
            if result.stderr.strip():
                parts.append(f"Stderr:\n{result.stderr.strip()}")
            return "\n\n".join(parts) if parts else "Executado sem output."
        except subprocess.TimeoutExpired:
            return f"Timeout após {timeout}s."
        except FileNotFoundError:
            return f"Interpretador não encontrado: {interp[0]}."
        except Exception as e:
            return f"Erro na execução: {e}"

    def _write(self, description: str, language: str, output_path: str) -> str:
        if not description:
            return "Descreva o que o código deve fazer."
        llm = self._get_llm()
        if not llm:
            return "LLM indisponível."
        
        prompt = (
            f"Você é um expert em {language}. Escreva código limpo e funcional.\n"
            f"Retorne APENAS o código. Sem explicação, sem markdown, sem backticks.\n\n"
            f"Descrição: {description}\n\nCódigo:"
        )
        try:
            response = llm.chat(
                f"Expert {language} developer. Output ONLY code.",
                [{"role": "user", "content": prompt}]
            )
            code = self._clean_code(response)
            path = self._resolve_path(output_path, language)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(code, encoding="utf-8")
            preview = "\n".join(code.splitlines()[:10])
            return f"Código escrito. Salvo em: {path}\n\nPreview:\n{preview}"
        except Exception as e:
            return f"Não consegui gerar o código: {e}"

    def _edit(self, file_path: str, instruction: str) -> str:
        if not file_path:
            return "Informe o caminho do arquivo para editar."
        if not instruction:
            return "Descreva que mudança fazer."
        
        p = Path(file_path)
        if not p.exists():
            return f"Arquivo não encontrado: {file_path}"
        
        content = p.read_text(encoding="utf-8")
        llm = self._get_llm()
        if not llm:
            return "LLM indisponível."
        
        prompt = (
            f"Aplique a seguinte mudança no código abaixo.\n"
            f"Retorne APENAS o código completo atualizado. Sem explicação, sem markdown.\n\n"
            f"Mudança: {instruction}\n\nCódigo original:\n{content}\n\nCódigo atualizado:"
        )
        try:
            response = llm.chat(
                "Expert code editor. Output ONLY the complete updated code.",
                [{"role": "user", "content": prompt}]
            )
            edited = self._clean_code(response)
            p.write_text(edited, encoding="utf-8")
            preview = "\n".join(edited.splitlines()[:10])
            return f"Arquivo editado: {file_path}\n\nPreview:\n{preview}"
        except Exception as e:
            return f"Não consegui editar: {e}"

    def _run(self, file_path: str) -> str:
        if not file_path:
            return "Informe o caminho do arquivo para executar."
        p = Path(file_path)
        if not p.exists():
            return f"Arquivo não encontrado: {file_path}"
        return self._run_file(p)

    def _build(self, description: str, language: str, output_path: str) -> str:
        """Loop: escreve → executa → conserta → executa (até 3 tentativas)."""
        if not description:
            return "Descreva o que quer construir."
        
        MAX_ATTEMPTS = 3
        llm = self._get_llm()
        if not llm:
            return "LLM indisponível."
        
        # 1. Escreve o código inicial
        write_result = self._write(description, language, output_path)
        if "Não consegui" in write_result:
            return write_result
        
        path = self._resolve_path(output_path, language)
        
        # 2. Loop de build
        for attempt in range(1, MAX_ATTEMPTS + 1):
            print(f"[CodeHelper] 🔄 Tentativa {attempt}/{MAX_ATTEMPTS}")
            
            output = self._run_file(path)
            
            if not self._has_error(output):
                return (
                    f"Build concluído! Funcionou na tentativa {attempt}. "
                    f"Salvo em {path}.\n\nOutput:\n{output}"
                )
            
            print(f"[CodeHelper] ⚠️ Erro na tentativa {attempt}, corrigindo...")
            
            code = path.read_text(encoding="utf-8")
            fix_prompt = (
                f"O código abaixo falhou com o seguinte erro. Corrija.\n"
                f"Retorne APENAS o código corrigido. Sem explicação.\n\n"
                f"Objetivo: {description}\n\n"
                f"Erro:\n{output[:2000]}\n\n"
                f"Código quebrado:\n{code}\n\nCódigo corrigido:"
            )
            try:
                response = llm.chat(
                    "Expert debugger. Output ONLY the fixed code.",
                    [{"role": "user", "content": fix_prompt}]
                )
                fixed = self._clean_code(response)
                path.write_text(fixed, encoding="utf-8")
            except Exception as e:
                return f"Não consegui corrigir na tentativa {attempt}: {e}"
        
        return f"Build falhou após {MAX_ATTEMPTS} tentativas. Último erro:\n{output[:300]}"

    def _explain(self, file_path: str, code: str) -> str:
        if file_path and not code:
            p = Path(file_path)
            if not p.exists():
                return f"Arquivo não encontrado: {file_path}"
            code = p.read_text(encoding="utf-8")
        if not code:
            return "Informe código ou caminho de arquivo para explicar."
        
        llm = self._get_llm()
        if not llm:
            return "LLM indisponível."
        
        try:
            response = llm.chat(
                "Explique código de forma clara e concisa em português. 3-6 frases.",
                [{"role": "user", "content": f"Explique:\n{code[:4000]}"}]
            )
            return response.strip()
        except Exception as e:
            return f"Não consegui explicar: {e}"

    def _optimize(self, file_path: str, code: str, language: str, output_path: str) -> str:
        if file_path and not code:
            p = Path(file_path)
            if not p.exists():
                return f"Arquivo não encontrado: {file_path}"
            code = p.read_text(encoding="utf-8")
        if not code:
            return "Informe código ou arquivo para otimizar."
        
        llm = self._get_llm()
        if not llm:
            return "LLM indisponível."
        
        prompt = (
            f"Otimize o código {language} abaixo para:\n"
            f"1. Performance — operações eficientes\n"
            f"2. Legibilidade — nomes claros, formatação\n"
            f"3. Best practices — patterns modernos\n"
            f"Retorne APENAS o código otimizado. Sem explicação.\n\n"
            f"Código original:\n{code[:6000]}\n\nCódigo otimizado:"
        )
        try:
            response = llm.chat(
                f"Expert {language} optimizer. Output ONLY optimized code.",
                [{"role": "user", "content": prompt}]
            )
            optimized = self._clean_code(response)
            
            save_path = Path(file_path) if file_path else self._resolve_path(output_path, language)
            save_path.write_text(optimized, encoding="utf-8")
            
            orig_lines = len(code.splitlines())
            opt_lines = len(optimized.splitlines())
            diff = orig_lines - opt_lines
            
            preview = "\n".join(optimized.splitlines()[:10])
            return (
                f"Código otimizado. Salvo em {save_path}\n"
                f"Linhas: {orig_lines} → {opt_lines} "
                f"({'−' if diff > 0 else '+'}{abs(diff)} linhas)\n\n"
                f"Preview:\n{preview}"
            )
        except Exception as e:
            return f"Não consegui otimizar: {e}"
