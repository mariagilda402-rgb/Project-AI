"""Visualizador Web — Servidor Flask + WebSocket para o Orb WebGL."""
import json
import sys
import os
import time
import threading
import mimetypes
from pathlib import Path

# --- State file ---
STATE_FILE = sys.argv[1] if len(sys.argv) > 1 else "data/visualizer_state.json"
_state = {"status": "idle", "subtitle": "", "emotion": "neutral", "position": "top_left", "display_mode": "auto"}
_last_read = 0
_audio_file = None
_audio_ready = False
_ws_clients = []
_ws_lock = threading.Lock()

def read_state():
    global _state, _last_read
    now = time.time()
    if now - _last_read < 0.1:
        return _state
    _last_read = now
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                new_state = json.load(f)
                _state.update(new_state)
    except Exception:
        pass
    return _state


def broadcast_state(state_dict):
    """Envia estado para todos os clientes WebSocket conectados."""
    msg = json.dumps({"type": "state", **state_dict})
    with _ws_lock:
        dead = []
        for ws in _ws_clients:
            try:
                ws.send(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            _ws_clients.remove(ws)


def state_poll_loop():
    """Thread que faz polling do arquivo de estado e envia atualizações via WS."""
    last_state_str = ""
    while True:
        state = read_state()
        state_str = json.dumps(state, sort_keys=True)
        if state_str != last_state_str:
            last_state_str = state_str
            broadcast_state(state)
        time.sleep(0.1)


def main():
    try:
        from flask import Flask, send_from_directory, jsonify, request, make_response, send_file
        from flask_sock import Sock
    except ImportError:
        print("[Visualizer] Instalando dependencias (flask, flask-sock)...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "flask", "flask-sock", "--quiet"])
        from flask import Flask, send_from_directory, jsonify, request, make_response, send_file
        from flask_sock import Sock

    # Diretorio dos arquivos estaticos (orb.js, index.html)
    static_dir = Path(__file__).resolve().parent / "visualizer_web"
    
    app = Flask(__name__, static_folder=str(static_dir))
    sock = Sock(app)

    @app.after_request
    def add_cors_headers(response):
        """Permite CORS para áudio e APIs."""
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    @app.route("/")
    def index():
        return send_from_directory(str(static_dir), "index.html")

    @app.route("/orb.js")
    def orb_js():
        return send_from_directory(str(static_dir), "orb.js")

    @app.route("/api/state")
    def api_state():
        global _audio_ready, _audio_file
        state = read_state()
        resp = {**state}
        if _audio_ready and _audio_file:
            resp["audio_ready"] = True
            resp["audio_file"] = _audio_file
        return jsonify(resp)

    @app.route("/api/audio")
    def api_audio():
        """Serve o arquivo de áudio atual com o MIME type correto."""
        global _audio_file
        if _audio_file and os.path.isfile(_audio_file):
            abs_path = os.path.abspath(_audio_file)
            # Determina MIME type correto
            mime_type = mimetypes.guess_type(abs_path)[0] or 'audio/mpeg'
            try:
                response = send_file(
                    abs_path,
                    mimetype=mime_type,
                    as_attachment=False,
                    download_name=os.path.basename(abs_path)
                )
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response.headers['Accept-Ranges'] = 'bytes'
                return response
            except Exception as e:
                print(f"[Visualizer] Erro ao servir audio: {e}")
                return "", 500
        return "", 404

    @app.route("/api/audio_finished", methods=["POST"])
    def api_audio_finished():
        global _audio_ready, _audio_file
        _audio_ready = False
        _audio_file = None
        return "", 204

    @app.route("/api/play_audio", methods=["POST"])
    def api_play_audio():
        """Recebe path de audio do Python e notifica o browser via WS."""
        global _audio_ready, _audio_file
        data = request.get_json(silent=True) or {}
        path = data.get("path", "")
        if path and os.path.isfile(path):
            _audio_file = os.path.abspath(path)
            _audio_ready = True
            # Notifica via WebSocket
            ts = str(int(time.time() * 1000))
            msg = json.dumps({
                "type": "play_audio", 
                "url": f"/api/audio?t={ts}",
                "filename": os.path.basename(path)
            })
            with _ws_lock:
                dead = []
                for ws in _ws_clients:
                    try:
                        ws.send(msg)
                    except Exception:
                        dead.append(ws)
                for ws in dead:
                    _ws_clients.remove(ws)
            return "", 200
        return jsonify({"error": f"Arquivo nao encontrado: {path}"}), 400

    @app.route("/api/stop_audio", methods=["POST"])
    def api_stop_audio():
        """Força o navegador a parar de tocar o áudio imediatamente."""
        global _audio_ready, _audio_file
        _audio_ready = False
        _audio_file = None
        msg = json.dumps({"type": "stop_audio"})
        with _ws_lock:
            dead = []
            for ws in _ws_clients:
                try:
                    ws.send(msg)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                _ws_clients.remove(ws)
        return "", 200

    @app.route("/api/chat", methods=["POST"])
    def api_chat():
        """Recebe texto da interface do navegador (caixa de texto)."""
        data = request.get_json(silent=True) or {}
        text = data.get("text", "").strip()
        if text:
            # Escreve no arquivo para o main loop ler
            import os
            os.makedirs("data", exist_ok=True)
            with open("data/browser_chat.txt", "a", encoding="utf-8") as f:
                f.write(text + "\n")
        return "", 200

    @sock.route("/ws")
    def ws_handler(ws):
        with _ws_lock:
            _ws_clients.append(ws)
        try:
            # Envia estado atual imediatamente
            state = read_state()
            ws.send(json.dumps({"type": "state", **state}))
            # Mantem a conexao aberta
            while True:
                data = ws.receive(timeout=30)
                if data is None:
                    # Ping/keepalive
                    try:
                        ws.send(json.dumps({"type": "ping"}))
                    except Exception:
                        break
        except Exception:
            pass
        finally:
            with _ws_lock:
                if ws in _ws_clients:
                    _ws_clients.remove(ws)

    # Inicia thread de polling
    poll_thread = threading.Thread(target=state_poll_loop, daemon=True)
    poll_thread.start()

    port = int(os.environ.get("VISUALIZER_PORT", "5123"))
    print(f"[Visualizer] Servidor Web iniciado em http://localhost:{port}")
    
    # Abre o navegador automaticamente
    import webbrowser
    threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
