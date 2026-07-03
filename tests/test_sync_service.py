import threading
import os

from src.services.sync_service import _sync_service, start_sync


def test_sync_service_offline_mode_returns_false(monkeypatch):
    monkeypatch.setenv("SUPABASE_DB_URL", "")
    _sync_service.pg_url = ""
    _sync_service.stop()

    started = start_sync()

    assert started is False
    assert _sync_service.thread is None or not _sync_service.thread.is_alive()
    assert _sync_service.is_running is False


def test_sync_service_start_is_idempotent(monkeypatch):
    monkeypatch.setenv("SUPABASE_DB_URL", "postgres://user:pass@localhost/db")
    _sync_service.pg_url = os.getenv("SUPABASE_DB_URL")
    _sync_service.stop()

    # Avoid performing real sync calls during test
    original_perform_sync = _sync_service.perform_sync
    _sync_service.perform_sync = lambda: None

    try:
        started_first = start_sync()
        thread_id_first = id(_sync_service.thread) if _sync_service.thread else None

        started_second = start_sync()
        thread_id_second = id(_sync_service.thread) if _sync_service.thread else None

        assert started_first is True
        assert started_second is True
        assert thread_id_first == thread_id_second
        assert _sync_service.is_running is True
    finally:
        _sync_service.perform_sync = original_perform_sync
        _sync_service.stop()
