import ctypes
import re

try:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    _PYCAW_AVAILABLE = True
except ImportError:
    _PYCAW_AVAILABLE = False

from .base import ToolResult


def _set_system_volume(percent: int):
    """Define o volume do sistema para uma porcentagem especifica (0-100)."""
    if not _PYCAW_AVAILABLE:
        return False
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        # Volume no pycaw vai de 0.0 a 1.0 ou em decibeis. Usamos escalar.
        volume.SetMasterVolumeLevelScalar(percent / 100.0, None)
        return True
    except Exception:
        return False


def _press(vk: int) -> None:
    ctypes.windll.user32.keybd_event(vk, 0, 0x0001, 0)
    ctypes.windll.user32.keybd_event(vk, 0, 0x0001 | 0x0002, 0)


class MediaControlTool:
    name = "media_control"
    description = "Controle de volume e midia (play, pause, volume especifico, proximo, anterior)."
    critical = False

    _ACTIONS = {
        "volume_up": ("Volume aumentado."),
        "volume_down": ("Volume diminuido."),
        "mute": ("Mute alternado."),
        "unmute": ("Mute alternado."),
        "play_pause": ("Play/Pause alternado."),
        "play": ("Play/Pause alternado."),
        "pause": ("Play/Pause alternado."),
        "next": ("Proxima faixa."),
        "previous": ("Faixa anterior."),
        "stop": ("Midia parada."),
    }

    _VK_MAP = {
        "volume_up": 0xAF,
        "volume_down": 0xAE,
        "mute": 0xAD,
        "play_pause": 0xB3,
        "next": 0xB0,
        "previous": 0xB1,
        "stop": 0xB2
    }

    def set_volume(self, value: int) -> ToolResult:
        """Define o volume do sistema para um valor especifico."""
        val = max(0, min(100, value))
        if _set_system_volume(val):
            return ToolResult(True, f"Volume do sistema definido para {val}%.")
        
        # Fallback se pycaw falhar: tenta aproximar com teclas (lento e impreciso)
        return ToolResult(False, "Nao consegui ajustar o volume preciso via software.")

    def run(self, command: str) -> ToolResult:
        cmd = (command or "").strip().lower()
        
        # 1. Tenta encontrar um numero no comando (ex: "volume 50")
        numbers = re.findall(r"\d+", cmd)
        if numbers and ("volume" in cmd or "definir" in cmd or "colocar" in cmd):
            return self.set_volume(int(numbers[0]))

        # 2. Mapeamento de linguagem natural
        nl_map = {
            "aumenta": "volume_up", "sobe": "volume_up", "mais alto": "volume_up",
            "abaixa": "volume_down", "diminui": "volume_down", "mais baixo": "volume_down",
            "mudo": "mute", "mute": "mute", "silenci": "mute",
            "play": "play_pause", "pause": "play_pause", "toca": "play_pause", "pausa": "play_pause",
            "proximo": "next", "próximo": "next", "pula": "next", "skip": "next",
            "anterior": "previous", "volta": "previous", "para": "stop"
        }

        for kw, action in nl_map.items():
            if kw in cmd:
                if action in ("volume_up", "volume_down"):
                    vk = self._VK_MAP[action]
                    # Repete 5 vezes para mudanca perceptivel
                    for _ in range(5): _press(vk)
                    return ToolResult(True, self._ACTIONS[action])
                
                vk = self._VK_MAP.get(action)
                if vk:
                    _press(vk)
                    return ToolResult(True, self._ACTIONS.get(action, "Feito."))

        return ToolResult(False, f"Nao entendi o comando de midia: {command}")
