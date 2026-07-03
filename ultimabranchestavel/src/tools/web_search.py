"""Pesquisa web via DuckDuckGo (sem API key)."""
from __future__ import annotations

import logging
import webbrowser

from .base import ToolResult

logger = logging.getLogger(__name__)


class WebSearchTool:
    name = "web_search"
    description = "Pesquisa na web e retorna resultados resumidos."
    critical = False

    def search(self, query: str, max_results: int = 5) -> ToolResult:
        """Busca textual no DuckDuckGo e retorna resultados formatados."""
        if not (query or "").strip():
            return ToolResult(False, "Query de busca vazia.")
        try:
            from ddgs import DDGS

            with DDGS() as ddgs:
                results = list(ddgs.text(query.strip(), max_results=max_results))
            if not results:
                return ToolResult(True, f"Nenhum resultado encontrado para: {query}")
            lines: list[str] = []
            for i, r in enumerate(results, 1):
                title = r.get("title", "")
                body = r.get("body", "")
                href = r.get("href", "")
                lines.append(f"{i}. {title}\n   {body}\n   {href}")
            return ToolResult(True, "\n\n".join(lines))
        except Exception as exc:
            logger.warning("Web search falhou: %s", exc)
            return ToolResult(False, f"Erro na busca web: {exc}")

    def open_url(self, url: str) -> ToolResult:
        """Abre uma URL especifica no navegador padrao."""
        url = (url or "").strip()
        if not url:
            return ToolResult(False, "URL vazia.")
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        try:
            webbrowser.open(url)
            return ToolResult(True, f"Navegador aberto em: {url}")
        except Exception as exc:
            return ToolResult(False, f"Erro ao abrir URL: {exc}")

    def search_and_open(self, query: str) -> ToolResult:
        """Abre o navegador com uma pesquisa Google."""
        if not (query or "").strip():
            return ToolResult(False, "Query vazia.")
        from urllib.parse import quote_plus

        url = f"https://www.google.com/search?q={quote_plus(query.strip())}"
        webbrowser.open(url)
        return ToolResult(True, f"Navegador aberto com busca: {query}")

    def run(self, command: str) -> ToolResult:
        return self.search(command)
