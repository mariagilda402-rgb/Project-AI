from __future__ import annotations



import atexit
import json
from collections import deque

import os
import queue

import re

import shutil
import shlex

import subprocess

import tempfile
import time
import threading
import uuid

from pathlib import Path

from typing import Any, Iterable

from src.services.tts_cache import TTSCache
from src.services.audio_fx import apply_fx_to_wav
from src.services.audio_utils import mp3_to_wav



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





TTS_PROVIDER_FALLBACKS = [
    "edge",
    "kokoro",
    "rvc",
    "piper",
    "openai",
    "elevenlabs",
    "murf",
    "fish",
    "local",
]

TTS_PROVIDER_ALIASES = {
    "coqui": "xtts",
    "coqui_xtts": "xtts",
    "coqui-xtts": "xtts",
    "xttsv2": "xtts",
    "xtts-v2": "xtts",
    "system": "local",
    "pyttsx3": "local",
}

TTS_PROVIDER_METHODS = {
    "xtts": "_speak_with_xtts",
    "xtts_rvc": "_speak_with_xtts_rvc",
    "styletts2": "_speak_with_styletts2",
    "fish": "_speak_with_fish",
    "murf": "_speak_with_murf",
    "elevenlabs": "_speak_with_elevenlabs",
    "edge": "_speak_with_edge",
    "rvc": "_speak_with_rvc",
    "kokoro": "_speak_with_kokoro",
    "piper": "_speak_with_piper",
    "openai": "_speak_with_openai",
    "local": "_speak_with_local",
}


def normalize_tts_provider(provider: str | None) -> str:
    value = (provider or "").strip().lower().replace("-", "_")
    if not value:
        return "xtts"
    return TTS_PROVIDER_ALIASES.get(value, value)


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
    order = [primary] if primary in TTS_PROVIDER_METHODS else ["xtts"]

    configured = parse_tts_provider_order(configured_fallbacks)
    for provider in configured or TTS_PROVIDER_FALLBACKS:
        if provider not in order:
            order.append(provider)

    for provider in TTS_PROVIDER_FALLBACKS:
        if provider not in order:
            order.append(provider)

    return order


def piper_jarvis_model_files(quality: str) -> tuple[str, str]:
    q = (quality or "medium").strip().lower()
    if q not in {"medium", "high"}:
        q = "medium"
    model_file = f"en/en_GB/jarvis/{q}/jarvis-{q}.onnx"
    return model_file, f"{model_file}.json"


_xtts_instances: dict[tuple[str, str], Any] = {}
_xtts_lock = threading.Lock()
_xtts_external_worker_lock = threading.Lock()
_xtts_external_worker: "_PersistentXTTSWorker | None" = None
_xtts_external_worker_key: tuple[str, str, str, str, str] | None = None
_styletts2_external_worker_lock = threading.Lock()
_styletts2_external_worker: "_PersistentStyleTTS2Worker | None" = None
_styletts2_external_worker_key: tuple[str, str, str, str, float, float, int, float] | None = None


def _tts_utf8_subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    return env


def _resolve_xtts_device(raw_device: str) -> str:
    device = (raw_device or "auto").strip().lower()
    if device != "auto":
        return device
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


class _PersistentXTTSWorker:
    def __init__(
        self,
        *,
        python_exe: str,
        model_name: str,
        speaker: str,
        language: str,
        device: str,
        cwd: Path,
        startup_timeout: float = 900.0,
        request_timeout: float = 900.0,
    ) -> None:
        self.python_exe = python_exe
        self.model_name = model_name
        self.speaker = speaker
        self.language = language
        self.device = device
        self.cwd = cwd
        self.startup_timeout = startup_timeout
        self.request_timeout = request_timeout
        self.proc: subprocess.Popen[str] | None = None
        self.stdout_queue: queue.Queue[str] = queue.Queue()
        self.stderr_tail: deque[str] = deque(maxlen=80)
        self.lock = threading.Lock()

    def is_alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def preload(self) -> None:
        with self.lock:
            self._ensure_started()

    def stop(self) -> None:
        proc = self.proc
        self.proc = None
        if proc is None or proc.poll() is not None:
            return
        if os.name == "nt":
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                )
                return
            except Exception:
                pass
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def synthesize(self, text: str, out: Path) -> None:
        with self.lock:
            self._ensure_started()
            assert self.proc is not None
            if self.proc.stdin is None:
                raise RuntimeError("XTTS worker sem stdin.")
            request_id = uuid.uuid4().hex
            payload = {
                "id": request_id,
                "text": text,
                "out": str(out),
                "language": self.language,
            }
            self.proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
            self.proc.stdin.flush()
            response = self._wait_for_message(request_id, self.request_timeout)
            if not response.get("ok"):
                raise RuntimeError(str(response.get("error") or "XTTS worker falhou."))

    def _ensure_started(self) -> None:
        if self.is_alive():
            return
        self.stop()
        self.stdout_queue = queue.Queue()
        self.stderr_tail.clear()
        cmd = [
            self.python_exe,
            "-m",
            "src.services.xtts_external_worker",
            "--server",
            "--model",
            self.model_name,
            "--speaker",
            self.speaker,
            "--language",
            self.language,
            "--device",
            self.device,
        ]
        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self.proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=str(self.cwd),
            env=_tts_utf8_subprocess_env(),
            creationflags=creationflags,
        )
        if self.proc.stdout is not None:
            threading.Thread(
                target=self._drain_stdout,
                args=(self.proc.stdout,),
                daemon=True,
            ).start()
        if self.proc.stderr is not None:
            threading.Thread(
                target=self._drain_stderr,
                args=(self.proc.stderr,),
                daemon=True,
            ).start()
        self._wait_for_message(None, self.startup_timeout)

    def _drain_stdout(self, stream) -> None:
        for line in stream:
            self.stdout_queue.put(line)

    def _drain_stderr(self, stream) -> None:
        for line in stream:
            text = line.strip()
            if text:
                self.stderr_tail.append(text)

    def _wait_for_message(
        self, request_id: str | None, timeout_sec: float
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            proc = self.proc
            if proc is not None and proc.poll() is not None and self.stdout_queue.empty():
                raise RuntimeError(
                    "XTTS worker encerrou antes da resposta. "
                    + self._stderr_summary()
                )
            remaining = max(0.05, min(0.5, deadline - time.monotonic()))
            try:
                line = self.stdout_queue.get(timeout=remaining)
            except queue.Empty:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(message, dict):
                continue
            if request_id is None and message.get("type") == "ready" and message.get("ok"):
                return message
            if request_id is not None and message.get("id") == request_id:
                return message
        raise TimeoutError("Timeout aguardando XTTS worker. " + self._stderr_summary())

    def _stderr_summary(self) -> str:
        if not self.stderr_tail:
            return ""
        return "Ultimo stderr: " + " | ".join(list(self.stderr_tail)[-6:])


class _PersistentStyleTTS2Worker:
    def __init__(
        self,
        *,
        python_exe: str,
        reference: str,
        model_checkpoint: str,
        config_path: str,
        alpha: float,
        beta: float,
        diffusion_steps: int,
        embedding_scale: float,
        cwd: Path,
        startup_timeout: float = 900.0,
        request_timeout: float = 900.0,
    ) -> None:
        self.python_exe = python_exe
        self.reference = reference
        self.model_checkpoint = model_checkpoint
        self.config_path = config_path
        self.alpha = alpha
        self.beta = beta
        self.diffusion_steps = diffusion_steps
        self.embedding_scale = embedding_scale
        self.cwd = cwd
        self.startup_timeout = startup_timeout
        self.request_timeout = request_timeout
        self.proc: subprocess.Popen[str] | None = None
        self.stdout_queue: queue.Queue[str] = queue.Queue()
        self.stderr_tail: deque[str] = deque(maxlen=80)
        self.lock = threading.Lock()

    def is_alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def preload(self) -> None:
        with self.lock:
            self._ensure_started()

    def stop(self) -> None:
        proc = self.proc
        self.proc = None
        if proc is None or proc.poll() is not None:
            return
        if os.name == "nt":
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                )
                return
            except Exception:
                pass
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def synthesize(self, text: str, out: Path) -> None:
        with self.lock:
            self._ensure_started()
            assert self.proc is not None
            if self.proc.stdin is None:
                raise RuntimeError("StyleTTS2 worker sem stdin.")
            request_id = uuid.uuid4().hex
            payload = {
                "id": request_id,
                "text": text,
                "out": str(out),
                "alpha": self.alpha,
                "beta": self.beta,
                "diffusion_steps": self.diffusion_steps,
                "embedding_scale": self.embedding_scale,
            }
            self.proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
            self.proc.stdin.flush()
            response = self._wait_for_message(request_id, self.request_timeout)
            if not response.get("ok"):
                raise RuntimeError(str(response.get("error") or "StyleTTS2 worker falhou."))

    def _ensure_started(self) -> None:
        if self.is_alive():
            return
        self.stop()
        self.stdout_queue = queue.Queue()
        self.stderr_tail.clear()
        cmd = [
            self.python_exe,
            "-m",
            "src.services.styletts2_external_worker",
            "--server",
            "--reference",
            self.reference,
            "--alpha",
            str(self.alpha),
            "--beta",
            str(self.beta),
            "--diffusion-steps",
            str(self.diffusion_steps),
            "--embedding-scale",
            str(self.embedding_scale),
        ]
        if self.model_checkpoint:
            cmd.extend(["--model-checkpoint", self.model_checkpoint])
        if self.config_path:
            cmd.extend(["--config", self.config_path])
        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self.proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=str(self.cwd),
            env=_tts_utf8_subprocess_env(),
            creationflags=creationflags,
        )
        if self.proc.stdout is not None:
            threading.Thread(
                target=self._drain_stdout,
                args=(self.proc.stdout,),
                daemon=True,
            ).start()
        if self.proc.stderr is not None:
            threading.Thread(
                target=self._drain_stderr,
                args=(self.proc.stderr,),
                daemon=True,
            ).start()
        self._wait_for_message(None, self.startup_timeout)

    def _drain_stdout(self, stream) -> None:
        for line in stream:
            self.stdout_queue.put(line)

    def _drain_stderr(self, stream) -> None:
        for line in stream:
            text = line.strip()
            if text:
                self.stderr_tail.append(text)

    def _wait_for_message(
        self, request_id: str | None, timeout_sec: float
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            proc = self.proc
            if proc is not None and proc.poll() is not None and self.stdout_queue.empty():
                raise RuntimeError(
                    "StyleTTS2 worker encerrou antes da resposta. "
                    + self._stderr_summary()
                )
            remaining = max(0.05, min(0.5, deadline - time.monotonic()))
            try:
                line = self.stdout_queue.get(timeout=remaining)
            except queue.Empty:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(message, dict):
                continue
            if request_id is None and message.get("type") == "ready" and message.get("ok"):
                return message
            if request_id is not None and message.get("id") == request_id:
                return message
        raise TimeoutError("Timeout aguardando StyleTTS2 worker. " + self._stderr_summary())

    def _stderr_summary(self) -> str:
        if not self.stderr_tail:
            return ""
        return "Ultimo stderr: " + " | ".join(list(self.stderr_tail)[-6:])


def _get_xtts_external_worker(
    *,
    python_exe: str,
    model_name: str,
    speaker: str,
    language: str,
    device: str,
) -> _PersistentXTTSWorker:
    global _xtts_external_worker, _xtts_external_worker_key
    cwd = Path(__file__).resolve().parents[2]
    key = (python_exe, model_name, speaker, language, device)
    with _xtts_external_worker_lock:
        if (
            _xtts_external_worker is not None
            and _xtts_external_worker_key == key
            and _xtts_external_worker.is_alive()
        ):
            return _xtts_external_worker
        if _xtts_external_worker is not None:
            _xtts_external_worker.stop()
        _xtts_external_worker = _PersistentXTTSWorker(
            python_exe=python_exe,
            model_name=model_name,
            speaker=speaker,
            language=language,
            device=device,
            cwd=cwd,
        )
        _xtts_external_worker_key = key
        return _xtts_external_worker


def _get_styletts2_external_worker(
    *,
    python_exe: str,
    reference: str,
    model_checkpoint: str = "",
    config_path: str = "",
    alpha: float = 0.3,
    beta: float = 0.7,
    diffusion_steps: int = 3,
    embedding_scale: float = 1.0,
) -> _PersistentStyleTTS2Worker:
    global _styletts2_external_worker, _styletts2_external_worker_key
    cwd = Path(__file__).resolve().parents[2]
    key = (
        python_exe,
        reference,
        model_checkpoint,
        config_path,
        float(alpha),
        float(beta),
        int(diffusion_steps),
        float(embedding_scale),
    )
    with _styletts2_external_worker_lock:
        if (
            _styletts2_external_worker is not None
            and _styletts2_external_worker_key == key
            and _styletts2_external_worker.is_alive()
        ):
            return _styletts2_external_worker
        if _styletts2_external_worker is not None:
            _styletts2_external_worker.stop()
        _styletts2_external_worker = _PersistentStyleTTS2Worker(
            python_exe=python_exe,
            reference=reference,
            model_checkpoint=model_checkpoint,
            config_path=config_path,
            alpha=alpha,
            beta=beta,
            diffusion_steps=diffusion_steps,
            embedding_scale=embedding_scale,
            cwd=cwd,
        )
        _styletts2_external_worker_key = key
        return _styletts2_external_worker


def _stop_xtts_external_worker() -> None:
    global _xtts_external_worker, _xtts_external_worker_key
    with _xtts_external_worker_lock:
        if _xtts_external_worker is not None:
            _xtts_external_worker.stop()
        _xtts_external_worker = None
        _xtts_external_worker_key = None


def _stop_styletts2_external_worker() -> None:
    global _styletts2_external_worker, _styletts2_external_worker_key
    with _styletts2_external_worker_lock:
        if _styletts2_external_worker is not None:
            _styletts2_external_worker.stop()
        _styletts2_external_worker = None
        _styletts2_external_worker_key = None


atexit.register(_stop_xtts_external_worker)
atexit.register(_stop_styletts2_external_worker)


def _split_reference_audio_paths(raw_value: str) -> list[Path]:
    paths: list[Path] = []
    for item in re.split(r"[;,]", raw_value or ""):
        value = os.path.expandvars(os.path.expanduser(item.strip()))
        if value:
            paths.append(Path(value))
    return paths


def _get_xtts(model_name: str, device: str):
    resolved_device = _resolve_xtts_device(device)
    cache_key = (model_name, resolved_device)
    if cache_key in _xtts_instances:
        return _xtts_instances[cache_key]
    with _xtts_lock:
        if cache_key in _xtts_instances:
            return _xtts_instances[cache_key]
        try:
            try:
                import transformers.utils.import_utils as import_utils

                if not hasattr(import_utils, "is_torchcodec_available"):
                    import_utils.is_torchcodec_available = lambda: False
            except Exception:
                pass
            from TTS.api import TTS as CoquiTTS
        except Exception as exc:
            raise RuntimeError(
                "Coqui TTS nao instalado. Instale o pacote opcional com: pip install coqui-tts"
            ) from exc

        api = CoquiTTS(model_name)
        if hasattr(api, "to"):
            api = api.to(resolved_device)
        _xtts_instances[cache_key] = api
        return api


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

            # Tenta injetar GPU AMD
            try:
                import onnxruntime as rt
                if hasattr(_kokoro_instance, 'sess'):
                    print("[Kokoro] Tentando injetar DmlExecutionProvider...", flush=True)
                    # Recria a sessao com o provider DML
                    _kokoro_instance.sess = rt.InferenceSession(
                        str(model_path),
                        providers=["DmlExecutionProvider", "CPUExecutionProvider"]
                    )
            except Exception as e:
                print(f"[Kokoro] Fallback GPU AMD falhou: {e}")

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

        provider_order: str | Iterable[str] | None = None,

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
        xtts_model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2",
        xtts_speaker_wav: str = "",
        xtts_language: str = "pt",
        xtts_device: str = "auto",
        xtts_rvc_voice: str = "Jarvis",
        xtts_python: str = "",
        xtts_persistent: bool = True,
        styletts2_command: str = "",
        styletts2_reference_wav: str = "",
        styletts2_python: str = "",
        styletts2_model_checkpoint: str = "",
        styletts2_config: str = "",
        styletts2_alpha: float = 0.3,
        styletts2_beta: float = 0.7,
        styletts2_diffusion_steps: int = 3,
        styletts2_embedding_scale: float = 1.0,
        styletts2_persistent: bool = True,
        styletts2_preload: bool = False,
        tts_prefetch_chunks: bool = True,
        elevenlabs_api_keys: str = "",
        piper_repo_id: str = "",
        piper_jarvis_quality: str = "medium",
        piper_model_file: str = "",
        piper_config_file: str = "",
        piper_use_cuda: bool = False,
        piper_fx_preset: str = "none",
        fish_audio_api_key: str = "",
    ) -> None:

        self.api_key = api_key
        self.fish_audio_api_key = fish_audio_api_key

        # Módulos lazy — só inicializados quando realmente usados
        self._rvc_manager = None   # lazy: criado na primeira chamada ao RVC
        self._local_engine = None  # lazy: só se todos os providers online falharem
        self.tts_cache = TTSCache()

        # Sistema de rotação de chaves ElevenLabs (Cooldown de 30 dias)
        self.elevenlabs_state_file = Path("data/elevenlabs_state.json")
        self.elevenlabs_state_file.parent.mkdir(parents=True, exist_ok=True)
        self.elevenlabs_exhausted_keys = {}
        if self.elevenlabs_state_file.exists():
            try:
                with open(self.elevenlabs_state_file, "r", encoding="utf-8") as f:
                    self.elevenlabs_exhausted_keys = json.load(f)
            except Exception:
                pass

        # Limpa chaves que já passaram do cooldown de 30 dias (30 * 24 * 60 * 60 segundos = 2592000)
        current_time = time.time()
        keys_to_restore = []
        for key, exhausted_time in self.elevenlabs_exhausted_keys.items():
            if current_time - exhausted_time >= 2592000:
                keys_to_restore.append(key)

        for key in keys_to_restore:
            del self.elevenlabs_exhausted_keys[key]

        if keys_to_restore:
            self._save_elevenlabs_state()
            print(f"[ElevenLabs] {len(keys_to_restore)} chaves saíram do cooldown de 30 dias e voltaram para o rodízio!")

        all_keys = [k.strip() for k in elevenlabs_api_keys.split(",") if k.strip()]
        self.elevenlabs_api_keys = [k for k in all_keys if k not in self.elevenlabs_exhausted_keys]
        self.current_elevenlabs_key_index = 0
        self.elevenlabs_voice_id_cache = {} # Mapeia (api_key, voice_name) -> voice_id

        if all_keys and not self.elevenlabs_api_keys:
            print("[ElevenLabs] ALERTA: Todas as suas chaves estão no cooldown de 30 dias! O TTS vai falhar.")

        self.client = OpenAI(api_key=api_key) if api_key else None

        self.model = model

        self.voice = voice

        self.provider = normalize_tts_provider(provider)
        self.provider_order_config = provider_order
        self.provider_order = resolve_tts_provider_order(
            self.provider, self.provider_order_config
        )

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
        self.xtts_model_name = (
            xtts_model_name or "tts_models/multilingual/multi-dataset/xtts_v2"
        ).strip()
        self.xtts_speaker_wav = (xtts_speaker_wav or "").strip()
        self.xtts_language = (xtts_language or "pt").strip().lower()
        self.xtts_device = (xtts_device or "auto").strip().lower()
        self.xtts_rvc_voice = (xtts_rvc_voice or "Jarvis").strip() or "Jarvis"
        self.xtts_python = (xtts_python or "").strip()
        self.xtts_persistent = bool(xtts_persistent)
        self.styletts2_command = (styletts2_command or "").strip()
        self.styletts2_reference_wav = (styletts2_reference_wav or "").strip()
        self.styletts2_python = (styletts2_python or "").strip()
        self.styletts2_model_checkpoint = (styletts2_model_checkpoint or "").strip()
        self.styletts2_config = (styletts2_config or "").strip()
        self.styletts2_alpha = max(0.0, min(1.0, float(styletts2_alpha)))
        self.styletts2_beta = max(0.0, min(1.0, float(styletts2_beta)))
        self.styletts2_diffusion_steps = max(1, min(20, int(styletts2_diffusion_steps)))
        self.styletts2_embedding_scale = max(0.1, min(10.0, float(styletts2_embedding_scale)))
        self.styletts2_persistent = bool(styletts2_persistent)
        self.styletts2_preload = bool(styletts2_preload)
        self.tts_prefetch_chunks = bool(tts_prefetch_chunks)

        self.piper_repo_id = piper_repo_id
        self.piper_jarvis_quality = piper_jarvis_quality
        self.piper_model_file = piper_model_file
        self.piper_config_file = piper_config_file
        self.piper_use_cuda = piper_use_cuda
        self.piper_fx_preset = piper_fx_preset

        self._interrupt_event = threading.Event()
        self._pygame_ready = False
        self.last_error = ""

    def warmup_xtts_async(self) -> bool:
        if not getattr(self, "xtts_persistent", False):
            return False
        xtts_python = getattr(self, "xtts_python", "").strip()
        if not xtts_python:
            return False
        refs = self._xtts_reference_files()
        if not refs:
            return False

        def warmup() -> None:
            try:
                worker = _get_xtts_external_worker(
                    python_exe=xtts_python,
                    model_name=getattr(
                        self,
                        "xtts_model_name",
                        "tts_models/multilingual/multi-dataset/xtts_v2",
                    ),
                    speaker=";".join(str(path) for path in refs),
                    language=getattr(self, "xtts_language", "pt") or "pt",
                    device=getattr(self, "xtts_device", "auto") or "auto",
                )
                worker.preload()
                print("[XTTS] Worker persistente aquecido.", flush=True)
            except Exception as exc:
                print(f"[XTTS] Preload falhou: {exc!r}", flush=True)

        threading.Thread(target=warmup, name="xtts-warmup", daemon=True).start()
        return True

    def _styletts2_reference_file(self) -> Path | None:
        raw = getattr(self, "styletts2_reference_wav", "").strip()
        if not raw:
            return None
        path = Path(os.path.expandvars(os.path.expanduser(raw)))
        return path if path.is_file() else None

    def warmup_styletts2_async(self) -> bool:
        if not getattr(self, "styletts2_persistent", False):
            return False
        styletts2_python = getattr(self, "styletts2_python", "").strip()
        if not styletts2_python:
            return False
        ref = self._styletts2_reference_file()
        if ref is None:
            return False

        def warmup() -> None:
            try:
                worker = _get_styletts2_external_worker(
                    python_exe=styletts2_python,
                    reference=str(ref),
                    model_checkpoint=getattr(self, "styletts2_model_checkpoint", ""),
                    config_path=getattr(self, "styletts2_config", ""),
                    alpha=getattr(self, "styletts2_alpha", 0.3),
                    beta=getattr(self, "styletts2_beta", 0.7),
                    diffusion_steps=getattr(self, "styletts2_diffusion_steps", 3),
                    embedding_scale=getattr(self, "styletts2_embedding_scale", 1.0),
                )
                worker.preload()
                print("[StyleTTS2] Worker persistente aquecido.", flush=True)
            except Exception as exc:
                print(f"[StyleTTS2] Preload falhou: {exc!r}", flush=True)

        threading.Thread(target=warmup, name="styletts2-warmup", daemon=True).start()
        return True

    def apply_agent_voice(
        self,
        provider: str,
        voice: str,
        speed: float,
        edge_rate: str,
        edge_vol: str,
        kokoro_voice: str
    ) -> None:
        """Atualiza a configuração de voz do TTS de acordo com o agente ativo."""
        self.provider = normalize_tts_provider(provider)
        self.provider_order = resolve_tts_provider_order(
            self.provider, getattr(self, "provider_order_config", None)
        )
        if self.provider == "edge":
            self.voice = voice
            self.edge_tts_rate = edge_rate
            self.edge_tts_volume = edge_vol
        elif self.provider == "kokoro":
            self.kokoro_voice = kokoro_voice
            self.kokoro_speed = speed
            # Só pré-carrega o Kokoro (380MB) se o provider realmente for kokoro
            threading.Thread(target=self._preload_kokoro, daemon=True).start()
        elif self.provider == "styletts2":
            self.voice = voice
            if getattr(self, "styletts2_preload", False):
                self.warmup_styletts2_async()
        else:
            self.voice = voice
            # Para outros providers (fish, rvc, edge, murf, elevenlabs) não há
            # motivo de carregar 380MB de modelo ONNX em background

        print("[TTS] Inicializado. Provider principal:", provider)

    def _preload_kokoro(self):
        try:
            self._kokoro = _get_kokoro()
        except Exception:
            pass

    def _get_rvc_manager(self):
        """Lazy-init do RVCManager — só carrega rvc_python quando necessário."""
        if self._rvc_manager is None:
            from src.services.rvc_service import RVCManager
            self._rvc_manager = RVCManager()
        return self._rvc_manager

    def _get_local_engine(self):
        """Lazy-init do pyttsx3 — só inicializa como último recurso."""
        if self._local_engine is None:
            self._local_engine = pyttsx3.init()
            self._local_engine.setProperty("rate", 170)
        return self._local_engine

    def stop(self) -> None:
        """Sinaliza para parar a fala atual imediatamente."""
        self._interrupt_event.set()

        # Para o áudio local (pygame)
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
        except Exception:
            pass

        # Para o áudio no visualizador (navegador)
        try:
            from src.services import visualizer
            if visualizer.is_browser_connected():
                import requests
                # Envia sinal de stop para o frontend
                requests.post(f"http://localhost:{visualizer._server_port}/api/stop_audio", timeout=0.5)
        except Exception:
            pass

        print("[TTS] Interrompido pelo usuário.")

    def set_volume(self, volume: str) -> None:
        """Ajusta o volume do Edge-TTS (ex: '+0%', '-50%', '100%')."""
        self.edge_tts_volume = volume
        print(f"[TTS] Volume da IA ajustado para: {volume}")

    def speak(self, text: str) -> None:
        self._interrupt_event.clear()

        # Interceptar tags de emoção geradas pelo LLM (ex: [feliz] Olá!)
        import re
        emotion_match = re.search(r"^\s*\[(feliz|triste|bravo|urgente|calmo|neutro)\]", text, re.IGNORECASE)
        if emotion_match:
            emotion = emotion_match.group(1).lower()
            print(f"[TTS] Emoção interceptada: {emotion}")
            if emotion == "feliz":
                self.kokoro_speed = 1.15
            elif emotion == "triste":
                self.kokoro_speed = 0.85
            elif emotion == "bravo":
                self.kokoro_speed = 1.20
            elif emotion == "urgente":
                self.kokoro_speed = 1.30
            elif emotion == "calmo":
                self.kokoro_speed = 0.90
            else:
                self.kokoro_speed = 1.0

            # Remover a tag para não ser lida em voz alta
            text = text[emotion_match.end():].strip()
        else:
            self.kokoro_speed = 1.0

        clean = strip_text_for_speech(text)

        if not clean:
            return

        try:
            chunks = split_text_for_tts(clean, self.max_chunk_chars)
            if (
                len(chunks) > 1
                and getattr(self, "tts_prefetch_chunks", False)
                and self._speak_prefetched_chunks(chunks)
            ):
                return

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



    def _generate_audio_file_for_provider(self, provider: str, text: str) -> Path | None:
        provider = normalize_tts_provider(provider)
        if provider == "styletts2":
            return self._generate_styletts2_file(text)
        if provider == "xtts":
            return self._generate_xtts_file(text)
        return None

    def _speak_prefetched_chunks(self, chunks: list[str]) -> bool:
        order = getattr(self, "provider_order", None) or resolve_tts_provider_order(
            getattr(self, "provider", "xtts")
        )
        file_providers = [p for p in order if p in {"styletts2", "xtts"}]
        if not file_providers:
            return False

        generated: dict[int, Path | None] = {}
        errors: dict[int, str] = {}
        lock = threading.Lock()

        def generate(index: int, chunk: str) -> None:
            for provider in file_providers:
                if self._interrupt_event.is_set():
                    return
                out = self._generate_audio_file_for_provider(provider, chunk)
                if out is not None:
                    with lock:
                        generated[index] = out
                    return
            with lock:
                generated[index] = None
                errors[index] = self.last_error

        if not chunks:
            return True

        generate(0, chunks[0])
        if generated.get(0) is None:
            return False

        def generate_rest() -> None:
            for idx, chunk in enumerate(chunks[1:], start=1):
                generate(idx, chunk)

        rest_thread = threading.Thread(target=generate_rest, daemon=True)
        rest_thread.start()
        time.sleep(0.01)

        for idx, chunk in enumerate(chunks):
            if self._interrupt_event.is_set():
                break
            while idx not in generated and not self._interrupt_event.is_set():
                time.sleep(0.03)
            out = generated.get(idx)
            if out is None:
                self.last_error = errors.get(idx, self.last_error)
                self._speak_one_chunk(chunk)
            else:
                if idx > 0 and self.pause_between_chunks_sec > 0:
                    self._pygame_teardown()
                    time.sleep(self.pause_between_chunks_sec)
                self._play_audio_file(out)

        return True

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

        order = getattr(self, "provider_order", None) or resolve_tts_provider_order(
            getattr(self, "provider", "xtts")
        )
        for index, provider in enumerate(order):
            method_name = TTS_PROVIDER_METHODS.get(provider)
            if not method_name:
                continue
            method = getattr(self, method_name, None)
            if method is None:
                continue
            if index > 0:
                reason = f" (motivo: {self.last_error[:80]})" if self.last_error else ""
                print(f"[TTS] Fallback {provider}{reason}...")
            try:
                if method(text):
                    return
            except Exception as exc:
                self.last_error = f"{provider} exception: {exc!r}"
                print(f"[TTS] {self.last_error}")

        if self.last_error:
            print(f"[DEBUG TTS Fallback] Motivo: {self.last_error}")
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

        # Fallback definitivo:
        # 1. Se Fish Audio falhou por saldo/API, tenta Edge-TTS (gratuito e confiável)
        # 2. Se Edge-TTS falhar, cai no RVC local como penúltima opção
        # 3. Último recurso: voz local do sistema
        if self.last_error:
            print(f"[TTS] Tentando fallback Edge-TTS (motivo: {self.last_error[:60]})...")
            if self._speak_with_edge(text):
                return

            # Edge-TTS também falhou - tenta RVC local como penúltima opção
            print(f"[TTS] Tentando fallback RVC...")
            original_voice = self.voice
            self.voice = "Jarvis"
            if self._speak_with_rvc(text):
                self.voice = original_voice
                return
            self.voice = original_voice

        if self.last_error:
            print(f"[DEBUG TTS Fallback] Motivo: {self.last_error}")

        print("[TTS] ⚠️ CUIDADO: Todos os serviços online falharam. Usando voz local do sistema.")
        engine = self._get_local_engine()
        engine.say(text)
        engine.runAndWait()



    def _speak_with_openai(self, text: str) -> bool:
        if not self.client:
            self.last_error = "OpenAI TTS sem OPENAI_API_KEY."
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
            self.last_error = f"OpenAI error: {exc}"
            return False

    def _speak_with_local(self, text: str) -> bool:
        try:
            print("[TTS] Todos os providers falharam. Usando voz local do sistema.")
            engine = self._get_local_engine()
            engine.say(text)
            engine.runAndWait()
            self.last_error = ""
            return True
        except Exception as exc:
            self.last_error = f"Erro no TTS local: {exc!r}"
            return False

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

    def _xtts_reference_files(self) -> list[Path]:
        refs = _split_reference_audio_paths(getattr(self, "xtts_speaker_wav", ""))
        return [path for path in refs if path.is_file()]

    def _generate_xtts_file(self, text: str) -> Path | None:
        refs = self._xtts_reference_files()
        if not refs:
            self.last_error = (
                "XTTS_SPEAKER_WAV nao configurado ou arquivo nao encontrado. "
                "Aponte para 1+ WAV/MP3 limpos da voz alvo."
            )
            return None

        try:
            model_name = getattr(
                self,
                "xtts_model_name",
                "tts_models/multilingual/multi-dataset/xtts_v2",
            )
            out = Path(tempfile.gettempdir()) / f"xtts_speech_{uuid.uuid4().hex[:8]}.wav"
            xtts_python = getattr(self, "xtts_python", "").strip()
            if xtts_python:
                speaker_arg = ";".join(str(path) for path in refs)
                if getattr(self, "xtts_persistent", False):
                    worker = _get_xtts_external_worker(
                        python_exe=xtts_python,
                        model_name=model_name,
                        speaker=speaker_arg,
                        language=getattr(self, "xtts_language", "pt") or "pt",
                        device=getattr(self, "xtts_device", "auto") or "auto",
                    )
                    worker.synthesize(text, out)
                    if out.is_file() and out.stat().st_size > 0:
                        self.last_error = ""
                        return out
                    self.last_error = "XTTS externo persistente nao gerou arquivo de audio."
                    return None

                cmd = [
                    xtts_python,
                    "-m",
                    "src.services.xtts_external_worker",
                    "--model",
                    model_name,
                    "--speaker",
                    speaker_arg,
                    "--language",
                    getattr(self, "xtts_language", "pt") or "pt",
                    "--device",
                    getattr(self, "xtts_device", "auto") or "auto",
                    "--out",
                    str(out),
                    "--text",
                    text,
                ]
                creationflags = 0
                if os.name == "nt":
                    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                proc = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=900,
                    creationflags=creationflags,
                    cwd=str(Path(__file__).resolve().parents[2]),
                )
                if proc.returncode != 0:
                    self.last_error = f"XTTS externo falhou ({proc.returncode}): {proc.stderr[:400]}"
                    return None
                if out.is_file() and out.stat().st_size > 0:
                    self.last_error = ""
                    return out
                self.last_error = "XTTS externo nao gerou arquivo de audio."
                return None

            xtts = _get_xtts(model_name, getattr(self, "xtts_device", "auto"))
            speaker_wav: str | list[str]
            speaker_wav = [str(path) for path in refs]
            if len(speaker_wav) == 1:
                speaker_wav = speaker_wav[0]
            xtts.tts_to_file(
                text=text,
                file_path=str(out),
                speaker_wav=speaker_wav,
                language=getattr(self, "xtts_language", "pt") or "pt",
            )
            if out.is_file() and out.stat().st_size > 0:
                self.last_error = ""
                return out
            self.last_error = "XTTS nao gerou arquivo de audio."
            return None
        except Exception as exc:
            self.last_error = f"Erro no XTTS v2: {exc!r}"
            return None

    def _speak_with_xtts(self, text: str) -> bool:
        out = self._generate_xtts_file(text)
        if out is None:
            return False
        self._play_audio_file(out)
        return True

    def _speak_with_xtts_rvc(self, text: str) -> bool:
        cached_file = self.tts_cache.get_cached_file(
            text, getattr(self, "xtts_rvc_voice", "Jarvis"), "xtts_rvc"
        )
        if cached_file:
            self._play_audio_file(cached_file)
            return True

        base = self._generate_xtts_file(text)
        if base is None:
            return False
        try:
            model_name = getattr(self, "xtts_rvc_voice", "") or self.voice or "Jarvis"
            out_rvc = Path(tempfile.gettempdir()) / f"xtts_rvc_{uuid.uuid4().hex[:8]}.wav"
            if self._get_rvc_manager().convert_audio(str(base), str(out_rvc), model_name):
                self.tts_cache.save_to_cache(text, model_name, "xtts_rvc", out_rvc)
                self._play_audio_file(out_rvc)
                self.last_error = ""
                return True
            self.last_error = "RVC nao converteu o audio gerado pelo XTTS."
            return False
        except Exception as exc:
            self.last_error = f"Erro no XTTS+RVC: {exc!r}"
            return False

    def _generate_styletts2_file(self, text: str) -> Path | None:
        out = Path(tempfile.gettempdir()) / f"styletts2_{uuid.uuid4().hex[:8]}.wav"
        styletts2_python = getattr(self, "styletts2_python", "").strip()
        has_command = bool(getattr(self, "styletts2_command", "").strip())
        if not styletts2_python and not has_command:
            self.last_error = (
                "STYLETTS2_COMMAND/STYLETTS2_PYTHON nao configurado. "
                "Configure o Python isolado do StyleTTS2 ou um comando externo."
            )
            return None
        ref = self._styletts2_reference_file()
        if ref is None:
            self.last_error = "STYLETTS2_REFERENCE_WAV nao configurado ou arquivo nao encontrado."
            return None

        if styletts2_python:
            try:
                if getattr(self, "styletts2_persistent", False):
                    worker = _get_styletts2_external_worker(
                        python_exe=styletts2_python,
                        reference=str(ref),
                        model_checkpoint=getattr(self, "styletts2_model_checkpoint", ""),
                        config_path=getattr(self, "styletts2_config", ""),
                        alpha=getattr(self, "styletts2_alpha", 0.3),
                        beta=getattr(self, "styletts2_beta", 0.7),
                        diffusion_steps=getattr(self, "styletts2_diffusion_steps", 3),
                        embedding_scale=getattr(self, "styletts2_embedding_scale", 1.0),
                    )
                    worker.synthesize(text, out)
                else:
                    cmd = [
                        styletts2_python,
                        "-m",
                        "src.services.styletts2_external_worker",
                        "--reference",
                        str(ref),
                        "--alpha",
                        str(getattr(self, "styletts2_alpha", 0.3)),
                        "--beta",
                        str(getattr(self, "styletts2_beta", 0.7)),
                        "--diffusion-steps",
                        str(getattr(self, "styletts2_diffusion_steps", 3)),
                        "--embedding-scale",
                        str(getattr(self, "styletts2_embedding_scale", 1.0)),
                        "--out",
                        str(out),
                        "--text",
                        text,
                    ]
                    model_checkpoint = getattr(self, "styletts2_model_checkpoint", "").strip()
                    config_path = getattr(self, "styletts2_config", "").strip()
                    if model_checkpoint:
                        cmd.extend(["--model-checkpoint", model_checkpoint])
                    if config_path:
                        cmd.extend(["--config", config_path])
                    creationflags = 0
                    if os.name == "nt":
                        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                    proc = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=900,
                        creationflags=creationflags,
                        cwd=str(Path(__file__).resolve().parents[2]),
                        env=_tts_utf8_subprocess_env(),
                    )
                    if proc.returncode != 0:
                        self.last_error = f"StyleTTS2 externo falhou ({proc.returncode}): {proc.stderr[:400]}"
                        return None
                if out.is_file() and out.stat().st_size > 0:
                    self.last_error = ""
                    return out
                self.last_error = "StyleTTS2 externo nao gerou arquivo de audio."
                return None
            except Exception as exc:
                self.last_error = f"Erro no StyleTTS2 externo: {exc!r}"
                return None

        cmd = self._styletts2_command_args(text, out)
        try:
            creationflags = 0
            if os.name == "nt":
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=600,
                creationflags=creationflags,
                env=_tts_utf8_subprocess_env(),
            )
            if proc.returncode != 0:
                self.last_error = f"StyleTTS2 falhou ({proc.returncode}): {proc.stderr[:300]}"
                return None
            if out.is_file() and out.stat().st_size > 0:
                self.last_error = ""
                return out
            self.last_error = f"StyleTTS2 nao gerou arquivo de audio em {out}."
            return None
        except Exception as exc:
            self.last_error = f"Erro no StyleTTS2: {exc!r}"
            return None

    def _styletts2_command_args(self, text: str, out: Path) -> list[str]:
        raw = getattr(self, "styletts2_command", "").strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                args = [str(item) for item in parsed]
            else:
                args = shlex.split(raw, posix=os.name != "nt")
        except Exception:
            args = shlex.split(raw, posix=os.name != "nt")

        ref = getattr(self, "styletts2_reference_wav", "").strip()
        replacements = {
            "{text}": text,
            "{out}": str(out),
            "{ref}": ref,
        }
        rendered: list[str] = []
        for arg in args:
            value = arg
            for token, replacement in replacements.items():
                value = value.replace(token, replacement)
            rendered.append(value)
        return rendered

    def _speak_with_styletts2(self, text: str) -> bool:
        out = self._generate_styletts2_file(text)
        if out is None:
            return False
        self._play_audio_file(out)
        return True

    def _speak_with_fish(self, text: str) -> bool:
        if not self.fish_audio_api_key:
            self.last_error = "FISH_AUDIO_API_KEY não configurada."
            return False

        # O voice_id do agente fica salvo em self.voice
        voice_id = self.voice
        if not voice_id or voice_id.lower() == "jarvis":
            # Caso não tenha um ID válido, cai fora
            self.last_error = "ID de voz do Fish Audio não configurado (voice_id no agents.json)."
            return False

        try:
            url = "https://api.fish.audio/v1/tts"
            headers = {
                "Authorization": f"Bearer {self.fish_audio_api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "text": text,
                "reference_id": voice_id,
                "format": "mp3",
                "mp3_bitrate": 128,
                "normalize": True
            }

            out_file = Path(tempfile.gettempdir()) / f"fish_speech_{threading.get_ident()}.mp3"

            resp = requests.post(url, headers=headers, json=data, timeout=30, stream=True)
            if resp.status_code == 200:
                with open(out_file, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)

                self._play_audio_file(out_file)
                return True
            else:
                self.last_error = f"Fish Audio falhou [{resp.status_code}]: {resp.text}"
                print(f"[TTS] {self.last_error}")
                return False
        except Exception as e:
            self.last_error = f"Fish Audio Exception: {e}"
            print(f"[TTS] {self.last_error}")
            return False

    def _speak_with_edge(self, text: str) -> bool:
        try:
            out = Path(tempfile.gettempdir()) / f"edge_speech_{threading.get_ident()}.mp3"

            # Remove o arquivo antigo se existir para nao dar conflito
            try:
                if out.exists():
                    out.unlink()
            except Exception:
                pass

            # Mapeamento de segurança: Se a voz for um personagem RVC, usa Antonio como base no Edge
            target_voice = self.voice or "pt-BR-AntonioNeural"
            if target_voice.lower() == "jarvis":
                target_voice = "pt-BR-AntonioNeural"

            import sys
            python_exe = sys.executable

            cmd = [
                python_exe, "-m", "edge_tts",
                "--text", text,
                "--write-media", str(out),
                "--voice", target_voice
            ]
            creationflags = 0
            if os.name == "nt":
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

            p = subprocess.Popen(
                cmd,
                creationflags=creationflags,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = p.communicate()

            if p.returncode != 0:
                self.last_error = f"Edge-TTS falhou (Code {p.returncode}): {stderr.strip()}"
                print(f"[TTS] Erro crítico no Edge-TTS: {stderr.strip()}")
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

    def _speak_with_rvc(self, text: str) -> bool:
        """Pipeline Assíncrono: Cache -> Edge-TTS (22050Hz) -> RVC -> FX -> Play"""
        if not text.strip():
            return False

        # Verifica o cache primeiro
        cached_file = self.tts_cache.get_cached_file(text, self.voice, "rvc")
        if cached_file:
            print(f"[TTSCache] Hit para: '{text[:20]}...'")
            self._play_audio_file(cached_file)
            return True

        try:
            chunk_id = uuid.uuid4().hex[:8]
            out_edge_mp3 = Path(tempfile.gettempdir()) / f"rvc_edge_base_{chunk_id}.mp3"
            out_edge_wav = Path(tempfile.gettempdir()) / f"rvc_edge_base_{chunk_id}.wav"
            out_rvc = Path(tempfile.gettempdir()) / f"rvc_converted_{chunk_id}.wav"
            out_fx = Path(tempfile.gettempdir()) / f"rvc_final_{chunk_id}.wav"

            for p in [out_edge_mp3, out_edge_wav, out_rvc, out_fx]:
                if p.exists():
                    try: p.unlink()
                    except: pass

            config = self._get_rvc_manager().get_config(self.voice if self.voice else "Jarvis")
            base_voice = config.get("base_voice") or config.get("voice") or "pt-BR-AntonioNeural"

            cmd = [
                "edge-tts",
                "--text", text,
                "--write-media", str(out_edge_mp3),
                "--voice", base_voice,
                f"--rate={self.edge_tts_rate}"
            ]

            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0

            p = subprocess.Popen(cmd, creationflags=creationflags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            while p.poll() is None:
                if self._interrupt_event.is_set():
                    try: p.terminate()
                    except: pass
                    return True
                time.sleep(0.05)

            if p.returncode != 0 or not out_edge_mp3.exists():
                print("[RVC] Falha ao gerar o áudio base no Edge-TTS.")
                return False

            # Passo 1.5: Converter MP3 para WAV para o RVC poder engolir
            if not mp3_to_wav(str(out_edge_mp3), str(out_edge_wav)):
                print("[RVC] Falha ao decodificar MP3 para WAV.")
                return False

            # Passo 2: Conversão RVC
            model_name = self.voice if self.voice else "Jarvis"
            print(f"[RVC] Convertendo voz para {model_name}...")

            success = self._get_rvc_manager().convert_audio(str(out_edge_wav), str(out_rvc), model_name)

            if not success or not out_rvc.exists():
                print("[RVC] Conversão falhou, tocando áudio original (Fallback)")
                self._play_audio_file(out_edge_mp3) # Toca o mp3 original
                return True

            # Passo 3: Pós-processamento de Áudio (Efeito Jarvis)
            # Lê se o arquivo config tem um preset de fx
            config = self._get_rvc_manager().get_config(model_name)
            fx_preset = config.get("fx_preset", "jarvis" if "jarvis" in model_name.lower() else "none")

            final_audio = out_rvc
            if fx_preset != "none":
                if apply_fx_to_wav(out_rvc, out_fx, preset=fx_preset):
                    final_audio = out_fx

            # Passo 4: Salva no Cache para não precisar rodar o RVC nessa frase de novo
            self.tts_cache.save_to_cache(text, self.voice, "rvc", final_audio)

            # Passo 5: Tocar
            self._play_audio_file(final_audio)

            # Limpeza do pygame para liberar o arquivo
            try:
                pygame.mixer.music.unload()
            except:
                pass

            return True

        except Exception as e:
            print(f"[RVC] Pipeline quebrou: {e}")
            return False

    def _save_elevenlabs_state(self):
        try:
            with open(self.elevenlabs_state_file, "w", encoding="utf-8") as f:
                json.dump(self.elevenlabs_exhausted_keys, f)
        except Exception:
            pass

    def _get_elevenlabs_voice_id_by_name(self, api_key: str, target_name: str) -> str:
        """Busca o ID da voz pelo nome na conta atual do ElevenLabs. Faz cache para não gastar requisições."""
        if not target_name:
            return "21m00Tcm4TlvDq8ikWAM" # Rachel default

        cache_key = f"{api_key}_{target_name}"
        if cache_key in self.elevenlabs_voice_id_cache:
            return self.elevenlabs_voice_id_cache[cache_key]

        import requests
        try:
            url = "https://api.elevenlabs.io/v1/voices"
            headers = {"xi-api-key": api_key}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                voices = response.json().get("voices", [])
                for v in voices:
                    if v.get("name", "").strip().lower() == target_name.strip().lower():
                        vid = v.get("voice_id")
                        self.elevenlabs_voice_id_cache[cache_key] = vid
                        return vid
        except Exception as e:
            print(f"[ElevenLabs] Erro ao buscar ID da voz '{target_name}': {e}")

        # Se não achou pelo nome, assume que o target_name já é o ID (fallback)
        return target_name

    def _speak_with_elevenlabs(self, text: str) -> bool:
        if not self.elevenlabs_api_keys:
            self.last_error = "Nenhuma API Key válida do ElevenLabs (todas esgotadas ou não configuradas)."
            return False

        import requests

        while self.current_elevenlabs_key_index < len(self.elevenlabs_api_keys):
            api_key = self.elevenlabs_api_keys[self.current_elevenlabs_key_index]

            # self.voice agora armazena o NOME da voz (ex: "Jarvis") ou o ID se o usuário preferir
            voice_name = self.voice if self.voice else "Rachel"
            voice_id = self._get_elevenlabs_voice_id_by_name(api_key, voice_name)

            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": api_key
            }
            data = {
                "text": text,
                "model_id": "eleven_multilingual_v2", # Aceita PT-BR nativamente
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }

            try:
                response = requests.post(url, json=data, headers=headers, timeout=15)
                if response.status_code == 200:
                    out = Path(tempfile.gettempdir()) / f"elevenlabs_{threading.get_ident()}.mp3"
                    with open(out, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=1024):
                            if chunk:
                                f.write(chunk)
                    self._play_audio_file(out)
                    self.last_error = ""
                    return True
                elif response.status_code in [401, 429]:
                    print(f"[ElevenLabs] Aviso: Chave bloqueada/esgotada (Status {response.status_code}). Indo pro castigo de 30 dias.")
                    # Coloca a chave de castigo e salva o arquivo
                    self.elevenlabs_exhausted_keys[api_key] = time.time()
                    self._save_elevenlabs_state()
                    self.current_elevenlabs_key_index += 1
                else:
                    self.last_error = f"ElevenLabs falhou com status {response.status_code}: {response.text}"
                    print(f"[ElevenLabs] Erro crítico: {self.last_error}")
                    return False
            except Exception as e:
                self.last_error = f"Erro de rede ElevenLabs: {e}"
                print(f"[ElevenLabs] Falha na rede: {e}")
                return False

        self.last_error = "ALERTA: Todas as chaves ativas do ElevenLabs acabaram de esgotar!"
        print("[ElevenLabs]", self.last_error)
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

    def _speak_with_piper(self, text: str) -> bool:
        """Gera áudio localmente usando Piper TTS (CPU ou AMD GPU via DirectML)."""
        import wave
        import onnxruntime
        try:
            from piper import PiperVoice, PiperConfig
        except ImportError:
            self.last_error = "Piper não instalado. Rode: pip install piper-tts"
            print(f"[TTS] {self.last_error}")
            return False

        # Verifica cache ou arquivo do modelo
        cache_dir = Path("data/cache/piper")
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Modelo padrao caso nao seja especificado
        repo_id = self.piper_repo_id or "rhasspy/piper-voices"
        if not self.piper_model_file and not self.piper_config_file and "jgkawell/jarvis" in repo_id:
            model_name, config_name = piper_jarvis_model_files(self.piper_jarvis_quality)
        else:
            model_name = self.piper_model_file or "pt_BR-faber-medium.onnx"
            config_name = self.piper_config_file or f"{model_name}.json"

        model_path = cache_dir / model_name
        config_path = cache_dir / config_name

        if not model_path.exists() or not config_path.exists():
            print(f"[Piper] Baixando modelo {model_name}...")
            # URL especifica para portugues ou repositório generico
            # No rhasspy/piper-voices, pt-br fica em pt/pt_BR/
            if "pt_BR" in model_name and "rhasspy" in repo_id:
                base_url = f"https://huggingface.co/{repo_id}/resolve/main/pt/pt_BR/faber/medium/"
            else:
                base_url = f"https://huggingface.co/{repo_id}/resolve/main/"

            try:
                for fname, pth in [(model_name, model_path), (config_name, config_path)]:
                    if not pth.exists():
                        pth.parent.mkdir(parents=True, exist_ok=True)
                        r = requests.get(base_url + fname, stream=True, timeout=120)
                        r.raise_for_status()
                        with open(pth, "wb") as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
            except Exception as e:
                self.last_error = f"Erro ao baixar modelo Piper: {e}"
                print(f"[Piper] {self.last_error}")
                return False

        try:
            # Carrega arquivo JSON de conf
            with open(config_path, "r", encoding="utf-8") as f:
                config_dict = json.load(f)

            # Setup providers (DirectML para AMD, ou CPU)
            providers = []
            if self.piper_use_cuda:
                providers.append("DmlExecutionProvider")
                providers.append("CUDAExecutionProvider")
            providers.append("CPUExecutionProvider")

            session = onnxruntime.InferenceSession(
                str(model_path),
                sess_options=onnxruntime.SessionOptions(),
                providers=providers
            )

            voice = PiperVoice(
                config=PiperConfig.from_dict(config_dict),
                session=session,
                espeak_data_dir=Path(os.path.dirname(__import__("piper").__file__)) / "espeak-ng-data"
            )

            out = Path(tempfile.gettempdir()) / f"piper_speech_{threading.get_ident()}.wav"

            with wave.open(str(out), "wb") as wav_file:
                voice.synthesize_wav(text, wav_file)

            if self.piper_fx_preset and self.piper_fx_preset != "none":
                out_fx = Path(tempfile.gettempdir()) / f"piper_speech_fx_{threading.get_ident()}.wav"
                if apply_fx_to_wav(out, out_fx, preset=self.piper_fx_preset):
                    out = out_fx

            if out.is_file():
                self._play_audio_file(out)
                self.last_error = ""
                return True

            self.last_error = "Arquivo Piper não gerado."
            return False

        except Exception as exc:
            self.last_error = f"Erro ao sintetizar voz com Piper: {exc}"
            print(f"[Piper] {self.last_error}")
            return False

    def _play_file(self, path: Path) -> None:
        """Toca o áudio apenas no PC (Alto-falantes)."""
        abs_path = path.resolve()
        if not abs_path.is_file():
            return

        # 1. Tenta FFPlay (muito estável, sem interface)
        if self._try_play_with_ffplay(abs_path):
            return

        # 2. Fallback: Pygame
        try:
            self._init_pygame_mixer(abs_path)
            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
            pygame.mixer.music.load(str(abs_path))
            pygame.mixer.music.play()

            clock = pygame.time.Clock()
            while pygame.mixer.music.get_busy():
                if self._interrupt_event.is_set():
                    pygame.mixer.music.stop()
                    break
                clock.tick(30)
            return
        except Exception as exc:
            print(f"[TTS] Falha no player local: {exc}")

    def _play_wav(self, path: Path) -> None:
        self._play_file(path)

    def _play_audio_file(self, path: Path) -> None:
        self._play_file(path)

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
