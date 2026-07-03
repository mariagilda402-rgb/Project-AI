"""API exposta às janelas HTML dos módulos Nexus (pywebview)."""
from __future__ import annotations

import json

from src.ui.nexus_desktop_bridge import nexus_bridge_call


class NexusModulePyApi:
    """Uma instância por janela de módulo."""

    def __init__(self, module: str, window_ref: list | None = None):
        self.module = (module or "").strip()
        self._window_ref = window_ref if window_ref is not None else [None]
        self._is_on_top = False

    def close_module(self):
        """Fecha esta janela (botão ✕) e restaura o Orb."""
        try:
            w = self._window_ref[0] if self._window_ref else None
            if not w:
                return False
            from src.ui.desktop_app import APP_INSTANCE

            if APP_INSTANCE:
                APP_INSTANCE._nexus_module_windows.pop(self.module, None)
                # Restaura o Orb flutuante
                try:
                    if APP_INSTANCE.ghost_window:
                        APP_INSTANCE.ghost_window.show()
                        APP_INSTANCE.ghost_window.evaluate_js(
                            "document.body.style.visibility = 'visible';"
                        )
                except Exception:
                    pass

            if self.module == "unified":
                w.hide()
            else:
                w.destroy()
            return True
        except Exception as e:
            print(f"[Nexus] close_module: {e}")
            return False

    def minimize_module(self):
        """Minimiza a janela atual."""
        try:
            w = self._window_ref[0] if self._window_ref else None
            if w:
                w.minimize()
            return True
        except Exception:
            return False

    def maximize_module(self):
        """Alterna entre maximizado e tamanho normal."""
        try:
            w = self._window_ref[0] if self._window_ref else None
            if w:
                if getattr(self, '_maximized', False):
                    # ── Desmaximizar ──
                    prev_x = getattr(self, '_prev_x', None)
                    prev_y = getattr(self, '_prev_y', None)
                    prev_w = getattr(self, '_prev_w', 1000)
                    prev_h = getattr(self, '_prev_h', 700)
                    # Esconde → redimensiona → reabre para forçar
                    # o WebView2 a re-inicializar o compositor de transparência
                    w.hide()
                    if prev_x is not None and prev_y is not None:
                        w.move(prev_x, prev_y)
                    w.resize(prev_w, prev_h)
                    import time
                    time.sleep(0.15)
                    w.show()
                    self._maximized = False
                else:
                    # ── Maximizar (Fake) ──
                    self._prev_x = w.x if hasattr(w, 'x') else None
                    self._prev_y = w.y if hasattr(w, 'y') else None
                    self._prev_w = w.width if hasattr(w, 'width') else 1000
                    self._prev_h = w.height if hasattr(w, 'height') else 700
                    try:
                        import ctypes
                        from ctypes.wintypes import RECT
                        user32 = ctypes.windll.user32
                        rect = RECT()
                        user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0)
                        w.move(rect.left, rect.top)
                        w.resize(rect.right - rect.left, rect.bottom - rect.top)
                    except Exception:
                        w.maximize()
                    self._maximized = True
            return True
        except Exception:
            return False

    def toggle_always_on_top(self):
        """Alterna a janela para ficar sempre no topo.

        Usa WinForms Invoke diretamente para garantir thread-safety,
        pois o pywebview 6.x chama TopMost sem Invoke (bug).
        """
        try:
            w = self._window_ref[0] if self._window_ref else None
            if not w:
                return False

            self._is_on_top = not self._is_on_top
            on_top = self._is_on_top

            # Tentativa primária usando winforms via pywebview
            try:
                if hasattr(w, "native") and w.native:
                    from System import Action
                    form = w.native
                    if hasattr(form, "Invoke"):
                        form.Invoke(Action(lambda: setattr(form, "TopMost", on_top)))
                        return on_top
            except Exception as e:
                print(f"[UI] WinForms Invoke falhou: {e}")

            # Fallback: ctypes Win32 usando native Handle
            try:
                import ctypes
                HWND_TOPMOST = -1
                HWND_NOTOPMOST = -2
                SWP_NOSIZE = 0x0001
                SWP_NOMOVE = 0x0002
                SWP_NOACTIVATE = 0x0010

                hwnd = None
                if hasattr(w, "native") and w.native and hasattr(w.native, "Handle"):
                    hwnd = int(w.native.Handle)

                if not hwnd:
                    hwnd = ctypes.windll.user32.FindWindowW(None, w.title)

                if hwnd:
                    top = HWND_TOPMOST if on_top else HWND_NOTOPMOST
                    ctypes.windll.user32.SetWindowPos(
                        hwnd, top, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
                    )
                    return on_top
            except Exception as e2:
                print(f"[UI] ctypes fallback falhou: {e2}")

            # Last resort
            w.on_top = on_top
            return on_top
        except Exception as e:
            print(f"[UI] Erro ao alternar topo: {e}")
            return False

    def bridge(self, method: str, args_json: str = "{}") -> str:
        return nexus_bridge_call(method, args_json)

    def jump(self, module: str, payload_json: str = "{}") -> str:
        """Fecha outras janelas Nexus e abre o módulo pedido (mesmo fluxo que o painel)."""
        try:
            from src.ui.desktop_app import APP_INSTANCE

            if not APP_INSTANCE:
                return json.dumps({"ok": False, "error": "app"})
            try:
                pl = json.loads(payload_json or "{}")
            except json.JSONDecodeError:
                pl = {}
            APP_INSTANCE.open_nexus_module(str(module or "overview"), pl)
            return json.dumps({"ok": True})
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})
