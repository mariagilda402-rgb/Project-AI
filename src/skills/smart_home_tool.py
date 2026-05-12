import asyncio
from typing import Any
from src.tools.base import BaseTool
from kasa import Discover

class SmartHomeTool(BaseTool):
    @property
    def name(self) -> str:
        return "control_smart_home"
        
    @property
    def description(self) -> str:
        return "Controla dispositivos de Casa Inteligente (Smart Home) na rede local (lâmpadas e tomadas TP-Link Kasa). Use para descobrir, ligar, desligar ou mudar a cor dos aparelhos."
        
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "A ação a ser executada: 'discover' (para listar os aparelhos), 'turn_on' ou 'turn_off'."
                },
                "target_ip": {
                    "type": "string",
                    "description": "O IP do dispositivo a ser controlado (necessário para turn_on/turn_off)."
                }
            },
            "required": ["action"]
        }
        
    def execute(self, args: dict[str, Any], context: dict[str, Any] = None) -> str:
        action = args.get("action")
        target_ip = args.get("target_ip")
        
        try:
            return asyncio.run(self._run_async_action(action, target_ip))
        except Exception as e:
            return f"Erro ao controlar Smart Home: {e}"

    async def _run_async_action(self, action: str, target_ip: str) -> str:
        if action == "discover":
            print("[SmartHome] Buscando dispositivos na rede local...")
            found_devices = await Discover.discover(target="255.255.255.255", timeout=5)
            
            if not found_devices:
                return "Nenhum dispositivo smart encontrado na rede Wi-Fi local."
                
            dev_list = []
            for ip, dev in found_devices.items():
                await dev.update()
                status = "LIGADO" if dev.is_on else "DESLIGADO"
                dev_list.append(f"- {dev.alias} (IP: {ip}) | Status: {status}")
                
            return "Dispositivos encontrados:\n" + "\n".join(dev_list)
            
        elif action in ["turn_on", "turn_off"]:
            if not target_ip:
                return "Erro: target_ip é obrigatório para ligar ou desligar."
                
            dev = await Discover.discover_single(target_ip)
            if not dev:
                return f"Dispositivo {target_ip} não encontrado ou offline."
                
            if action == "turn_on":
                await dev.turn_on()
                return f"Aparelho {dev.alias} LIGADO com sucesso."
            else:
                await dev.turn_off()
                return f"Aparelho {dev.alias} DESLIGADO com sucesso."
                
        return f"Ação desconhecida: {action}"
