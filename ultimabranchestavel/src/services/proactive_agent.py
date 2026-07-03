import threading
import time
import random
from src.services.llm import LLMService
from src.services.vision import VisionService

class ProactiveAgent:
    def __init__(self, agent_orchestrator, tts_instance, min_interval_minutes=15, max_interval_minutes=45):
        self.orchestrator = agent_orchestrator
        self.tts = tts_instance
        self.min_interval = min_interval_minutes
        self.max_interval = max_interval_minutes
        self.running = False
        self.thread = None

    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        print("[ProactiveAgent] Iniciado. Assistente puxará assunto aleatoriamente.")

    def stop(self):
        self.running = False

    def _loop(self):
        # Atraso inicial para não falar assim que ligar
        time.sleep(120)
        
        while self.running:
            # Espera um tempo aleatório entre o min e o max
            wait_time = random.uniform(self.min_interval * 60, self.max_interval * 60)
            time.sleep(wait_time)
            
            if not self.running: break
            
            self._trigger_proactive_interaction()

    def _trigger_proactive_interaction(self):
        try:
            print("[ProactiveAgent] Avaliando a tela para puxar assunto...")
            # Pega o vision service do orquestrador
            vision = self.orchestrator.vision
            if not vision: return
            
            # Tira print silencioso da tela
            import os
            from PIL import ImageGrab
            
            screenshot = ImageGrab.grab()
            temp_path = "temp_proactive_screen.jpg"
            screenshot.convert("RGB").save(temp_path, quality=70)
            
            # Chama o LLM Visão (Groq ou Gemini)
            llm = self.orchestrator.llm
            system_prompt = (
                "Você está olhando a tela do usuário de forma proativa. O objetivo é quebrar o silêncio "
                "e fazer companhia. Olhe para a tela: se o usuário estiver fazendo algo interessante "
                "(ex: programando, jogando, lendo um artigo, assistindo um vídeo), faça um comentário curto, "
                "informal e amigável sobre isso, puxando assunto. "
                "Se a tela estiver vazia, ou se ele estiver só no desktop sem fazer nada produtivo ou interessante, "
                "responda EXATAMENTE com a palavra VAZIO."
            )
            
            with open(temp_path, "rb") as f:
                img_bytes = f.read()

            analysis = vision.describe_screen(
                user_request=f"{system_prompt}\n\nO que tem na tela? Comente se for interessante, ou diga VAZIO.",
                image_bytes=img_bytes
            )
            
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
            if not analysis or "VAZIO" in analysis.upper():
                print("[ProactiveAgent] Nada interessante na tela. Silêncio mantido.")
                return
                
            print(f"[ProactiveAgent] Assunto gerado: {analysis}")
            
            # Adiciona ao histórico para que a IA se lembre de ter falado isso
            self.orchestrator.memory.add_short_term("assistant", analysis)
            
            # Injeta no chat de interface
            try:
                from src.main import _add_chat
                _add_chat("assistant", "Assistente", analysis)
            except Exception:
                pass
                
            # Fala o áudio
            if self.tts:
                self.tts.speak(analysis)
                
        except Exception as e:
            print(f"[ProactiveAgent] Erro na interação proativa: {e}")
