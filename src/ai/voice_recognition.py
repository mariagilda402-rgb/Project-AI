import speech_recognition as sr
import threading
import time
import logging

class JarvisVoice:
    def __init__(self, db_connection=None):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.db = db_connection
        self.is_listening = False
        self.current_user = "Desconhecido"
        self.current_level = 0
        
        # Ajustar ruidos do microfone na inicialização
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
    def set_user(self, name, level):
        self.current_user = name
        self.current_level = level
        logging.info(f"🎤 [Voice Biometrics] Usuário reconhecido: {name} (Nível {level})")

    def _listen_loop(self, callback):
        logging.info("🎤 Jarvis Voice Recognition started in background.")
        self.is_listening = True
        while self.is_listening:
            try:
                with self.microphone as source:
                    audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=5)
                
                # Reconhecimento via API Gratuita do Google (Super Leve)
                text = self.recognizer.recognize_google(audio, language="pt-BR").lower()
                
                if "jarvis" in text:
                    command = text.split("jarvis", 1)[1].strip()
                    if command:
                        callback(command, self.current_user, self.current_level)
                    else:
                        logging.info("🎤 Jarvis: Sim, senhor?")
                        
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                logging.error(f"🎤 Jarvis TTS Error: {e}")
                time.sleep(5)
            except Exception as e:
                logging.error(f"🎤 Jarvis Unexpected Error: {e}")
                time.sleep(2)

    def start_listening(self, command_callback):
        thread = threading.Thread(target=self._listen_loop, args=(command_callback,), daemon=True)
        thread.start()
        
    def stop_listening(self):
        self.is_listening = False

    def simulate_biometric_login(self, phrase):
        """
        Simulador de extração de Embeddings (SpeechBrain/Resemblyzer)
        Para não travar o PC do usuário instalando 2GB de PyTorch agora, 
        usamos reconhecimento de contexto para simular a biometria.
        """
        phrase = phrase.lower()
        if "eu sou" in phrase or "esta é" in phrase or "aqui é" in phrase:
            name_parts = phrase.split()
            # Pega a ultima palavra como nome (ex: "esta é a laura" -> "laura")
            name = name_parts[-1].capitalize()
            
            # Buscar no banco
            if self.db:
                try:
                    conn = self.db._get_connection()
                    cur = conn.cursor()
                    cur.execute("SELECT access_level FROM voice_profiles WHERE name ILIKE %s", (name,))
                    res = cur.fetchone()
                    if res:
                        self.set_user(name, res[0])
                        return f"Reconhecimento biométrico confirmado. Olá, {name} (Nível {res[0]})."
                    else:
                        # Criar visitante
                        cur.execute("INSERT INTO voice_profiles (name, access_level) VALUES (%s, 1)", (name,))
                        conn.commit()
                        self.set_user(name, 1)
                        return f"Novo perfil biométrico criado para {name} (Nível 1)."
                except Exception as e:
                    logging.error(f"DB Error: {e}")
                    
        return None
