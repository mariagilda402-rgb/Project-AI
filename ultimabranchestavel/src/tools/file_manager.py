"""Gerenciamento de arquivos e pastas do Windows (restrito a pastas do usuário)."""
from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path

from .base import ToolResult

def _user_home() -> Path:
    return Path.home()

PATH_ALIASES: dict[str, str] = {
    "downloads": "Downloads", "download": "Downloads",
    "documentos": "Documents", "documents": "Documents",
    "desktop": "Desktop", "area de trabalho": "Desktop", "área de trabalho": "Desktop",
    "imagens": "Pictures", "fotos": "Pictures", "pictures": "Pictures",
    "musicas": "Music", "músicas": "Music", "music": "Music",
    "videos": "Videos", "vídeos": "Videos",
}

BLOCKED_PATHS = ["C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)", "C:\\ProgramData"]
ALLOWED_FOLDER_NAMES = {"Downloads", "Documents", "Desktop", "Pictures", "Music", "Videos"}


def _resolve_path(raw: str) -> Path | None:
    raw = raw.strip().strip("'\"")
    alias_key = raw.lower()
    if alias_key in PATH_ALIASES:
        return _user_home() / PATH_ALIASES[alias_key]
    p = Path(raw)
    if not p.is_absolute():
        parts = raw.replace("\\", "/").split("/")
        first = parts[0].lower()
        if first in PATH_ALIASES:
            p = _user_home() / PATH_ALIASES[first] / "/".join(parts[1:])
        else:
            return None
    return p


def _is_allowed(path: Path) -> bool:
    resolved = str(path.resolve()).replace("/", "\\")
    for blocked in BLOCKED_PATHS:
        if resolved.startswith(blocked):
            return False
    home = str(_user_home().resolve()).replace("/", "\\")
    if not resolved.startswith(home):
        return False
    rel = resolved[len(home):].lstrip("\\")
    top_folder = rel.split("\\")[0] if rel else ""
    return top_folder in ALLOWED_FOLDER_NAMES


def _human_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


class FileManagerTool:
    name = "file_manager"
    description = "Gerencia arquivos e pastas (listar, contar, mover, copiar, deletar, buscar, ler, escrever)."
    critical = True

    def list_dir(self, path_str: str) -> ToolResult:
        path = _resolve_path(path_str)
        if not path or not _is_allowed(path):
            return ToolResult(False, f"Caminho inválido ou não permitido: {path_str}")
        if not path.exists() or not path.is_dir():
            return ToolResult(False, f"Pasta não encontrada: {path_str}")
        items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        if not items:
            return ToolResult(True, f"Pasta '{path.name}' está vazia.")
        lines: list[str] = []
        dirs = [i for i in items if i.is_dir()]
        files = [i for i in items if i.is_file()]
        for d in dirs[:30]:
            lines.append(f"[DIR] {d.name}/")
        for f in files[:50]:
            lines.append(f"[ARQ] {f.name} ({_human_size(f.stat().st_size)})")
        header = f"Conteúdo de '{path.name}' ({len(dirs)} pastas, {len(files)} arquivos):"
        return ToolResult(True, header + "\n" + "\n".join(lines))

    def count_files(self, path_str: str, extension: str = "") -> ToolResult:
        path = _resolve_path(path_str)
        if not path or not _is_allowed(path) or not path.exists():
            return ToolResult(False, f"Pasta inválida: {path_str}")
        ext = extension.strip().lower()
        if ext and not ext.startswith("."):
            ext = "." + ext
        count = sum(1 for i in path.iterdir() if i.is_file() and (not ext or i.suffix.lower() == ext))
        ext_msg = f" com extensão '{ext}'" if ext else ""
        return ToolResult(True, f"Pasta '{path.name}': {count} arquivos{ext_msg}.")

    def file_info(self, path_str: str) -> ToolResult:
        path = _resolve_path(path_str)
        if not path or not _is_allowed(path) or not path.exists():
            return ToolResult(False, f"Arquivo não encontrado: {path_str}")
        stat = path.stat()
        info = [
            f"Nome: {path.name}", f"Tamanho: {_human_size(stat.st_size)}",
            f"Modificado: {datetime.fromtimestamp(stat.st_mtime).strftime('%d/%m/%Y %H:%M')}",
            f"Caminho: {path}",
        ]
        return ToolResult(True, "\n".join(info))

    def search_files(self, path_str: str, query: str) -> ToolResult:
        path = _resolve_path(path_str)
        if not path or not _is_allowed(path) or not path.exists():
            return ToolResult(False, f"Pasta inválida: {path_str}")
        query_l = query.lower()
        matches: list[str] = []
        try:
            for item in path.rglob("*"):
                if query_l in item.name.lower():
                    rel = item.relative_to(path)
                    size = _human_size(item.stat().st_size) if item.is_file() else "pasta"
                    tag = '[DIR]' if item.is_dir() else '[ARQ]'
                    matches.append(f"  {tag} {rel} ({size})")
                    if len(matches) >= 30:
                        break
        except PermissionError:
            pass
        if not matches:
            return ToolResult(True, f"Nenhum resultado para '{query}' em '{path.name}'.")
        return ToolResult(True, f"{len(matches)} resultados para '{query}':\n" + "\n".join(matches))

    def create_dir(self, path_str: str) -> ToolResult:
        path = _resolve_path(path_str)
        if not path or not _is_allowed(path):
            return ToolResult(False, f"Não permitido: {path_str}")
        if path.exists():
            return ToolResult(False, f"Já existe: {path.name}")
        try:
            path.mkdir(parents=True)
            return ToolResult(True, f"Pasta criada: {path.name}")
        except Exception as e:
            return ToolResult(False, f"Erro: {e}")

    def move_file(self, src_str: str, dst_str: str) -> ToolResult:
        src, dst = _resolve_path(src_str), _resolve_path(dst_str)
        if not src or not _is_allowed(src) or not src.exists():
            return ToolResult(False, f"Origem inválida: {src_str}")
        if not dst or not _is_allowed(dst):
            return ToolResult(False, f"Destino inválido: {dst_str}")
        try:
            dest = dst / src.name if dst.is_dir() else dst
            shutil.move(str(src), str(dest))
            return ToolResult(True, f"Movido: {src.name} → {dest.parent.name}/")
        except Exception as e:
            return ToolResult(False, f"Erro: {e}")

    def copy_file(self, src_str: str, dst_str: str) -> ToolResult:
        src, dst = _resolve_path(src_str), _resolve_path(dst_str)
        if not src or not _is_allowed(src) or not src.exists():
            return ToolResult(False, f"Origem inválida: {src_str}")
        if not dst or not _is_allowed(dst):
            return ToolResult(False, f"Destino inválido: {dst_str}")
        try:
            dest = dst / src.name if dst.is_dir() else dst
            if src.is_dir():
                shutil.copytree(str(src), str(dest))
            else:
                shutil.copy2(str(src), str(dest))
            return ToolResult(True, f"Copiado: {src.name} → {dest.parent.name}/")
        except Exception as e:
            return ToolResult(False, f"Erro: {e}")

    def delete_file(self, path_str: str) -> ToolResult:
        path = _resolve_path(path_str)
        if not path or not _is_allowed(path) or not path.exists():
            return ToolResult(False, f"Não encontrado: {path_str}")
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            return ToolResult(True, f"Deletado: {path.name}")
        except Exception as e:
            return ToolResult(False, f"Erro: {e}")

    def rename_file(self, path_str: str, new_name: str) -> ToolResult:
        path = _resolve_path(path_str)
        if not path or not _is_allowed(path) or not path.exists():
            return ToolResult(False, f"Não encontrado: {path_str}")
        if not new_name.strip():
            return ToolResult(False, "Novo nome vazio.")
        try:
            path.rename(path.parent / new_name.strip())
            return ToolResult(True, f"Renomeado: {path.name} → {new_name.strip()}")
        except Exception as e:
            return ToolResult(False, f"Erro: {e}")

    def disk_usage(self, path_str: str) -> ToolResult:
        path = _resolve_path(path_str)
        if not path or not _is_allowed(path) or not path.exists():
            return ToolResult(False, f"Não encontrado: {path_str}")
        total, count = 0, 0
        try:
            for item in path.rglob("*"):
                if item.is_file():
                    total += item.stat().st_size
                    count += 1
        except PermissionError:
            pass
        return ToolResult(True, f"Pasta '{path.name}': {_human_size(total)} em {count} arquivos.")

    def read_text_file(self, path_str: str) -> ToolResult:
        path = _resolve_path(path_str)
        if not path or not _is_allowed(path) or not path.exists() or not path.is_file():
            return ToolResult(False, f"Arquivo inválido: {path_str}")
        if path.stat().st_size > 50 * 1024:
            return ToolResult(False, f"Arquivo muito grande ({_human_size(path.stat().st_size)}). Limite: 50 KB.")
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            return ToolResult(True, f"Conteúdo de '{path.name}':\n{content}")
        except Exception as e:
            return ToolResult(False, f"Erro: {e}")

    def write_text_file(self, path_str: str, content: str) -> ToolResult:
        path = _resolve_path(path_str)
        if not path or not _is_allowed(path):
            return ToolResult(False, f"Não permitido: {path_str}")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return ToolResult(True, f"Arquivo salvo: {path.name} ({_human_size(len(content.encode('utf-8')))})")
        except Exception as e:
            return ToolResult(False, f"Erro: {e}")

    def run(self, command: str) -> ToolResult:
        cmd = (command or "").strip()
        if not cmd:
            return ToolResult(False, "Comando vazio.")
        parts = cmd.split("|")
        action = parts[0].strip().lower() if len(parts) > 0 else ""
        path_str = parts[1].strip() if len(parts) > 1 else ""
        arg = parts[2].strip() if len(parts) > 2 else ""

        dispatch = {
            "list_dir": lambda: self.list_dir(path_str),
            "count_files": lambda: self.count_files(path_str, arg),
            "file_info": lambda: self.file_info(path_str),
            "search_files": lambda: self.search_files(path_str, arg),
            "create_dir": lambda: self.create_dir(path_str),
            "move_file": lambda: self.move_file(path_str, arg),
            "copy_file": lambda: self.copy_file(path_str, arg),
            "delete_file": lambda: self.delete_file(path_str),
            "rename_file": lambda: self.rename_file(path_str, arg),
            "disk_usage": lambda: self.disk_usage(path_str),
            "read_text_file": lambda: self.read_text_file(path_str),
            "write_text_file": lambda: self.write_text_file(path_str, arg),
        }
        handler = dispatch.get(action)
        if handler:
            return handler()
        return ToolResult(False, f"Ação desconhecida: {action}")
