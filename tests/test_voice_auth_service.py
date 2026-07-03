import sqlite3

from src.services.voice_auth_service import format_voice_source, resolve_voice_identity


class FakeBiometrics:
    ready = True

    def __init__(self, match=None):
        self.match = match
        self.saved = []

    def extract_embedding(self, audio):
        return [0.1, 0.2, 0.3] if audio is not None else None

    def identify_speaker(self, db_conn, current_embedding):
        return self.match

    def save_profile(self, db_conn, name, access_level, embedding):
        self.saved.append((name, access_level, embedding))
        db_conn.execute(
            "INSERT INTO voice_profiles (name, access_level, voice_embedding) VALUES (?, ?, ?)",
            (name, access_level, "fake-embedding"),
        )
        db_conn.commit()
        return True


def make_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE voice_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            access_level INTEGER DEFAULT 1,
            voice_embedding TEXT
        )
        """
    )
    return conn


def test_secret_keyword_bootstraps_first_admin_with_voice_embedding():
    conn = make_conn()
    bio = FakeBiometrics()

    identity = resolve_voice_identity(conn, "Jarvis senha alfa cinco", audio_data=object(), biometrics=bio)

    assert identity.name == "Admin"
    assert identity.access_level == 100
    assert identity.just_registered is True
    assert bio.saved == [("Admin", 100, [0.1, 0.2, 0.3])]
    assert format_voice_source(identity) == "Voz:Admin:100"


def test_existing_admin_requires_biometric_match_before_level_100():
    conn = make_conn()
    conn.execute(
        "INSERT INTO voice_profiles (name, access_level, voice_embedding) VALUES (?, ?, ?)",
        ("Admin", 100, "fake-embedding"),
    )

    identity = resolve_voice_identity(conn, "Jarvis abra o painel", audio_data=None, biometrics=FakeBiometrics())

    assert identity.name == "Desconhecido"
    assert identity.access_level == 0
    assert format_voice_source(identity) == "Voz:Desconhecido:0"


def test_existing_admin_match_preserves_access_level():
    conn = make_conn()
    conn.execute(
        "INSERT INTO voice_profiles (name, access_level, voice_embedding) VALUES (?, ?, ?)",
        ("Admin", 100, "fake-embedding"),
    )

    identity = resolve_voice_identity(
        conn,
        "Jarvis abrir modo noticias",
        audio_data=object(),
        biometrics=FakeBiometrics(match=("Admin", 100)),
    )

    assert identity.name == "Admin"
    assert identity.access_level == 100
    assert identity.just_registered is False
