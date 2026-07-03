"""
File Processor Tool — Adaptado do Mark-XXXIX.
Processa arquivos de múltiplos tipos: Imagens, PDFs, Word, Excel, Código, Áudio, Vídeo.
"""

import os
import re
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from src.tools.base import BaseTool

def _detect_type(path: Path) -> str:
    ext = path.suffix.lower().lstrip(".")
    image_exts = {"jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff", "svg", "ico"}
    video_exts = {"mp4", "avi", "mov", "mkv", "wmv", "flv", "webm", "m4v", "3gp"}
    audio_exts = {"mp3", "wav", "ogg", "m4a", "aac", "flac", "wma", "opus"}
    code_exts  = {"py", "js", "ts", "jsx", "tsx", "html", "css", "java", "c",
                  "cpp", "cs", "go", "rs", "rb", "php", "swift", "kt", "sh",
                  "bash", "ps1", "lua", "r", "m", "sql", "yaml", "toml"}
    archive_exts = {"zip", "rar", "tar", "gz", "7z", "bz2", "xz"}

    if ext in image_exts:  return "image"
    if ext in video_exts:  return "video"
    if ext in audio_exts:  return "audio"
    if ext in code_exts:   return "code"
    if ext in archive_exts: return "archive"
    if ext == "pdf":       return "pdf"
    if ext in ("docx", "doc"): return "docx"
    if ext in ("txt", "md", "rst", "log"): return "text"
    if ext in ("csv", "tsv"): return "csv"
    if ext in ("xlsx", "xls", "ods"): return "excel"
    if ext == "json":      return "json"
    if ext == "xml":       return "xml"
    if ext in ("pptx", "ppt"): return "pptx"
    return "unknown"

def _file_size_str(path: Path) -> str:
    size = path.stat().st_size
    if size < 1024:        return f"{size} B"
    if size < 1024**2:     return f"{size/1024:.1f} KB"
    if size < 1024**3:     return f"{size/1024**2:.1f} MB"
    return f"{size/1024**3:.1f} GB"

def _output_path(src: Path, suffix: str, new_ext: str = None) -> Path:
    ext  = new_ext or src.suffix
    name = f"{src.stem}_{suffix}{ext}"
    return src.parent / name

# Wrapper functions for the processors
def _process_image(path: Path, action: str, params: dict, llm) -> str:
    try: from PIL import Image
    except ImportError: return "Pillow is not installed. Run: pip install Pillow"
    action = action or "describe"

    if action in ("describe", "ocr", "analyze", "read", "extract_text"):
        try:
            from src.services.vision import _vision_instance
            if not _vision_instance: return "Serviço de visão indisponível."
            
            prompt = {
                "describe": "Descreva esta imagem em detalhes.",
                "ocr":      "Extraia todo o texto visível. Retorne APENAS o texto formatado.",
                "analyze":  "Analise: objetos, cores, composição, texto, contexto.",
            }.get(action, "Descreva esta imagem.")
            
            if params.get("instruction"): prompt = params["instruction"]
            
            with open(path, "rb") as f:
                img_bytes = f.read()
            
            result = _vision_instance.describe_screen(prompt, img_bytes)
            
            if len(result) > 500 and params.get("save", True):
                out = _output_path(path, "result", ".txt")
                out.write_text(result, encoding="utf-8")
                return f"{result[:300]}...\n\nSalvo em: {out}"
            return result
        except Exception as e:
            return f"Falha ao analisar imagem: {e}"

    if action == "resize":
        width  = int(params.get("width",  0))
        height = int(params.get("height", 0))
        scale  = float(params.get("scale", 0))
        try:
            img = Image.open(path)
            w, h = img.size
            if scale: new_size = (int(w * scale), int(h * scale))
            elif width and height: new_size = (width, height)
            elif width: new_size = (width, int(h * width / w))
            elif height: new_size = (int(w * height / h), height)
            else: return "Especifique width, height, ou scale."
            out = _output_path(path, f"resized_{new_size[0]}x{new_size[1]}")
            img.resize(new_size, Image.LANCZOS).save(out)
            return f"Redimensionado de {w}x{h} para {new_size[0]}x{new_size[1]}. Salvo: {out.name}"
        except Exception as e: return f"Falha no resize: {e}"

    if action == "convert":
        fmt = params.get("format", "png").lower().strip(".")
        fmt_map = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WEBP", "bmp": "BMP"}
        pil_fmt = fmt_map.get(fmt, fmt.upper())
        try:
            img = Image.open(path).convert("RGB") if fmt in ["jpg", "jpeg"] else Image.open(path)
            out = _output_path(path, "converted", f".{fmt}")
            img.save(out, pil_fmt)
            return f"Convertido para {fmt.upper()}. Salvo: {out.name}"
        except Exception as e: return f"Falha na conversão: {e}"

    return "Ação de imagem não reconhecida."


class FileProcessorTool(BaseTool):
    @property
    def name(self) -> str:
        return "file_processor"

    @property
    def description(self) -> str:
        return (
            "Processa qualquer arquivo do sistema (imagens, pdfs, docs, data). "
            "Ações para imagem: describe | ocr | resize | convert | analyze. "
            "Especifique o path e a action."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Caminho completo do arquivo"
                },
                "action": {
                    "type": "string",
                    "description": "Ação a ser executada no arquivo"
                },
                "instruction": {
                    "type": "string",
                    "description": "Instrução livre (ex: 'traduza isso para PT-BR')"
                },
                "format": {
                    "type": "string",
                    "description": "Formato de destino (ex: 'pdf', 'mp3', 'png')"
                },
                "width": {"type": "integer"},
                "height": {"type": "integer"},
                "scale": {"type": "number"},
                "save": {"type": "boolean", "description": "Salvar output num arquivo? (default true)"}
            },
            "required": ["file_path"]
        }

    def execute(self, args: dict[str, Any], context: dict[str, Any] = None) -> str:
        path_str = args.get("file_path", "").strip()
        if not path_str: return "file_path vazio."
        
        path = Path(path_str)
        if not path.exists(): return f"Arquivo não encontrado: {path_str}"
        if not path.is_file(): return f"Não é um arquivo: {path_str}"

        llm = context.get("llm") if context else None
        if not llm:
            try:
                from src.services.llm import _global_llm_instance
                llm = _global_llm_instance
            except ImportError: pass
            
        file_type = _detect_type(path)
        action = args.get("action", "").lower().strip()
        
        print(f"[FileProcessor] ⚙️ Processando {file_type}: {path.name} ({action})")
        
        if file_type == "image":
            return _process_image(path, action, args, llm)
            
        # Para outros tipos (text, code, json), chama o LLM direto
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")[:20000]
            if not llm: return "LLM indisponível para ler o texto do arquivo."
            
            prompt = f"O usuário pediu '{action or args.get('instruction') or 'analise'}'.\n\nArquivo: {path.name}\nConteúdo:\n{content}"
            return llm.chat("Você é o FileProcessor, um analista de dados.", [{"role": "user", "content": prompt}])
        except Exception as e:
            return f"Erro genérico ao processar arquivo: {e}"
