"""Gerenciamento de aplicativos do Windows (listar, abrir, fechar, foco, batch)."""
from __future__ import annotations

import ctypes
import subprocess
import time
import os
import winreg
from pathlib import Path

from .base import ToolResult


# Aliases comuns PT-BR -> executável/nome real
APP_ALIASES: dict[str, str] = {
    "chrome": "chrome", "navegador": "chrome", "google chrome": "chrome",
    "bloco de notas": "notepad", "bloco de nota": "notepad", "notepad": "notepad", "bloco": "notepad",
    "código": "code", "vscode": "code", "vs code": "code", "visual studio code": "code",
    "spotify": "spotify",
    "explorador": "explorer", "arquivos": "explorer", "explorador de arquivos": "explorer",
    "calculadora": "calc", "calc": "calc",
    "paint": "mspaint",
    "terminal": "wt", "windows terminal": "wt",
    "cmd": "cmd", "prompt": "cmd",
    "powershell": "powershell",
    "discord": "discord",
    "steam": "steam",
    "word": "winword", "excel": "excel", "powerpoint": "powerpnt",
    "teams": "teams", "microsoft teams": "teams",
    "outlook": "outlook",
    "edge": "msedge", "microsoft edge": "msedge",
    "firefox": "firefox",
    "opera": "opera",
    "brave": "brave",
    "obs": "obs64", "obs studio": "obs64",
    "vlc": "vlc",
    "gimp": "gimp",
    "telegram": "telegram",
    "whatsapp": "whatsapp",
    "zoom": "zoom",
    "slack": "slack",
    "notion": "notion",
    "figma": "figma",
}


def _scan_registry_apps() -> dict[str, str]:
    """Escaneia o Registro do Windows e retorna {nome_lower: caminho_exe}."""
    apps: dict[str, str] = {}
    reg_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]

    for hive, key_path in reg_paths:
        try:
            key = winreg.OpenKey(hive, key_path)
        except OSError:
            continue
        for i in range(winreg.QueryInfoKey(key)[0]):
            try:
                subkey_name = winreg.EnumKey(key, i)
                subkey = winreg.OpenKey(key, subkey_name)
            except OSError:
                continue
            try:
                display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
            except (FileNotFoundError, OSError):
                winreg.CloseKey(subkey)
                continue
            if not display_name:
                winreg.CloseKey(subkey)
                continue

            exe_path = ""
            # Tenta DisplayIcon (geralmente aponta direto para o .exe)
            try:
                icon = winreg.QueryValueEx(subkey, "DisplayIcon")[0]
                icon = icon.split(",")[0].strip().strip('"')
                if icon.lower().endswith(".exe") and Path(icon).is_file():
                    exe_path = icon
            except (FileNotFoundError, OSError):
                pass
            
            # Tenta InstallLocation + buscar .exe dentro
            if not exe_path:
                try:
                    loc = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                    if loc and Path(loc).is_dir():
                        # Procura executável com nome parecido ao DisplayName
                        for f in Path(loc).glob("*.exe"):
                            fname = f.stem.lower()
                            dname = display_name.lower()
                            if fname in dname or dname.startswith(fname):
                                exe_path = str(f)
                                break
                        # Se não achou parecido, pega o primeiro .exe
                        if not exe_path:
                            exes = list(Path(loc).glob("*.exe"))
                            if len(exes) == 1:
                                exe_path = str(exes[0])
                except (FileNotFoundError, OSError):
                    pass
            
            winreg.CloseKey(subkey)
            if exe_path:
                apps[display_name.lower()] = exe_path
        winreg.CloseKey(key)
    return apps


def _scan_start_menu() -> dict[str, str]:
    """Escaneia atalhos do Menu Iniciar e retorna {nome_lower: caminho_lnk}."""
    shortcuts: dict[str, str] = {}
    dirs = [
        Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
    ]
    for d in dirs:
        if not d.is_dir():
            continue
        for lnk in d.rglob("*.lnk"):
            name = lnk.stem.lower()
            # Ignora atalhos de desinstalação
            if "uninstall" in name or "desinstalar" in name:
                continue
            shortcuts[name] = str(lnk)
    return shortcuts


class _AppCache:
    """Cache de apps instalados. Escaneia uma vez, depois busca instantânea."""
    _registry: dict[str, str] = {}
    _start_menu: dict[str, str] = {}
    _loaded = False

    @classmethod
    def _ensure_loaded(cls):
        if cls._loaded:
            return
        try:
            cls._registry = _scan_registry_apps()
        except Exception:
            cls._registry = {}
        try:
            cls._start_menu = _scan_start_menu()
        except Exception:
            cls._start_menu = {}
        cls._loaded = True
        total = len(cls._registry) + len(cls._start_menu)
        print(f"[AppCache] {len(cls._registry)} apps no registro, {len(cls._start_menu)} atalhos no Menu Iniciar.", flush=True)

    @classmethod
    def find(cls, name: str) -> str | None:
        """Busca um app pelo nome. Retorna o caminho do .exe ou .lnk."""
        cls._ensure_loaded()
        name_l = name.lower()

        # 1. Match exato no registro
        if name_l in cls._registry:
            return cls._registry[name_l]

        # 2. Match exato no Menu Iniciar
        if name_l in cls._start_menu:
            return cls._start_menu[name_l]

        # 3. Match parcial no registro (ex: "spotify" encontra "Spotify Premium")
        for key, path in cls._registry.items():
            if name_l in key or key.startswith(name_l):
                return path

        # 4. Match parcial no Menu Iniciar
        best_match: str | None = None
        best_score = 0.0
        for key, path in cls._start_menu.items():
            if name_l in key and len(name_l) >= 3:
                score = len(name_l) / len(key)
                if score > best_score:
                    best_score = score
                    best_match = path
        return best_match


def _enum_visible_windows() -> list[dict]:
    """Lista todas as janelas visíveis com título e PID."""
    windows: list[dict] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def callback(hwnd, _):
        if not ctypes.windll.user32.IsWindowVisible(hwnd):
            return True
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buff = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value.strip()
        if not title or title in ("Program Manager", "Settings"):
            return True
        # Pega o PID
        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        windows.append({"title": title, "hwnd": hwnd, "pid": pid.value})
        return True

    ctypes.windll.user32.EnumWindows(callback, 0)
    return windows


# Protocolos URI para apps que suportam (fallback)
_URI_PROTOCOLS = {
    "spotify": "spotify:", "discord": "discord:", "steam": "steam://open/main",
    "teams": "msteams:", "slack": "slack:", "zoom": "zoommtg:",
}

# Comandos globais do Windows (garantidos funcionar via shell)
_SYSTEM_COMMANDS = {"notepad", "calc", "mspaint", "cmd", "powershell", "explorer", "wt"}


class AppManagerTool:
    name = "app_manager"
    description = "Gerencia apps do Windows (listar instalados/abertos, abrir, fechar, foco, batch, escrever no notepad)."
    critical = False

    def list_installed(self) -> ToolResult:
        """Lista apps instalados usando o registro do Windows."""
        apps: list[str] = []
        reg_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        seen = set()
        for hive, key_path in reg_paths:
            try:
                key = winreg.OpenKey(hive, key_path)
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        subkey = winreg.OpenKey(key, subkey_name)
                        try:
                            display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                            if display_name and display_name not in seen:
                                seen.add(display_name)
                                apps.append(display_name)
                        except FileNotFoundError:
                            pass
                        winreg.CloseKey(subkey)
                    except OSError:
                        pass
                winreg.CloseKey(key)
            except OSError:
                pass

        apps.sort(key=str.lower)
        if not apps:
            return ToolResult(True, "Não encontrei apps instalados no registro.")
        total = len(apps)
        display = apps[:60]
        text = "\n".join(f"  • {a}" for a in display)
        extra = f"\n  ... e mais {total - 60} apps." if total > 60 else ""
        return ToolResult(True, f"Apps instalados ({total}):\n{text}{extra}")

    def list_running(self) -> ToolResult:
        """Lista janelas/apps abertos no momento."""
        windows = _enum_visible_windows()
        if not windows:
            return ToolResult(True, "Nenhuma janela visível encontrada.")
        seen = set()
        unique: list[str] = []
        for w in windows:
            t = w["title"]
            if t not in seen:
                seen.add(t)
                unique.append(t)
        text = "\n".join(f"  • {t}" for t in unique[:30])
        return ToolResult(True, f"Apps/janelas abertas ({len(unique)}):\n{text}")

    def open_app(self, name: str) -> ToolResult:
        """Abre um app pelo nome. Usa aliases + cache do registro + Menu Iniciar + protocolos URI."""
        name = (name or "").strip()
        if not name:
            return ToolResult(False, "Nome do app vazio.")

        # 1. Resolve Alias (PT-BR -> executável)
        name_l = name.lower()
        resolved = APP_ALIASES.get(name_l, name_l)

        # 1.5 Paths infames comuns não registrados no Windows (Spotify, Discord, etc)
        # Muitos apps se escondem em AppData/LocalAppData e não vão pro PATH global.
        infamous_paths = {
            "spotify": r"%APPDATA%\Spotify\Spotify.exe",
            "discord": r"%LOCALAPPDATA%\Discord\Update.exe --processStart Discord.exe",
            "whatsapp": r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe",
            "telegram": r"%APPDATA%\Telegram Desktop\Telegram.exe"
        }
        if resolved in infamous_paths:
            path_expanded = os.path.expandvars(infamous_paths[resolved])
            # Para comandos compostos como o discord, testamos se o exe real existe primeiro
            base_exe = path_expanded.split(" --")[0]
            if Path(base_exe).is_file():
                try:
                    subprocess.Popen(path_expanded, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return ToolResult(True, f"Aberto (caminho oculto): {resolved}")
                except Exception as e:
                    return ToolResult(False, f"Erro no caminho oculto: {e}")

        # 2. Comandos globais do Windows (notepad, calc, etc)
        if resolved in _SYSTEM_COMMANDS:
            try:
                subprocess.Popen(
                    resolved, shell=True, creationflags=0x08000000,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                return ToolResult(True, f"Aberto: {resolved}")
            except Exception as e:
                return ToolResult(False, f"Erro ao abrir {resolved}: {e}")

        # 3. Busca no cache universal (tenta alias E nome original)
        search_names = list(dict.fromkeys([resolved, name_l]))  # sem duplicatas, ordem preservada
        for search in search_names:
            cached = _AppCache.find(search)
            if cached:
                # Filtra resultados indesejados (uninstall, setup, update)
                cached_lower = cached.lower()
                if any(bad in cached_lower for bad in ("uninstall", "setup", "update.exe")):
                    continue
                try:
                    os.startfile(cached)
                    return ToolResult(True, f"Aberto: {cached}")
                except Exception as e:
                    return ToolResult(False, f"Encontrei '{name}' em {cached}, mas falhou: {e}")

        # 4. Tenta protocolo URI (spotify:, discord:, steam:, etc)
        if resolved in _URI_PROTOCOLS:
            try:
                os.startfile(_URI_PROTOCOLS[resolved])
                return ToolResult(True, f"Aberto via protocolo: {resolved}")
            except Exception:
                pass

        # 5. Último recurso: shell genérico com verificação de erro
        try:
            proc = subprocess.Popen(
                resolved, shell=True, creationflags=0x08000000,
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
            )
            try:
                proc.wait(timeout=2)
                stderr = (proc.stderr.read() or b"").decode(errors="ignore")
                if proc.returncode != 0 or "não pode encontrar" in stderr.lower():
                    return ToolResult(False, f"'{name}' não encontrado no sistema.")
            except subprocess.TimeoutExpired:
                pass  # Não terminou = provavelmente está rodando
            return ToolResult(True, f"Aberto: {resolved}")
        except Exception as e:
            return ToolResult(False, f"Falha ao abrir '{name}': {e}")

    def open_batch(self, names_str: str) -> ToolResult:
        """Abre múltiplos apps de uma vez (nomes separados por vírgula)."""
        names = [n.strip() for n in names_str.split(",") if n.strip()]
        if not names:
            return ToolResult(False, "Lista de apps vazia.")

        results: list[str] = []
        for app_name in names:
            r = self.open_app(app_name)
            symbol = "✓" if r.ok else "✗"
            results.append(f"  {symbol} {app_name}")
            time.sleep(0.4)  # Delay para o Windows processar

        return ToolResult(True, f"Resultado ({len(names)} apps):\n" + "\n".join(results))

    def close_app(self, name: str) -> ToolResult:
        """Fecha um app/janela por nome."""
        name = (name or "").strip()
        if not name:
            return ToolResult(False, "Nome do app vazio.")

        name_l = name.lower()
        resolved = APP_ALIASES.get(name_l, name_l)

        # 1. Tenta fechar por título de janela
        windows = _enum_visible_windows()
        for w in windows:
            if name_l in w["title"].lower() or resolved in w["title"].lower():
                # Envia WM_CLOSE (fechamento graceful)
                WM_CLOSE = 0x0010
                ctypes.windll.user32.PostMessageW(w["hwnd"], WM_CLOSE, 0, 0)
                return ToolResult(True, f"Fechado: {w['title']}")

        # 2. Fallback: taskkill
        exe = resolved if resolved.endswith(".exe") else resolved + ".exe"
        try:
            result = subprocess.run(
                ["taskkill", "/IM", exe, "/F"],
                capture_output=True, text=True, timeout=5,
                creationflags=0x08000000
            )
            if result.returncode == 0:
                return ToolResult(True, f"Processo '{exe}' encerrado.")
            return ToolResult(False, f"Não encontrei '{name}' aberto.")
        except Exception as e:
            return ToolResult(False, f"Erro ao fechar '{name}': {e}")

    def focus_app(self, name: str) -> ToolResult:
        """Traz uma janela para o primeiro plano."""
        name_l = (name or "").strip().lower()
        if not name_l:
            return ToolResult(False, "Nome do app vazio.")

        resolved = APP_ALIASES.get(name_l, name_l)
        windows = _enum_visible_windows()

        for w in windows:
            if name_l in w["title"].lower() or resolved in w["title"].lower():
                hwnd = w["hwnd"]
                ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                ctypes.windll.user32.SetForegroundWindow(hwnd)
                return ToolResult(True, f"Trouxe pra frente: {w['title']}")

        return ToolResult(False, f"Janela '{name}' não encontrada.")

    def write_to_notepad(self, text: str) -> ToolResult:
        """Escreve texto no Bloco de Notas (que deve estar aberto)."""
        if not text:
            return ToolResult(False, "Texto vazio.")

        # Procura a janela do Notepad
        hwnd = ctypes.windll.user32.FindWindowW("Notepad", None)
        if not hwnd:
            # Tenta abrir o Notepad
            subprocess.Popen(["notepad.exe"])
            time.sleep(1.5)
            hwnd = ctypes.windll.user32.FindWindowW("Notepad", None)
            if not hwnd:
                return ToolResult(False, "Não consegui abrir o Bloco de Notas.")

        # Foca o Notepad
        ctypes.windll.user32.ShowWindow(hwnd, 9)
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        time.sleep(0.3)

        # Encontra o campo de edição (child window da classe Edit)
        edit_hwnd = ctypes.windll.user32.FindWindowExW(hwnd, None, "Edit", None)
        if not edit_hwnd:
            # Notepad do Windows 11 usa RichEditD2DPT
            edit_hwnd = ctypes.windll.user32.FindWindowExW(hwnd, None, "RichEditD2DPT", None)
        
        if edit_hwnd:
            # Envia texto via WM_SETTEXT é destrutivo, então usamos EM_REPLACESEL para append
            EM_REPLACESEL = 0x00C2
            text_buffer = ctypes.create_unicode_buffer(text)
            ctypes.windll.user32.SendMessageW(
                edit_hwnd, EM_REPLACESEL, True, text_buffer
            )
            return ToolResult(True, f"Texto escrito no Bloco de Notas ({len(text)} caracteres).")
        
        # Fallback: usa pyautogui se disponível
        try:
            import pyautogui
            pyautogui.typewrite(text, interval=0.01) if text.isascii() else pyautogui.write(text)
            return ToolResult(True, f"Texto digitado no Bloco de Notas ({len(text)} caracteres).")
        except ImportError:
            return ToolResult(False, "Não consegui encontrar o campo de edição do Notepad.")

    def run(self, command: str) -> ToolResult:
        """Roteia por formato action|target|argument."""
        cmd = (command or "").strip()
        if not cmd:
            return ToolResult(False, "Comando vazio.")

        # Suporta tanto action|target quanto action:target
        if "|" in cmd:
            parts = cmd.split("|")
        elif ":" in cmd:
            parts = cmd.split(":", 1)
        else:
            parts = [cmd]
            
        action = parts[0].strip().lower()
        target = parts[1].strip() if len(parts) > 1 else ""
        argument = parts[2].strip() if len(parts) > 2 else ""

        if action == "list_installed":
            return self.list_installed()
        if action == "list_running":
            return self.list_running()
        if action == "open_app":
            return self.open_app(target)
        if action == "open_batch":
            return self.open_batch(target)
        if action == "close_app":
            return self.close_app(target)
        if action == "focus_app":
            return self.focus_app(target)
        if action == "write_to_notepad":
            return self.write_to_notepad(target or argument)

        return ToolResult(False, f"Ação desconhecida: {action}")
