from __future__ import annotations

import base64
from io import BytesIO
import logging

from google import genai
from google.genai import types
from mss import mss
from openai import OpenAI
from PIL import Image
from src.services.llm import sleep_before_gemini_retry
from src.services.rate_limit import SlidingWindowRateLimiter

logger = logging.getLogger(__name__)

# Lado maior em pixels antes de enviar à NVIDIA (menos payload = menos espera).
_NVIDIA_VISION_MAX_SIDE = 1280
# Groq: imagem base64 limitada (~4MB na doc); JPEG menor que PNG.
_GROQ_VISION_INITIAL_MAX_SIDE = 1152
_GROQ_JPEG_MAX_BYTES = 2_700_000


class VisionService:
    def __init__(
        self,
        vision_provider: str,
        gemini_api_key: str,
        gemini_model: str,
        nvidia_api_key: str,
        nvidia_model: str,
        groq_api_key: str = "",
        groq_vision_model: str = "",
        max_rpm: int = 10,
        retry_attempts: int = 3,
        http_timeout: float = 180.0,
    ) -> None:
        self.vision_provider = (vision_provider or "gemini").lower()
        self.gemini_client = genai.Client(api_key=gemini_api_key) if gemini_api_key else None
        self.gemini_model = gemini_model
        to = max(30.0, min(600.0, http_timeout))
        self.nvidia_client = (
            OpenAI(
                api_key=nvidia_api_key,
                base_url="https://integrate.api.nvidia.com/v1",
                timeout=to,
            )
            if nvidia_api_key
            else None
        )
        self.nvidia_model = nvidia_model
        self.groq_client = (
            OpenAI(
                api_key=groq_api_key,
                base_url="https://api.groq.com/openai/v1",
                timeout=to,
            )
            if groq_api_key
            else None
        )
        self.groq_vision_model = (groq_vision_model or "").strip()
        self._limiter = SlidingWindowRateLimiter(max_requests_per_minute=max_rpm)
        self._retry_attempts = max(1, retry_attempts)

    def capture_screen_bytes(self) -> bytes:
        with mss() as sct:
            monitor = sct.monitors[1]
            shot = sct.grab(monitor)
            img = Image.frombytes("RGB", shot.size, shot.rgb)
            buf = BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()

    @staticmethod
    def _downscale_png_if_large(image_bytes: bytes, max_side: int = _NVIDIA_VISION_MAX_SIDE) -> bytes:
        buf_in = BytesIO(image_bytes)
        img = Image.open(buf_in)
        w, h = img.size
        if max(w, h) <= max_side:
            return image_bytes
        img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        out = BytesIO()
        img.save(out, format="PNG", optimize=True)
        return out.getvalue()

    def describe_screen(self, user_request: str) -> str:
        if self.vision_provider == "nvidia":
            return self._describe_with_nvidia(user_request)
        if self.vision_provider == "groq":
            return self._describe_with_groq(user_request)
        return self._describe_with_gemini(user_request)

    def _describe_with_gemini(self, user_request: str) -> str:
        if not self.gemini_client:
            return "GEMINI_API_KEY nao configurada para visao de tela (VISION_PROVIDER=gemini)."

        image_bytes = self.capture_screen_bytes()
        for attempt in range(1, self._retry_attempts + 1):
            try:
                self._limiter.wait_for_slot()
                response = self.gemini_client.models.generate_content(
                    model=self.gemini_model,
                    contents=[
                        user_request,
                        types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                    ],
                )
                return (response.text or "").strip()
            except Exception as exc:
                if attempt == self._retry_attempts:
                    return "Falha ao interpretar a tela com Gemini. Tente novamente."
                sleep_before_gemini_retry(exc, attempt)
        return "Falha ao interpretar a tela com Gemini. Tente novamente."

    def _describe_with_nvidia(self, user_request: str) -> str:
        if not self.nvidia_client or not self.nvidia_model:
            return (
                "NVIDIA_API_KEY / modelo nao configurados para visao "
                "(VISION_PROVIDER=nvidia)."
            )
        image_bytes = self._downscale_png_if_large(self.capture_screen_bytes())
        b64 = base64.standard_b64encode(image_bytes).decode("ascii")
        data_url = f"data:image/png;base64,{b64}"
        for attempt in range(1, self._retry_attempts + 1):
            try:
                self._limiter.wait_for_slot()
                completion = self.nvidia_client.chat.completions.create(
                    model=self.nvidia_model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": user_request},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": data_url},
                                },
                            ],
                        }
                    ],
                )
                return (completion.choices[0].message.content or "").strip()
            except Exception as exc:
                logger.warning(
                    "NVIDIA (visao) falhou (tentativa %s/%s): %s",
                    attempt,
                    self._retry_attempts,
                    exc,
                )
                if attempt == self._retry_attempts:
                    return (
                        "Falha ao interpretar a tela com NVIDIA NIM (timeout ou erro de rede). "
                        "Aumente LLM_HTTP_TIMEOUT no .env se o modelo for lento."
                    )
                sleep_before_gemini_retry(exc, attempt)
        return "Falha ao interpretar a tela com NVIDIA NIM. Tente novamente."

    @staticmethod
    def _png_to_groq_jpeg_data_url(png_bytes: bytes) -> str:
        """Redimensiona e comprime para caber no limite de payload base64 da Groq."""
        buf_in = BytesIO(png_bytes)
        img = Image.open(buf_in).convert("RGB")
        max_side = _GROQ_VISION_INITIAL_MAX_SIDE
        quality = 82
        for _ in range(10):
            im = img.copy()
            im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
            out = BytesIO()
            im.save(out, format="JPEG", quality=quality, optimize=True)
            raw = out.getvalue()
            if len(raw) <= _GROQ_JPEG_MAX_BYTES:
                b64 = base64.standard_b64encode(raw).decode("ascii")
                return f"data:image/jpeg;base64,{b64}"
            max_side = max(480, int(max_side * 0.82))
            quality = max(55, quality - 7)
        raw = out.getvalue()
        b64 = base64.standard_b64encode(raw).decode("ascii")
        return f"data:image/jpeg;base64,{b64}"

    def _describe_with_groq(self, user_request: str) -> str:
        if not self.groq_client or not self.groq_vision_model:
            return (
                "GROQ_API_KEY / GROQ_VISION_MODEL nao configurados para visao "
                "(VISION_PROVIDER=groq)."
            )
        png_bytes = self.capture_screen_bytes()
        data_url = self._png_to_groq_jpeg_data_url(png_bytes)
        for attempt in range(1, self._retry_attempts + 1):
            try:
                self._limiter.wait_for_slot()
                completion = self.groq_client.chat.completions.create(
                    model=self.groq_vision_model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": user_request},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": data_url},
                                },
                            ],
                        }
                    ],
                )
                return (completion.choices[0].message.content or "").strip()
            except Exception as exc:
                logger.warning(
                    "Groq (visao) falhou (tentativa %s/%s): %s",
                    attempt,
                    self._retry_attempts,
                    exc,
                )
                if attempt == self._retry_attempts:
                    return (
                        "Falha ao interpretar a tela com Groq (cota, modelo ou imagem muito grande). "
                        "Confira GROQ_VISION_MODEL e limites em console.groq.com/docs/vision"
                    )
                sleep_before_gemini_retry(exc, attempt)
        return "Falha ao interpretar a tela com Groq. Tente novamente."
