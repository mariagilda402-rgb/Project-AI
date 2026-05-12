import json
import threading
from pathlib import Path
from dataclasses import asdict
import pystray
from PIL import Image, ImageDraw
import webview

def create_tray_icon():
    # Cria um icone simples para a bandeja
    image = Image.new('RGB', (64, 64), color=(30, 30, 30))
    d = ImageDraw.Draw(image)
    d.ellipse((16, 16, 48, 48), fill=(0, 200, 255))
    return image

APP_INSTANCE = None

class DesktopApi:
    def __init__(self, task_queue, agent_manager, settings, chat_log=None, system_logs=None):
        self.task_queue = task_queue
        self.agent_manager = agent_manager
        self.settings = settings
        self._chat_log = chat_log if chat_log is not None else []
        self._system_logs = system_logs if system_logs is not None else []

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
        # ... status simulado ou real
        return {"status": "ok"}
        
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
        return self.agent_manager.set_active_agent(agent_id)

    def create_agent(self, data):
        if not self.agent_manager: return None
        try: speed = float(data.get('tts_speed', 1.0) or 1.0)
        except (TypeError, ValueError): speed = 1.0
        agent = self.agent_manager.create_agent(
            name=data.get('name', 'Novo Agente'),
            persona=data.get('persona', 'Assistente padrão.'),
            tts_provider=data.get('tts_provider', 'edge'),
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
            'tts_voice': s.tts_voice,
            'stt_language': s.stt_language,
            'use_mic': s.use_mic,
            'enable_visualizer': s.enable_visualizer,
            'edge_tts_rate': s.edge_tts_rate,
            'kokoro_voice': s.kokoro_voice,
        }

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

class DesktopApp:
    def __init__(self, start_url: str = "http://127.0.0.1:5123", task_queue=None,
                 agent_manager=None, settings=None, chat_log=None, system_logs=None):
        global APP_INSTANCE
        APP_INSTANCE = self
        
        self.start_url = start_url
        self.task_queue = task_queue
        self.api = DesktopApi(task_queue, agent_manager, settings, chat_log, system_logs)

        self.ghost_window = None
        self.panel_window = None
        self.tray = None
        self._panel_visible = False

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
        """Abre o painel e esconde o orb flutuante."""
        if self.panel_window and self.ghost_window:
            self.ghost_window.evaluate_js("document.body.style.visibility = 'hidden';")
            self.ghost_window.hide()
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

    def on_tray_quit(self, icon, item):
        icon.stop()
        if self.ghost_window: self.ghost_window.destroy()
        if self.panel_window: self.panel_window.destroy()

    def on_tray_toggle_panel(self, icon, item):
        """Alterna entre Ghost Mode e Panel Mode (duplo clique na bandeja)."""
        if self._panel_visible:
            self._hide_panel()
        else:
            self._show_panel()

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
            win = webview.create_window(
                title="Jarvis Image Viewer",
                html=html_content,
                frameless=True,
                transparent=True,
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

        # Caminho do painel HTML
        panel_html_path = str(Path(__file__).resolve().parent / "panel.html")

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
            url=f"file:///{panel_html_path}",
            width=1000,
            height=700,
            js_api=self.api,
            hidden=True, # Inicia escondido
            frameless=True,
            transparent=True,
            easy_drag=True
        )

        # Ao fechar o painel, apenas oculta
        self.panel_window.events.closing += self._on_panel_closing

        webview.start(debug=False)
