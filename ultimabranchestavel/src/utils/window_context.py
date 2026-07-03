import ctypes
import datetime

def get_active_window_title() -> str:
    """Retorna o titulo da janela atualmente em foco no Windows."""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value
        return ""
    except Exception:
        return ""

def build_proactive_context() -> str:
    """Monta um mini-contexto para injetar na mensagem do usuario."""
    now = datetime.datetime.now()
    dias_semana = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado", "Domingo"]
    dia = dias_semana[now.weekday()]
    hora_str = now.strftime("%d/%m/%Y %H:%M")
    
    window = get_active_window_title()
    window_info = f" | Janela em foco: '{window}'" if window else ""
    
    return f"[{dia}, {hora_str}{window_info}]"
