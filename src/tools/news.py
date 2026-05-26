from __future__ import annotations

from src.services.nexus_service import get_nexus_service
from src.tools.base import BaseTool


class NewsTool(BaseTool):
    """
    Busca noticias atuais usando o mesmo motor do Nexus News Briefing Studio.
    """

    name = "get_news"
    description = "Busca manchetes recentes sobre um tema e reutiliza o cache local do Nexus quando a busca ao vivo falha."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Tema da noticia (ex: tecnologia, politica, economia). Se vazio, usa top news Brasil.",
            },
            "max_results": {
                "type": "integer",
                "description": "Numero maximo de noticias para retornar (padrao 5, maximo 10).",
            },
        },
    }

    def execute(
        self,
        args: dict | str | None = None,
        context: dict | None = None,
        *,
        query: str = "",
        max_results: int = 5,
    ) -> str:
        if isinstance(args, dict):
            query = str(args.get("query") or args.get("topic") or query or "").strip()
            max_results = args.get("max_results") or args.get("limit") or max_results
        elif isinstance(args, str):
            query = args.strip() or query
        query = (query or "").strip() or "top news Brasil"
        try:
            limit = min(max(1, int(max_results or 5)), 10)
        except (TypeError, ValueError):
            limit = 5

        try:
            briefing = get_nexus_service().build_news_briefing(
                query,
                limit=limit,
                open_window=False,
            )
        except Exception as e:
            return f"Erro ao buscar noticias: {e}"

        items = briefing.get("items") or []
        if not briefing.get("ok") or not items:
            return briefing.get("error") or f"Nenhuma noticia encontrada para o tema: {query}"

        suffix = " (ultimo briefing salvo)" if briefing.get("from_cache") else ""
        lines = [f"Noticias recentes sobre '{briefing.get('query') or query}':{suffix}"]
        for idx, item in enumerate(items, 1):
            source = item.get("source") or "Fonte desconhecida"
            published = item.get("published_at") or ""
            lines.append(
                f"{idx}. {item.get('title') or 'Sem titulo'} ({source} - {published})\n"
                f"   Resumo: {item.get('summary') or ''}\n"
                f"   Fonte: {item.get('url') or 'sem link'}"
            )
        return "\n".join(lines)
