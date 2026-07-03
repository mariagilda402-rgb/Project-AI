from __future__ import annotations

import json
import threading
from typing import Any, Callable

from werkzeug.serving import make_server

from src.jarvis_unified.device_registry import DeviceRegistry
from src.jarvis_unified.event_bus import JarvisEventBus
from src.jarvis_unified.models import DeviceInfo, JarvisEvent
from src.jarvis_unified.command_router import UnifiedCommandRouter
from src.jarvis_unified.session_state import JarvisSessionState


class UnifiedJarvisLocalBridge:
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 5124,
        token: str = "",
        on_event: Callable[[JarvisEvent], None] | None = None,
        command_router: UnifiedCommandRouter | None = None,
    ) -> None:
        self.host = host or "0.0.0.0"
        self.port = int(port or 5124)
        self.token = token or ""
        self.session_state = JarvisSessionState(active_user="local")
        self.device_registry = DeviceRegistry()
        self.event_bus = JarvisEventBus()
        self.command_router = command_router or UnifiedCommandRouter()
        if on_event:
            self.event_bus.subscribe(on_event)
        self._thread: threading.Thread | None = None
        self._server: Any | None = None
        self._clients: list[Any] = []
        self._clients_lock = threading.RLock()
        self._shutdown_lock = threading.Lock()

    def start_background(self) -> threading.Thread:
        if self._thread and self._thread.is_alive():
            return self._thread
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()
        return self._thread

    def run(self) -> None:
        try:
            from flask import Flask, jsonify, request
            from flask_sock import Sock
        except ImportError as exc:
            raise RuntimeError("flask and flask-sock are required for Unified Jarvis bridge") from exc

        app = Flask(__name__)
        sock = Sock(app)

        @app.after_request
        def add_cors_headers(response):
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            return response

        @app.route("/jarvis/status")
        def status():
            return jsonify({
                "ok": True,
                "session": self.session_state.current().to_dict(),
                "devices": [device.to_dict() for device in self.device_registry.list_devices(include_stale=True)],
            })

        @app.route("/jarvis/event", methods=["POST"])
        def post_event():
            if not self._authorized(request):
                return jsonify({"ok": False, "error": "unauthorized"}), 401
            event = JarvisEvent.from_dict(request.get_json(silent=True) or {})
            print(f"[UnifiedJarvis] HTTP event received: {event.type} from {event.source_device} target {event.target_device}")
            self._handle_event(event)
            return jsonify({"ok": True, "event_id": event.event_id})

        @sock.route("/jarvis/ws")
        def ws_handler(ws):
            if self.token:
                # flask-sock exposes the active request context here.
                supplied = request.args.get("token") or request.headers.get("Authorization", "").replace("Bearer ", "")
                if supplied != self.token:
                    ws.close()
                    return
            with self._clients_lock:
                self._clients.append(ws)
            try:
                ws.send(json.dumps({"type": "session", "session": self.session_state.current().to_dict()}))
                while True:
                    raw = ws.receive()
                    if raw is None:
                        break
                    try:
                        event = JarvisEvent.from_dict(json.loads(raw))
                    except Exception:
                        continue
                    print(f"[UnifiedJarvis] WS event received: {event.type} from {event.source_device} target {event.target_device}")
                    self._handle_event(event)
            finally:
                with self._clients_lock:
                    if ws in self._clients:
                        self._clients.remove(ws)

        print(f"[UnifiedJarvis] Local bridge em http://{self.host}:{self.port}")
        self._server = make_server(self.host, self.port, app)
        try:
            self._server.serve_forever()
        finally:
            self._server = None

    def stop(self, timeout: float = 3.0) -> None:
        with self._shutdown_lock:
            if self._server:
                try:
                    self._server.shutdown()
                except Exception as exc:
                    print(f"[UnifiedJarvis] Falha ao parar servidor: {exc}")
            with self._clients_lock:
                for ws in list(self._clients):
                    try:
                        ws.close()
                    except Exception:
                        pass
                self._clients.clear()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=timeout)
            self._server = None

    def _authorized(self, request: Any) -> bool:
        if not self.token:
            return True
        supplied = request.args.get("token") or request.headers.get("Authorization", "").replace("Bearer ", "")
        return supplied == self.token

    def _handle_event(self, event: JarvisEvent) -> None:
        if event.type != "device_register" and event.source_device:
            self.device_registry.heartbeat(event.source_device)
        if event.type == "device_register":
            device = DeviceInfo.from_dict(event.payload)
            self.device_registry.register(device)
            current = self.session_state.current()
            if not current.voice_endpoint and device.capabilities.get("voice_input"):
                self.session_state.set_voice_endpoint(device.device_id)
            if not current.display_endpoint and device.capabilities.get("display"):
                self.session_state.set_display_endpoint(device.device_id)
            self._broadcast({"type": "session", "session": self.session_state.current().to_dict()})
        elif event.type == "device_heartbeat":
            device_id = event.payload.get("device_id") or event.source_device
            self.device_registry.heartbeat(str(device_id))
        elif event.type == "handoff_voice":
            self.session_state.set_voice_endpoint(str(event.payload.get("device_id") or event.source_device))
            self._broadcast({"type": "session", "session": self.session_state.current().to_dict()})
        elif event.type == "set_action_target":
            self.session_state.set_action_target(str(event.payload.get("device_id") or event.target_device))
            self._broadcast({"type": "session", "session": self.session_state.current().to_dict()})
        elif event.type == "interrupt":
            self.session_state.interrupt()
            self._broadcast(event.to_dict())
        else:
            self._broadcast(event.to_dict())
        self.event_bus.publish(event)
        self._route_event(event)

    def _route_event(self, event: JarvisEvent) -> None:
        if not self.command_router:
            return
        try:
            outgoing = self.command_router.route_event(event, self.session_state.current())
        except Exception as exc:
            outgoing = [
                JarvisEvent.create(
                    session_id=self.session_state.current().session_id,
                    source_device="desktop:local",
                    target_device=event.source_device or "*",
                    event_type="assistant_delta",
                    payload={"text": f"Falha ao rotear comando unificado: {exc}"},
                )
            ]
        for routed_event in outgoing:
            self.emit_event(routed_event)

    def emit_event(self, event: JarvisEvent) -> None:
        self._broadcast(event.to_dict())
        self.event_bus.publish(event)

    def _broadcast(self, payload: dict[str, Any]) -> None:
        message = json.dumps(payload, ensure_ascii=False)
        with self._clients_lock:
            clients = list(self._clients)
        dead = []
        for ws in clients:
            try:
                ws.send(message)
            except Exception:
                dead.append(ws)
        if dead:
            with self._clients_lock:
                for ws in dead:
                    if ws in self._clients:
                        self._clients.remove(ws)


def start_unified_jarvis_bridge(
    settings: Any,
    on_event: Callable[[JarvisEvent], None] | None = None,
    command_router: UnifiedCommandRouter | None = None,
) -> UnifiedJarvisLocalBridge | None:
    if not getattr(settings, "unified_jarvis_enabled", False):
        return None
    bridge = UnifiedJarvisLocalBridge(
        host=getattr(settings, "unified_jarvis_host", "0.0.0.0"),
        port=getattr(settings, "unified_jarvis_port", 5124),
        token=getattr(settings, "unified_jarvis_token", ""),
        on_event=on_event,
        command_router=command_router,
    )
    bridge.start_background()
    return bridge
