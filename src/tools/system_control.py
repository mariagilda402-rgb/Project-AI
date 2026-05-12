"""
System Control Tool — Inspirada no Mark-XXXIX.
Controles nativos de hardware: Volume, Brilho, Mudo e Gerenciamento de Janelas.
"""

import os
import platform
import subprocess
from typing import Any
import pyautogui

from src.tools.base import BaseTool

_OS = platform.system()

class SystemControlTool(BaseTool):
    @property
    def name(self) -> str:
        return "system_control"

    @property
    def description(self) -> str:
        return (
            "Controla hardware e janelas do sistema operacional Windows. "
            "Use para: ajustar volume (set_volume, volume_up, volume_down), "
            "ajustar brilho (set_brightness, brightness_up, brightness_down), "
            "mudar mudo (toggle_mute), gerenciar janelas (maximize, minimize, close_window), "
            "e ações de sistema (lock_screen, screenshot)."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Ação: set_volume, volume_up, volume_down, toggle_mute, set_brightness, brightness_up, brightness_down, maximize, minimize, close_window, lock_screen, screenshot"
                },
                "value": {
                    "type": "integer",
                    "description": "Valor numérico para set_volume ou set_brightness (0-100)"
                }
            },
            "required": ["action"]
        }

    def execute(self, args: dict[str, Any], context: dict[str, Any] = None) -> str:
        action = args.get("action", "").lower().strip()
        value = args.get("value")

        try:
            if action == "set_volume":
                return self._set_volume(value)
            elif action == "volume_up":
                for _ in range(5): pyautogui.press("volumeup")
                return "Volume aumentado."
            elif action == "volume_down":
                for _ in range(5): pyautogui.press("volumedown")
                return "Volume diminuído."
            elif action == "toggle_mute":
                pyautogui.press("volumemute")
                return "Mudo alternado."
            
            elif action == "set_brightness":
                return self._set_brightness(value)
            elif action == "brightness_up":
                return self._change_brightness(10)
            elif action == "brightness_down":
                return self._change_brightness(-10)

            elif action == "maximize":
                pyautogui.hotkey("win", "up")
                return "Janela maximizada."
            elif action == "minimize":
                pyautogui.hotkey("win", "down")
                return "Janela minimizada."
            elif action == "close_window":
                pyautogui.hotkey("alt", "f4")
                return "Janela fechada."
            
            elif action == "lock_screen":
                os.system("rundll32.exe user32.dll,LockWorkStation")
                return "Computador bloqueado."
            elif action == "screenshot":
                pyautogui.hotkey("win", "printscreen")
                return "Captura de tela salva na pasta de Imagens."

            return f"Ação '{action}' não reconhecida ou não suportada."

        except Exception as e:
            return f"Erro ao executar controle de sistema: {e}"

    def _set_volume(self, level: int) -> str:
        if level is None: return "Nível de volume não especificado."
        level = max(0, min(100, int(level)))
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            import math
            
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            
            # Converte volume 0-100 para dB (-65.25 a 0.0)
            if level == 0:
                volume.SetMute(1, None)
                return "Volume definido como 0 (Mudo)."
            else:
                volume.SetMute(0, None)
                vol_db = 20 * math.log10(level / 100)
                volume.SetMasterVolumeLevel(max(-65.25, vol_db), None)
                return f"Volume definido para {level}%."
        except Exception as e:
            return f"Falha ao ajustar volume via pycaw: {e}"

    def _set_brightness(self, level: int) -> str:
        if level is None: return "Nível de brilho não especificado."
        level = max(0, min(100, int(level)))
        try:
            import screen_brightness_control as sbc
            sbc.set_brightness(level)
            return f"Brilho definido para {level}%."
        except Exception as e:
            return f"Falha ao ajustar brilho: {e}"

    def _change_brightness(self, delta: int) -> str:
        try:
            import screen_brightness_control as sbc
            current = sbc.get_brightness()[0]
            new_val = max(0, min(100, current + delta))
            sbc.set_brightness(new_val)
            return f"Brilho ajustado para {new_val}%."
        except Exception as e:
            return f"Falha ao alterar brilho: {e}"
