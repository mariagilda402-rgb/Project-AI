from __future__ import annotations



import json

import os

import re

import shutil

import subprocess

import tempfile

import time
import threading

from pathlib import Path

from typing import Any



import pyttsx3

import pygame

import requests

from openai import OpenAI





def strip_text_for_speech(text: str) -> str:

    """Remove markdown e excesso de simbolos que atrapalham TTS e leitura longa."""

    t = text.replace("**", "").replace("__", "").replace("*", "").replace("`", "")

    t = re.sub(r"^#+\s*", "", t, flags=re.MULTILINE)

    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)

    # Remove marcadores de lista (-, •, >) no inicio de linhas
    t = re.sub(r"^\s*[-•>]\s+", "", t, flags=re.MULTILINE)
    t = re.sub(r"^\s*\d+\.\s+", "", t, flags=re.MULTILINE)

    # Remove blocos de codigo
    t = re.sub(r"```[\s\S]*?```", "", t)

    t = re.sub(r"\n{3,}", "\n\n", t)

    t = re.sub(r"[ \t]+", " ", t)

    # Emojis geram artefactos em alguns motores TTS / pygame; remove blocos comuns.

    t = re.sub(

        r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]",

        "",

        t,

    )

    return t.strip()





def split_text_for_tts(text: str, max_chars: int) -> list[str]:

    """Parte o texto em blocos <= max_chars, preferindo cortar em fim de frase."""

    text = text.strip()

    if not text:

        return []

    max_c = max(1, min(8000, int(max_chars)))

    if len(text) <= max_c:

        return [text]

    chunks: list[str] = []

    rest = text

    guard = 0

    while rest and guard < 5000:

        guard += 1

        if len(rest) <= max_c:

            chunks.append(rest.strip())

            break

        window = rest[:max_c]

        end = max_c

        for sep in ("\n\n", ". ", "? ", "! ", "\n"):

            p = window.rfind(sep)

            if p >= max_c // 5:

                end = p + len(sep)

                break

        else:

            p = window.rfind(" ")

            if p >= max_c // 6:

                end = p + 1

        piece = rest[:end].strip()

        if not piece:

            end = max_c

            piece = rest[:end].strip()

        chunks.append(piece)

        rest = rest[end:].lstrip()

    return [c for c in chunks if c]





# Singleton Kokoro para nao recarregar o modelo (~380MB) a cada chunk.
_kokoro_instance = None
_kokoro_lock = threading.Lock()

_KOKORO_CACHE_DIR = Path("data/cache/kokoro")
_KOKORO_FILES = {
    "kokoro-v1.0.onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
    "voices-v1.0.bin": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
}


def _download_kokoro_file(filename: str, url: str) -> Path:
    """Baixa arquivo do modelo se nao existir no cache local."""
    dest = _KOKORO_CACHE_DIR / filename
    if dest.is_file():
        return dest
    _KOKORO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[Kokoro] Baixando {filename}...", flush=True)
    resp = requests.get(url, stream=True, timeout=600)
    resp.raise_for_status()
    total = int(resp.headers.get("content-length", 0))
    downloaded = 0
    tmp = dest.with_suffix(".tmp")
    with open(tmp, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1024 * 256):
            f.write(chunk)
            downloaded += len(chunk)
            if total > 0:
                pct = downloaded * 100 // total
                print(f"\r[Kokoro] {filename}: {pct}% ({downloaded // (1024*1024)}MB/{total // (1024*1024)}MB)", end="", flush=True)
    print(flush=True)
    tmp.rename(dest)
    return dest


def _get_kokoro():
    """Lazy-load do modelo Kokoro ONNX (singleton thread-safe).
    
    Baixa automaticamente do GitHub Releases na primeira execucao.
    Arquivos ficam em data/cache/kokoro/ (~390MB total).
    """
    global _kokoro_instance
    if _kokoro_instance is not None:
        return _kokoro_instance
    with _kokoro_lock:
        if _kokoro_instance is not None:
            return _kokoro_instance
        try:
            from kokoro_onnx import Kokoro

            model_path = _download_kokoro_file("kokoro-v1.0.onnx", _KOKORO_FILES["kokoro-v1.0.onnx"])
            voices_path = _download_kokoro_file("voices-v1.0.bin", _KOKORO_FILES["voices-v1.0.bin"])
            print("[Kokoro] Carregando modelo ONNX...", flush=True)
            _kokoro_instance = Kokoro(str(model_path), str(voices_path))
            print("[Kokoro] Modelo carregado com sucesso.", flush=True)
        except Exception as exc:
            print(f"[Kokoro] Falha ao carregar modelo: {exc}")
            _kokoro_instance = None
    return _kokoro_instance


class TTSService:

    def __init__(

        self,

        api_key: str,

        model: str,

        voice: str,

        provider: str = "local",

        murf_api_key: str = "",

        murf_voice_id: str = "",

        murf_api_url: str = "https://api.murf.ai/v1/speech/generate",

        allow_system_player_on_failure: bool = False,

        max_chunk_chars: int = 200,
        pause_between_chunks_sec: float = 0.1,
        edge_tts_rate: str = "+10%",
        edge_tts_volume: str = "-20%",
        kokoro_voice: str = "pf_dora",
        kokoro_speed: float = 1.0,
    ) -> None:

        self.api_key = api_key
        self.client = OpenAI(api_key=api_key) if api_key else None

        self.model = model

        self.voice = voice

        self.provider = provider.strip().lower()

        self.murf_api_key = murf_api_key

        self.murf_voice_id, self.murf_options = self._normalize_murf_voice_config(murf_voice_id)

        self.murf_api_url = murf_api_url

        self.allow_system_player_on_failure = allow_system_player_on_failure

        self.max_chunk_chars = max(100, min(8000, int(max_chunk_chars)))

        self.pause_between_chunks_sec = max(0.0, min(3.0, float(pause_between_chunks_sec)))
        self.edge_tts_rate = edge_tts_rate
        self.edge_tts_volume = edge_tts_volume
        self.kokoro_voice = (kokoro_voice or "pf_dora").strip()
        self.kokoro_speed = max(0.5, min(2.0, kokoro_speed))

        self.local_engine = pyttsx3.init()
        self.local_engine.setProperty("rate", 170)

        self._interrupt_event = threading.Event()
        self._pygame_ready = False
        self.last_error = ""

        # Pre-load Kokoro model in background to avoid delay if fallback is needed
        self._kokoro = None
        if self.provider == "kokoro":
            self._kokoro = _get_kokoro()
        else:
            threading.Thread(target=self._preload_kokoro, daemon=True).start()

        print("[TTS] Inicializado. Provider principal:", provider)

    def _preload_kokoro(self):
        try:
            self._kokoro = _get_kokoro()
        except Exception:
            pass

    def stop(self) -> None:
        """Sinaliza para parar a fala atual."""
        self._interrupt_event.set()
        try:
            if self._pygame_ready and pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass
            
        try:
            from src.services import visualizer
            if visualizer.is_browser_connected():
                import requests
                requests.post(f"http://localhost:{visualizer._server_port}/api/stop_audio", timeout=1)
        except Exception:
            pass

    def speak(self, text: str) -> None:
        self._interrupt_event.clear()
        clean = strip_text_for_speech(text)

        if not clean:
            return

        try:
            chunks = split_text_for_tts(clean, self.max_chunk_chars)

            for i, chunk in enumerate(chunks):
                if self._interrupt_event.is_set():
                    break

                if i > 0 and self.pause_between_chunks_sec > 0:
                    self._pygame_teardown()
                    time.sleep(self.pause_between_chunks_sec)
                    
                if self._interrupt_event.is_set():
                    break

                self._speak_one_chunk(chunk)
        except Exception as e:
            # Captura qualquer erro no TTS para não travar
            print(f"[TTS] Erro durante speak: {e}")
        # NÃO chama set_idle aqui — o main.py gerencia o estado final



    def _play_audio_file(self, path: Path) -> None:
        """Toca áudio pelo browser (audio-reativo) ou fallback local."""
        played_in_browser = False
        try:
            from src.services import visualizer
            if visualizer.is_browser_connected():
                # Envia para o visualizador
                import requests
                r = requests.post(f"http://localhost:{visualizer._server_port}/api/play_audio", json={"path": str(path.resolve())}, timeout=5)
                if r.status_code == 200:
                    played_in_browser = True
                    # set_speaking SÓ após o browser aceitar o áudio
                    try:
                        visualizer.set_speaking("")
                    except Exception:
                        pass
                    # Espera acabar ou ser interrompido
                    for _ in range(3000):
                        if self._interrupt_event.is_set():
                            break
                        time.sleep(0.1)
                        try:
                            sr = requests.get(f"http://localhost:{visualizer._server_port}/api/state", timeout=2)
                            if sr.status_code == 200 and not sr.json().get("audio_ready", False):
                                break
                        except Exception:
                            pass
        except Exception:
            pass
            
        if not played_in_browser:
            # set_speaking para fallback local (pygame)
            try:
                from src.services import visualizer
                visualizer.set_speaking("")
            except Exception:
                pass
            self._play_mp3(path)

    def _speak_one_chunk(self, text: str) -> None:
        if not text.strip():
            return

        if self.provider == "murf":
            if self._speak_with_murf(text):
                return

        if self.provider == "edge":
            if self._speak_with_edge(text):
                return

        if self.provider == "kokoro":
            if self._speak_with_kokoro(text):
                return

        if self.client:
            try:
                with tempfile.TemporaryDirectory() as tmp:
                    out = Path(tmp) / "speech.mp3"
                    with self.client.audio.speech.with_streaming_response.create(
                        model=self.model,
                        voice=self.voice,
                        input=text,
                    ) as response:
                        response.stream_to_file(out)
                    self._play_audio_file(out)
                    return
            except Exception as e:
                self.last_error = f"OpenAI error: {e}"

        # Kokoro como fallback offline (antes do pyttsx3)
        if self.provider != "kokoro":
            if self._speak_with_kokoro(text):
                return

        if self.last_error:
            print(f"[DEBUG TTS Fallback] Motivo: {self.last_error}")
        self.local_engine.say(text)
        self.local_engine.runAndWait()



    def _pygame_teardown(self) -> None:

        if not self._pygame_ready:

            return

        try:

            pygame.mixer.music.stop()

            try:

                pygame.mixer.music.unload()

            except Exception:

                pass

            pygame.mixer.quit()

        except Exception:

            pass

        self._pygame_ready = False



    def _speak_with_edge(self, text: str) -> bool:
        try:
            out = Path(tempfile.gettempdir()) / f"edge_speech_{threading.get_ident()}.mp3"
            
            # Remove o arquivo antigo se existir para nao dar conflito
            try:
                if out.exists():
                    out.unlink()
            except Exception:
                pass
                
            cmd = [
                "edge-tts",
                "--text", text,
                "--write-media", str(out),
                "--voice", self.voice or "pt-BR-ThalitaNeural",
                f"--rate={self.edge_tts_rate}",
                f"--volume={self.edge_tts_volume}"
            ]
            creationflags = 0
            if os.name == "nt":
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            
            p = subprocess.Popen(
                cmd, 
                creationflags=creationflags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            while p.poll() is None:
                if self._interrupt_event.is_set():
                    try:
                        p.terminate()
                    except Exception:
                        pass
                    return True # Interrompido
                time.sleep(0.05)
            
            if p.returncode != 0:
                self.last_error = f"Edge-TTS falhou com codigo {p.returncode}"
                return False
                
            if out.exists() and out.stat().st_size > 0:
                self._play_audio_file(out)
                
                # Descarrega o audio do pygame explicitamente para liberar o arquivo
                try:
                    pygame.mixer.music.unload()
                except Exception:
                    pass
                    
                self.last_error = ""
                return True
            self.last_error = "Arquivo edge-tts não gerado."
            return False
        except Exception as exc:
            self.last_error = f"Erro no edge-tts: {exc!r}"
            return False


    def _speak_with_kokoro(self, text: str) -> bool:
        """Gera audio localmente com Kokoro ONNX (offline, sem internet)."""
        kokoro = _get_kokoro()
        if kokoro is None:
            self.last_error = "Kokoro nao disponivel (modelo nao carregado)."
            return False
        try:
            import soundfile as sf

            samples, sample_rate = kokoro.create(
                text,
                voice=self.kokoro_voice,
                speed=self.kokoro_speed,
                lang="pt-br",
            )
            if samples is None or len(samples) == 0:
                self.last_error = "Kokoro gerou audio vazio."
                return False

            out = Path(tempfile.gettempdir()) / f"kokoro_speech_{threading.get_ident()}.wav"
            sf.write(str(out), samples, sample_rate)

            if out.is_file():
                self._play_wav(out)
                self.last_error = ""
                return True

            self.last_error = "Arquivo Kokoro WAV nao gerado."
            return False
        except Exception as exc:
            self.last_error = f"Erro no Kokoro TTS: {exc!r}"
            return False


    def _play_wav(self, path: Path) -> None:
        """Toca um WAV usando o visualizador, ffplay ou pygame."""
        abs_path = path.resolve()
        if not abs_path.is_file():
            raise FileNotFoundError(str(abs_path))

        # Tenta pelo visualizador do navegador (audio-reativo)
        played_in_browser = False
        try:
            from src.services import visualizer
            if visualizer.is_browser_connected():
                import requests
                r = requests.post(f"http://localhost:{visualizer._server_port}/api/play_audio", json={"path": str(abs_path)}, timeout=5)
                if r.status_code == 200:
                    played_in_browser = True
                    for _ in range(600):
                        if self._interrupt_event.is_set():
                            break
                        time.sleep(0.5)
                        try:
                            sr = requests.get(f"http://localhost:{visualizer._server_port}/api/state", timeout=2)
                            if sr.status_code == 200 and not sr.json().get("audio_ready", False):
                                break
                        except Exception:
                            pass
        except Exception:
            pass
        if played_in_browser:
            return

        # Tenta ffplay (sem janela)
        if self._try_play_with_ffplay(abs_path):
            return

        # Fallback: pygame
        try:
            self._init_pygame_mixer(abs_path)
            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
            pygame.mixer.music.load(str(abs_path))
            pygame.mixer.music.play()
            time.sleep(0.08)
            clock = pygame.time.Clock()
            while pygame.mixer.music.get_busy():
                clock.tick(60)
            return
        except Exception as exc:
            raise RuntimeError(f"Nao foi possivel tocar o WAV. pygame: {exc!r}")

    def _speak_with_murf(self, text: str) -> bool:

        if not self.murf_api_key or not self.murf_voice_id:

            self.last_error = "Murf sem API key ou voice id."

            return False

        try:

            payload_candidates: list[dict[str, Any]] = [

                {"text": text, "voiceId": self.murf_voice_id, **self.murf_options},

                {"text": text, "voice_id": self.murf_voice_id},

                {"text": text, "voiceId": self.murf_voice_id, "format": "MP3", **self.murf_options},

                {"text": text, "voice_id": self.murf_voice_id, "format": "MP3"},

            ]

            headers_candidates: list[dict[str, str]] = [

                {"api-key": self.murf_api_key, "Content-Type": "application/json"},

                {"x-api-key": self.murf_api_key, "Content-Type": "application/json"},

            ]



            last_failure = "Falha desconhecida no Murf."

            for headers in headers_candidates:

                for payload in payload_candidates:

                    resp = requests.post(

                        self.murf_api_url,

                        json=payload,

                        headers=headers,

                        timeout=60,

                    )

                    if resp.status_code >= 400:

                        last_failure = (

                            f"Murf HTTP {resp.status_code}: {resp.text[:220].strip()}"

                        )

                        continue



                    data = resp.json()

                    audio_url = (

                        data.get("audioFile")

                        or data.get("audioUrl")

                        or data.get("audio_file")

                        or data.get("file")

                        or data.get("audioFileUrl")

                    )

                    if not audio_url:

                        last_failure = f"Murf sem URL de audio: {str(data)[:220]}"

                        continue



                    audio_resp = requests.get(audio_url, timeout=60)

                    if audio_resp.status_code >= 400:

                        last_failure = (

                            f"Download audio Murf HTTP {audio_resp.status_code}: "

                            f"{audio_resp.text[:220].strip()}"

                        )

                        continue



                    out = self._murf_cache_path()

                    out.parent.mkdir(parents=True, exist_ok=True)

                    out.write_bytes(audio_resp.content)

                    try:

                        self._play_audio_file(out)

                    except Exception as exc:

                        last_failure = f"Audio Murf gerado, mas falhou ao tocar: {exc!r}"

                        continue

                    self.last_error = ""

                    return True



            self.last_error = last_failure

            return False

        except Exception as exc:

            self.last_error = f"Excecao ao falar com Murf API: {exc!r}"

            return False



    @staticmethod

    def _murf_cache_path() -> Path:

        return Path("data/cache/murf_last.mp3")



    def _play_mp3(self, path: Path) -> None:

        """

        Toca MP3 dentro do processo (pygame). Opcional: ffplay sem janela se estiver no PATH.

        Abrir o reprodutor do Windows (os.startfile) fica desligado por padrao — ative

        TTS_ALLOW_SYSTEM_PLAYER apenas se precisar de fallback manual.

        """

        abs_path = path.resolve()

        if not abs_path.is_file():

            raise FileNotFoundError(str(abs_path))



        errors: list[str] = []

        # ffplay costuma decodificar MP3 corretamente no Windows; pygame as vezes
        # toca com tom/velocidade errados se a taxa do ficheiro nao bate com o mixer.
        if self._try_play_with_ffplay(abs_path):
            return

        try:

            self._init_pygame_mixer(abs_path)

            pygame.mixer.music.stop()

            try:

                pygame.mixer.music.unload()

            except Exception:

                pass

            pygame.mixer.music.load(str(abs_path))

            pygame.mixer.music.play()

            time.sleep(0.08)

            clock = pygame.time.Clock()

            while pygame.mixer.music.get_busy():

                clock.tick(60)

            return

        except Exception as exc:

            errors.append(f"pygame: {exc!r}")



        if self.allow_system_player_on_failure and os.name == "nt":

            os.startfile(str(abs_path))  # type: ignore[attr-defined]

            return



        raise RuntimeError("Nao foi possivel tocar o MP3. " + " | ".join(errors))



    @staticmethod

    def _read_mp3_sample_rate_hz(path: Path | None) -> int:

        """Taxa de amostragem do MP3 (evita som acelerado/robotico no pygame)."""

        if not path or not path.is_file():

            return 44100

        try:

            from mutagen.mp3 import MP3

            info = MP3(str(path)).info

            rate = int(getattr(info, "sample_rate", 0) or 0)

            if 8000 <= rate <= 192_000:

                return rate

        except Exception:

            pass

        return 44100



    def _init_pygame_mixer(self, mp3_path: Path | None = None) -> None:

        """Reabre o mixer com a taxa do ficheiro (SDL em Windows e sensivel a mismatch)."""

        try:

            pygame.mixer.quit()

        except Exception:

            pass

        self._pygame_ready = False

        sr = self._read_mp3_sample_rate_hz(mp3_path)

        for freq in (sr, 48000, 44100, 22050):

            try:

                pygame.mixer.init(

                    frequency=freq, size=-16, channels=2, buffer=4096

                )

                self._pygame_ready = True

                return

            except Exception:

                continue

        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)

        self._pygame_ready = True



    @staticmethod

    def _try_play_with_ffplay(path: Path) -> bool:

        ffplay = shutil.which("ffplay")

        if not ffplay:

            return False

        try:

            creationflags = 0

            if os.name == "nt":

                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

            subprocess.run(

                [

                    ffplay,

                    "-nodisp",

                    "-autoexit",

                    "-loglevel",

                    "quiet",

                    "-volume",

                    "85",

                    str(path),

                ],

                check=True,

                timeout=600,

                creationflags=creationflags,

            )

            return True

        except Exception:

            return False



    @staticmethod

    def _normalize_murf_voice_config(raw_value: str) -> tuple[str, dict[str, Any]]:

        value = (raw_value or "").strip()

        if not value:

            return "", {}

        if value.startswith("{") and value.endswith("}"):

            try:

                payload = json.loads(value)

                if isinstance(payload, dict):

                    extracted = str(payload.get("voice_id", "")).strip()

                    options: dict[str, Any] = {}

                    locale = str(payload.get("multiNativeLocale", "")).strip()

                    style = str(payload.get("style", "")).strip()

                    if locale:

                        options["locale"] = locale

                    if style:

                        options["style"] = style

                    if extracted:

                        return extracted, options

            except Exception:

                return value, {}

        return value, {}


