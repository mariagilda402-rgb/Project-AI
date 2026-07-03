import sounddevice as sd
import numpy as np
import time
import threading

class ClapDetector:
    """
    Escuta o microfone em background para detectar o som de duas palmas (double-clap).
    É extremamente leve, operando apenas com a amplitude do áudio (RMS).
    """
    def __init__(self, on_clap_callback, threshold=0.15, min_gap=0.1, max_gap=1.2, cooldown=3.0):
        self.on_clap_callback = on_clap_callback
        self.threshold = threshold
        self.min_gap = min_gap
        self.max_gap = max_gap
        self.cooldown = cooldown
        
        self.last_clap_time = 0.0
        self.is_listening = False
        self.stream = None
        
        # Valores conservadores para captar o áudio sem estresse
        self.sample_rate = 44100
        self.block_size = 1024
        
        self.trigger_lock = threading.Lock()
        self.last_trigger_time = 0.0

    def _audio_callback(self, indata, frames, time_info, status):
        now = time.time()
        
        with self.trigger_lock:
            if now - self.last_trigger_time < self.cooldown:
                return # Ignora áudio durante o cooldown

        # RMS volume spike (Root Mean Square)
        rms = float(np.sqrt(np.mean(indata ** 2)))
        
        if rms > self.threshold:
            gap = now - self.last_clap_time
            if gap >= self.min_gap:
                if gap <= self.max_gap and self.last_clap_time > 0:
                    # Segunda palma! Aciona o gatilho
                    self.last_clap_time = 0.0
                    with self.trigger_lock:
                        self.last_trigger_time = now
                    # Dispara o callback em uma nova thread para não travar o stream de áudio
                    threading.Thread(target=self.on_clap_callback, daemon=True).start()
                else:
                    # Primeira palma detectada
                    self.last_clap_time = now

    def start(self):
        if self.is_listening:
            return
        self.is_listening = True
        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                channels=1,
                dtype="float32",
                callback=self._audio_callback
            )
            self.stream.start()
        except Exception as e:
            print(f"[ClapDetector] Erro ao iniciar listener de palmas: {e}")
            self.is_listening = False

    def stop(self):
        if not self.is_listening:
            return
        self.is_listening = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
