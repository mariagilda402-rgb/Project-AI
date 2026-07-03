from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolStep:
    """Passo extraido de marcadores `[tool:...]` na resposta da LLM."""

    kind: str
    arg: str | None = None


# Regex generica para [tool:nome:arg] ou [tool:nome] ou [nome] (para legados como olhartela)
_LEGACY_MARKERS = {
    "olhartela": "vision",
    "olhar": "vision",
    "tirarprint": "vision",
    "screenshot": "vision",
    "notepad": "notepad",
    "browser": "open_browser",
}

_GENERIC_PATTERN = re.compile(r"\[\s*(?:tool:\s*)?([a-z0-9_]+)(?:\s*:\s*([^\]]*))?\s*\]", re.I)

def parse_tool_markers(text: str) -> tuple[str, list[ToolStep]]:
    """
    Separa texto falavel dos marcadores de ferramenta, na ordem em que aparecem.
    """
    raw = text or ""
    steps: list[ToolStep] = []
    speak_chunks: list[str] = []
    remaining = raw

    while remaining:
        m = _GENERIC_PATTERN.search(remaining)
        if not m:
            speak_chunks.append(remaining)
            break

        start, end = m.span()
        raw_name = m.group(1).lower()
        arg = (m.group(2) or "").strip() or None

        # Resolve legados
        kind = _LEGACY_MARKERS.get(raw_name, raw_name)

        speak_chunks.append(remaining[:start])
        steps.append(ToolStep(kind, arg))
        remaining = remaining[end:]

    speakable = " ".join(c.strip() for c in speak_chunks if c and c.strip())
    return speakable, steps
