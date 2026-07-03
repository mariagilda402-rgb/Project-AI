from src.tools.base import BaseTool
import urllib.request
import urllib.parse
from typing import Any

class WeatherTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_weather"
        
    @property
    def description(self) -> str:
        return "Obtém a previsão do tempo atual para uma cidade específica."
        
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "O nome da cidade (ex: Sao Paulo)"
                }
            },
            "required": ["city"]
        }
        
    def execute(self, args: dict[str, Any], context: dict[str, Any] = None) -> str:
        city = args.get("city")
        if not city:
            return "Erro: cidade não informada."
            
        try:
            city_encoded = urllib.parse.quote(city)
            url = f"https://wttr.in/{city_encoded}?format=%l:+%C+%t+(Sensação:+%f)+Vento:+%w"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                result = response.read().decode('utf-8')
            return f"Clima: {result}"
        except Exception as e:
            return f"Falha ao buscar o clima: {e}"
