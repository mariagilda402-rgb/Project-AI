from src.tools.base import BaseTool
import urllib.request
import json
from typing import Any

class BitcoinTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_bitcoin_price"
        
    @property
    def description(self) -> str:
        return "Obtém a cotação atual do Bitcoin em Dólar (USD)."
        
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }
        
    def execute(self, args: dict[str, Any], context: dict[str, Any] = None) -> str:
        try:
            url = "https://api.coindesk.com/v1/bpi/currentprice.json"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                
            price = data["bpi"]["USD"]["rate"]
            return f"O preço atual do Bitcoin é ${price} USD."
        except Exception as e:
            return f"Falha ao buscar cotação do Bitcoin: {e}"
