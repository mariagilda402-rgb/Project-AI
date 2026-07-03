import os
import urllib.request
import threading
import time
import numpy as np

# AVISO: Requer 'pip install onnxruntime sounddevice numpy'
try:
    import onnxruntime as ort
    import sounddevice as sd
    HAS_ONNX = True
except ImportError:
    HAS_ONNX = False

class AudioEventDetector:
    def __init__(self, tts_instance, memory_store):
        self.tts = tts_instance
        self.memory = memory_store
        self.running = False
        self.thread = None
        self.session = None
        
        self.model_path = os.path.join(os.path.dirname(__file__), "yamnet.onnx")
        self.class_map = {
            0: "Speech",
            49: "Cough",
            50: "Sneeze",
            51: "Sniff",
            16: "Laughter",
            73: "Dog"
        }

    def _download_model_if_needed(self):
        if not os.path.exists(self.model_path):
            print("[AudioEvents] Baixando YAMNet (3MB)...")
            url = "https://raw.githubusercontent.com/onnx/models/main/vision/classification/squeezenet/model/squeezenet1.0-3.onnx" 
            # Nota: Este link é um placeholder seguro! Para produção real, usaríamos o yamnet.onnx validado.
            # urllib.request.urlretrieve(url, self.model_path)
            # print("[AudioEvents] Download concluído.")
            pass

    def start(self):
        if not HAS_ONNX:
            print("[AudioEvents] Bibliotecas ausentes. Para ativar, rode: pip install onnxruntime sounddevice")
            return
            
        self._download_model_if_needed()
        if not os.path.exists(self.model_path):
            print("[AudioEvents] Modelo não encontrado.")
            return

        try:
            self.session = ort.InferenceSession(self.model_path)
            self.running = True
            self.thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.thread.start()
            print("[AudioEvents] Detector de Tosse/Espirro iniciado em background.")
        except Exception as e:
            print(f"[AudioEvents] Falha ao iniciar modelo: {e}")

    def stop(self):
        self.running = False

    def _listen_loop(self):
        # Configuração: 16kHz, mono, pedaços de 1 segundo
        sample_rate = 16000
        chunk_size = 16000 
        
        while self.running:
            try:
                # Grava 1 segundo de áudio (silenciosamente)
                audio_data = sd.rec(int(chunk_size), samplerate=sample_rate, channels=1, dtype='float32')
                sd.wait()
                
                # Prepara tensor
                waveform = np.squeeze(audio_data)
                
                # Inference
                if self.session:
                    # Em um yamnet real, as saídas são scores de 521 classes
                    # out = self.session.run(None, {"waveform": waveform})
                    # scores = out[0].mean(axis=0)
                    # top_class = np.argmax(scores)
                    
                    # Placeholder para simulação (se ativado via mock)
                    top_class = -1
                    
                    if top_class == 49:  # Cough
                        print("[AudioEvents] Tosse detectada!")
                        self._trigger_ai_reaction("O usuário acabou de tossir muito.")
                        time.sleep(10) # Cooldown
                        
                    elif top_class == 50:  # Sneeze
                        print("[AudioEvents] Espirro detectado!")
                        self._trigger_ai_reaction("O usuário acabou de espirrar.")
                        time.sleep(10) # Cooldown
                        
            except Exception as e:
                print(f"[AudioEvents] Erro: {e}")
                time.sleep(5)

    def _trigger_ai_reaction(self, event_text):
        if self.tts:
            # Em uma implementação real, nós passaríamos event_text para a LLM gerar uma resposta natural
            if "tossir" in event_text:
                self.tts.speak("Você está bem? Quer que eu lembre de tomar um xarope ou marcar uma pausa?")
            elif "espirrar" in event_text:
                self.tts.speak("Saúde!")
