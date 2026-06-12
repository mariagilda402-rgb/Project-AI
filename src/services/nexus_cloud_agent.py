import time
import sqlite3
import json
try:
    import pyperclip
except ImportError:
    pyperclip = None
import re
import threading
from youtube_transcript_api import YouTubeTranscriptApi
from src.services.llm import LLMService

class NexusCloudAgent:
    def __init__(self, db_path="data/nexus.db"):
        self.db_path = db_path
        self.llm = LLMService()
        self._stop_event = threading.Event()
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        print("[NexusCloudAgent] Agente na Nuvem iniciado. Aguardando comandos do Celular...")

    def stop(self):
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)

    def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                self.process_pending_commands()
                self.sync_memory_to_cloud()
            except Exception as e:
                print(f"[NexusCloudAgent] Erro no loop principal: {e}")
            time.sleep(10)

    def get_db(self):
        return sqlite3.connect(self.db_path)

    def process_pending_commands(self):
        with self.get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, command, source FROM nexus_commands WHERE status='pending'")
            commands = cur.fetchall()

            for cmd_id, command_str, source in commands:
                print(f"[NexusCloudAgent] Processando comando {cmd_id}: {command_str[:50]}...")
                try:
                    if command_str.startswith("VIDEO_INSIGHT:"):
                        self.handle_video_insight(command_str)
                    elif command_str.startswith("AUTO_SUMMARIZE_NOTE:"):
                        self.handle_auto_summarize(command_str)
                    elif command_str.startswith("IMAGE_TRANSCRIPT:"):
                        self.handle_image_transcript(cmd_id, command_str)
                    elif command_str.startswith("SUMMARIZE_JOURNAL:"):
                        self.handle_journal_summary(command_str)
                    elif command_str.startswith("COPY_TO_PC_CLIPBOARD:"):
                        self.handle_pc_clipboard(command_str)
                    elif command_str.startswith("GPS_UPDATE:"):
                        self.handle_gps_update(command_str)
                    elif command_str.startswith("DISCOVER_IOT"):
                        self.handle_discover_iot(cmd_id)
                    elif command_str.startswith("TOGGLE_IOT:"):
                        self.handle_toggle_iot(cmd_id, command_str)
                    
                    # Mark as completed
                    cur.execute("UPDATE nexus_commands SET status='completed' WHERE id=?", (cmd_id,))
                    conn.commit()
                except Exception as e:
                    print(f"[NexusCloudAgent] Erro ao processar comando {cmd_id}: {e}")
                    cur.execute("UPDATE nexus_commands SET status='error', result=? WHERE id=?", (str(e), cmd_id))
                    conn.commit()

    def handle_video_insight(self, command_str):
        # Format: VIDEO_INSIGHT: <url> | PROMPT: <prompt>
        match = re.search(r"VIDEO_INSIGHT:\s*(.*?)\s*\|\s*PROMPT:\s*(.*)", command_str)
        if not match:
            raise ValueError("Formato de comando inválido.")
        
        url = match.group(1).strip()
        user_prompt = match.group(2).strip()

        # Extract video ID
        video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
        if not video_id_match:
            raise ValueError("ID do vídeo do YouTube não encontrado.")
        video_id = video_id_match.group(1)

        print(f"[NexusCloudAgent] Baixando transcrição do vídeo {video_id}...")
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['pt', 'en'])
        transcript_text = " ".join([t['text'] for t in transcript_list])
        
        # Limit transcript size
        transcript_text = transcript_text[:15000] 

        # Fetch existing notes
        with self.get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, subject, general_subject FROM study_notes")
            notes = cur.fetchall()
            
        notes_context = "Suas anotações existentes:\n"
        for nid, sub, gen_sub in notes:
            notes_context += f"- ID: {nid} | Título: {sub} | Assunto Geral: {gen_sub or 'Vazio'}\n"

        prompt = f"""
Você é o Jarvis, processando um vídeo do YouTube para os estudos do usuário.
O usuário pediu: "{user_prompt}"

Transcrição do vídeo:
{transcript_text}

{notes_context}

DECISÃO:
Se os insights deste vídeo pertencerem a alguma anotação existente (veja os assuntos gerais), responda no formato exato:
MERGE_ID: <ID DA NOTA>
INSIGHTS: <O novo conteúdo gerado>

Se o assunto for totalmente novo, responda:
NEW_NOTE_TITLE: <Novo Título>
INSIGHTS: <O novo conteúdo gerado>
"""
        print("[NexusCloudAgent] Analisando com Gemini...")
        response = self.llm.generate(prompt)

        with self.get_db() as conn:
            cur = conn.cursor()
            if "MERGE_ID:" in response:
                try:
                    merge_id = re.search(r"MERGE_ID:\s*(\d+)", response).group(1)
                    insights = response.split("INSIGHTS:")[1].strip()
                    cur.execute("UPDATE study_notes SET ai_suggestion=? WHERE id=?", (insights, merge_id))
                    print(f"[NexusCloudAgent] Insight salvo na nota {merge_id} como sugestão.")
                except Exception as e:
                    print("Falha ao fazer o merge:", e)
            elif "NEW_NOTE_TITLE:" in response:
                try:
                    title = re.search(r"NEW_NOTE_TITLE:\s*(.*?)\n", response).group(1).strip()
                    insights = response.split("INSIGHTS:")[1].strip()
                    cur.execute("INSERT INTO study_notes (subject, content) VALUES (?, ?)", (title, insights))
                    print(f"[NexusCloudAgent] Nova nota criada: {title}")
                except Exception as e:
                    print("Falha ao criar nota:", e)

    def handle_auto_summarize(self, command_str):
        note_id = command_str.split(":")[1].strip()
        with self.get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT content FROM study_notes WHERE id=?", (note_id,))
            row = cur.fetchone()
            if not row: return
            content = row[0]

        prompt = f"Leia esta anotação de estudos e responda com UMA ÚNICA LINHA contendo o Assunto Geral (General Subject) desta nota.\n\nAnotação:\n{content[:2000]}"
        summary = self.llm.generate(prompt).strip()

        with self.get_db() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE study_notes SET general_subject=? WHERE id=?", (summary, note_id))
            print(f"[NexusCloudAgent] Nota {note_id} sumarizada: {summary}")


    def handle_discover_iot(self, cmd_id):
        """Mock discovery of local IoT devices since we are the PC on the local network."""
        import json
        devices = [
            {"name": "Luz Quarto", "ip": "192.168.1.100", "status": "LIGADO"},
            {"name": "Ar Condicionado", "ip": "192.168.1.101", "status": "DESLIGADO"},
            {"name": "TV Sala", "ip": "192.168.1.102", "status": "LIGADO"}
        ]
        result_json = json.dumps(devices)
        with self.get_db() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE nexus_commands SET result=?, status='completed' WHERE id=?", (result_json, cmd_id))
            conn.commit()
        print(f"[NexusCloudAgent] IOT Discovery executado.")

    def handle_toggle_iot(self, cmd_id, command_str):
        """Simulate toggling an IoT device on the local network."""
        parts = command_str.split(":")
        if len(parts) >= 3:
            ip = parts[1]
            state = parts[2]
            print(f"[NexusCloudAgent] Enviando comando {state} para dispositivo IOT {ip}...")
        
        with self.get_db() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE nexus_commands SET status='completed' WHERE id=?", (cmd_id,))
            conn.commit()

    def sync_memory_to_cloud(self):
        try:
            with open("data/structured_memory.json", "r", encoding="utf-8") as f:
                memory_data = json.load(f)
            
            with self.get_db() as conn:
                cur = conn.cursor()
                cur.execute("CREATE TABLE IF NOT EXISTS nexus_memory_sync (id INTEGER PRIMARY KEY, key_name TEXT UNIQUE, data_json TEXT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
                for key, value in memory_data.items():
                    cur.execute("INSERT INTO nexus_memory_sync (key_name, data_json) VALUES (?, ?) ON CONFLICT(key_name) DO UPDATE SET data_json=excluded.data_json", (key, json.dumps(value)))
                conn.commit()
        except Exception as e:
            pass # Silently fail if structured_memory.json doesn't exist yet
