import os
import re
import json
from pathlib import Path
from typing import Any
import urllib.parse
import urllib.request
from datetime import datetime

from src.tools.base import BaseTool

# Pasta onde todas as imagens geradas são salvas
IMAGES_DIR = Path("data/generated_images")


def _slug(text: str, max_len: int = 40) -> str:
    """Converte o prompt em um nome de arquivo seguro e legível."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "_", slug)
    slug = slug[:max_len].strip("_")
    return slug or "imagem"


class GenerateImageTool(BaseTool):
    """
    Ferramenta para gerar imagens usando IA (Pollinations.ai).
    Salva na pasta data/generated_images com nome descritivo e registra na memória.
    """

    @property
    def name(self) -> str:
        return "generate_image"

    @property
    def description(self) -> str:
        return (
            "Gera uma imagem a partir de um texto (prompt em inglês preferencialmente) "
            "e salva na pasta de imagens geradas. Retorna o caminho absoluto da imagem. "
            "Após gerar, use show_image para exibir na tela se o usuário pedir."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "A descrição detalhada da imagem a ser gerada (em inglês para melhor resultado)."
                },
                "label": {
                    "type": "string",
                    "description": "Nome curto e descritivo em português para identificar a imagem (ex: 'cachoeira', 'gato fofo'). Usado no nome do arquivo."
                }
            },
            "required": ["prompt"]
        }

    def execute(self, args: dict[str, Any], context: dict[str, Any] = None) -> str:
        prompt = args.get("prompt", "").strip()
        label = args.get("label", "").strip() or prompt

        if not prompt:
            return "Erro: 'prompt' não fornecido."

        print(f"[GenerateImageTool] Gerando imagem: '{label}' | Prompt: '{prompt[:60]}...'")

        try:
            IMAGES_DIR.mkdir(parents=True, exist_ok=True)

            # Nome descritivo: label_slug + timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            slug = _slug(label)
            filename = f"{slug}_{timestamp}.jpg"
            filepath = IMAGES_DIR / filename

            # Gera via Pollinations.ai
            encoded_prompt = urllib.parse.quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"

            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as response, open(filepath, "wb") as out_file:
                out_file.write(response.read())

            abs_path = str(filepath.resolve())

            # Salva na memória de imagens (JSON simples)
            self._save_to_image_index(label, prompt, abs_path)

            return (
                f"Imagem '{label}' gerada com sucesso!\n"
                f"Arquivo: {abs_path}\n"
                f"Para exibir na tela, use a ferramenta show_image com esse caminho."
            )
        except Exception as e:
            return f"Falha ao gerar imagem: {e}"

    def _save_to_image_index(self, label: str, prompt: str, path: str):
        """Salva informações da imagem gerada em um índice JSON."""
        index_path = IMAGES_DIR / "index.json"
        try:
            if index_path.exists():
                with open(index_path, "r", encoding="utf-8") as f:
                    index = json.load(f)
            else:
                index = []

            index.append({
                "label": label,
                "prompt": prompt,
                "path": path,
                "created_at": datetime.now().isoformat()
            })

            with open(index_path, "w", encoding="utf-8") as f:
                json.dump(index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[GenerateImageTool] Falha ao salvar índice: {e}")


class ShowImageTool(BaseTool):
    """
    Ferramenta para exibir uma imagem flutuante na tela do usuário.
    Pode buscar por nome/label se o caminho completo não for fornecido.
    """

    @property
    def name(self) -> str:
        return "show_image"

    @property
    def description(self) -> str:
        return (
            "Exibe uma imagem em uma janela popup flutuante. "
            "Pode receber o caminho completo do arquivo OU um nome/label da imagem gerada anteriormente (ex: 'cachoeira'). "
            "Busca automaticamente no índice de imagens geradas."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Caminho absoluto do arquivo de imagem OU nome/label da imagem gerada (ex: 'cachoeira')."
                }
            },
            "required": ["filepath"]
        }

    def execute(self, args: dict[str, Any], context: dict[str, Any] = None) -> str:
        filepath = (args.get("filepath") or "").strip()
        if not filepath:
            return "Erro: 'filepath' não fornecido."

        # Tenta encontrar o arquivo diretamente
        path_obj = Path(filepath)
        if not path_obj.exists():
            # Busca pelo label no índice
            found = self._search_index(filepath)
            if found:
                path_obj = Path(found)
            else:
                return (
                    f"Não encontrei a imagem '{filepath}'. "
                    f"Tente gerar ela primeiro ou forneça o caminho completo."
                )

        if not path_obj.is_file():
            return f"Erro: '{path_obj}' não é um arquivo válido."

        try:
            import src.ui.desktop_app
            if src.ui.desktop_app.APP_INSTANCE:
                src.ui.desktop_app.APP_INSTANCE.show_floating_image(str(path_obj.resolve()))
                return f"Exibindo imagem: {path_obj.name}"
            else:
                return "Erro: Interface de janelas não inicializada."
        except Exception as e:
            return f"Falha ao exibir a imagem: {e}"

    def _search_index(self, query: str) -> str | None:
        """Busca uma imagem no índice pelo label."""
        index_path = IMAGES_DIR / "index.json"
        if not index_path.exists():
            return None
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                index = json.load(f)
            query_l = query.lower()
            # Busca do mais recente para o mais antigo
            for entry in reversed(index):
                label = entry.get("label", "").lower()
                if query_l in label or label in query_l:
                    path = entry.get("path", "")
                    if Path(path).exists():
                        return path
        except Exception:
            pass
        return None


class ListImagesTool(BaseTool):
    """Lista todas as imagens geradas anteriormente."""

    @property
    def name(self) -> str:
        return "list_generated_images"

    @property
    def description(self) -> str:
        return "Lista todas as imagens geradas pela IA, com nome e data de criação."

    @property
    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}, "required": []}

    def execute(self, args: dict[str, Any], context: dict[str, Any] = None) -> str:
        index_path = IMAGES_DIR / "index.json"
        if not index_path.exists():
            return "Nenhuma imagem foi gerada ainda."
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                index = json.load(f)
            if not index:
                return "Nenhuma imagem foi gerada ainda."
            lines = []
            for entry in reversed(index[-20:]):  # últimas 20
                label = entry.get("label", "?")
                created = entry.get("created_at", "")[:16].replace("T", " ")
                path = entry.get("path", "")
                exists = "✓" if Path(path).exists() else "✗"
                lines.append(f"  {exists} [{created}] {label}")
            return "Imagens geradas:\n" + "\n".join(lines)
        except Exception as e:
            return f"Erro ao listar imagens: {e}"
