"""Controle local do Spotify Desktop (sem Premium, sem API Web).

Usa teclas de mídia do Windows, protocolo URI spotify: e leitura do título da janela.
"""
from __future__ import annotations

import ctypes
import subprocess
import time
import os

from .base import ToolResult

# ── Virtual Key Codes ──
_VK_MEDIA_PLAY_PAUSE = 0xB3
_VK_MEDIA_NEXT = 0xB0
_VK_MEDIA_PREV = 0xB1
_VK_MEDIA_STOP = 0xB2
_VK_RETURN = 0x0D
_VK_TAB = 0x09
_KEYEVENTF_EXTENDEDKEY = 0x0001
_KEYEVENTF_KEYUP = 0x0002


def _press(vk: int, extended: bool = True) -> None:
    flags = _KEYEVENTF_EXTENDEDKEY if extended else 0
    ctypes.windll.user32.keybd_event(vk, 0, flags, 0)
    ctypes.windll.user32.keybd_event(vk, 0, flags | _KEYEVENTF_KEYUP, 0)


def _get_spotify_window_title() -> str:
    """Lê o título da janela do Spotify via EnumWindows.
    
    Quando uma música está tocando, o título segue o padrão 'Artista - Música'.
    Quando pausado ou no menu principal, mostra 'Spotify Free' ou 'Spotify Premium'.
    """
    titles: list[str] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
    def enum_callback(hwnd, _):
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value
            # Filtra janelas do Spotify (ignora sub-janelas internas)
            if "Spotify" in title and len(title) > 3:
                titles.append(title)
        return True

    ctypes.windll.user32.EnumWindows(enum_callback, 0)

    # Prioriza títulos que parecem ser "Artista - Música"
    for t in titles:
        if " - " in t and t not in ("Spotify Free", "Spotify Premium", "Spotify"):
            return t
    # Fallback: retorna qualquer título com Spotify
    return titles[0] if titles else ""


def _is_spotify_running() -> bool:
    """Verifica se o processo Spotify.exe está ativo."""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Spotify.exe", "/NH"],
            capture_output=True, text=True, timeout=5,
            creationflags=0x08000000  # CREATE_NO_WINDOW
        )
        return "Spotify.exe" in result.stdout
    except Exception:
        return False


def _open_spotify() -> bool:
    """Abre o Spotify Desktop."""
    try:
        # Tenta via protocolo URI (funciona se o Spotify estiver instalado)
        os.startfile("spotify:")
        return True
    except Exception:
        try:
            # Fallback: tenta via Start Menu
            subprocess.Popen(
                ["cmd", "/c", "start", "", "spotify"],
                creationflags=0x08000000
            )
            return True
        except Exception:
            return False


def _focus_spotify() -> bool:
    """Traz a janela do Spotify para o primeiro plano."""
    import ctypes
    
    target_hwnd = None

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
    def enum_callback(hwnd, _):
        nonlocal target_hwnd
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value
            if "Spotify" in title and ctypes.windll.user32.IsWindowVisible(hwnd):
                target_hwnd = hwnd
                return False  # Para de enumerar
        return True

    ctypes.windll.user32.EnumWindows(enum_callback, 0)

    if target_hwnd:
        # Restaura se minimizado
        ctypes.windll.user32.ShowWindow(target_hwnd, 9)  # SW_RESTORE
        ctypes.windll.user32.SetForegroundWindow(target_hwnd)
        return True
    return False


class SpotifyTool:
    name = "spotify"
    description = "Controle local do Spotify (play, pause, skip, buscar musica, ver o que esta tocando)."
    critical = False

    def play_pause(self) -> ToolResult:
        _press(_VK_MEDIA_PLAY_PAUSE)
        return ToolResult(True, "Play/Pause alternado.")

    def next_track(self) -> ToolResult:
        _press(_VK_MEDIA_NEXT)
        return ToolResult(True, "Próxima faixa.")

    def previous_track(self) -> ToolResult:
        _press(_VK_MEDIA_PREV)
        return ToolResult(True, "Faixa anterior.")

    def current_track(self) -> ToolResult:
        title = _get_spotify_window_title()
        if not title:
            if not _is_spotify_running():
                return ToolResult(False, "Spotify não está aberto.")
            return ToolResult(True, "Spotify está aberto, mas não consigo identificar a música (pode estar pausado ou no menu).")
        if " - " in title:
            # Formato: "Artista - Música"
            return ToolResult(True, f"Tocando agora: {title}")
        return ToolResult(True, f"Spotify: {title}")

    def search_and_play(self, query: str) -> ToolResult:
        """Abre a busca no Spotify e tenta reproduzir o primeiro resultado."""
        if not query:
            return ToolResult(False, "Informe o nome da música ou artista.")

        was_running = _is_spotify_running()
        if not was_running:
            _open_spotify()
            time.sleep(2.0)

        # Abre o Spotify na busca via protocolo URI
        try:
            from urllib.parse import quote
            uri = f"spotify:search:{quote(query)}"
            os.startfile(uri)
        except Exception as e:
            return ToolResult(False, f"Erro ao abrir busca no Spotify: {e}")

        # Aguarda o app abrir e carregar a busca
        wait_time = 5.0 if not was_running else 2.5
        time.sleep(wait_time)

        # Tenta focar a janela do Spotify e pressionar Enter para tocar o primeiro resultado
        if _focus_spotify():
            time.sleep(1.0)
            # Pressiona Enter para reproduzir o primeiro resultado
            _press(_VK_RETURN, extended=False)
            return ToolResult(True, f"Busquei '{query}' no Spotify e tentei reproduzir.")
        
        return ToolResult(True, f"Abri a busca por '{query}' no Spotify, mas não consegui focar a janela para dar o play automático.")

    def open_spotify(self) -> ToolResult:
        if _is_spotify_running():
            _focus_spotify()
            return ToolResult(True, "Spotify já estava aberto, trouxe pra frente.")
        if _open_spotify():
            return ToolResult(True, "Spotify aberto.")
        return ToolResult(False, "Não consegui abrir o Spotify. Verifique se está instalado.")

    def run(self, command: str) -> ToolResult:
        """Roteia o comando por linguagem natural ou por action|arg."""
        cmd = (command or "").strip()

        # Formato estruturado: action|argument
        if "|" in cmd:
            parts = cmd.split("|", 1)
            action = parts[0].strip().lower()
            arg = parts[1].strip() if len(parts) > 1 else ""
        else:
            action, arg = self._parse_natural(cmd)

        if action in ("play", "pause", "play_pause"):
            return self.play_pause()
        if action in ("next", "skip", "pular", "proxima", "próxima"):
            return self.next_track()
        if action in ("previous", "prev", "anterior", "voltar"):
            return self.previous_track()
        if action in ("current", "tocando", "qual", "que_musica"):
            return self.current_track()
        if action in ("search", "search_and_play", "tocar", "buscar", "reproduzir"):
            return self.search_and_play(arg or cmd)
        if action in ("open", "abrir"):
            return self.open_spotify()

        # Fallback: trata como busca
        return self.search_and_play(cmd)

    def _parse_natural(self, text: str) -> tuple[str, str]:
        """Interpreta linguagem natural e extrai action + argumento."""
        t = text.lower()

        if any(kw in t for kw in ("que música", "que musica", "tocando", "qual música", "qual musica", "o que tá", "o que ta")):
            return "current", ""
        if any(kw in t for kw in ("pula", "skip", "próxima", "proxima", "pular")):
            return "next", ""
        if any(kw in t for kw in ("anterior", "volta", "voltar música", "voltar musica")):
            return "previous", ""
        if any(kw in t for kw in ("pause", "pausa", "pausar")):
            return "pause", ""
        if any(kw in t for kw in ("play", "resume", "continua", "retoma")):
            return "play", ""
        if any(kw in t for kw in ("abra", "abrir", "abre spotify")):
            return "open", ""

        # Qualquer coisa com "toque", "coloque", "bote" = buscar e tocar
        for kw in ("toque", "coloque", "bote", "reproduza", "toca", "coloca", "bota", "reproduz", "pesquise", "busque"):
            if kw in t:
                # Extrai o argumento após a keyword
                idx = t.index(kw) + len(kw)
                arg = text[idx:].strip().lstrip("a ").lstrip("o ").strip()
                if arg:
                    return "search_and_play", arg

        return "search_and_play", text
