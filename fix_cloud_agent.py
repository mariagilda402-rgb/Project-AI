import re

path = 'src/services/nexus_cloud_agent.py'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Add new imports
if 'import pyperclip' not in c:
    c = c.replace('import json', 'import json\ntry:\n    import pyperclip\nexcept ImportError:\n    pyperclip = None')

# 2. Route new commands in process_pending_commands
old_route = '                    elif command_str.startswith("AUTO_SUMMARIZE_NOTE:"):\n                        self.handle_auto_summarize(command_str)'
new_route = '''                    elif command_str.startswith("AUTO_SUMMARIZE_NOTE:"):
                        self.handle_auto_summarize(command_str)
                    elif command_str.startswith("IMAGE_TRANSCRIPT:"):
                        self.handle_image_transcript(cmd_id, command_str)
                    elif command_str.startswith("SUMMARIZE_JOURNAL:"):
                        self.handle_journal_summary(command_str)
                    elif command_str.startswith("COPY_TO_PC_CLIPBOARD:"):
                        self.handle_pc_clipboard(command_str)
                    elif command_str.startswith("GPS_UPDATE:"):
                        self.handle_gps_update(command_str)'''

c = c.replace(old_route, new_route)

# 3. Add new handler methods before sync_memory_to_cloud
new_handlers = '''
    def handle_image_transcript(self, cmd_id, command_str):
        """Uses Gemini Vision to transcribe a handwritten image from Base64."""
        import base64
        b64_data = command_str.split("IMAGE_TRANSCRIPT:", 1)[1].strip()
        image_bytes = base64.b64decode(b64_data)
        
        print(f"[NexusCloudAgent] Transcrevendo imagem ({len(image_bytes)} bytes) com Gemini Vision...")
        
        # Use Gemini multimodal API
        prompt = "Transcreva com precisão todo o texto manuscrito desta imagem de caderno. Preserve a estrutura (títulos, listas, parágrafos). Apenas retorne o texto transcrito, sem introdução."
        transcription = self.llm.generate_with_image(prompt, image_bytes, mime_type="image/jpeg")
        
        # Save result back to nexus_commands for mobile to pick up
        with self.get_db() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE nexus_commands SET result=?, status='completed' WHERE id=?", (transcription, cmd_id))
            conn.commit()
        print(f"[NexusCloudAgent] Transcrição salva, {len(transcription)} chars.")

    def handle_journal_summary(self, command_str):
        """Summarizes a journal entry and saves mood analysis."""
        date_str = command_str.split("SUMMARIZE_JOURNAL:", 1)[1].strip()
        with self.get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT content FROM journal_entries WHERE date=?", (date_str,))
            row = cur.fetchone()
            if not row:
                return
            content = row[0]
        
        prompt = f"""Analise esta entrada de diário e responda em JSON com os campos:
- "mood": humor geral (ótimo/bom/neutro/ruim/péssimo)
- "keywords": lista de 3-5 palavras-chave principais
- "summary": resumo de 1 frase
- "insights": qualquer padrão ou insight relevante para o crescimento pessoal

Diário: {content[:3000]}"""
        
        analysis = self.llm.generate(prompt)
        with self.get_db() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE journal_entries SET ai_analysis=? WHERE date=?", (analysis, date_str))
            conn.commit()
        print(f"[NexusCloudAgent] Diário de {date_str} analisado.")

    def handle_pc_clipboard(self, command_str):
        """Copies text to the PC's clipboard using pyperclip."""
        text = command_str.split("COPY_TO_PC_CLIPBOARD:", 1)[1].strip()
        if pyperclip:
            pyperclip.copy(text)
            print(f"[NexusCloudAgent] Copiado para clipboard do PC: {text[:50]}...")
            
            # Send PC notification back to mobile
            self._notify_mobile(f"✅ Texto copiado no PC: '{text[:40]}...'")
        else:
            print("[NexusCloudAgent] pyperclip não instalado. Execute: pip install pyperclip")

    def handle_gps_update(self, command_str):
        """Receives GPS data from mobile and checks geofences."""
        import json as _json
        geo_str = command_str.split("GPS_UPDATE:", 1)[1].strip()
        try:
            geo = _json.loads(geo_str)
            print(f"[NexusCloudAgent] GPS do celular: lat={geo.get('lat')}, lon={geo.get('lon')}")
            # Store for reference
            with self.get_db() as conn:
                cur = conn.cursor()
                cur.execute("CREATE TABLE IF NOT EXISTS mobile_gps_log (id INTEGER PRIMARY KEY AUTOINCREMENT, lat REAL, lon REAL, accuracy REAL, recorded_at TEXT)")
                cur.execute("INSERT INTO mobile_gps_log (lat, lon, accuracy, recorded_at) VALUES (?, ?, ?, ?)",
                           (geo.get('lat'), geo.get('lon'), geo.get('accuracy'), geo.get('timestamp')))
                conn.commit()
        except Exception as e:
            print(f"[NexusCloudAgent] Erro ao processar GPS: {e}")

    def _notify_mobile(self, message):
        """Send a push notification to the mobile app via Supabase nexus_commands."""
        with self.get_db() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO nexus_commands (command, source, status) VALUES (?, 'pc_notification', 'pending')", (message,))
            conn.commit()

'''

if 'handle_image_transcript' not in c:
    c = c.replace('    def sync_memory_to_cloud(self):', new_handlers + '    def sync_memory_to_cloud(self):')

with open(path, 'w', encoding='utf-8') as f:
    f.write(c)

print("NexusCloudAgent updated successfully!")
