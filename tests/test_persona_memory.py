from __future__ import annotations

import tempfile
from pathlib import Path

from src.memory.store import MemoryStore


def test_persona_note_recorded_on_trigger():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "m.db"
        m = MemoryStore(str(db))
        try:
            m.maybe_record_persona_note("Prefiro que você seja bem direta.")
            notes = m.get_long_term("persona_evolution", default=[])
            assert isinstance(notes, list)
            assert len(notes) == 1
            assert "direta" in notes[0].lower()
        finally:
            m.close()


def test_persona_note_skipped_without_trigger():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "m.db"
        m = MemoryStore(str(db))
        try:
            m.maybe_record_persona_note("Abre o Spotify")
            assert m.get_long_term("persona_evolution", default=[]) == []
        finally:
            m.close()
