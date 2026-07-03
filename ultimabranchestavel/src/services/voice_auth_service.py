from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ADMIN_NAME = "Admin"
ADMIN_LEVEL = 100
DEFAULT_ADMIN_KEYWORD = "senha alfa cinco"


@dataclass(frozen=True)
class VoiceIdentity:
    name: str = "Desconhecido"
    access_level: int = 0
    just_registered: bool = False
    message: str = ""


def _admin_exists(conn: Any) -> bool:
    row = conn.execute(
        "SELECT id FROM voice_profiles WHERE name = ? LIMIT 1",
        (ADMIN_NAME,),
    ).fetchone()
    return row is not None


def _build_biometrics():
    try:
        from src.services.voice_biometrics import VoiceBiometrics

        return VoiceBiometrics()
    except Exception:
        return None


def resolve_voice_identity(
    conn: Any,
    text: str,
    *,
    audio_data: Any = None,
    biometrics: Any = None,
    admin_keyword: str = DEFAULT_ADMIN_KEYWORD,
) -> VoiceIdentity:
    """Resolve quem falou sem promover todo microfone local a Admin."""
    lowered = (text or "").lower()
    bio = biometrics if biometrics is not None else _build_biometrics()
    admin_exists = _admin_exists(conn)

    current_embedding = None
    if audio_data is not None and bio is not None and getattr(bio, "ready", False):
        try:
            current_embedding = bio.extract_embedding(audio_data)
        except Exception:
            current_embedding = None

    if not admin_exists and admin_keyword.lower() in lowered:
        if current_embedding is not None and bio is not None:
            try:
                if bio.save_profile(conn, ADMIN_NAME, ADMIN_LEVEL, current_embedding):
                    return VoiceIdentity(
                        name=ADMIN_NAME,
                        access_level=ADMIN_LEVEL,
                        just_registered=True,
                        message="Admin registrado por voz.",
                    )
            except Exception:
                pass

        return VoiceIdentity(
            message="Palavra-chave aceita, mas a biometria de voz nao esta pronta para registrar o Admin.",
        )

    if current_embedding is not None and bio is not None:
        try:
            match = bio.identify_speaker(conn, current_embedding)
        except Exception:
            match = None
        if match:
            name, level = match
            return VoiceIdentity(name=str(name), access_level=int(level or 0))

    return VoiceIdentity()


def format_voice_source(identity: VoiceIdentity) -> str:
    return f"Voz:{identity.name}:{int(identity.access_level or 0)}"
