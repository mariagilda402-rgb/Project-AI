from __future__ import annotations

import speech_recognition as sr


class STTService:
    """
    Reconhecimento via SpeechRecognition + Google (rede).
    Em geral lida melhor com PT + palavras em ingles ocasionais do que modelos locais
    treinados so para um idioma (ex.: VosK PT).
    """

    def __init__(self, use_mic: bool = False, language: str = "pt-BR", groq_api_key: str = "") -> None:
        self.use_mic = use_mic
        self.language = language.strip() or "pt-BR"
        self.recognizer = sr.Recognizer()
        
        # Ajustes de sensibilidade
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 1.2  # Espera 1.2s de silêncio antes de cortar (evita cortar frases)
        self.recognizer.non_speaking_duration = 0.8  # Margem extra de silêncio
        
        self.groq_client = None
        if groq_api_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=groq_api_key)
            except ImportError:
                pass
        
        # Calibração inicial
        self.calibrated = False

    def calibrate(self, duration: float = 1.0):
        """Ajusta o reconhecedor ao ruído ambiente."""
        try:
            with sr.Microphone() as source:
                print(f"[STT] Calibrando ruído ambiente ({duration}s)...")
                self.recognizer.adjust_for_ambient_noise(source, duration=duration)
                self.calibrated = True
                print(f"[STT] Calibração concluída. Threshold: {self.recognizer.energy_threshold}")
        except Exception as e:
            print(f"[STT] Erro na calibração: {e}")

    def _viz_set(self, func_name: str, *args, **kwargs):
        """Helper seguro para chamar funções do visualizador."""
        try:
            from src.services import visualizer
            getattr(visualizer, func_name)(*args, **kwargs)
        except Exception:
            pass

    def _transcribe(self, audio: sr.AudioData) -> str:
        if self.groq_client:
            import tempfile
            import os
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp.write(audio.get_wav_data())
                    tmp_name = tmp.name
                
                with open(tmp_name, "rb") as file:
                    transcription = self.groq_client.audio.transcriptions.create(
                        file=(tmp_name, file.read()),
                        model="whisper-large-v3-turbo",
                        response_format="json",
                        language="pt" if "pt" in self.language.lower() else "en"
                    )
                os.remove(tmp_name)
                return transcription.text.strip()
            except Exception as e:
                print(f"Groq Whisper falhou ({e}), usando Google como fallback...")
                pass
                
        return self.recognizer.recognize_google(audio, language=self.language)

    def listen(self) -> str:
        if not self.use_mic:
            return input("Voce: ").strip()

        # Estado: LISTENING
        self._viz_set("set_listening")
        with sr.Microphone() as source:
            print("Ouvindo...")
            try:
                # Aumentado o timeout para dar tempo de começar a falar
                audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=20)
            except sr.WaitTimeoutError:
                return ""
            except Exception as e:
                print(f"[STT] Erro ao ouvir: {e}")
                return ""
        try:
            text = self._transcribe(audio)
            print(f"Voce (STT): {text}")
            return text.strip()
        except Exception:
            return ""

    def listen_mic_only(self) -> str:
        """Forca a escuta pelo microfone (usado pelo atalho de teclado)."""
        import winsound
        try:
            # Beep curto para avisar que comecou a ouvir
            winsound.Beep(1000, 200)
        except Exception:
            pass

        # Estado: LISTENING
        self._viz_set("set_listening")
        with sr.Microphone() as source:
            print("Ouvindo (atalho)...")
            try:
                audio = self.recognizer.listen(source, timeout=8, phrase_time_limit=20)
            except Exception:
                return ""
        try:
            text = self._transcribe(audio)
            print(f"Voce (Voz): {text}")
            return text.strip()
        except Exception:
            return ""

    def start_continuous_listening(self, callback, on_speech_start=None, on_speech_end=None) -> Any:
        """Inicia escuta em background com detecção de fala em tempo real.
        callback(text: str) -> chamado quando o texto é reconhecido.
        on_speech_start() -> chamado quando detecta voz (visualizador verde).
        on_speech_end()   -> chamado quando a voz para (visualizador idle).
        Retorna uma função para parar a escuta.
        """
        import threading
        import audioop
        import time

        _running = [True]
        _speech_active = [False]
        _silence_count = [0]
        SILENCE_LIMIT = 8  # ~500ms de silêncio
        recognizer = self.recognizer
        stt_self = self

        class _MonitoredStream:
            """Proxy que intercepta reads do microfone para monitorar energia."""
            def __init__(self, inner, sample_width):
                self._inner = inner
                self._sw = sample_width

            def read(self, size):
                data = self._inner.read(size)
                if not _running[0]:
                    return data
                try:
                    energy = audioop.rms(data, self._sw)
                    if energy > recognizer.energy_threshold:
                        _silence_count[0] = 0
                        if not _speech_active[0]:
                            _speech_active[0] = True
                            if on_speech_start:
                                on_speech_start()
                    else:
                        _silence_count[0] += 1
                        if _speech_active[0] and _silence_count[0] > SILENCE_LIMIT:
                            _speech_active[0] = False
                            if on_speech_end:
                                on_speech_end()
                except Exception:
                    pass
                return data

            def close(self):
                return self._inner.close()

            def __getattr__(self, name):
                return getattr(self._inner, name)

        def _process_audio(audio):
            """Transcreve em thread separada para não bloquear o listener."""
            try:
                text = stt_self._transcribe(audio)
                # Garante idle após transcrição
                if _speech_active[0]:
                    _speech_active[0] = False
                    if on_speech_end:
                        on_speech_end()
                if text.strip():
                    callback(text.strip())
            except Exception:
                if _speech_active[0]:
                    _speech_active[0] = False
                    if on_speech_end:
                        on_speech_end()

        def _listener_thread():
            source = sr.Microphone()
            with source as s:
                recognizer.adjust_for_ambient_noise(s, duration=0.5)
                # Wrappea o stream APÓS aberto — dentro do with
                s.stream = _MonitoredStream(s.stream, s.SAMPLE_WIDTH)

                while _running[0]:
                    try:
                        audio = recognizer.listen(s, timeout=5, phrase_time_limit=30)
                        # Processa em thread separada para voltar a ouvir imediatamente
                        threading.Thread(target=_process_audio, args=(audio,), daemon=True).start()
                    except sr.WaitTimeoutError:
                        pass
                    except Exception:
                        time.sleep(0.5)

        thread = threading.Thread(target=_listener_thread, daemon=True)
        thread.start()

        def stop(wait_for_stop=True):
            _running[0] = False
            if wait_for_stop:
                thread.join(timeout=3)

        return stop

    def listen_push_to_talk(self, hotkey: str = 'ctrl+shift') -> str:
        import keyboard
        import pyaudio
        import time
        import speech_recognition as sr
        
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        
        try:
            p = pyaudio.PyAudio()
            stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        except Exception as e:
            print(f"Erro no PyAudio: {e}")
            return ""

        import winsound
        try:
            winsound.Beep(1500, 100)
        except:
            pass

        # Estado: LISTENING
        self._viz_set("set_listening")

        frames = []
        while keyboard.is_pressed(hotkey):
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
            except Exception:
                pass
            time.sleep(0.001)

        try:
            winsound.Beep(1000, 100)
        except:
            pass
            
        stream.stop_stream()
        stream.close()
        p.terminate()

        if not frames:
            return ""
            
        raw_data = b''.join(frames)
        audio_data = sr.AudioData(raw_data, RATE, 2)
        try:
            text = self._transcribe(audio_data)
            return text.strip()
        except Exception:
            return ""
