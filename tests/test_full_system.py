import pytest
import os
import json
import sqlite3
from pathlib import Path

# --- Fixtures ---

@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Garante que os testes não afetem o banco ou arquivos reais."""
    test_db_path = "tests/test_nexus.db"
    monkeypatch.setenv("NEXUS_DB_PATH", test_db_path)
    monkeypatch.setenv("VISUALIZER_PORT", "5124")
    monkeypatch.setenv("SUPABASE_DB_URL", "")
    import os
    if "SUPABASE_DB_URL" in os.environ:
        os.environ["SUPABASE_DB_URL"] = ""
    
    yield
    
    # Cleanup after test
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except:
            pass

@pytest.fixture
def memory_db():
    from src.database.nexus_db import NexusDatabase
    db = NexusDatabase()
    # Forçar usar memory para ser ultra rápido (ou um arquivo test.db temporário)
    # Como NexusDatabase abre via connect, já mockamos o caminho
    yield db

@pytest.fixture
def nexus_service(memory_db):
    from src.services.nexus_service import NexusService
    service = NexusService()
    service.db = memory_db
    yield service

# --- Testes de Integração e Sistema ---

def test_nexus_db_initialization(memory_db):
    """Testa se o banco de dados é criado e a migração inicial rodou."""
    with memory_db._get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='nexus_user'")
        assert cur.fetchone() is not None, "A tabela nexus_user não foi criada."
        
        cur.execute("SELECT level FROM nexus_user WHERE id = 1")
        assert cur.fetchone()[0] >= 1, "Usuário base não inicializado corretamente."

def test_add_and_complete_habit(nexus_service):
    """Testa criação de hábito, log de conclusão e acréscimo de XP."""
    with nexus_service.db._get_connection() as conn:
        initial_xp = conn.execute("SELECT xp FROM nexus_user WHERE id=1").fetchone()[0]

    # Criar um hábito
    nexus_service.handle_structured_command({"action": "habit_add", "name": "Beber Água Teste", "frequency": "daily"})
    
    with nexus_service.db._get_connection() as conn:
        habit_row = conn.execute("SELECT id FROM habits WHERE name='Beber Água Teste'").fetchone()
        assert habit_row is not None
        habit_id = habit_row[0]
        
    # Concluir hábito
    nexus_service.handle_structured_command({"action": "habit_complete", "habit_name": "Beber Água Teste"})
    
    with nexus_service.db._get_connection() as conn:
        # Verifica o log de completude
        log_row = conn.execute("SELECT id FROM habit_logs WHERE habit_id=?", (habit_id,)).fetchone()
        assert log_row is not None
        
        # Verifica se o XP do usuário subiu
        new_xp = conn.execute("SELECT xp FROM nexus_user WHERE id=1").fetchone()[0]
        assert new_xp > initial_xp, "O XP não aumentou após concluir um hábito"

def test_nexus_batch_operations_and_hud_emission(nexus_service):
    """Testa o engine de batch usado pela LLM e se não quebra a emissão de HUD."""
    steps = [
        {"action": "habit_add", "name": "Ler 10 páginas"},
        {"action": "task_add", "title": "Estudar Testes"},
        {"action": "invalid_action_foo_bar"}
    ]
    
    # Executa o lote
    raw_result = nexus_service.handle_nexus_batch(steps)
    result = json.loads(raw_result)
    
    assert "batch_id" in result
    assert len(result["steps"]) == 3
    
    # 2 Sucessos, 1 falha (ação desconhecida)
    assert result["steps"][0]["ok"] is True
    assert result["steps"][1]["ok"] is True
    assert result["steps"][2]["ok"] is False
    assert "Acao desconhecida" in result["steps"][2]["message"]

def test_dashboard_summary_integrity(nexus_service):
    """Garante que a extração de métricas pro UI não crasheie."""
    # Adiciona alguns dados dummy
    nexus_service.handle_structured_command({"action": "habit_add", "name": "H1", "frequency": "daily"})
    nexus_service.handle_structured_command({"action": "finance_add", "type": "expense", "amount": 50.5, "category": "Teste", "description": "Pizza"})
    
    data = nexus_service.get_dashboard_summary()
    assert "finance" in data
    assert "habits" in data
    assert "user" in data
    
    assert data["finance"]["today"] >= 1
    assert data["user"]["level"] >= 1
    assert data["habits"]["total"] >= 1

def test_desktop_api_mock(monkeypatch):
    """Garante que o bridge de API Desktop está validando os dados corretos."""
    from src.ui.desktop_app import DesktopApi
    api = DesktopApi(None, None, None)
    
    # Testar hud sem quebrar se a janela não existir
    # api._hud_window is None (default in tests)
    assert api.show_activity_hud('{"test": true}') is False
    assert api.hide_activity_hud() is False
    
    # Testar se os módulos abrem safe e pegam exceções silenciosamente
    assert api.close_module() is True # mock pass


def test_hud_window_lazy_initialization(monkeypatch):
    from src.ui import desktop_app

    app = object.__new__(desktop_app.DesktopApp)
    app._hud_window = None
    app.api = object()

    class DummyWindow:
        def __init__(self):
            self.visible = False
            self.script = None
        def show(self):
            self.visible = True
        def evaluate_js(self, code):
            self.script = code

    dummy = DummyWindow()

    def fake_create_window(title, url, width, height, frameless, transparent, on_top, hidden, js_api, background_color=None):
        assert title == "__nexus_hud__"
        assert url.endswith("nexus_hud.html")
        assert width == 420
        assert height == 560
        assert frameless is True
        assert transparent is True
        assert on_top is True
        assert hidden is True
        assert js_api is app.api
        return dummy

    monkeypatch.setattr(desktop_app.webview, "create_window", fake_create_window)

    assert app.show_activity_hud({"title": "Test HUD", "items": [{"label": "Teste"}]}) is True
    assert app._hud_window is dummy
    assert dummy.visible is True
    assert "hudShow" in dummy.script


def test_memory_protection(monkeypatch, tmp_path):
    """Garante que a StructuredMemory responde com _locked em vez de falhar quando sem chave válida."""
    from src.memory import structured_memory
    
    # Isolar arquivo de memória num temp path
    test_mem_path = tmp_path / "test_mem.json"
    test_mem_path.write_text("gAAAAA_invalid_cipher_text")
    monkeypatch.setattr(structured_memory, "STRUCTURED_MEMORY_PATH", test_mem_path)
    
    state = structured_memory.load_structured_memory()
    # Deverá vir como dita travada por falhar decriptar sem senha
    assert isinstance(state, dict)
    assert state.get("_locked") is True
