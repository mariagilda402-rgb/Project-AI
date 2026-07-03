from __future__ import annotations

import json
import os
import re
import tempfile
import time
import threading

from pathlib import Path
from typing import Iterable

import pygame
import requests

from openai import OpenAI

from src.services.tts_cache import TTSCache
from src.services.audio_utils import mp3_to_wav


def strip_text_for_speech(text: str) -> str:
    """Remove markdown e símbolos que atrapalham o TTS."""
    t = text.replace("**", "").replace("__", "").replace("*", "").replace("`", "")
    t = re.sub(r"^#+\s*", "", t, flags=re.MULTILINE)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = re.sub(r"^\s*[-•>]\s+", "", t, flags=re.MULTILINE)
    t = re.sub(r"^\s*\d+\.\s+", "", t, flags=re.MULTILINE)
    t = re.sub(r"```[\s\S]*?```", "", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]", "", t)
    return t.strip()


def split_text_for_tts(text: str, max_chars: int) -> list[str]:
    """Divide o texto em blocos <= max_chars, preferindo fim de frase."""
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


# ── Providers disponíveis (apenas API) ──────────────────────────────────────
TTS_PROVIDER_METHODS = {
    "edge":       "_speak_with_edge",
    "elevenlabs": "_speak_with_elevenlabs",
    "murf":       "_speak_with_murf",
    "openai":     "_speak_with_openai",
    "fish":       "_speak_with_fish",
    "local":      "_speak_with_local",
}

TTS_PROVIDER_FALLBACKS = ["edge", "elevenlabs", "murf", "openai", "fish", "local"]

TTS_PROVIDER_ALIASES = {
    "system": "local",
    "pyttsx3": "local",
    # Aliases legados — redirecionam para edge como melhor fallback gratuito
    "xtts": "edge",
    "xtts_rvc": "edge",
    "styletts2": "edge",
    "kokoro": "edge",
    "piper": "edge",
    "rvc": "edge",
}


def normalize_tts_provider(provider: str | None) -> str:
    value = (provider or "").strip().lower().replace("-", "_")
    if not value:
        return "edge"
    return TTS_PROVIDER_ALIASES.get(value, value if value in TTS_PROVIDER_METHODS else "edge")


def _iter_provider_tokens(raw: str | Iterable[str] | None) -> Iterable[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return (piece.strip() for piece in re.split(r"[,;\s]+", raw) if piece.strip())
    return (str(piece).strip() for piece in raw if str(piece).strip())


def parse_tts_provider_order(raw: str | Iterable[str] | None) -> list[str]:
    order: list[str] = []
    for item in _iter_provider_tokens(raw):
        provider = normalize_tts_provider(item)
        if provider in TTS_PROVIDER_METHODS and provider not in order:
            order.append(provider)
    return order


def resolve_tts_provider_order(
    primary_provider: str | None,
    configured_fallbacks: str | Iterable[str] | None = None,
) -> list[str]:
    primary = normalize_tts_provider(primary_provider)
    order = [primary] if primary in TTS_PROVIDER_METHODS else ["edge"]
    configured = parse_tts_provider_order(configured_fallbacks)
    for provider in configured or TTS_PROVIDER_FALLBACKS:
        if provider not in order:
            order.append(provider)
    for provider in TTS_PROVIDER_FALLBACKS:
        if provider not in order:
            order.append(provider)
    return order


# ── TTSService ───────────────────────────────────────────────────────────────

class TTSService:

    def __init__(
        self,
        api_key: str,
        model: str,
        voice: str,
        provider: str = "edge",
        provider_order: str | Iterable[str] | None = None,
        murf_api_key: str = "",
        murf_voice_id: str = "",
        murf_api_url: str = "https://api.murf.ai/v1/speech/generate",
        allow_system_player_on_failure: bool = False,
        max_chunk_chars: int = 1800,
        pause_between_chunks_sec: float = 0.1,
        edge_tts_rate: str = "+10%",
        edge_tts_volume: str = "-20%",
        tts_prefetch_chunks: bool = True,
        elevenlabs_api_keys: str = "",
        fish_audio_api_key: str = "",
        # Parâmetros legados ignorados — mantidos para compatibilidade de assinatura
        kokoro_voice: str = "pf_dora",
        kokoro_speed: float = 1.0,
        xtts_model_name: str = "",
        xtts_speaker_wav: str = "",
        xtts_language: str = "pt",
        xtts_device: str = "auto",
        xtts_rvc_voice: str = "Jarvis",
        xtts_python: str = "",
        xtts_persistent: bool = False,
        styletts2_command: str = "",
        styletts2_reference_wav: str = "",
        styletts2_python: str = "",
        styletts2_model_checkpoint: str = "",
        styletts2_config: str = "",
        styletts2_alpha: float = 0.3,
        styletts2_beta: float = 0.7,
        styletts2_diffusion_steps: int = 3,
        styletts2_embedding_scale: float = 1.0,
        styletts2_persistent: bool = False,
        styletts2_preload: bool = False,
        piper_repo_id: str = "",
        piper_jarvis_quality: str = "medium",
        piper_model_file: str = "",
        piper_config_file: str = "",
        piper_use_cuda: bool = False,
        piper_fx_preset: str = "none",
    ) -> None:
        self.api_key = api_key
        self.fish_audio_api_key = fish_audio_api_key
        self._local_engine = None
        self.tts_cache = TTSCache()

        # ElevenLabs — rotação de chaves com cooldown de 30 dias
        self.elevenlabs_state_file = Path("data/elevenlabs_state.json")
        self.elevenlabs_state_file.parent.mkdir(parents=True, exist_ok=True)
        self.elevenlabs_exhausted_keys: dict = {}
        if self.elevenlabs_state_file.exists():
            try:
                with open(self.elevenlabs_state_file, "r", encoding="utf-8") as f:
                    self.elevenlabs_exhausted_keys = json.load(f)
            except Exception:
                pass

        # Restaura chaves que saíram do cooldown
        current_time = time.time()
        keys_to_restore = [
            k for k, t in self.elevenlabs_exhausted_keys.items()
            if current_time - t >= 2592000  # 30 dias
        ]
        for key in keys_to_restore:
            del self.elevenlabs_exhausted_keys[key]
        if keys_to_restore:
            self._save_elevenlabs_state()
            print(f"[ElevenLabs] {len(keys_to_restore)} chaves saíram do cooldown e voltaram ao rodízio!")

        all_keys = [k.strip() for k in elevenlabs_api_keys.split(",") if k.strip()]
        self.elevenlabs_api_keys = [k for k in all_keys if k not in self.elevenlabs_exhausted_keys]
        self.current_elevenlabs_key_index = 0
        self.elevenlabs_voice_id_cache: dict = {}

        if all_keys and not self.elevenlabs_api_keys:
            print("[ElevenLabs] ALERTA: Todas as chaves estão no cooldown de 30 dias!")

        self.client = OpenAI(api_key=api_key) if api_key else None
        self.model = model
        self.voice = voice
        self.provider = normalize_tts_provider(provider)
        self.provider_order_config = provider_order
        self.provider_order = resolve_tts_provider_order(self.provider, self.provider_order_config)
        self.murf_api_key = murf_api_key
        self.murf_voice_id, self.murf_options = self._normalize_murf_voice_config(murf_voice_id)
        self.murf_api_url = murf_api_url
        self.allow_system_player_on_failure = allow_system_player_on_failure
        self.max_chunk_chars = max(100, min(8000, int(max_chunk_chars)))
        self.pause_between_chunks_sec = max(0.0, min(3.0, float(pause_between_chunks_sec)))
        self.edge_tts_rate = edge_tts_rate
        self.edge_tts_volume = edge_tts_volume
        self.tts_prefetch_chunks = bool(tts_prefetch_chunks)
        self._interrupt_event = threading.Event()
        self._pygame_ready = False
        self.last_error = ""

    # ── Stubs de compatibilidade (não fazem nada, modelos locais removidos) ──
    def warmup_xtts_async(self) -> bool:
        return False

    def warmup_styletts2_async(self) -> bool:
        return False

    def apply_agent_voice(self, provider: str, voice: str, speed: float,
                          edge_rate: str, edge_vol: str, kokoro_voice: str) -> None:
        self.provider = normalize_tts_provider(provider)
        self.provider_order = resolve_tts_provider_order(
            self.provider, getattr(self, "provider_order_config", None)
        )
        self.voice = voice
        if self.provider == "edge":
            self.edge_tts_rate = edge_rate
            self.edge_tts_volume = edge_vol
        print(f"[TTS] Provider ativo: {self.provider}")

    # ── Core speak ───────────────────────────────────────────────────────────

    def stop(self) -> None:
        self._interrupt_event.set()
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
        except Exception:
            pass
        try:
            from src.services import visualizer
            if visualizer.is_browser_connected():
                requests.post(
                    f"http://localhost:{visualizer._server_port}/api/stop_audio",
                    timeout=0.5,
                )
        except Exception:
            pass
        print("[TTS] Interrompido.")

    def set_volume(self, volume: str) -> None:
        self.edge_tts_volume = volume
        print(f"[TTS] Volume ajustado para: {volume}")

    def speak(self, text: str) -> None:
        self._interrupt_event.clear()

        # Interpreta tags de emoção opcionais do LLM
        emotion_match = re.search(
            r"^\s*\[(feliz|triste|bravo|urgente|calmo|neutro)\]", text, re.IGNORECASE
        )
        if emotion_match:
            text = text[emotion_match.end():].strip()

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
            print(f"[TTS] Erro durante speak: {e}")

    def _speak_one_chunk(self, text: str) -> None:
        if not text.strip():
            return
        order = self.provider_order or resolve_tts_provider_order(self.provider)
        for index, provider in enumerate(order):
            method_name = TTS_PROVIDER_METHODS.get(provider)
            if not method_name:
                continue
            method = getattr(self, method_name, None)
            if method is None:
                continue
            if index > 0:
                reason = f" (motivo: {self.last_error[:80]})" if self.last_error else ""
                print(f"[TTS] Fallback → {provider}{reason}")
            try:
                if method(text):
                    return
            except Exception as exc:
                self.last_error = f"{provider}: {exc!r}"
                print(f"[TTS] {self.last_error}")

    # ── Utilitários de áudio ─────────────────────────────────────────────────

    def _play_audio_file(self, path: Path) -> None:
        played_in_browser = False
        try:
            from src.services import visualizer
            if visualizer.is_browser_connected():
                r = requests.post(
                    f"http://localhost:{visualizer._server_port}/api/play_audio",
                    json={"path": str(path.resolve())},
                    timeout=5,
                )
                if r.status_code == 200:
                    played_in_browser = True
                    try:
                        visualizer.set_speaking("")
                    except Exception:
                        pass
                    for _ in range(3000):
                        if self._interrupt_event.is_set():
                            break
                        time.sleep(0.1)
                        try:
                            sr = requests.get(
                                f"http://localhost:{visualizer._server_port}/api/state",
                                timeout=2,
                            )
                            if sr.status_code == 200 and not sr.json().get("audio_ready", False):
                                break
                        except Exception:
                            pass
        except Exception:
            pass

        if not played_in_browser:
            try:
                from src.services import visualizer
                visualizer.set_speaking("")
            except Exception:
                pass
            self._play_mp3(path)

    def _play_mp3(self, path: Path) -> None:
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self._pygame_ready = True
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                if self._interrupt_event.is_set():
                    pygame.mixer.music.stop()
                    break
                time.sleep(0.05)
        except Exception as exc:
            print(f"[TTS] pygame falhou: {exc}")
            if self.allow_system_player_on_failure:
                try:
                    import subprocess
                    subprocess.Popen(
                        ["start", "", str(path)], shell=True,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                except Exception:
                    pass
        finally:
            self._pygame_teardown()

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

    def _get_local_engine(self):
        if self._local_engine is None:
            try:
                import pyttsx3
                self._local_engine = pyttsx3.init()
                self._local_engine.setProperty("rate", 170)
            except Exception:
                pass
        return self._local_engine

    # ── Murf helpers ─────────────────────────────────────────────────────────

    def _normalize_murf_voice_config(self, raw: str) -> tuple[str, dict]:
        if not raw:
            return "", {}
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                voice_id = parsed.pop("voice_id", "")
                return voice_id, parsed
        except json.JSONDecodeError:
            pass
        return raw.strip(), {}

    # ── ElevenLabs helpers ────────────────────────────────────────────────────

    def _save_elevenlabs_state(self) -> None:
        try:
            with open(self.elevenlabs_state_file, "w", encoding="utf-8") as f:
                json.dump(self.elevenlabs_exhausted_keys, f)
        except Exception:
            pass

    def _get_active_elevenlabs_key(self) -> str | None:
        if not self.elevenlabs_api_keys:
            return None
        idx = self.current_elevenlabs_key_index % len(self.elevenlabs_api_keys)
        return self.elevenlabs_api_keys[idx]

    def _rotate_elevenlabs_key(self, exhausted: bool = False) -> None:
        key = self._get_active_elevenlabs_key()
        if key and exhausted:
            self.elevenlabs_exhausted_keys[key] = time.time()
            self.elevenlabs_api_keys = [k for k in self.elevenlabs_api_keys if k != key]
            self._save_elevenlabs_state()
            print(f"[ElevenLabs] Chave esgotada. {len(self.elevenlabs_api_keys)} restantes.")
        else:
            self.current_elevenlabs_key_index += 1

    def _resolve_elevenlabs_voice_id(self, api_key: str, voice_name: str) -> str | None:
        cache_key = (api_key, voice_name)
        if cache_key in self.elevenlabs_voice_id_cache:
            return self.elevenlabs_voice_id_cache[cache_key]
        try:
            r = requests.get(
                "https://api.elevenlabs.io/v1/voices",
                headers={"xi-api-key": api_key},
                timeout=10,
            )
            r.raise_for_status()
            for v in r.json().get("voices", []):
                if v.get("name", "").lower() == voice_name.lower():
                    vid = v["voice_id"]
                    self.elevenlabs_voice_id_cache[cache_key] = vid
                    return vid
        except Exception:
            pass
        return None

    # ── Providers (API) ───────────────────────────────────────────────────────

    def _speak_with_edge(self, text: str) -> bool:
        try:
            import edge_tts
            import asyncio

            voice_map = {
                "Jarvis": "pt-BR-AntonioNeural",
                "Maria": "pt-BR-FranciscaNeural",
            }
            voice = voice_map.get(self.voice, self.voice)
            if not voice or voice not in voice_map.values():
                voice = "pt-BR-AntonioNeural"

            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / "edge.mp3"

                async def _gen():
                    communicate = edge_tts.Communicate(
                        text,
                        voice,
                        rate=self.edge_tts_rate,
                        volume=self.edge_tts_volume,
                    )
                    await communicate.save(str(out))

                asyncio.run(_gen())
                if out.is_file() and out.stat().st_size > 0:
                    self._play_audio_file(out)
                    self.last_error = ""
                    return True
            self.last_error = "Edge TTS não gerou áudio."
            return False
        except Exception as exc:
            self.last_error = f"Edge TTS: {exc!r}"
            return False

    def _speak_with_elevenlabs(self, text: str) -> bool:
        if not self.elevenlabs_api_keys:
            self.last_error = "ElevenLabs: sem chaves configuradas."
            return False
        for _ in range(len(self.elevenlabs_api_keys)):
            api_key = self._get_active_elevenlabs_key()
            if not api_key:
                break
            try:
                voice_id = self._resolve_elevenlabs_voice_id(api_key, self.voice) or self.voice
                with tempfile.TemporaryDirectory() as tmp:
                    out = Path(tmp) / "el.mp3"
                    r = requests.post(
                        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream",
                        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
                        json={
                            "text": text,
                            "model_id": "eleven_multilingual_v2",
                            "voice_settings": {"stability": 0.4, "similarity_boost": 0.8},
                        },
                        stream=True,
                        timeout=30,
                    )
                    if r.status_code == 401 or r.status_code == 422:
                        self._rotate_elevenlabs_key(exhausted=True)
                        continue
                    r.raise_for_status()
                    with open(out, "wb") as f:
                        for chunk in r.iter_content(chunk_size=4096):
                            f.write(chunk)
                    if out.is_file() and out.stat().st_size > 0:
                        self._play_audio_file(out)
                        self.last_error = ""
                        return True
            except Exception as exc:
                self.last_error = f"ElevenLabs: {exc!r}"
                self._rotate_elevenlabs_key(exhausted=False)
        self.last_error = "ElevenLabs: todas as chaves falharam."
        return False

    def _speak_with_murf(self, text: str) -> bool:
        if not self.murf_api_key:
            self.last_error = "Murf: MURF_API_KEY não configurada."
            return False
        try:
            payload = {
                "text": text,
                "voiceId": self.murf_voice_id or "Kylie",
                "format": "MP3",
                **self.murf_options,
            }
            r = requests.post(
                self.murf_api_url,
                headers={
                    "api-key": self.murf_api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30,
            )
            r.raise_for_status()
            audio_url = r.json().get("audioFile") or r.json().get("audioUrl")
            if not audio_url:
                self.last_error = "Murf: resposta sem URL de áudio."
                return False
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / "murf.mp3"
                dl = requests.get(audio_url, timeout=30)
                dl.raise_for_status()
                out.write_bytes(dl.content)
                self._play_audio_file(out)
                self.last_error = ""
                return True
        except Exception as exc:
            self.last_error = f"Murf: {exc!r}"
            return False

    def _speak_with_openai(self, text: str) -> bool:
        if not self.client:
            self.last_error = "OpenAI TTS: sem OPENAI_API_KEY."
            return False
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
                self.last_error = ""
                return True
        except Exception as exc:
            self.last_error = f"OpenAI TTS: {exc!r}"
            return False

    def _speak_with_fish(self, text: str) -> bool:
        api_key = self.fish_audio_api_key
        if not api_key:
            self.last_error = "Fish Audio: sem FISH_AUDIO_API_KEY."
            return False
        try:
            r = requests.post(
                "https://api.fish.audio/v1/tts",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"text": text, "format": "mp3", "latency": "balanced"},
                timeout=30,
                stream=True,
            )
            r.raise_for_status()
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / "fish.mp3"
                with open(out, "wb") as f:
                    for chunk in r.iter_content(chunk_size=4096):
                        f.write(chunk)
                if out.is_file() and out.stat().st_size > 0:
                    self._play_audio_file(out)
                    self.last_error = ""
                    return True
            self.last_error = "Fish Audio: sem áudio na resposta."
            return False
        except Exception as exc:
            self.last_error = f"Fish Audio: {exc!r}"
            return False

    def _speak_with_local(self, text: str) -> bool:
        """Último fallback: pyttsx3 (voz do sistema)."""
        try:
            engine = self._get_local_engine()
            if engine is None:
                self.last_error = "pyttsx3 não instalado."
                return False
            print("[TTS] Usando voz local do sistema (pyttsx3).")
            engine.say(text)
            engine.runAndWait()
            self.last_error = ""
            return True
        except Exception as exc:
            self.last_error = f"pyttsx3: {exc!r}"
            return False
