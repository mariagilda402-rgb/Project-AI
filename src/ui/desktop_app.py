import json
import re
import threading
import time
import os
import html as html_lib
from pathlib import Path
from dataclasses import asdict
from collections import deque

# ── Força cor de fundo do WebView2 para transparente/escuro ANTES do motor inicializar ──
# Isso impede o flash branco em resize/maximize.  Formato: AARRGGBB hex.
# 00000000 = totalmente transparente.  Se não funcionar, use 0A0A0A (escuro opaco).
os.environ.setdefault("WEBVIEW2_DEFAULT_BACKGROUND_COLOR", "00000000")

import pystray
from PIL import Image, ImageDraw
import webview

NEXUS_SCHEDULER_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><script>
setInterval(function(){ try { if (window.pywebview && pywebview.api) pywebview.api.nexus_scheduler_tick(); } catch(e) {} }, 400);
</script></head><body style="margin:0;background:#e5e7eb;"></body></html>"""


def _nexus_modules_base_dir() -> Path:
    """Diretório `src/ui/nexus_modules` (absoluto), independentemente do cwd."""
    return Path(__file__).resolve().parent / "nexus_modules"


def _normalize_nexus_theme(boot: dict | None) -> str:
    theme = str((boot or {}).get("theme") or "dark").strip().lower()
    return "light" if theme == "light" else "dark"


_NEXUS_SAFE_THEME_TOKENS = {
    "--bg",
    "--bg-panel",
    "--surface",
    "--surface-hover",
    "--border",
    "--border-accent",
    "--text",
    "--text-dim",
    "--text-muted",
    "--muted",
    "--accent",
    "--accent-hover",
    "--accent-glow",
    "--accent-subtle",
    "--danger",
    "--success",
    "--warning",
    "--sidebar",
    "--shadow",
}


def _nexus_theme_style_attr(boot: dict | None) -> str:
    tokens = (boot or {}).get("theme_tokens")
    if not isinstance(tokens, dict):
        return ""
    parts = []
    for key in sorted(_NEXUS_SAFE_THEME_TOKENS):
        if key not in tokens:
            continue
        value = str(tokens.get(key) or "").strip()
        if not value or len(value) > 96:
            continue
        if any(ch in value for ch in ['"', "'", "<", ">", "{", "}"]):
            continue
        parts.append(f"{key}: {value}")
    if not parts:
        return ""
    return ' style="' + html_lib.escape("; ".join(parts), quote=True) + '"'


def _nexus_theme_preset_attr(boot: dict | None) -> str:
    raw = str((boot or {}).get("theme_preset") or "default").strip().lower()
    preset = re.sub(r"[^a-z0-9_-]+", "-", raw).strip("-") or "default"
    return html_lib.escape(preset[:80], quote=True)


def _compose_nexus_module_html(raw_html: str, boot: dict, is_iframe: bool = False) -> str | None:
    """
    Injeta <base> + boot em JS + tema frame, e envolve o body no mesmo chrome
    do painel. Se for iframe, omite a barra de título superior.
    """
    base_uri = _nexus_modules_base_dir().as_uri().rstrip("/") + "/"
    boot = boot or {}
    theme = _normalize_nexus_theme(boot)
    boot_json = json.dumps(boot, ensure_ascii=False)
    preset_attr = _nexus_theme_preset_attr(boot)
    style_attr = _nexus_theme_style_attr(boot)
    head_inject = (
        f'<base href="{base_uri}">'
        f"<script>window.__NEXUS_BOOT__={boot_json};</script>"
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">'
        '<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap" rel="stylesheet">'
        '<link rel="stylesheet" href="nexus_frame.css" />'
        '<style>html, body { background: transparent !important; }</style>'
    )
    out, n = re.subn(r"</head>", head_inject + "</head>", raw_html, count=1, flags=re.I)
    if n != 1:
        return None

    if is_iframe:
        chrome_open = (
            f'<div id="nx-app-wrapper" class="neon-enabled" data-theme="{theme}" '
            f'data-theme-preset="{preset_attr}"{style_attr}>'
            '<div class="nx-chrome-inner" style="border-radius: 0;">'
        )
    else:
        chrome_open = (
            f'<div id="nx-app-wrapper" class="neon-enabled" data-theme="{theme}" '
            f'data-theme-preset="{preset_attr}"{style_attr}>'
            '<div class="nx-chrome-bar">'
            '<div class="nx-chrome-title"><span class="nx-dot"></span><span>Nexus Life OS</span></div>'
            '<div class="nx-chrome-actions">'
            '<button type="button" class="nx-theme-toggle" '
            'onclick="if(window.pywebview&&pywebview.api)pywebview.api.toggle_always_on_top().then(r => this.style.color = r ? \'var(--accent)\' : \'inherit\');" '
            'title="Fixar no Topo">📌</button>'
            '<button type="button" class="nx-theme-toggle" data-nx-theme-toggle '
            'onclick="if(window.nxToggleTheme)window.nxToggleTheme();" '
            'title="Alternar tema" aria-label="Alternar tema">◐</button>'
            '<button type="button" class="nx-chrome-close" '
            'onclick="if(window.pywebview&&pywebview.api)pywebview.api.minimize_module();" '
            'title="Minimizar">_</button>'
            '<button type="button" class="nx-chrome-close" '
            'onclick="if(window.pywebview&&pywebview.api)pywebview.api.maximize_module();" '
            'title="Maximizar">□</button>'
            '<button type="button" class="nx-chrome-close" '
            'onclick="if(window.pywebview&&pywebview.api)pywebview.api.close_module();" '
            'title="Fechar">✕</button>'
            "</div>"
            "</div>"
            '<div class="nx-chrome-inner">'
        )
    out, n = re.subn(r"(<body[^>]*>)", r"\1" + chrome_open, out, count=1, flags=re.I)
    if n != 1:
        return None
    out, n = re.subn(r"</body>", "</div></div></body>", out, count=1, flags=re.I)
    if n != 1:
        return None
    return out


def create_tray_icon():
    # Cria um icone simples para a bandeja
    image = Image.new('RGB', (64, 64), color=(30, 30, 30))
    d = ImageDraw.Draw(image)
    d.ellipse((16, 16, 48, 48), fill=(0, 200, 255))
    return image

APP_INSTANCE = None

class DesktopApi:
    def __init__(
        self,
        task_queue,
        agent_manager,
        settings,
        chat_log=None,
        system_logs=None,
        confirm_bus=None,
        runtime_status=None,
        llm=None,
        tts=None,
        stt=None,
        tools=None,
    ):
        self.task_queue = task_queue
        self.agent_manager = agent_manager
        self.settings = settings
        self._chat_log = chat_log if chat_log is not None else []
        self._system_logs = system_logs if system_logs is not None else []
        self._confirm_bus = confirm_bus
        self._runtime_status = runtime_status
        self._llm = llm
        self._tts = tts
        self._stt = stt
        self._tools = tools

    def get_critical_confirm_pending(self):
        """Retorna {id, tool_name, detail} ou None se não houver pedido pendente."""
        if not self._confirm_bus or not self._confirm_bus.enabled:
            return None
        return self._confirm_bus.get_pending()

    def resolve_critical_confirm(self, request_id, approved):
        if not self._confirm_bus or not request_id:
            return False
        return self._confirm_bus.resolve(str(request_id), bool(approved))

    def get_chat_history(self, since_index=0):
        """Retorna mensagens do chat a partir de um índice."""
        idx = max(0, int(since_index))
        return {"messages": self._chat_log[idx:], "total": len(self._chat_log)}

    def get_system_logs(self, since_index=0):
        """Retorna logs do sistema a partir de um índice."""
        idx = max(0, int(since_index))
        return {"logs": self._system_logs[idx:], "total": len(self._system_logs)}

    def toggle_mic(self):
        # ... envia evento de toggle mic
        if self.task_queue:
            self.task_queue.put(("/toggle_mic", "Painel"))
        return True

    def get_status(self):
        snap = self._runtime_status.snapshot() if self._runtime_status else {}
        qsz = -1
        if self.task_queue:
            try:
                qsz = self.task_queue.qsize()
            except NotImplementedError:
                qsz = -1
        lp = getattr(self._llm, "last_provider", "") if self._llm else ""
        lm = getattr(self._llm, "last_model", "") if self._llm else ""
        hotkey = ""
        if self.settings:
            hotkey = getattr(self.settings, "panel_hotkey", "win+shift+a")
        recent = []
        if self._tools and hasattr(self._tools, "get_recent_tool_events"):
            recent = self._tools.get_recent_tool_events()
        return {
            **snap,
            "queue_approx": qsz,
            "llm_last_provider": lp,
            "llm_last_model": lm,
            "panel_hotkey": hotkey,
            "recent_tools": recent,
        }

    def diagnostics_audio(self):
        try:
            from src.check_audio import run_audio_diagnostics
            return run_audio_diagnostics(self.settings)
        except Exception as e:
            return {"error": str(e)[:200]}

    def diagnostics_tts(self):
        if self.task_queue:
            self.task_queue.put(("/tts_test", "Painel"))
            return True
        return False

    def diagnostics_llm(self):
        if self.task_queue:
            self.task_queue.put(("/diagnostics_llm", "Painel"))
            return True
        return False

    def get_telemetry_tail(self, max_lines=50):
        try:
            from src.telemetry.events import read_event_tail
            return read_event_tail(int(max_lines))
        except Exception as e:
            return [{"error": str(e)}]

    def get_structured_memory(self):
        try:
            from src.memory.structured_memory import load_structured_memory
            return load_structured_memory()
        except Exception as e:
            print(f"[DesktopApi] structured memory: {e}")
            return {}

    def delete_structured_memory_entry(self, category, key):
        try:
            from src.memory.structured_memory import forget
            return forget(str(key or "").strip(), str(category or "notes").strip())
        except Exception as e:
            print(f"[DesktopApi] forget: {e}")
            return f"Erro: {e}"

    def get_tools_reference(self):
        try:
            from src.agent import prompts as pr
            return {
                "markers_block": pr.AGENT_SYSTEM_CORE,
                "function_calling_intro": pr.AGENT_SYSTEM_PROMPT_FUNCTION_CALLING[:2200],
            }
        except Exception as e:
            return {"error": str(e)}

    def get_critical_actions_reference(self):
        try:
            from src.tools.critical_actions import critical_actions_reference
            return critical_actions_reference()
        except Exception as e:
            return {"error": str(e)}

    _PREF_EXPORT_PATHS = (
        "data/critical_confirm_enabled.json",
        "data/agents.json",
        "data/visualizer_state.json",
    )

    def export_preferences_bundle(self):
        try:
            import tkinter as tk
            from tkinter import filedialog

            bundle = {}
            for rel in self._PREF_EXPORT_PATHS:
                p = Path(rel)
                if p.exists():
                    try:
                        bundle[rel] = json.loads(p.read_text(encoding="utf-8"))
                    except Exception:
                        bundle[rel] = None
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON", "*.json")],
                title="Exportar preferências (sem segredos)",
                initialfile="jarvis_preferences.json",
            )
            root.destroy()
            if not path:
                return False
            Path(path).write_text(
                json.dumps(bundle, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return True
        except Exception as e:
            print(f"[DesktopApi] export prefs: {e}")
            return False

    def import_preferences_bundle(self):
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            path = filedialog.askopenfilename(
                filetypes=[("JSON", "*.json")],
                title="Importar preferências",
            )
            root.destroy()
            if not path:
                return False
            raw = Path(path).read_text(encoding="utf-8")
            bundle = json.loads(raw)
            if not isinstance(bundle, dict):
                return False
            for rel, val in bundle.items():
                if rel not in self._PREF_EXPORT_PATHS or val is None:
                    continue
                p = Path(rel)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(json.dumps(val, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
        except Exception as e:
            print(f"[DesktopApi] import prefs: {e}")
            return False

    def send_chat_message(self, text):
        """Envia uma mensagem de texto do painel para a fila do orquestrador."""
        if not text or not str(text).strip(): return False
        if self.task_queue:
            self.task_queue.put((str(text).strip(), "Painel"))
            return True
        return False

    def start_round_robin(self, query, agent_ids, chained=False):
        """Dispara modo Round-Robin na fila de tarefas."""
        if self.task_queue:
            import queue
            while not self.task_queue.empty():
                try: self.task_queue.get_nowait(); self.task_queue.task_done()
                except queue.Empty: break
            cmd = f"/roundrobin|{chained}|{','.join(agent_ids)}|{query}"
            self.task_queue.put((cmd, "Painel"))
        return True

    def start_debate(self, topic, agent_ids, rounds=3):
        """Dispara modo Debate na fila de tarefas."""
        if self.task_queue:
            import queue
            while not self.task_queue.empty():
                try: self.task_queue.get_nowait(); self.task_queue.task_done()
                except queue.Empty: break
            cmd = f"/debate|{rounds}|{','.join(agent_ids)}|{topic}"
            self.task_queue.put((cmd, "Painel"))
        return True

    def select_file(self):
        """Abre a janela nativa para selecionar um arquivo."""
        try:
            import webview
            window = webview.windows[0]
            result = window.create_file_dialog(webview.OPEN_DIALOG)
            if result and len(result) > 0:
                return result[0]
        except Exception as e:
            print(f"[UI] Erro ao selecionar arquivo: {e}")
        return None

    def process_file(self, path, action=""):
        """Coloca na fila uma task para processar o arquivo."""
        if path and self.task_queue:
            cmd = f'Processe o arquivo "{path}". {action}'.strip()
            self.task_queue.put((cmd, "Painel"))
            return True
        return False

    # ── Agents CRUD ──

    def list_agents(self):
        if not self.agent_manager: return []
        return [asdict(a) for a in self.agent_manager.list_agents()]

    def get_active_agent_id(self):
        if not self.agent_manager: return ""
        return self.agent_manager._active_agent_id

    def set_active_agent(self, agent_id):
        if not self.agent_manager: return False
        ok = self.agent_manager.set_active_agent(agent_id)
        if ok:
            self._apply_active_agent_tts()
        return ok

    def _apply_active_agent_tts(self):
        if not self.agent_manager or not self._tts:
            return
        try:
            ag = self.agent_manager.get_active_agent()
            self._tts.apply_agent_voice(
                provider=ag.tts_provider,
                voice=ag.tts_voice,
                speed=ag.tts_speed,
                edge_rate=ag.edge_tts_rate,
                edge_vol=ag.edge_tts_volume,
                kokoro_voice=ag.kokoro_voice,
            )
        except Exception as e:
            print(f"[DesktopApi] Erro ao aplicar TTS do agente: {e}")

    def create_agent(self, data):
        if not self.agent_manager: return None
        try: speed = float(data.get('tts_speed', 1.0) or 1.0)
        except (TypeError, ValueError): speed = 1.0
        agent = self.agent_manager.create_agent(
            name=data.get('name', 'Novo Agente'),
            persona=data.get('persona', 'Assistente padrão.'),
            tts_provider=data.get('tts_provider', getattr(self.settings, "tts_provider", "edge") if self.settings else "edge"),
            tts_voice=data.get('tts_voice', 'pt-BR-FranciscaNeural'),
            tts_speed=speed,
            kokoro_voice=data.get('kokoro_voice', 'pf_dora'),
        )
        return asdict(agent) if agent else None

    def update_agent(self, agent_id, data):
        if not self.agent_manager: return None
        try: speed = float(data.get('tts_speed', 1.0) or 1.0)
        except (TypeError, ValueError): speed = 1.0
        agent = self.agent_manager.update_agent(
            agent_id,
            name=data.get('name'),
            persona=data.get('persona'),
            tts_provider=data.get('tts_provider'),
            tts_voice=data.get('tts_voice'),
            tts_speed=speed,
            kokoro_voice=data.get('kokoro_voice'),
        )
        if agent and agent.id == self.agent_manager._active_agent_id:
            self._apply_active_agent_tts()
        return asdict(agent) if agent else None

    def delete_agent(self, agent_id):
        if not self.agent_manager: return False
        return self.agent_manager.delete_agent(agent_id)

    def list_trash_agents(self):
        if not self.agent_manager: return []
        return [asdict(a) for a in self.agent_manager.list_trash_agents()]

    def restore_agent(self, agent_id):
        if not self.agent_manager: return False
        return self.agent_manager.restore_agent(agent_id)

    def permanent_delete_agent(self, agent_id):
        if not self.agent_manager: return False
        return self.agent_manager.permanent_delete_agent(agent_id)

    # ── Memory CRUD ──
    def list_memories(self, collection_name, query=""):
        try:
            from src.memory.vector_db import SemanticMemory
            sm = SemanticMemory()
            if not sm.enabled: return None

            coll = sm._get_or_create_collection(collection_name)

            if query:
                results = coll.get(
                    where_document={"$contains": query},
                    include=["documents"],
                    limit=50
                )
            else:
                results = coll.get(include=["documents"], limit=100)

            memories = []
            if results and results.get("ids"):
                for mid, doc in zip(results["ids"], results["documents"]):
                    memories.append({"id": mid, "text": doc})
            return {"total": len(memories), "memories": memories}
        except Exception as e:
            print(f"[DesktopApi] Erro ao listar memórias: {e}")
            return None

    def export_memories(self, collection_name):
        """Abre janela para salvar JSON das memórias."""
        try:
            from src.memory.vector_db import SemanticMemory
            import tkinter as tk
            from tkinter import filedialog

            sm = SemanticMemory()
            if not sm.enabled: return False
            coll = sm._get_or_create_collection(collection_name)
            res = coll.get(include=["documents", "metadatas"])

            data_to_export = []
            if res and res.get("ids"):
                for doc, meta in zip(res["documents"], res["metadatas"]):
                    data_to_export.append({"text": doc, "metadata": meta})

            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
                title="Exportar Memórias",
                initialfile=f"{collection_name}_backup.json"
            )
            root.destroy()

            if path:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data_to_export, f, ensure_ascii=False, indent=2)
                return True
            return False
        except Exception as e:
            print(f"[DesktopApi] Erro ao exportar: {e}")
            return False

    def trigger_import_memories(self, collection_name):
        """Abre janela para selecionar JSON e manda pra fila importar."""
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            path = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json")],
                title="Importar Memórias"
            )
            root.destroy()

            if path and self.task_queue:
                cmd = f"/import_memory|{collection_name}|{path}"
                self.task_queue.put((cmd, "Painel"))
                return True
            return False
        except Exception as e:
            print(f"[DesktopApi] Erro ao engatilhar importação: {e}")
            return False

    def delete_memory(self, collection_name, memory_id):
        """Move uma memória para a lixeira (Fase 4.2)."""
        try:
            from src.memory.vector_db import SemanticMemory
            sm = SemanticMemory()
            if not sm.enabled: return False

            coll = sm._get_or_create_collection(collection_name)
            res = coll.get(ids=[memory_id], include=["documents", "embeddings", "metadatas"])
            if not res or not res["ids"]: return False

            doc = res["documents"][0]
            emb = res["embeddings"][0] if "embeddings" in res and res["embeddings"] else None
            meta = res["metadatas"][0] if "metadatas" in res and res["metadatas"] else {}
            meta["original_collection"] = collection_name

            trash_coll = sm._get_or_create_collection("trash_memories")
            if emb:
                trash_coll.add(ids=[memory_id], embeddings=[emb], documents=[doc], metadatas=[meta])
            else:
                trash_coll.add(ids=[memory_id], documents=[doc], metadatas=[meta])

            coll.delete(ids=[memory_id])
            return True
        except Exception as e:
            print(f"[DesktopApi] Erro ao mover memória para lixeira: {e}")
            return False

    def list_trash_memories(self):
        """Lista memórias na lixeira."""
        try:
            from src.memory.vector_db import SemanticMemory
            sm = SemanticMemory()
            if not sm.enabled: return []
            trash_coll = sm._get_or_create_collection("trash_memories")
            results = trash_coll.get(include=["documents", "metadatas"])
            memories = []
            if results and results.get("ids"):
                for mid, doc, meta in zip(results["ids"], results["documents"], results["metadatas"]):
                    memories.append({
                        "id": mid,
                        "text": doc,
                        "original_collection": meta.get("original_collection", "Desconhecido") if meta else "Desconhecido"
                    })
            return memories
        except Exception as e:
            print(f"[DesktopApi] Erro ao listar lixeira de memórias: {e}")
            return []

    def restore_memory(self, memory_id):
        """Restaura a memória da lixeira para a coleção original."""
        try:
            from src.memory.vector_db import SemanticMemory
            sm = SemanticMemory()
            if not sm.enabled: return False

            trash_coll = sm._get_or_create_collection("trash_memories")
            res = trash_coll.get(ids=[memory_id], include=["documents", "embeddings", "metadatas"])
            if not res or not res["ids"]: return False

            doc = res["documents"][0]
            emb = res["embeddings"][0] if "embeddings" in res and res["embeddings"] else None
            meta = res["metadatas"][0] if "metadatas" in res and res["metadatas"] else {}
            orig_coll_name = meta.pop("original_collection", "user_memories")

            orig_coll = sm._get_or_create_collection(orig_coll_name)
            if emb:
                orig_coll.add(ids=[memory_id], embeddings=[emb], documents=[doc], metadatas=[meta])
            else:
                orig_coll.add(ids=[memory_id], documents=[doc], metadatas=[meta])

            trash_coll.delete(ids=[memory_id])
            return True
        except Exception as e:
            print(f"[DesktopApi] Erro ao restaurar memória: {e}")
            return False

    def permanent_delete_memory(self, memory_id):
        """Deleta permanentemente da lixeira."""
        try:
            from src.memory.vector_db import SemanticMemory
            sm = SemanticMemory()
            if not sm.enabled: return False
            trash_coll = sm._get_or_create_collection("trash_memories")
            trash_coll.delete(ids=[memory_id])
            return True
        except Exception as e:
            print(f"[DesktopApi] Erro ao deletar memória da lixeira: {e}")
            return False

    def get_config(self):
        if not self.settings: return {}
        s = self.settings
        return {
            'llm_provider': s.llm_provider,
            'gemini_model': s.gemini_model,
            'groq_model': s.groq_model,
            'tts_provider': s.tts_provider,
            'tts_provider_order': getattr(s, "tts_provider_order", ""),
            'tts_voice': s.tts_voice,
            'stt_language': s.stt_language,
            'use_mic': s.use_mic,
            'stt_energy_threshold': getattr(s, "stt_energy_threshold", 1100),
            'stt_dynamic_energy': getattr(s, "stt_dynamic_energy", True),
            'stt_pause_threshold': getattr(s, "stt_pause_threshold", 0.8),
            'stt_non_speaking_duration': getattr(s, "stt_non_speaking_duration", 0.35),
            'stt_calibration_seconds': getattr(s, "stt_calibration_seconds", 0.8),
            'stt_min_audio_seconds': getattr(s, "stt_min_audio_seconds", 0.35),
            'enable_visualizer': s.enable_visualizer,
            'start_vision_tracker': getattr(s, "start_vision_tracker", False),
            'start_heartbeat': getattr(s, "start_heartbeat", True),
            'start_proactive_agent': getattr(s, "start_proactive_agent", False),
            'enable_clap_trigger': getattr(s, "enable_clap_trigger", True),
            'clap_threshold': getattr(s, "clap_threshold", 0.15),
            'clap_min_gap': getattr(s, "clap_min_gap", 0.1),
            'clap_max_gap': getattr(s, "clap_max_gap", 1.2),
            'clap_cooldown': getattr(s, "clap_cooldown", 3.0),
            'edge_tts_rate': s.edge_tts_rate,
            'kokoro_voice': s.kokoro_voice,
            'xtts_preload': getattr(s, "xtts_preload", True),
            'styletts2_python': getattr(s, "styletts2_python", ""),
            'styletts2_reference_wav': getattr(s, "styletts2_reference_wav", ""),
            'styletts2_alpha': getattr(s, "styletts2_alpha", 0.3),
            'styletts2_beta': getattr(s, "styletts2_beta", 0.7),
            'styletts2_diffusion_steps': getattr(s, "styletts2_diffusion_steps", 3),
            'styletts2_embedding_scale': getattr(s, "styletts2_embedding_scale", 1.0),
            'styletts2_persistent': getattr(s, "styletts2_persistent", True),
            'styletts2_preload': getattr(s, "styletts2_preload", False),
            'tts_prefetch_chunks': getattr(s, "tts_prefetch_chunks", True),
            'piper_repo_id': getattr(s, "piper_repo_id", "jgkawell/jarvis"),
            'piper_jarvis_quality': getattr(s, "piper_jarvis_quality", "medium"),
            'piper_use_cuda': getattr(s, "piper_use_cuda", False),
            'piper_fx_preset': getattr(s, "piper_fx_preset", "none"),
            'critical_confirm_enabled': self.get_critical_confirm_enabled(),
            'panel_hotkey': getattr(s, "panel_hotkey", "win+shift+a"),
            'vision_detail_default': getattr(s, "vision_detail_default", False),
            'study_professor_mode': getattr(s, "study_professor_mode", False),
            'ui_motion_level': getattr(s, "ui_motion_level", "balanced"),
            'ui_density': getattr(s, "ui_density", "comfortable"),
        }

    def _update_env_file(self, updates: dict[str, object]) -> None:
        env_path = Path(__file__).resolve().parents[2] / ".env"
        existing = env_path.read_text(encoding="utf-8-sig") if env_path.exists() else ""
        lines = existing.splitlines()
        seen: set[str] = set()
        rendered: list[str] = []
        for line in lines:
            key = line.split("=", 1)[0].strip() if "=" in line and not line.lstrip().startswith("#") else ""
            if key in updates:
                if key in seen:
                    continue
                rendered.append(f"{key}={updates[key]}")
                seen.add(key)
            else:
                rendered.append(line)
        for key, value in updates.items():
            if key not in seen:
                rendered.append(f"{key}={value}")
        env_path.write_text("\n".join(rendered) + "\n", encoding="utf-8")

    def update_tts_config(self, data):
        if not self.settings or not self._tts:
            return {"ok": False, "error": "TTS/settings indisponiveis."}
        try:
            provider = str(data.get("tts_provider") or getattr(self.settings, "tts_provider", "edge")).strip().lower()
            order = str(data.get("tts_provider_order") or getattr(self.settings, "tts_provider_order", "")).strip()
            style_python = str(data.get("styletts2_python") or "").strip()
            style_ref = str(data.get("styletts2_reference_wav") or "").strip()
            diffusion = max(1, min(20, int(float(data.get("styletts2_diffusion_steps") or 3))))
            embedding = max(0.1, min(10.0, float(data.get("styletts2_embedding_scale") or 1.0)))
            prefetch = bool(data.get("tts_prefetch_chunks", True))

            updates = {
                "TTS_PROVIDER": provider,
                "TTS_PROVIDER_ORDER": order,
                "STYLETTS2_PYTHON": style_python,
                "STYLETTS2_REFERENCE_WAV": style_ref,
                "STYLETTS2_DIFFUSION_STEPS": diffusion,
                "STYLETTS2_EMBEDDING_SCALE": embedding,
                "STYLETTS2_PERSISTENT": "true",
                "STYLETTS2_PRELOAD": "true" if provider == "styletts2" else "false",
                "TTS_PREFETCH_CHUNKS": "true" if prefetch else "false",
            }
            self._update_env_file(updates)

            object.__setattr__(self.settings, "tts_provider", provider)
            object.__setattr__(self.settings, "tts_provider_order", order)
            object.__setattr__(self.settings, "styletts2_python", style_python)
            object.__setattr__(self.settings, "styletts2_reference_wav", style_ref)
            object.__setattr__(self.settings, "styletts2_diffusion_steps", diffusion)
            object.__setattr__(self.settings, "styletts2_embedding_scale", embedding)
            object.__setattr__(self.settings, "styletts2_persistent", True)
            object.__setattr__(self.settings, "styletts2_preload", provider == "styletts2")
            object.__setattr__(self.settings, "tts_prefetch_chunks", prefetch)

            self._tts.provider = provider
            self._tts.provider_order_config = order
            from src.services.tts import resolve_tts_provider_order

            self._tts.provider_order = resolve_tts_provider_order(provider, order)
            self._tts.styletts2_python = style_python
            self._tts.styletts2_reference_wav = style_ref
            self._tts.styletts2_diffusion_steps = diffusion
            self._tts.styletts2_embedding_scale = embedding
            self._tts.styletts2_persistent = True
            self._tts.styletts2_preload = provider == "styletts2"
            self._tts.tts_prefetch_chunks = prefetch
            if provider == "styletts2":
                self._tts.warmup_styletts2_async()

            return {"ok": True, "provider": provider, "order": self._tts.provider_order}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def update_stt_config(self, data):
        if not self.settings:
            return {"ok": False, "error": "Settings indisponiveis."}
        try:
            use_mic = bool(data.get("use_mic", getattr(self.settings, "use_mic", True)))
            language = str(data.get("stt_language") or getattr(self.settings, "stt_language", "pt-BR")).strip() or "pt-BR"
            energy = max(150, min(8000, int(float(data.get("stt_energy_threshold") or 1100))))
            dynamic = bool(data.get("stt_dynamic_energy", True))
            pause = max(0.25, min(3.0, float(data.get("stt_pause_threshold") or 0.8)))
            non_speaking = max(0.1, min(2.0, float(data.get("stt_non_speaking_duration") or 0.35)))
            calibration = max(0.1, min(5.0, float(data.get("stt_calibration_seconds") or 0.8)))
            min_audio = max(0.05, min(3.0, float(data.get("stt_min_audio_seconds") or 0.35)))

            updates = {
                "USE_MIC": "true" if use_mic else "false",
                "STT_LANGUAGE": language,
                "STT_ENERGY_THRESHOLD": energy,
                "STT_DYNAMIC_ENERGY": "true" if dynamic else "false",
                "STT_PAUSE_THRESHOLD": pause,
                "STT_NON_SPEAKING_DURATION": non_speaking,
                "STT_CALIBRATION_SECONDS": calibration,
                "STT_MIN_AUDIO_SECONDS": min_audio,
            }
            self._update_env_file(updates)

            object.__setattr__(self.settings, "use_mic", use_mic)
            object.__setattr__(self.settings, "stt_language", language)
            object.__setattr__(self.settings, "stt_energy_threshold", energy)
            object.__setattr__(self.settings, "stt_dynamic_energy", dynamic)
            object.__setattr__(self.settings, "stt_pause_threshold", pause)
            object.__setattr__(self.settings, "stt_non_speaking_duration", non_speaking)
            object.__setattr__(self.settings, "stt_calibration_seconds", calibration)
            object.__setattr__(self.settings, "stt_min_audio_seconds", min_audio)

            if self._stt and hasattr(self._stt, "configure"):
                self._stt.configure(
                    use_mic=use_mic,
                    language=language,
                    energy_threshold=energy,
                    dynamic_energy_threshold=dynamic,
                    pause_threshold=pause,
                    non_speaking_duration=non_speaking,
                    min_audio_seconds=min_audio,
                )
                if use_mic and bool(data.get("recalibrate", False)):
                    self._stt.calibrate(duration=calibration)
                    if self._runtime_status:
                        backend = "groq" if getattr(self._stt, "groq_client", None) else "google"
                        self._runtime_status.set_stt_info(backend, self._stt.calibrated)

            return {
                "ok": True,
                "stt_language": language,
                "stt_energy_threshold": energy,
                "stt_dynamic_energy": dynamic,
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def update_startup_config(self, data):
        if not self.settings:
            return {"ok": False, "error": "Settings indisponiveis."}
        try:
            start_vision = bool(data.get("start_vision_tracker", False))
            start_heartbeat = bool(data.get("start_heartbeat", True))
            start_proactive = bool(data.get("start_proactive_agent", False))
            enable_clap = bool(data.get("enable_clap_trigger", True))
            clap_threshold = max(0.03, min(1.0, float(data.get("clap_threshold") or 0.15)))
            clap_min_gap = max(0.02, min(1.0, float(data.get("clap_min_gap") or 0.1)))
            clap_max_gap = max(0.2, min(4.0, float(data.get("clap_max_gap") or 1.2)))
            clap_cooldown = max(0.5, min(20.0, float(data.get("clap_cooldown") or 3.0)))
            xtts_preload = bool(data.get("xtts_preload", getattr(self.settings, "xtts_preload", True)))
            styletts2_preload = bool(data.get("styletts2_preload", getattr(self.settings, "styletts2_preload", False)))

            updates = {
                "START_VISION_TRACKER": "true" if start_vision else "false",
                "START_HEARTBEAT": "true" if start_heartbeat else "false",
                "START_PROACTIVE_AGENT": "true" if start_proactive else "false",
                "ENABLE_CLAP_TRIGGER": "true" if enable_clap else "false",
                "CLAP_THRESHOLD": clap_threshold,
                "CLAP_MIN_GAP": clap_min_gap,
                "CLAP_MAX_GAP": clap_max_gap,
                "CLAP_COOLDOWN": clap_cooldown,
                "XTTS_PRELOAD": "true" if xtts_preload else "false",
                "STYLETTS2_PRELOAD": "true" if styletts2_preload else "false",
            }
            self._update_env_file(updates)

            object.__setattr__(self.settings, "start_vision_tracker", start_vision)
            object.__setattr__(self.settings, "start_heartbeat", start_heartbeat)
            object.__setattr__(self.settings, "start_proactive_agent", start_proactive)
            object.__setattr__(self.settings, "enable_clap_trigger", enable_clap)
            object.__setattr__(self.settings, "clap_threshold", clap_threshold)
            object.__setattr__(self.settings, "clap_min_gap", clap_min_gap)
            object.__setattr__(self.settings, "clap_max_gap", clap_max_gap)
            object.__setattr__(self.settings, "clap_cooldown", clap_cooldown)
            object.__setattr__(self.settings, "xtts_preload", xtts_preload)
            object.__setattr__(self.settings, "styletts2_preload", styletts2_preload)

            return {"ok": True, "requires_restart": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def update_ui_config(self, data):
        if not self.settings:
            return {"ok": False, "error": "Settings indisponiveis."}
        try:
            motion = str(data.get("ui_motion_level") or "balanced").strip().lower()
            if motion not in {"reduced", "balanced", "expressive"}:
                motion = "balanced"
            density = str(data.get("ui_density") or "comfortable").strip().lower()
            if density not in {"comfortable", "compact"}:
                density = "comfortable"

            self._update_env_file(
                {
                    "UI_MOTION_LEVEL": motion,
                    "UI_DENSITY": density,
                }
            )
            object.__setattr__(self.settings, "ui_motion_level", motion)
            object.__setattr__(self.settings, "ui_density", density)
            return {"ok": True, "ui_motion_level": motion, "ui_density": density}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_critical_confirm_enabled(self):
        if not self._confirm_bus:
            return False
        return self._confirm_bus.enabled

    def set_critical_confirm_enabled(self, enabled):
        if not self._confirm_bus:
            return False
        try:
            from src.tools.critical_confirm import save_critical_confirm_enabled

            en = bool(enabled)
            if not en:
                pending = self._confirm_bus.get_pending()
                if pending:
                    self._confirm_bus.resolve(pending["id"], False)
            self._confirm_bus.enabled = en
            save_critical_confirm_enabled(en)
        except Exception as e:
            print(f"[DesktopApi] Erro ao salvar confirmação crítica: {e}")
            return False
        return True

    def close_panel(self):
        """Fecha o painel (chamado pelo botão X no HTML)."""
        global APP_INSTANCE
        if APP_INSTANCE:
            APP_INSTANCE._on_panel_closing()
        return True

    def open_nexus_hud(self):
        """Abre o Nexus em janelas desktop (preferencial) ou no navegador."""
        try:
            if APP_INSTANCE:
                APP_INSTANCE.open_nexus_module("overview", {})
                return True
        except Exception as e:
            print(f"[DesktopApi] open_nexus_hud desktop: {e}")
        import os
        import webbrowser

        port = os.environ.get("VISUALIZER_PORT", "5123")
        try:
            webbrowser.open(f"http://127.0.0.1:{port}/nexus/")
            return True
        except Exception as e:
            print(f"[DesktopApi] open_nexus_hud: {e}")
            return False

    def open_nexus_module(self, module, payload_json="{}"):
        """Abre um módulo Nexus (fecha os outros). Chamado do painel ou do JS."""
        app = APP_INSTANCE
        if not app:
            return False
        try:
            payload = json.loads(payload_json or "{}")
        except json.JSONDecodeError:
            payload = {}
        try:
            return bool(app.open_nexus_module(str(module or "overview"), payload))
        except Exception as e:
            print(f"[DesktopApi] open_nexus_module: {e}")
            return False

    def nexus_theme_list(self):
        try:
            from src.services.nexus_service import get_nexus_service

            return get_nexus_service().list_window_themes()
        except Exception as e:
            print(f"[DesktopApi] nexus_theme_list: {e}")
            return {"modules": [], "presets": [], "assignments": {}, "error": str(e)}

    def nexus_theme_apply(self, module, preset_id):
        try:
            from src.services.nexus_service import get_nexus_service

            return get_nexus_service().apply_window_theme(str(module or ""), str(preset_id or ""))
        except Exception as e:
            print(f"[DesktopApi] nexus_theme_apply: {e}")
            return {"ok": False, "error": str(e)}

    def nexus_theme_generate(self, module, prompt, name=""):
        try:
            from src.services.nexus_service import get_nexus_service

            return get_nexus_service().generate_window_theme_preset(
                str(module or ""),
                str(prompt or ""),
                name=str(name or "").strip() or None,
            )
        except Exception as e:
            print(f"[DesktopApi] nexus_theme_generate: {e}")
            return {"ok": False, "error": str(e)}

    def nexus_scheduler_tick(self):
        """Drena pedidos de abertura vindos de outras threads (IA → fila → GUI)."""
        app = APP_INSTANCE
        if not app:
            return
        app._apply_visualizer_window_state()
        now = time.monotonic()
        with app._nexus_lock:
            if now < getattr(app, "_nexus_next_open_at", 0.0):
                return
            if not app._nexus_signal_q:
                return
            mod, payload = app._nexus_signal_q.popleft()
        try:
            app.open_nexus_module(mod, payload)
            try:
                hold_ms = int((payload or {}).get("hold_ms") or 0)
            except (TypeError, ValueError):
                hold_ms = 0
            if hold_ms > 0:
                with app._nexus_lock:
                    app._nexus_next_open_at = time.monotonic() + (hold_ms / 1000.0)
        except Exception as e:
            print(f"[Nexus] Falha ao abrir {mod}: {e}")

    def generate_persona(self, character_name):
        """Usa a LLM para gerar um prompt de personalidade completo para um personagem."""
        if not character_name or not character_name.strip():
            return None
        try:
            from src.services.llm import LLMService
            s = self.settings
            llm = LLMService(
                gemini_api_key=s.gemini_api_key,
                gemini_model=s.gemini_model,
                openrouter_api_key=s.openrouter_api_key,
                openrouter_model=s.openrouter_model,
                nvidia_api_key=s.nvidia_api_key,
                nvidia_model=s.nvidia_model,
                groq_api_key=s.groq_api_key,
                groq_model=s.groq_model,
                primary_llm_provider=s.llm_provider,
                fallback_gemini=s.llm_fallback_gemini,
            )
            system = (
                "Você é um criador de personagens de IA. Dado o nome de um personagem "
                "(de anime, filme, série, jogo, ou qualquer ficção), gere um prompt de "
                "personalidade completo em português para que uma IA atue como aquele personagem. "
                "O prompt deve incluir: traços de personalidade, forma de falar (gírias, bordões), "
                "nível de formalidade, humor, como trata as pessoas, referências ao universo original, "
                "e maneirismos únicos. Seja detalhado mas conciso (máximo 8 linhas). "
                "Se o personagem for orgulhoso, arrogante ou sarcástico, exagere nesses traços. "
                "Retorne APENAS o prompt de personalidade, sem título nem explicação."
            )
            result = llm.chat(
                system_prompt=system,
                messages=[{"role": "user", "content": f"Gere a persona para: {character_name.strip()}"}]
            )
            return result.strip() if result else None
        except Exception as e:
            print(f"[DesktopApi] Erro ao gerar persona: {e}")
            return None

    # --- API do Nexus Life OS acoplada ao DesktopApi ---
    def close_module(self):
        try:
            from src.ui.desktop_app import APP_INSTANCE
            if APP_INSTANCE and APP_INSTANCE.panel_window:
                APP_INSTANCE.panel_window.hide()
            if APP_INSTANCE and APP_INSTANCE.ghost_window:
                APP_INSTANCE.ghost_window.show()
                APP_INSTANCE.ghost_window.evaluate_js("document.body.style.visibility = 'visible';")
            return True
        except: return False

    def minimize_module(self):
        try:
            from src.ui.desktop_app import APP_INSTANCE
            if APP_INSTANCE and APP_INSTANCE.panel_window:
                APP_INSTANCE.panel_window.minimize()
            return True
        except: return False

    def maximize_module(self):
        try:
            from src.ui.desktop_app import APP_INSTANCE
            if APP_INSTANCE and APP_INSTANCE.panel_window:
                w = APP_INSTANCE.panel_window
                if getattr(self, '_maximized', False):
                    # ── Desmaximizar ──
                    prev_x = getattr(self, '_prev_x', None)
                    prev_y = getattr(self, '_prev_y', None)
                    prev_w = getattr(self, '_prev_w', 1000)
                    prev_h = getattr(self, '_prev_h', 700)
                    # Esconde → redimensiona → reabre para forçar
                    # o WebView2 a re-inicializar o compositor
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
        except Exception: return False

    def bridge(self, method: str, args_json: str = "{}") -> str:
        from src.ui.nexus_desktop_bridge import nexus_bridge_call
        return nexus_bridge_call(method, args_json)

    def jump(self, module: str, payload_json: str = "{}") -> str:
        try:
            import json
            from src.ui.desktop_app import APP_INSTANCE
            if not APP_INSTANCE: return "{}"
            try: pl = json.loads(payload_json or "{}")
            except: pl = {}
            APP_INSTANCE.open_nexus_module(str(module or "overview"), pl)
            return '{"ok": true}'
        except Exception as e:
            import json
            return json.dumps({"ok": False, "error": str(e)})

class DesktopApp:
    def __init__(self, start_url: str = "http://127.0.0.1:5123", task_queue=None,
                 agent_manager=None, settings=None, chat_log=None, system_logs=None,
                 confirm_bus=None, runtime_status=None, llm=None, tts=None, stt=None, tools=None):
        global APP_INSTANCE
        APP_INSTANCE = self

        self.start_url = start_url
        self.task_queue = task_queue
        self._panel_hotkey = (
            (getattr(settings, "panel_hotkey", None) or "win+shift+a").strip().lower()
            if settings else "win+shift+a"
        )
        self.api = DesktopApi(
            task_queue, agent_manager, settings, chat_log, system_logs,
            confirm_bus=confirm_bus,
            runtime_status=runtime_status,
            llm=llm,
            tts=tts,
            stt=stt,
            tools=tools,
        )

        self.ghost_window = None
        self.panel_window = None
        self._panel_current_mode = "settings" # "settings" ou "nexus"
        self.tray = None
        self._panel_visible = False
        self._nexus_module_windows: dict = {}
        self._nexus_lock = threading.Lock()
        self._nexus_signal_q: deque = deque(maxlen=16)
        self._nexus_next_open_at = 0.0
        self._nexus_scheduler = None
        self._visualizer_last_state = ""
        self._visualizer_last_position = ""
        self._visualizer_last_window_visible: bool | None = None

    def _on_panel_closing(self):
        """Intercepta o fechamento do painel: esconde em vez de destruir e mostra o ghost."""
        try:
            self.panel_window.hide()
            self.ghost_window.show()
            self.ghost_window.evaluate_js("document.body.style.visibility = 'visible';")
            self._panel_visible = False
            print("[UI] Painel escondido. Orb flutuante restaurado.")
        except Exception as e:
            print(f"[UI] Erro ao fechar painel: {e}")
        return False  # Impede destruição da janela

    def _show_panel(self):
        """Abre o painel principal (panel.html) e esconde o orb flutuante."""
        if self.panel_window and self.ghost_window:
            if self._panel_current_mode != "settings":
                panel_html_uri = (Path(__file__).resolve().parent / "panel.html").as_uri()
                self.panel_window.load_url(panel_html_uri)
                self._panel_current_mode = "settings"

            self.ghost_window.evaluate_js("document.body.style.visibility = 'hidden';")
            self.ghost_window.hide()
            try:
                self.panel_window.restore()
            except Exception:
                pass
            self.panel_window.show()
            self._panel_visible = True
            print("[UI] Painel aberto. Orb flutuante escondido.")

    def _hide_panel(self):
        """Fecha o painel e mostra o orb flutuante."""
        if self.panel_window and self.ghost_window:
            self.panel_window.hide()
            self.ghost_window.show()
            self.ghost_window.evaluate_js("document.body.style.visibility = 'visible';")
            self._panel_visible = False
            print("[UI] Painel fechado. Orb flutuante restaurado.")

    def _apply_visualizer_window_state(self):
        """Aplica posicao/visibilidade gravadas pela tool `visualizer_control`."""
        if not self.ghost_window:
            return
        try:
            from src.services import visualizer

            state_file = Path(visualizer.STATE_FILE)
            if not state_file.exists():
                return
            raw = state_file.read_text(encoding="utf-8")
            if raw == getattr(self, "_visualizer_last_state", ""):
                return
            self._visualizer_last_state = raw
            state = json.loads(raw)
        except Exception:
            return

        position = str(state.get("position") or "").strip()
        if position and position != getattr(self, "_visualizer_last_position", ""):
            self._move_orb(position)
            self._visualizer_last_position = position

        mode = str(state.get("display_mode") or "").strip().lower()
        visible = state.get("visible", True) is not False
        status = str(state.get("status") or "idle").strip().lower()
        should_show: bool | None = None
        if not visible or mode == "hidden":
            should_show = False
        elif mode == "always":
            should_show = True
        elif mode == "auto":
            should_show = status not in {"idle", "sleeping"}

        if should_show is None:
            return
        should_show = should_show and not self._panel_visible
        if should_show == getattr(self, "_visualizer_last_window_visible", None):
            return
        try:
            if should_show:
                self.ghost_window.show()
            else:
                self.ghost_window.hide()
            self._visualizer_last_window_visible = should_show
        except Exception:
            pass

    def close_all_nexus_modules(self):
        for w in list(self._nexus_module_windows.values()):
            try:
                w.destroy()
            except Exception:
                pass
        self._nexus_module_windows.clear()

    def open_nexus_module(self, module: str, payload: dict | None = None) -> bool:
        """Abre um módulo Nexus. Módulos unificados abrem no painel único; standalone abre janela própria."""
        from src.ui.nexus_window_api import NexusModulePyApi

        # Módulos que vivem dentro do painel unificado
        unified_sections = {
            "overview", "habits", "finance", "notes",
            "study", "tasks", "progress", "goals", "quiz",
        }
        # Módulos que continuam como janelas separadas (pesados/independentes)
        standalone_modules = {"memory_graph", "news", "ops"}

        allowed = unified_sections | standalone_modules
        mod = (module or "overview").strip().lower()
        # Aliases
        if mod in ("dashboard", "rewards"):
            mod = "overview" if mod == "dashboard" else "goals"
        if mod not in allowed:
            mod = "overview"

        pl = {}
        try:
            from src.services.nexus_service import get_nexus_service
            pl.update(get_nexus_service().get_window_theme_boot(mod))
        except Exception as e:
            print(f"[Nexus] Tema da janela indisponivel: {e}")
        pl.update(dict(payload or {}))

        # ── Módulos standalone: janela própria ──
        if mod in standalone_modules:
            # Fecha janelas standalone anteriores mas NÃO o unified
            for k in list(self._nexus_module_windows.keys()):
                if k != "unified":
                    try:
                        self._nexus_module_windows[k].destroy()
                    except Exception:
                        pass
                    self._nexus_module_windows.pop(k, None)
            return self._open_standalone_module(mod, pl)

        # ── Módulos unificados: painel único ──
        # Se a janela pré-alocada existe e já está no modo nexus
        if self.panel_window and self._panel_current_mode == "nexus":
            try:
                js_payload = json.dumps(pl, ensure_ascii=False).replace("'", "\\'")
                self.panel_window.evaluate_js(
                    f"if(window.nexusNavigateTo) nexusNavigateTo('{mod}', {js_payload});"
                )
                self.panel_window.show()
                if self.ghost_window:
                    try:
                        self.ghost_window.evaluate_js("document.body.style.visibility = 'hidden';")
                        self.ghost_window.hide()
                    except Exception: pass
                return True
            except Exception:
                pass

        # Fecha janelas standalone anteriores
        self.close_all_nexus_modules()

        # Prepara o HTML
        pl["section"] = mod
        html_path = (_nexus_modules_base_dir() / "unified.html").resolve()
        if not html_path.is_file():
            print(f"[Nexus] unified.html não encontrado: {html_path}")
            return False

        for s in unified_sections:
            s_path = (_nexus_modules_base_dir() / f"{s}.html").resolve()
            if s_path.is_file():
                try:
                    s_raw = s_path.read_text(encoding="utf-8")
                    s_comp = _compose_nexus_module_html(s_raw, pl, is_iframe=True)
                    if s_comp:
                        s_path.with_name(f"{s}_compiled.html").write_text(s_comp, encoding="utf-8")
                except Exception as e:
                    print(f"[Nexus] Erro compilando seccao {s}: {e}")

        try:
            raw_html = html_path.read_text(encoding="utf-8")
        except OSError as e:
            print(f"[Nexus] Erro ao ler unified.html: {e}")
            return False
        html_page = _compose_nexus_module_html(raw_html, pl)
        if not html_page:
            print("[Nexus] HTML do painel unificado inválido.")
            return False

        temp_html_path = html_path.with_name("unified_compiled.html")
        try:
            temp_html_path.write_text(html_page, encoding="utf-8")
        except OSError as e:
            print(f"[Nexus] Erro ao gravar compilação: {e}")
            return False

        if self.panel_window:
            self.panel_window.load_url(temp_html_path.as_uri())
            self.panel_window.show()
            self._panel_current_mode = "nexus"

            if self.ghost_window:
                try:
                    self.ghost_window.evaluate_js("document.body.style.visibility = 'hidden';")
                    self.ghost_window.hide()
                except Exception: pass
            return True
        else:
            print("[Nexus] Janela do painel não encontrada!")
            return False

        return True

    def _open_standalone_module(self, mod: str, pl: dict) -> bool:
        """Abre um módulo como janela separada (memory_graph, news, ops)."""
        from src.ui.nexus_window_api import NexusModulePyApi

        html_path = (_nexus_modules_base_dir() / f"{mod}.html").resolve()
        if not html_path.is_file():
            print(f"[Nexus] Ficheiro em falta: {html_path}")
            return False
        try:
            raw_html = html_path.read_text(encoding="utf-8")
        except OSError as e:
            print(f"[Nexus] Erro ao ler {html_path}: {e}")
            return False
        html_page = _compose_nexus_module_html(raw_html, pl)
        if not html_page:
            print("[Nexus] HTML do módulo inválido (falta </head> ou <body>).")
            return False
        temp_html_path = html_path.with_name(f"{mod}_compiled.html")
        try:
            temp_html_path.write_text(html_page, encoding="utf-8")
        except OSError as e:
            print(f"[Nexus] Erro ao gravar compilação: {e}")
            return False
        titles = {
            "memory_graph": "Nexus \u00b7 Grafo neural",
            "news": "Nexus \u00b7 Noticias",
            "ops": "Nexus \u00b7 Operacoes",
        }
        win_ref: list = [None]
        api = NexusModulePyApi(mod, win_ref)
        win = webview.create_window(
            titles.get(mod, "Nexus"),
            url=temp_html_path.as_uri(),
            width=1000,
            height=700,
            min_size=(640, 480),
            js_api=api,
            frameless=True,
            transparent=True,
            background_color='#0a0a0a',
            easy_drag=True,
        )
        win_ref[0] = win
        self._nexus_module_windows[mod] = win
        # Esconde o Orb enquanto a janela standalone estiver aberta
        if self.ghost_window:
            try:
                self.ghost_window.evaluate_js("document.body.style.visibility = 'hidden';")
                self.ghost_window.hide()
            except Exception:
                pass

        # Quando fechar, restaura o Orb (close_module em nexus_window_api.py também faz isso)
        def on_standalone_closed():
            self._nexus_module_windows.pop(mod, None)
            if self.ghost_window:
                try:
                    self.ghost_window.show()
                    self.ghost_window.evaluate_js("document.body.style.visibility = 'visible';")
                except Exception:
                    pass

        win.events.closed += on_standalone_closed
        return True

    def on_tray_quit(self, icon, item):
        if icon:
            icon.stop()
        try:
            if self._nexus_scheduler: self._nexus_scheduler.destroy()
        except: pass
        if self.ghost_window: self.ghost_window.destroy()
        if self.panel_window: self.panel_window.destroy()
        self.close_all_nexus_modules()
        print("[UI] Encerrando sistema a partir da bandeja...")
        import os
        os._exit(0)

    def on_tray_toggle_panel(self, icon, item):
        """Alterna entre Ghost Mode e Panel Mode (duplo clique na bandeja)."""
        if self._panel_visible:
            self._hide_panel()
        else:
            self._show_panel()

    def _setup_hotkeys(self):
        """Atalho global configurável (PANEL_HOTKEY no .env) para alternar Ghost / Painel."""
        try:
            import keyboard
            combo = self._panel_hotkey.replace(" ", "")
            print(f"[UI] Hotkey listener iniciado ({combo} para alternar).")
            while True:
                try:
                    keyboard.wait(combo)
                    self.on_tray_toggle_panel(None, None)
                    print("[UI] Hotkey acionado: alternando modo.")
                except Exception as e:
                    print(f"[UI] Erro no hotkey: {e}")
        except ImportError:
            print("[UI] Aviso: biblioteca 'keyboard' não disponível para hotkeys globais.")

    def _move_orb(self, position="top_left"):
        """Move o Orb para um canto da tela (Fase 1.1)."""
        if not self.ghost_window: return
        try:
            import webview
            screens = webview.screens
            if not screens: return
            screen = screens[0]
            w, h = screen.width, screen.height
            orb_w, orb_h = 250, 250

            x, y = 50, 50
            if position == "top_right":
                x, y = w - orb_w - 50, 50
            elif position == "bottom_right":
                x, y = w - orb_w - 50, h - orb_h - 100
            elif position == "bottom_left":
                x, y = 50, h - orb_h - 100
            elif position == "center":
                x, y = (w // 2) - (orb_w // 2), (h // 2) - (orb_h // 2)

            self.ghost_window.move(int(x), int(y))
        except Exception as e:
            print(f"[UI] Erro ao mover orb: {e}")

    def show_floating_image(self, image_path: str):
        """Abre uma janela pywebview para exibir uma imagem no centro da tela."""
        try:
            import webview

            html_content = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{
                        margin: 0;
                        overflow: hidden;
                        background: transparent;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        width: 100vw;
                    }}
                    img {{
                        max-width: 100%;
                        max-height: 100%;
                        object-fit: contain;
                        border-radius: 12px;
                        box-shadow: 0px 10px 30px rgba(0,0,0,0.5);
                    }}
                    .close-btn {{
                        position: absolute;
                        top: 10px;
                        right: 10px;
                        background: rgba(0,0,0,0.6);
                        color: white;
                        border: none;
                        border-radius: 50%;
                        width: 30px;
                        height: 30px;
                        font-weight: bold;
                        cursor: pointer;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        font-family: sans-serif;
                    }}
                    .close-btn:hover {{ background: rgba(255,0,0,0.8); }}
                </style>
            </head>
            <body>
                <button class="close-btn" onclick="pywebview.api.close_window()">X</button>
                <img src="file:///{Path(image_path).resolve().as_posix()}" />
            </body>
            </html>
            '''

            class ImageApi:
                def __init__(self):
                    self.window = None
                def close_window(self):
                    if self.window: self.window.destroy()

            api = ImageApi()
            import tempfile
            fd, tmp_path = tempfile.mkstemp(suffix=".html", prefix="jarvis_img_")
            with open(fd, 'w', encoding='utf-8') as f:
                f.write(html_content)

            win = webview.create_window(
                title="Jarvis Image Viewer",
                url=f"file:///{Path(tmp_path).resolve().as_posix()}",
                frameless=True,
                transparent=True,
                background_color='#0a0a0a',
                on_top=True,
                width=600,
                height=600,
                js_api=api
            )
            api.window = win
            print(f"[UI] Visualizador de imagem aberto para: {image_path}")
        except Exception as e:
            print(f"[UI] Erro ao abrir imagem flutuante: {e}")

    def run_tray(self):
        """Inicia a thread do ícone de bandeja (System Tray)."""
        # Menu de Posição do Orb
        pos_menu = pystray.Menu(
            pystray.MenuItem("Canto Superior Esquerdo", lambda: self._move_orb("top_left")),
            pystray.MenuItem("Canto Superior Direito", lambda: self._move_orb("top_right")),
            pystray.MenuItem("Canto Inferior Esquerdo", lambda: self._move_orb("bottom_left")),
            pystray.MenuItem("Canto Inferior Direito", lambda: self._move_orb("bottom_right")),
            pystray.MenuItem("Centro da Tela", lambda: self._move_orb("center")),
        )

        menu = pystray.Menu(
            pystray.MenuItem("Abrir Painel / Chat", self.on_tray_toggle_panel, default=True),
            pystray.MenuItem("Posição do Orb", pos_menu),
            pystray.MenuItem("Sair do Assistente", self.on_tray_quit)
        )
        self.tray = pystray.Icon("AI_Assistant", create_tray_icon(), "AI Assistant", menu)
        self.tray.run()

    def _apply_ghost_click(self):
        """Usa API do Windows para tornar a janela do Orb invisível para o mouse."""
        import time
        import ctypes
        # Espera a janela abrir
        time.sleep(2)
        try:
            # Encontra a janela pelo título
            hwnd = ctypes.windll.user32.FindWindowW(None, "AI_Ghost_Orb")
            if hwnd:
                GWL_EXSTYLE = -20
                WS_EX_LAYERED = 0x00080000
                WS_EX_TRANSPARENT = 0x00000020
                ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style | WS_EX_LAYERED | WS_EX_TRANSPARENT)
                print("[UI] Ghost Click ativado no Orb.")
        except Exception as e:
            print(f"[UI] Erro ao aplicar Ghost Click: {e}")

    def start(self):
        """Inicia a UI do Assistente (Janelas e Bandeja)."""
        threading.Thread(target=self.run_tray, daemon=True).start()
        self._panel_visible = False

        # Aplica Ghost Click no background
        threading.Thread(target=self._apply_ghost_click, daemon=True).start()

        # Inicia hotkey listener em thread separada
        threading.Thread(target=self._setup_hotkeys, daemon=True).start()

        # Caminho do painel HTML (as_uri: espaços e caminhos Windows corretos)
        panel_html_uri = (Path(__file__).resolve().parent / "panel.html").as_uri()

        # Cria ambas as janelas no inicio para evitar bloqueio multi-thread
        self.ghost_window = webview.create_window(
            title="AI_Ghost_Orb",
            url=self.start_url,
            frameless=True,
            transparent=True,
            on_top=True,
            width=250,
            height=250,
            x=50,
            y=50
        )
        self.panel_window = webview.create_window(
            title="AI Assistant - Gerenciamento",
            url=panel_html_uri,
            width=1000,
            height=700,
            js_api=self.api,
            hidden=True,
            frameless=True,
            transparent=True,
            background_color='#0a0a0a',
            easy_drag=True
        )

        # Ao fechar o painel, apenas oculta
        self.panel_window.events.closing += self._on_panel_closing


        self._nexus_scheduler = webview.create_window(
            "__nexus_scheduler__",
            html=NEXUS_SCHEDULER_HTML,
            width=80,
            height=80,
            x=-3200,
            y=-3200,
            frameless=True,
            js_api=self.api,
            hidden=True,
        )

        webview.start(debug=False)
