"""Gerenciador do visualizador — servidor web (Flask + WebSocket) com orb WebGL."""
from __future__ import annotations

import json
import subprocess
import sys
import os
import time
import threading
import traceback
import atexit
from pathlib import Path

_process = None
STATE_FILE = Path("data/visualizer_state.json")
_state = {"status": "idle", "subtitle": "", "emotion": "neutral", "position": "bottom_right", "visible": True}
_server_port = int(os.environ.get("VISUALIZER_PORT", "5123"))
_browser_connected = False
_browser_check_time = 0  # Timestamp do ultimo check

def _save_state():
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Preserva campos extras (como posicao e visibilidade) ao salvar
        to_save = _state.copy()
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    current = json.load(f)
                    current.update(_state)
                    to_save = current
            except:
                pass
            
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(to_save, f, indent=2)
    except Exception as e:
        print(f"[Visualizer] Erro ao salvar estado: {e}")


def _safe_set_state(status: str, subtitle: str = "", emotion: str | None = None):
    """Wrapper seguro para mudar estado — nunca levanta exceção."""
    try:
        _state["status"] = status
        _state["subtitle"] = subtitle
        if emotion is not None:
            _state["emotion"] = emotion
        _save_state()
    except Exception as e:
        print(f"[Visualizer] Erro ao mudar estado para {status}: {e}")


def start():
    """Inicia o visualizador web (Flask + WebSocket + Orb WebGL)."""
    global _process
    if _process is not None and _process.poll() is None:
        return
        
    _save_state()
    
    app_path = Path(__file__).parent / "visualizer_app.py"
    
    # Inicia como subprocesso
    try:
        env = os.environ.copy()
        env["VISUALIZER_PORT"] = str(_server_port)
        _process = subprocess.Popen(
            [sys.executable, str(app_path), str(STATE_FILE)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        print(f"[Visualizer] Servidor Web do Orb iniciado na porta {_server_port}.")
    except Exception as e:
        print(f"[Visualizer] Falha ao iniciar visualizador: {e}")

def stop():
    global _process
    if _process:
        try:
            _process.terminate()
        except Exception:
            pass
        _process = None

atexit.register(stop)

def is_browser_connected() -> bool:
    """Verifica se o servidor web do visualizador está rodando e acessível.
    
    Usa cache de 5 segundos para evitar spam de requests.
    """
    global _browser_connected, _browser_check_time
    if _process is None or _process.poll() is not None:
        _browser_connected = False
        return False
    
    now = time.time()
    # Cache: se já checou nos últimos 5 segundos, retorna o último resultado
    if now - _browser_check_time < 5.0:
        return _browser_connected
    
    _browser_check_time = now
    try:
        import requests
        r = requests.get(f"http://localhost:{_server_port}/api/state", timeout=1)
        _browser_connected = r.status_code == 200
        return _browser_connected
    except Exception:
        _browser_connected = False
        return False


def play_audio_sync(audio_path: str) -> bool:
    """Envia um arquivo de áudio para o navegador tocar (para audio-reativo).
    
    Bloqueia até que o navegador sinalize que terminou de tocar.
    Retorna False se falhar, para que o TTS use fallback local.
    """
    if not is_browser_connected():
        return False
    
    try:
        import requests
        r = requests.post(
            f"http://localhost:{_server_port}/api/play_audio",
            json={"path": audio_path},
            timeout=5
        )
        if r.status_code != 200:
            return False
        
        # Espera o audio terminar (polling)
        max_wait = 600  # max 5 minutos (600 * 0.5s)
        for _ in range(max_wait):
            time.sleep(0.5)
            try:
                sr = requests.get(f"http://localhost:{_server_port}/api/state", timeout=2)
                if sr.status_code == 200:
                    data = sr.json()
                    if not data.get("audio_ready", False):
                        return True  # Audio terminou
            except Exception:
                pass
        return True
    except Exception as e:
        print(f"[Visualizer] Erro ao enviar audio para browser: {e}")
        return False


# ─── State setters ─── Todos são seguros (nunca levantam exceção) ───

def set_idle():
    """Estado: ocioso — respiração suave, aguardando."""
    _safe_set_state("idle", subtitle="")

def set_listening():
    """Estado: escutando — o usuário está falando."""
    _safe_set_state("listening", subtitle="")

def set_thinking():
    """Estado: pensando — a IA está processando."""
    _safe_set_state("thinking", subtitle="")

def set_speaking(subtitle: str = ""):
    """Estado: falando — a IA está respondendo com voz."""
    emotion = detect_emotion(subtitle) if subtitle else "neutral"
    _safe_set_state("speaking", subtitle=subtitle, emotion=emotion)

def set_error(detail: str = ""):
    """Estado: erro — algo deu errado."""
    _safe_set_state("error", subtitle=detail)

def set_loading(detail: str = ""):
    """Estado: carregando — conectando à API ou carregando modelo."""
    _safe_set_state("loading", subtitle=detail)

def set_success(detail: str = ""):
    """Estado: sucesso — tarefa concluída."""
    _safe_set_state("success", subtitle=detail)

def set_warning(detail: str = ""):
    """Estado: aviso — rate limit, contexto cheio, etc."""
    _safe_set_state("warning", subtitle=detail)

def set_sleeping():
    """Estado: dormindo — assistente inativa."""
    _safe_set_state("sleeping", subtitle="")

def set_emotion(emotion: str):
    """Muda apenas a emoção sem alterar o estado."""
    try:
        _state["emotion"] = emotion
        _save_state()
    except Exception:
        pass


def detect_emotion(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ("haha", "kk", "rsrs", "legal", "boa", "ótimo", "incrível", "maravilh", "show", "bacana", "massa", "parabéns", "adorei", "perfeito")):
        return "happy"
    if any(w in t for w in ("desculp", "infelizmente", "triste", "sinto muito", "pena", "não consig")):
        return "sad"
    if any(w in t for w in ("nossa", "uau", "caramba", "poxa", "sério", "impressionante", "olha só")):
        return "surprised"
    return "neutral"
