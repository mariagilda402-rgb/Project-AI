"""Controle de volume e midia do Windows via teclas virtuais (sem deps extras)."""
from __future__ import annotations

import ctypes

from .base import ToolResult

# Virtual Key Codes (Windows)
_VK_VOLUME_MUTE = 0xAD
_VK_VOLUME_DOWN = 0xAE
_VK_VOLUME_UP = 0xAF
_VK_MEDIA_NEXT = 0xB0
_VK_MEDIA_PREV = 0xB1
_VK_MEDIA_STOP = 0xB2
_VK_MEDIA_PLAY_PAUSE = 0xB3
_KEYEVENTF_EXTENDEDKEY = 0x0001
_KEYEVENTF_KEYUP = 0x0002


def _press(vk: int) -> None:
    ctypes.windll.user32.keybd_event(vk, 0, _KEYEVENTF_EXTENDEDKEY, 0)
    ctypes.windll.user32.keybd_event(vk, 0, _KEYEVENTF_EXTENDEDKEY | _KEYEVENTF_KEYUP, 0)


class MediaControlTool:
    name = "media_control"
    description = "Controle de volume e midia (play, pause, volume, proximo, anterior)."
    critical = False

    _ACTIONS = {
        "volume_up": (_VK_VOLUME_UP, "Volume aumentado."),
        "volume_down": (_VK_VOLUME_DOWN, "Volume diminuido."),
        "mute": (_VK_VOLUME_MUTE, "Mute alternado."),
        "unmute": (_VK_VOLUME_MUTE, "Mute alternado."),
        "play_pause": (_VK_MEDIA_PLAY_PAUSE, "Play/Pause alternado."),
        "play": (_VK_MEDIA_PLAY_PAUSE, "Play/Pause alternado."),
        "pause": (_VK_MEDIA_PLAY_PAUSE, "Play/Pause alternado."),
        "next": (_VK_MEDIA_NEXT, "Proxima faixa."),
        "previous": (_VK_MEDIA_PREV, "Faixa anterior."),
        "stop": (_VK_MEDIA_STOP, "Midia parada."),
    }

    # Mapeamento de linguagem natural para action key.
    _NL_MAP = {
        "aumenta": "volume_up",
        "sobe": "volume_up",
        "mais alto": "volume_up",
        "louder": "volume_up",
        "abaixa": "volume_down",
        "diminui": "volume_down",
        "mais baixo": "volume_down",
        "lower": "volume_down",
        "mudo": "mute",
        "mute": "mute",
        "silenci": "mute",
        "play": "play_pause",
        "pause": "play_pause",
        "toca": "play_pause",
        "pausa": "play_pause",
        "resume": "play_pause",
        "proximo": "next",
        "próximo": "next",
        "proxima": "next",
        "próxima": "next",
        "pula": "next",
        "skip": "next",
        "next": "next",
        "anterior": "previous",
        "volta": "previous",
        "previous": "previous",
        "para": "stop",
        "stop": "stop",
    }

    def control(self, action: str) -> ToolResult:
        key = (action or "").strip().lower().replace("-", "_").replace(" ", "_")
        # Tenta match direto.
        if key in self._ACTIONS:
            vk, msg = self._ACTIONS[key]
            steps = int(key == "volume_up" or key == "volume_down") * 2 or 1
            for _ in range(steps):
                _press(vk)
            return ToolResult(True, msg)
        return ToolResult(False, f"Acao de midia desconhecida: {action}")

    def control_nl(self, text: str) -> ToolResult:
        """Interpreta linguagem natural e executa a acao correspondente."""
        lowered = (text or "").lower()
        for keyword, action in self._NL_MAP.items():
            if keyword in lowered:
                # Volume: repetir tecla para mudanca perceptivel.
                if action in ("volume_up", "volume_down"):
                    vk = self._ACTIONS[action][0]
                    for _ in range(5):
                        _press(vk)
                    return ToolResult(True, self._ACTIONS[action][1])
                return self.control(action)
        return ToolResult(False, f"Nao entendi a acao de midia: {text}")

    def run(self, command: str) -> ToolResult:
        # Tenta como action direta, senao como linguagem natural.
        key = (command or "").strip().lower().replace("-", "_").replace(" ", "_")
        if key in self._ACTIONS:
            return self.control(key)
        return self.control_nl(command)
