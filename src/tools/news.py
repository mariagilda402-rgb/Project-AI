from src.tools.base import BaseTool

class NewsTool(BaseTool):
    """
    Busca notícias atuais via DuckDuckGo.
    """
    name = "get_news"
    description = "Busca as manchetes de notícias mais recentes sobre um tema específico ou notícias gerais do Brasil/Mundo."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "O tema da notícia (ex: 'tecnologia', 'política', 'economia'). Se vazio, buscará 'top news Brasil'."
            },
            "max_results": {
                "type": "integer",
                "description": "Número máximo de notícias para retornar (padrão 5, máximo 10)."
            }
        }
    }

    def execute(self, query: str = "", max_results: int = 5) -> str:
        try:
            from duckduckgo_search import DDGS
            
            if not query:
                query = "top news Brasil"
                
            max_results = min(max(1, max_results), 10)
            
            results = []
            with DDGS() as ddgs:
                for r in ddgs.news(query, max_results=max_results):
                    results.append(r)
            
            if not results:
                return f"Nenhuma notícia encontrada para o tema: {query}"
                
            formatted_news = [f"Notícias recentes sobre '{query}':"]
            for idx, r in enumerate(results, 1):
                title = r.get("title", "Sem título")
                source = r.get("source", "Fonte desconhecida")
                date = r.get("date", "")
                body = r.get("body", "")
                formatted_news.append(f"{idx}. {title} ({source} - {date})\n   Resumo: {body}\n")
                
            return "\n".join(formatted_news)

        except ImportError:
            return "Erro: pacote 'duckduckgo-search' não está instalado."
        except Exception as e:
            return f"Erro ao buscar notícias: {str(e)}"
