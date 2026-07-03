from __future__ import annotations

import json
from collections import deque
from datetime import date, timedelta
from pathlib import Path

from src.database.nexus_db import NexusDatabase
from src.services.nexus_service import NexusService
from src.skills.nexus_manager import NexusManagerSkill
from src.tools.nexus import NexusTool
from src.tools.registry import ToolRegistry


def test_registry_marker_nexus_routes(tmp_path):
    dbp = tmp_path / "nexus_test.db"
    nx = NexusTool()
    nx.service.db = NexusDatabase(db_path=str(dbp))
    reg = ToolRegistry([nx], require_critical_confirmation=False)
    r = reg.run_by_marker("nexus", "abrir nexus", "abrir nexus")
    assert r.ok
    assert "Abrindo" in (r.message or "")


def test_nexus_window_signal_queue_preserves_sequence(monkeypatch):
    import threading

    import src.ui.desktop_app as desktop_app
    from src.ui.nexus_signals import enqueue_nexus_desktop_open

    class FakeApp:
        def __init__(self):
            self._nexus_lock = threading.Lock()
            self._nexus_signal_q = deque(maxlen=16)

    app = FakeApp()
    monkeypatch.setattr(desktop_app, "APP_INSTANCE", app)

    enqueue_nexus_desktop_open("finance", {"step": 1})
    enqueue_nexus_desktop_open("habits", {"step": 2})
    enqueue_nexus_desktop_open("notes", {"step": 3})

    assert list(app._nexus_signal_q) == [
        ("finance", {"step": 1}),
        ("habits", {"step": 2}),
        ("notes", {"step": 3}),
    ]


def test_open_ui_maps_all_current_nexus_modules(monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()

    for tab, expected in [
        ("dashboard", "overview"),
        ("overview", "overview"),
        ("habits", "habits"),
        ("finance", "finance"),
        ("notes", "notes"),
        ("study", "study"),
        ("tasks", "tasks"),
        ("progress", "progress"),
        ("goals", "goals"),
        ("rewards", "goals"),
        ("quiz", "quiz"),
        ("news", "news"),
        ("noticias", "news"),
        ("memory_graph", "memory_graph"),
        ("grafo neural", "memory_graph"),
        ("ops", "ops"),
        ("business", "ops"),
    ]:
        msg = svc.handle_structured_command({"action": "open_ui", "tab": tab})
        assert "Abrindo" in msg
        assert calls[-1][0] == expected
        assert calls[-1][1]["animate"] == "open_module"


def test_nexus_batch_executes_steps_and_enqueues_windows_in_order(tmp_path, monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "batch.db"))

    raw = svc.handle_structured_command(
        {
            "action": "nexus_batch",
            "steps": [
                {
                    "action": "finance_add",
                    "type": "expense",
                    "amount": "500",
                    "category": "Alimentacao",
                    "description": "alimentacao",
                },
                {
                    "action": "habit_add",
                    "name": "Caminhar",
                    "description": "Horario sugerido: 14:00",
                    "xp_reward": "50",
                },
                {"action": "open_ui", "tab": "notes"},
            ],
        }
    )

    result = json.loads(raw)
    assert result["ok"] is True
    assert [step["action"] for step in result["steps"]] == ["finance_add", "habit_add", "open_ui"]
    assert [module for module, _ in calls] == ["finance", "habits", "notes"]
    assert all(payload.get("batch_id") for _, payload in calls)
    assert [payload.get("batch_step") for _, payload in calls] == [1, 2, 3]
    assert svc.db.list_finance_transactions(None, None)[0]["amount"] == 500.0
    assert any(h["name"] == "Caminhar" for h in svc.db.get_habits())


def test_window_theme_apply_persists_and_boot_tokens(tmp_path, monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "themes.db"))

    listing = svc.list_window_themes()
    assert any(module["id"] == "finance" for module in listing["modules"])
    assert any(preset["id"] == "emerald-ledger" for preset in listing["presets"])

    applied = svc.apply_window_theme("finance", "emerald-ledger")

    assert applied["ok"] is True
    assert applied["assignment"] == {"finance": "emerald-ledger"}
    assert calls[-1][0] == "finance"
    assert calls[-1][1]["animate"] == "theme_apply"
    boot = svc.get_window_theme_boot("finance")
    assert boot["theme_preset"] == "emerald-ledger"
    assert boot["theme"] == "dark"
    assert boot["theme_tokens"]["--accent"] == "#10b981"

    stored = json.loads((tmp_path / "nexus_window_themes.json").read_text(encoding="utf-8"))
    assert stored["modules"]["finance"] == "emerald-ledger"


def test_window_theme_generator_saves_tokens_without_prompt_memory(tmp_path, monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "themes.db"))
    prompt = "tema neon azul de estudos com glassmorphism calmo"

    generated = svc.generate_window_theme_preset("notes", prompt, name="Caderno Neon")

    assert generated["ok"] is True
    preset = generated["preset"]
    assert preset["id"] == "caderno-neon"
    assert preset["mode"] == "dark"
    assert preset["tokens"]["--accent"] == "#38bdf8"
    assert generated["assignment"] == {"notes": "caderno-neon"}
    assert calls[-1][0] == "notes"
    assert svc.get_window_theme_boot("notes")["theme_preset"] == "caderno-neon"

    stored_text = (tmp_path / "nexus_window_themes.json").read_text(encoding="utf-8")
    assert prompt not in stored_text
    assert "source_prompt" not in stored_text


def test_structured_theme_commands_apply_and_generate(tmp_path, monkeypatch):
    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", lambda *args, **kwargs: None)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "themes.db"))

    listed = json.loads(svc.handle_structured_command({"action": "theme_list"}))
    assert any(module["id"] == "finance" for module in listed["modules"])

    applied = json.loads(
        svc.handle_structured_command(
            {"action": "theme_apply", "module": "finance", "preset_id": "emerald-ledger"}
        )
    )
    assert applied["ok"] is True
    assert applied["assignment"]["finance"] == "emerald-ledger"

    generated = json.loads(
        svc.handle_structured_command(
            {
                "action": "theme_generate",
                "module": "study",
                "prompt": "tema claro dourado premium para revisoes",
                "name": "Biblioteca Solar",
            }
        )
    )
    assert generated["ok"] is True
    assert generated["preset"]["id"] == "biblioteca-solar"
    assert generated["preset"]["mode"] == "light"
    assert generated["assignment"]["study"] == "biblioteca-solar"


def test_nexus_manager_generates_window_theme_by_voice(tmp_path, monkeypatch):
    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", lambda *args, **kwargs: None)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "themes.db"))
    manager = NexusManagerSkill(svc)

    msg = manager.handle_command("Jarvis, gere um tema neon verde para a janela de financas")

    assert "Tema" in msg
    assert svc.get_window_theme_boot("finance")["theme_tokens"]["--accent"] == "#10b981"


def test_news_briefing_builds_video_transcript_and_narration(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", lambda module, payload=None: calls.append((module, payload or {})))
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "news.db"))
    fixture = [
        {
            "title": "Nova tecnologia acelera estudos personalizados",
            "source": "Agencia Teste",
            "date": "2026-05-16",
            "url": "https://example.com/tech",
            "body": "Pesquisadores apresentaram uma plataforma que adapta revisoes. A promessa e reduzir o tempo de estudo sem perder qualidade.",
        },
        {
            "title": "Economia brasileira registra novo indicador",
            "source": "Jornal Teste",
            "date": "2026-05-16",
            "url": "https://example.com/economia",
            "body": "O novo indicador mostra mudancas no consumo. Analistas observam cautela para os proximos meses.",
        },
    ]

    briefing = svc.build_news_briefing("tecnologia", limit=2, results=fixture)

    assert briefing["ok"] is True
    assert briefing["query"] == "tecnologia"
    assert len(briefing["items"]) == 2
    first = briefing["items"][0]
    assert first["video"]["provider"] == "youtube-search"
    assert "youtube.com/results" in first["video"]["url"]
    assert first["transcript"]["past"]
    assert first["transcript"]["present"] == first["title"]
    assert first["transcript"]["future"]
    assert first["summary"].startswith("Pesquisadores")
    assert "[Noticia 1]" in briefing["narration"]
    assert calls[-1][0] == "news"
    assert calls[-1][1]["animate"] == "news_briefing"


def test_news_briefing_builds_spotlight_deck_fields(tmp_path, monkeypatch):
    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", lambda *args, **kwargs: None)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "news_deck.db"))

    briefing = svc.build_news_briefing(
        "educacao",
        limit=1,
        results=[
            {
                "title": "Escolas adotam tutores de IA no ensino medio",
                "source": "Agencia Deck",
                "date": "2026-05-16",
                "url": "https://example.com/deck",
                "body": "Redes estaduais testam tutores de IA para revisar conteudos. Professores afirmam que a ferramenta ajuda a identificar lacunas. Especialistas pedem criterios de privacidade.",
            }
        ],
        open_window=False,
    )
    item = briefing["items"][0]

    assert briefing["deck"]["mode"] == "spotlight"
    assert briefing["deck"]["spotlight_index"] == 1
    assert "Noticia 1" in briefing["deck"]["briefing_script"]
    assert item["why_it_matters"].startswith("Importa porque")
    assert len(item["timeline"]) == 3
    assert item["timeline"][0]["label"] == "Contexto"
    assert item["timeline"][1]["label"] == "Agora"
    assert item["timeline"][2]["label"] == "Proximo passo"
    assert "educacao" in item["impact_tags"]
    assert any(action["id"] == "follow_up" for action in item["actions"])


def test_news_briefing_builds_narration_segments_and_spotlight_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", lambda *args, **kwargs: None)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "news_segments.db"))

    briefing = svc.build_news_briefing(
        "tecnologia",
        limit=2,
        results=[
            {
                "title": "Laboratorios publicam novo modelo de IA",
                "source": "Fonte IA",
                "date": "2026-05-16",
                "url": "https://example.com/ia",
                "body": "O modelo promete respostas mais rapidas em tarefas de estudo. Pesquisadores dizem que a eficiencia reduz custos. A proxima etapa e validar seguranca.",
            },
            {
                "title": "Escolas testam simulados adaptativos",
                "source": "Fonte Escola",
                "date": "2026-05-16",
                "url": "https://example.com/escola",
                "body": "As escolas usam dados de erros para montar revisoes. Professores acompanham lacunas por turma.",
            },
        ],
        open_window=False,
    )

    deck = briefing["deck"]

    assert briefing["narration"] == deck["briefing_script"]
    assert deck["spotlight"]["item_index"] == 1
    assert deck["spotlight"]["title"] == "Laboratorios publicam novo modelo de IA"
    assert deck["spotlight"]["primary_action"] == "Salvar no MindPalace"
    assert deck["source_count"] == 2
    assert deck["estimated_duration_sec"] >= 20
    assert len(deck["segments"]) == 2
    assert deck["segments"][0]["cue"] == "[Noticia 1]"
    assert deck["segments"][0]["item_index"] == 1
    assert "Por que importa" in deck["segments"][0]["script"]
    assert deck["segments"][0]["duration_sec"] >= 10


def test_news_followup_task_creates_task_from_item(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", lambda module, payload=None: calls.append((module, payload or {})))
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "news_followup.db"))
    item = svc.build_news_briefing(
        "saude",
        limit=1,
        results=[
            {
                "title": "Hospitais ampliam triagem digital",
                "source": "Fonte Saude",
                "date": "2026-05-16",
                "url": "https://example.com/triagem",
                "body": "Hospitais adotam triagem digital para reduzir filas. A avaliacao inicial mostra ganho de tempo.",
            }
        ],
        open_window=False,
    )["items"][0]

    result = svc.create_news_followup_task(item=item)
    tasks = svc.db.list_tasks(include_done=True)

    assert result["ok"] is True
    assert tasks[0]["title"].startswith("Acompanhar noticia: Hospitais ampliam triagem digital")
    assert result["task_id"] == tasks[0]["id"]
    assert calls[-1][0] == "tasks"
    assert calls[-1][1]["animate"] == "news_followup_task"


def test_news_briefing_persists_history_and_reuses_cache(tmp_path, monkeypatch):
    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", lambda *args, **kwargs: None)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "news_cache.db"))
    fixture = [
        {
            "title": "Tecnologia educacional chega as escolas",
            "source": "Agencia Cache",
            "date": "2026-05-16",
            "url": "https://example.com/cache",
            "body": "A nova tecnologia organiza revisoes. Professores relatam ganhos de foco.",
        }
    ]

    first = svc.build_news_briefing("educacao", limit=1, results=fixture, open_window=False)
    history = svc.list_news_briefings()
    monkeypatch.setattr(svc, "_fetch_news_results", lambda query, limit: [])
    cached = svc.build_news_briefing("educacao", limit=1, open_window=False)

    assert first["ok"] is True
    assert history[0]["query"] == "educacao"
    assert history[0]["item_count"] == 1
    assert cached["ok"] is True
    assert cached["from_cache"] is True
    assert cached["stale"] is True
    assert cached["cached_generated_at"] == first["generated_at"]
    assert cached["items"][0]["title"] == "Tecnologia educacional chega as escolas"


def test_save_news_item_to_note_creates_mindpalace_note(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", lambda module, payload=None: calls.append((module, payload or {})))
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "news_note.db"))
    briefing = svc.build_news_briefing(
        "ciencia",
        limit=1,
        results=[
            {
                "title": "Missao cientifica revela novos dados",
                "source": "Observatorio Teste",
                "date": "2026-05-16",
                "url": "https://example.com/ciencia",
                "body": "A missao coletou novos dados. Os cientistas explicam que a analise deve continuar.",
            }
        ],
        open_window=False,
    )

    result = svc.save_news_item_to_note(
        item=briefing["items"][0],
        subject="Atualidades",
    )
    note = svc.db.get_study_note(result["note_id"])

    assert result["ok"] is True
    assert note["subject"] == "Atualidades"
    assert note["title"] == "Missao cientifica revela novos dados"
    assert "## Resumo" in note["content"]
    assert "https://example.com/ciencia" in note["content"]
    assert "youtube.com/results" in note["content"]
    assert calls[-1][0] == "notes"
    assert calls[-1][1]["animate"] == "news_save_note"


def test_structured_news_save_note_accepts_briefing_payload(tmp_path, monkeypatch):
    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", lambda *args, **kwargs: None)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "news_structured_note.db"))
    briefing = svc.build_news_briefing(
        "energia",
        limit=1,
        results=[
            {
                "title": "Energia limpa ganha investimento",
                "source": "Fonte Energia",
                "date": "2026-05-16",
                "url": "https://example.com/energia",
                "body": "O investimento prioriza redes inteligentes. Especialistas esperam queda de custo.",
            }
        ],
        open_window=False,
    )

    raw = svc.handle_structured_command(
        {
            "action": "news_save_note",
            "briefing": briefing,
            "item_index": 1,
            "subject": "Energia",
        }
    )
    result = json.loads(raw)
    note = svc.db.get_study_note(result["note_id"])

    assert result["ok"] is True
    assert note["subject"] == "Energia"
    assert "Energia limpa ganha investimento" in note["title"]


def test_structured_news_briefing_accepts_fixture_results(tmp_path, monkeypatch):
    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", lambda *args, **kwargs: None)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "news_structured.db"))
    raw = svc.handle_structured_command(
        {
            "action": "news_briefing",
            "query": "brasil",
            "limit": 1,
            "results": json.dumps(
                [
                    {
                        "title": "Manchete de teste",
                        "source": "Fonte Teste",
                        "date": "2026-05-16",
                        "url": "https://example.com/news",
                        "body": "Resumo de teste para briefing. Proxima linha importante.",
                    }
                ]
            ),
        }
    )

    briefing = json.loads(raw)
    assert briefing["ok"] is True
    assert briefing["items"][0]["title"] == "Manchete de teste"
    assert briefing["items"][0]["video"]["provider"] == "youtube-search"


def test_desktop_bridge_exposes_news_briefing(tmp_path, monkeypatch):
    from src.ui import nexus_desktop_bridge as bridge

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", lambda *args, **kwargs: None)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "bridge_news.db"))
    monkeypatch.setattr(bridge, "get_nexus_service", lambda: svc)

    response = json.loads(
        bridge.nexus_bridge_call(
            "news_briefing",
            json.dumps(
                {
                    "query": "brasil",
                    "limit": 1,
                    "results": [
                        {
                            "title": "Noticia via bridge",
                            "source": "Fonte",
                            "date": "2026-05-16",
                            "url": "https://example.com/bridge",
                            "body": "Conteudo curto para resumo.",
                        }
                    ],
                }
            ),
        )
    )

    assert response["ok"] is True
    assert response["data"]["items"][0]["title"] == "Noticia via bridge"


def test_desktop_bridge_saves_news_item_to_note(tmp_path, monkeypatch):
    from src.ui import nexus_desktop_bridge as bridge

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", lambda *args, **kwargs: None)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "bridge_news_note.db"))
    monkeypatch.setattr(bridge, "get_nexus_service", lambda: svc)
    item = svc.build_news_briefing(
        "saude",
        limit=1,
        results=[
            {
                "title": "Saude digital melhora triagem",
                "source": "Fonte Saude",
                "date": "2026-05-16",
                "url": "https://example.com/saude",
                "body": "Hospitais testam triagem digital. O objetivo e reduzir filas.",
            }
        ],
        open_window=False,
    )["items"][0]

    response = json.loads(
        bridge.nexus_bridge_call(
            "news_save_note",
            json.dumps({"item": item, "subject": "Saude"}),
        )
    )
    note = svc.db.get_study_note(response["data"]["note_id"])

    assert response["ok"] is True
    assert note["subject"] == "Saude"
    assert "Saude digital melhora triagem" in note["title"]


def test_desktop_bridge_creates_news_followup_task(tmp_path, monkeypatch):
    from src.ui import nexus_desktop_bridge as bridge

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", lambda *args, **kwargs: None)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "bridge_news_task.db"))
    monkeypatch.setattr(bridge, "get_nexus_service", lambda: svc)
    item = svc.build_news_briefing(
        "mercado",
        limit=1,
        results=[
            {
                "title": "Mercado testa nova regra",
                "source": "Fonte Mercado",
                "date": "2026-05-16",
                "url": "https://example.com/mercado",
                "body": "A nova regra muda processos internos. Analistas esperam revisoes ao longo da semana.",
            }
        ],
        open_window=False,
    )["items"][0]

    response = json.loads(
        bridge.nexus_bridge_call(
            "news_followup_task",
            json.dumps({"item": item}),
        )
    )

    assert response["ok"] is True
    assert response["data"]["task_id"] == svc.db.list_tasks(include_done=True)[0]["id"]


def test_news_flashcards_generate_creates_note_and_due_cards(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "src.ui.nexus_signals.enqueue_nexus_desktop_open",
        lambda module, payload=None: calls.append((module, payload or {})),
    )
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "news_flashcards.db"))
    item = svc.build_news_briefing(
        "educacao",
        limit=1,
        results=[
            {
                "title": "Escolas testam tutores de IA",
                "source": "Fonte Educacao",
                "date": "2026-05-16",
                "url": "https://example.com/educacao",
                "body": "Escolas testam tutores de IA em sala de aula. O objetivo e personalizar revisoes e reduzir lacunas de aprendizagem.",
            }
        ],
        open_window=False,
    )["items"][0]

    result = svc.create_news_flashcards(item=item, max_cards=3)
    cards = svc.db.list_flashcards_due(10)
    note = svc.db.get_study_note(result["note_id"])

    assert result["ok"] is True
    assert result["created"] >= 1
    assert note["subject"] == "Noticias"
    assert any(card["note_id"] == result["note_id"] for card in cards)
    assert calls[-1][0] == "study"
    assert calls[-1][1]["animate"] == "news_flashcards_generate"


def test_desktop_bridge_generates_news_flashcards(tmp_path, monkeypatch):
    from src.ui import nexus_desktop_bridge as bridge

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", lambda *args, **kwargs: None)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "bridge_news_flashcards.db"))
    monkeypatch.setattr(bridge, "get_nexus_service", lambda: svc)
    item = svc.build_news_briefing(
        "ciencia",
        limit=1,
        results=[
            {
                "title": "Pesquisadores anunciam bateria nova",
                "source": "Fonte Ciencia",
                "date": "2026-05-16",
                "url": "https://example.com/ciencia",
                "body": "A bateria promete maior durabilidade. O estudo compara novos materiais e ciclos de carga.",
            }
        ],
        open_window=False,
    )["items"][0]

    response = json.loads(
        bridge.nexus_bridge_call(
            "news_flashcards_generate",
            json.dumps({"item": item, "max_cards": 2}),
        )
    )

    assert response["ok"] is True
    assert response["data"]["created"] >= 1


def test_nexus_manager_opens_news_panel_by_natural_name(monkeypatch):
    calls = []
    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", lambda module, payload=None: calls.append((module, payload or {})))

    manager = NexusManagerSkill(NexusService())
    msg = manager.handle_command("Jarvis, mostre as ultimas noticias")

    assert "Abrindo" in msg
    assert calls[-1][0] == "news"


def test_nexus_manager_opens_memory_graph_by_natural_name(monkeypatch):
    calls = []
    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", lambda module, payload=None: calls.append((module, payload or {})))

    manager = NexusManagerSkill(NexusService())
    msg = manager.handle_command("Jarvis, abra o grafo neural do MindPalace")

    assert "Abrindo" in msg
    assert calls[-1][0] == "memory_graph"


def test_news_tool_uses_nexus_briefing_and_base_run(monkeypatch):
    from src.tools.news import NewsTool

    calls = {}

    class FakeNexus:
        def build_news_briefing(self, query, limit=3, open_window=False):
            calls["query"] = query
            calls["limit"] = limit
            calls["open_window"] = open_window
            return {
                "ok": True,
                "query": query,
                "from_cache": False,
                "items": [
                    {
                        "index": 1,
                        "title": "Noticia da tool",
                        "source": "Fonte Tool",
                        "published_at": "2026-05-16",
                        "summary": "Resumo estruturado.",
                        "url": "https://example.com/tool",
                    }
                ],
            }

    monkeypatch.setattr("src.tools.news.get_nexus_service", lambda: FakeNexus(), raising=False)

    result = NewsTool().run(json.dumps({"query": "ia", "max_results": 1}))

    assert result.ok is True
    assert "Noticias recentes sobre 'ia'" in result.message
    assert "Noticia da tool" in result.message
    assert "Resumo estruturado." in result.message
    assert calls == {"query": "ia", "limit": 1, "open_window": False}


def test_memory_graph_builds_cross_module_nodes_and_edges(tmp_path):
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "memory_graph.db"))
    (tmp_path / "structured_memory.json").write_text(
        json.dumps(
            {
                "preferences": {
                    "study_style": {"value": "prefere revisoes curtas com flashcards", "updated": "2026-05-16"}
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (tmp_path / "Memory.md").write_text("# Rotina ENEM\nRevisar matemática e redação.", encoding="utf-8")
    svc.create_note("Matematica", "Funcoes do ENEM", "Função afim aparece em simulados e revisoes.")
    note_id = svc._last_created_note_id
    with svc.db._get_connection() as conn:
        conn.execute(
            "INSERT INTO flashcards (note_id, front, back) VALUES (?, ?, ?)",
            (note_id, "O que e funcao afim?", "Uma relacao do tipo f(x)=ax+b."),
        )
        conn.commit()
    svc.db.add_habit("Revisar Matematica", "Bloco diario", 70)
    svc.db.add_task("Resolver lista ENEM", date.today().isoformat(), 30)
    svc.add_goal("Passar no ENEM", "2026-11-01")
    reward_id = svc.add_reward("Rodizio depois do simulado", 450, "Recompensa de estudo")

    graph = svc.build_memory_graph(limit=40, include_markdown=True)

    assert graph["ok"] is True
    node_ids = {node["id"] for node in graph["nodes"]}
    node_types = {node["type"] for node in graph["nodes"]}
    assert "nexus:core" in node_ids
    assert f"note:{note_id}" in node_ids
    assert f"reward:{reward_id}" in node_ids
    assert {"subject", "note", "flashcard", "habit", "task", "goal", "reward", "memory", "markdown"} <= node_types
    assert any(edge["source"] == "subject:matematica" and edge["target"] == f"note:{note_id}" for edge in graph["edges"])
    assert any(edge["source"] == f"note:{note_id}" and edge["target"].startswith("tag:") for edge in graph["edges"])
    assert graph["stats"]["nodes"] == len(graph["nodes"])
    assert graph["stats"]["edges"] == len(graph["edges"])


def test_memory_graph_infers_semantic_cross_module_links(tmp_path):
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "smart_memory_graph.db"))
    svc.create_note(
        "Natureza",
        "Energia solar no ENEM",
        "Placas solares convertem radiacao em energia eletrica limpa.",
    )
    note_id = svc._last_created_note_id
    svc.db.add_task("Criar flashcards de energia solar", date.today().isoformat(), 25)
    svc.db.add_habit("Revisar energia solar", "Bloco de estudo rapido", 45)
    svc.add_goal("Dominar energia solar", "2026-11-01")

    graph = svc.build_memory_graph(query="energia solar", limit=60, include_markdown=False)

    note = next(node for node in graph["nodes"] if node["id"] == f"note:{note_id}")
    assert note["relevance"] > 0
    assert {"energia", "solar"} <= set(note["keywords"])
    assert graph["ranked_matches"][0]["id"] == f"note:{note_id}"
    semantic_edges = [edge for edge in graph["edges"] if edge["type"] in ("relates", "semantic")]
    assert semantic_edges
    assert graph["stats"]["smart_edges"] > 0
    assert any(
        {edge["source"], edge["target"]} == {f"note:{note_id}", node["id"]}
        for edge in semantic_edges
        for node in graph["nodes"]
        if node["type"] in {"task", "habit", "goal"}
    )


def test_memory_graph_local_semantic_layer_links_related_synonyms(tmp_path):
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "memory_graph_semantic.db"))
    svc.create_note(
        "Natureza",
        "Celulas fotovoltaicas",
        "Placas fotovoltaicas convertem radiacao em eletricidade limpa.",
    )
    note_id = svc._last_created_note_id
    svc.db.add_task("Revisar energia solar antes do simulado", date.today().isoformat(), 20)

    graph = svc.build_memory_graph(query="energia solar", limit=80, include_markdown=False)

    note = next(node for node in graph["nodes"] if node["id"] == f"note:{note_id}")
    assert "energia_solar" in note["semantic_topics"]
    semantic_edges = [edge for edge in graph["edges"] if edge["type"] == "semantic"]
    assert semantic_edges
    assert graph["stats"]["semantic_edges"] == len(semantic_edges)
    assert any(
        {edge["source"], edge["target"]} == {f"note:{note_id}", node["id"]}
        for edge in semantic_edges
        for node in graph["nodes"]
        if node["type"] == "task"
    )


def test_memory_graph_exports_and_imports_obsidian_markdown(tmp_path):
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "memory_graph_obsidian.db"))
    svc.create_note("Natureza", "Energia solar", "Resumo sobre placas solares e revisao ENEM.")
    export_dir = tmp_path / "obsidian_export"

    exported = svc.export_memory_graph_obsidian(export_dir, query="energia solar", include_markdown=False)

    assert exported["ok"] is True
    assert exported["count"] >= 1
    assert (export_dir / "Nexus Memory Graph.md").exists()
    first_file = Path(exported["files"][0])
    assert "[[" in first_file.read_text(encoding="utf-8")

    import_dir = tmp_path / "obsidian_import"
    import_dir.mkdir()
    (import_dir / "Nova Ideia.md").write_text(
        "# Nova Ideia\nConectar energia solar com revisao de fisica.",
        encoding="utf-8",
    )

    imported = svc.import_obsidian_markdown(import_dir, subject="Obsidian")
    notes = svc.db.list_study_notes("Obsidian")

    assert imported["ok"] is True
    assert imported["count"] == 1
    assert any(note["title"] == "Nova Ideia" for note in notes)


def test_ops_dashboard_tracks_metrics_recommendations_and_opens_window(tmp_path, monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "ops.db"))

    updated = svc.set_ops_metric("mrr", 15444, label="MRR", unit="BRL", target=15000, trend="up")
    assert updated["ok"] is True
    svc.set_ops_metric("downloads", 3960, label="Downloads", unit="count", target=3500, trend="up")
    svc.set_ops_metric("roas", 1.4, label="ROAS anuncios", unit="ratio", target=1.2, trend="up")
    svc.set_ops_metric("refunds", 0, label="Reembolsos", unit="count", target=0, trend="down")

    dashboard = svc.build_ops_dashboard(open_window=True)

    assert dashboard["ok"] is True
    assert dashboard["stats"]["targets_hit"] >= 4
    assert dashboard["focus_metric"]["key"] == "mrr"
    assert any("dobrar" in rec["action"].lower() or "aumentar" in rec["action"].lower() for rec in dashboard["recommendations"])
    assert "MRR" in dashboard["narrative"]
    assert calls[-1][0] == "ops"
    assert calls[-1][1]["animate"] == "ops_dashboard"
    assert calls[-1][1]["dashboard"]["focus_metric"]["key"] == "mrr"


def test_structured_ops_commands_and_desktop_bridge(tmp_path, monkeypatch):
    import src.ui.nexus_desktop_bridge as bridge

    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "ops_bridge.db"))
    monkeypatch.setattr("src.ui.nexus_desktop_bridge.get_nexus_service", lambda: svc)

    raw = svc.handle_structured_command(
        {
            "action": "ops_metric_set",
            "key": "mrr",
            "value": "12000",
            "label": "MRR",
            "unit": "BRL",
            "target": "20000",
        }
    )
    result = json.loads(raw)
    assert result["ok"] is True
    assert result["metric"]["key"] == "mrr"

    dashboard = json.loads(svc.handle_structured_command({"action": "ops_dashboard", "open_window": "false"}))
    assert dashboard["ok"] is True
    assert dashboard["metrics"][0]["key"] == "mrr"

    bridged = json.loads(bridge.nexus_bridge_call("ops_dashboard", json.dumps({"open_window": False})))
    assert bridged["ok"] is True
    assert bridged["data"]["focus_metric"]["key"] == "mrr"


def test_memory_graph_context_returns_ranked_matches_and_neighbors(tmp_path):
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "memory_graph_context.db"))
    svc.create_note("Natureza", "Energia solar", "Resumo sobre energia solar e placas fotovoltaicas.")
    note_id = svc._last_created_note_id
    svc.db.add_task("Resolver questoes de energia solar", date.today().isoformat(), 20)
    svc.add_goal("Aumentar acertos em Natureza", "2026-11-01")

    context = svc.build_memory_graph_context("energia solar", limit=3, include_markdown=False)

    assert context["ok"] is True
    assert context["query"] == "energia solar"
    assert context["matches"][0]["id"] == f"note:{note_id}"
    assert context["matches"][0]["related"]
    assert "Energia solar" in context["context_text"]
    assert "Resolver questoes de energia solar" in context["context_text"]
    assert "notes" in context["suggested_modules"]


def test_structured_memory_graph_context_returns_json_payload(tmp_path):
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "structured_memory_context.db"))
    svc.create_note("Humanas", "Revolucao Francesa", "Burguesia, iluminismo e crise fiscal.")

    raw = svc.handle_structured_command(
        {"action": "memory_graph_context", "query": "iluminismo", "limit": 2}
    )
    context = json.loads(raw)

    assert context["ok"] is True
    assert context["query"] == "iluminismo"
    assert context["matches"]
    assert "Revolucao Francesa" in context["context_text"]


def test_desktop_bridge_exposes_memory_graph_context(tmp_path, monkeypatch):
    import src.ui.nexus_desktop_bridge as bridge

    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "bridge_memory_context.db"))
    svc.create_note("MindPalace", "Mapa neural", "Grafo de memoria local para estudos.")
    monkeypatch.setattr(bridge, "get_nexus_service", lambda: svc)

    response = json.loads(
        bridge.nexus_bridge_call("memory_graph_context", json.dumps({"query": "grafo"}))
    )

    assert response["ok"] is True
    assert response["data"]["ok"] is True
    assert response["data"]["matches"][0]["label"] == "Mapa neural"


def test_structured_memory_graph_returns_json_payload(tmp_path):
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "structured_memory_graph.db"))
    svc.create_note("Noticias", "Energia solar", "Resumo sobre energia solar.")

    raw = svc.handle_structured_command({"action": "memory_graph", "query": "solar", "limit": 20})
    graph = json.loads(raw)

    assert graph["ok"] is True
    assert graph["query"] == "solar"
    assert any(node["type"] == "note" and "Energia solar" in node["label"] for node in graph["nodes"])


def test_desktop_bridge_exposes_memory_graph(tmp_path, monkeypatch):
    import src.ui.nexus_desktop_bridge as bridge

    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "bridge_memory_graph.db"))
    svc.create_note("MindPalace", "Mapa mental", "Rede neural de notas.")
    monkeypatch.setattr(bridge, "get_nexus_service", lambda: svc)

    response = json.loads(bridge.nexus_bridge_call("memory_graph", json.dumps({"query": "mapa"})))

    assert response["ok"] is True
    assert response["data"]["ok"] is True
    assert any(node["type"] == "note" and "Mapa mental" in node["label"] for node in response["data"]["nodes"])


def test_habit_streak_consecutive_days(tmp_path):
    db = NexusDatabase(db_path=str(tmp_path / "streak.db"))
    hid = db.add_habit("X", "d", 10)
    with db._get_connection() as conn:
        d0 = date.today()
        for i in range(3):
            ds = (d0 - timedelta(days=i)).isoformat()
            conn.execute(
                "INSERT INTO habit_logs (habit_id, completed_at) VALUES (?, ?)",
                (hid, f"{ds} 12:00:00"),
            )
        conn.commit()
    assert db._compute_habit_streak(hid) == 3


def test_finance_add_enqueues_desktop_receipt(tmp_path, monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "finance_receipt.db"))

    msg = svc.handle_structured_command(
        {
            "action": "finance_add",
            "type": "expense",
            "amount": "150,00",
            "category": "Tecnologia",
            "description": "mousepad",
            "occurred_at": "2026-05-14",
            "necessity": 4,
        }
    )

    assert "150.00" in msg
    assert calls
    module, payload = calls[-1]
    assert module == "finance"
    assert payload["animate"] == "finance_add"
    assert payload["receipt"]["kind"] == "finance"
    assert payload["receipt"]["type"] == "expense"
    assert payload["receipt"]["amount"] == 150.0
    assert payload["receipt"]["category"] == "Tecnologia"
    assert payload["receipt"]["description"] == "mousepad"
    assert payload["receipt"]["occurred_at"] == "2026-05-14"
    rows = svc.db.list_finance_transactions("2026-05-14", "2026-05-14")
    assert payload["highlight_id"] == rows[0]["id"]
    assert payload["receipt"]["id"] == rows[0]["id"]


def test_habit_complete_enqueues_desktop_receipt(tmp_path, monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "habit_receipt.db"))
    hid = svc.db.add_habit("Meditar", "10 minutos", 40)

    msg = svc.handle_structured_command(
        {"action": "habit_complete", "habit_name": "meditar"}
    )

    assert "Meditar" in msg
    assert calls
    module, payload = calls[-1]
    assert module == "habits"
    assert payload["highlight_id"] == hid
    assert payload["animate"] == "habit_complete"
    assert payload["receipt"]["kind"] == "habit"
    assert payload["receipt"]["name"] == "Meditar"
    assert payload["receipt"]["xp"] >= 40
    assert payload["receipt"]["streak"] >= 1


def test_finance_add_accepts_natural_date_aliases(tmp_path, monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "finance_dates.db"))

    svc.handle_structured_command(
        {
            "action": "finance_add",
            "type": "expense",
            "amount": 21,
            "category": "Teste",
            "description": "alias",
            "occurred_at": "ontem de ontem",
        }
    )

    expected = (date.today() - timedelta(days=2)).isoformat()
    rows = svc.db.list_finance_transactions(expected, expected)
    assert rows
    assert rows[0]["occurred_at"] == expected
    assert calls[-1][1]["receipt"]["occurred_at"] == expected


def test_finance_snapshot_includes_daily_series_and_categories(tmp_path):
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "finance_chart_data.db"))
    svc.db.add_transaction("income", 1000, "Salario", "freela", 10, occurred_at="2026-05-02")
    svc.db.add_transaction("expense", 150, "Tecnologia", "mousepad", 5, occurred_at="2026-05-02")
    svc.db.add_transaction("expense", 50, "Lanche", "sanduiche", 5, occurred_at="2026-05-03")

    snapshot = svc.get_finance_snapshot(year=2026, month=5)

    assert len(snapshot["daily_series"]) == 31
    day_two = next(day for day in snapshot["daily_series"] if day["date"] == "2026-05-02")
    assert day_two["income"] == 1000.0
    assert day_two["expense"] == 150.0
    assert day_two["net"] == 850.0
    assert snapshot["category_breakdown"][0]["category"] == "Tecnologia"
    assert snapshot["category_breakdown"][0]["expense"] == 150.0


def test_finance_snapshot_exposes_debt_adjusted_insights(tmp_path):
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "finance_debt_insights.db"))
    svc.db.add_transaction("income", 1000, "Salario", "salario", 10, occurred_at="2026-05-01")
    svc.db.add_transaction("expense", 200, "Cartao", "parcela", 5, occurred_at="2026-05-02", is_debt=1)
    svc.db.add_transaction("expense", 150, "Mercado", "compras", 5, occurred_at="2026-05-03")

    snapshot = svc.get_finance_snapshot(year=2026, month=5)

    assert snapshot["finance_insights"]["cash_after_debt"] == 800.0
    assert snapshot["finance_insights"]["non_debt_expense"] == 150.0
    assert snapshot["finance_insights"]["debt_ratio_pct"] == 20
    assert snapshot["finance_insights"]["expense_ratio_pct"] == 35
    assert snapshot["finance_insights"]["free_after_all_expenses"] == 650.0


def test_finance_delete_by_description_removes_transaction_and_enqueues(tmp_path, monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "finance_delete.db"))
    svc.db.add_transaction("expense", 150, "Tecnologia", "mousepad gamer", 5, occurred_at="2026-05-14")
    svc.db.add_transaction("expense", 20, "Lanche", "coxinha", 5, occurred_at="2026-05-14")

    msg = svc.handle_structured_command(
        {
            "action": "finance_delete",
            "type": "expense",
            "description": "mousepad",
            "occurred_at": "2026-05-14",
        }
    )

    rows = svc.db.list_finance_transactions("2026-05-14", "2026-05-14")
    assert "removido" in msg.lower()
    assert [r["description"] for r in rows] == ["coxinha"]
    assert calls[-1][0] == "finance"
    assert calls[-1][1]["animate"] == "finance_delete"
    assert calls[-1][1]["receipt"]["action"] == "finance_delete"
    assert calls[-1][1]["receipt"]["description"] == "mousepad gamer"


def test_desktop_bridge_deletes_finance_transaction(tmp_path, monkeypatch):
    from src.ui import nexus_desktop_bridge as bridge

    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "bridge_finance_delete.db"))
    svc.db.add_transaction("expense", 77, "Teste", "apagar isto", 5, occurred_at="2026-05-14")
    tx_id = svc.db.list_finance_transactions("2026-05-14", "2026-05-14")[0]["id"]
    monkeypatch.setattr(bridge, "get_nexus_service", lambda: svc)

    deleted = json.loads(
        bridge.nexus_bridge_call("finance_delete", json.dumps({"transaction_id": tx_id}))
    )

    assert deleted["ok"]
    assert deleted["data"]["deleted"]["id"] == tx_id
    assert svc.db.list_finance_transactions("2026-05-14", "2026-05-14") == []


def test_finance_update_by_id_edits_transaction_and_enqueues(tmp_path, monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "finance_update.db"))
    svc.db.add_transaction("expense", 150, "Tecnologia", "mousepad", 5, occurred_at="2026-05-14")
    tx_id = svc.db.list_finance_transactions("2026-05-14", "2026-05-14")[0]["id"]

    result = svc.update_finance_transaction(
        transaction_id=tx_id,
        amount=180,
        category="Setup",
        description="mousepad speed",
        occurred_at="2026-05-15",
        notes="corrigido pela IA",
        is_debt=1,
    )

    rows = svc.db.list_finance_transactions("2026-05-15", "2026-05-15")
    assert result["ok"] is True
    assert rows[0]["id"] == tx_id
    assert rows[0]["amount"] == 180
    assert rows[0]["category"] == "Setup"
    assert rows[0]["description"] == "mousepad speed"
    assert rows[0]["notes"] == "corrigido pela IA"
    assert rows[0]["is_debt"] == 1
    assert calls[-1][0] == "finance"
    assert calls[-1][1]["animate"] == "finance_update"
    assert calls[-1][1]["receipt"]["action"] == "finance_update"
    assert calls[-1][1]["receipt"]["id"] == tx_id


def test_structured_command_updates_finance_transaction_by_match(tmp_path, monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "structured_finance_update.db"))
    svc.db.add_transaction("expense", 150, "Tecnologia", "mousepad gamer", 5, occurred_at="2026-05-14")
    svc.db.add_transaction("expense", 20, "Lanche", "coxinha", 5, occurred_at="2026-05-14")

    msg = svc.handle_structured_command(
        {
            "action": "finance_update",
            "target_description": "mousepad",
            "target_date": "2026-05-14",
            "new_amount": "175,50",
            "new_category": "Setup",
            "new_notes": "valor ajustado",
            "new_is_debt": 1,
        }
    )

    rows = svc.db.list_finance_transactions("2026-05-14", "2026-05-14")
    edited = next(row for row in rows if row["description"] == "mousepad gamer")
    untouched = next(row for row in rows if row["description"] == "coxinha")
    assert "atualizado" in msg.lower()
    assert edited["amount"] == 175.5
    assert edited["category"] == "Setup"
    assert edited["notes"] == "valor ajustado"
    assert edited["is_debt"] == 1
    assert untouched["amount"] == 20
    assert calls[-1][0] == "finance"
    assert calls[-1][1]["receipt"]["action"] == "finance_update"


def test_desktop_bridge_updates_finance_transaction(tmp_path, monkeypatch):
    from src.ui import nexus_desktop_bridge as bridge

    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "bridge_finance_update.db"))
    svc.db.add_transaction("income", 900, "Freela", "landing page", 10, occurred_at="2026-05-10")
    tx_id = svc.db.list_finance_transactions("2026-05-10", "2026-05-10")[0]["id"]
    monkeypatch.setattr(bridge, "get_nexus_service", lambda: svc)

    updated = json.loads(
        bridge.nexus_bridge_call(
            "finance_update",
            json.dumps(
                {
                    "transaction_id": tx_id,
                    "amount": 1200,
                    "category": "Cliente",
                    "description": "landing page + manutencao",
                    "occurred_at": "2026-05-11",
                    "notes": "reajuste final",
                }
            ),
        )
    )

    row = svc.db.get_finance_transaction(tx_id)
    assert updated["ok"]
    assert updated["data"]["updated"]["id"] == tx_id
    assert row["amount"] == 1200
    assert row["category"] == "Cliente"
    assert row["occurred_at"] == "2026-05-11"
    assert row["notes"] == "reajuste final"


def test_nexus_manager_understands_update_expense_amount(tmp_path, monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "manager_finance_update.db"))
    svc.db.add_transaction("expense", 150, "Tecnologia", "mousepad gamer", 5, occurred_at=date.today().isoformat())
    manager = NexusManagerSkill(svc)

    msg = manager.handle_command("corrija o gasto com mousepad de hoje para 175 reais")

    rows = svc.db.list_finance_transactions(date.today().isoformat(), date.today().isoformat())
    assert "atualizado" in msg.lower()
    assert rows[0]["amount"] == 175
    assert calls[-1][0] == "finance"
    assert calls[-1][1]["animate"] == "finance_update"


def test_structured_command_redeems_reward_and_updates_goal(tmp_path):
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "reward_goal_structured.db"))
    svc.db.add_xp(1000)
    svc.add_goal("Passar no ENEM")

    reward_raw = svc.handle_structured_command(
        {"action": "reward_redeem", "reward_name": "Anime"}
    )
    goal_msg = svc.handle_structured_command(
        {"action": "goal_update", "name": "ENEM", "progress": 45}
    )

    reward = json.loads(reward_raw)
    assert reward["ok"] is True
    assert "Anime" in reward["message"]
    assert "45%" in goal_msg
    assert svc.get_goals()[0]["progress"] == 45


def test_reward_status_exposes_daily_limit_reset_and_history(tmp_path):
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "reward_status.db"))
    svc.db.add_xp(1000)

    ok, msg = svc.process_reward("Anime")
    status = svc.get_reward_status(limit=3)

    assert ok is True
    assert "Anime" in msg
    assert status["daily_limit"] == 1
    assert status["remaining_today"] == 0
    assert status["next_available_date"] == (date.today() + timedelta(days=1)).isoformat()
    assert status["reset_at"].startswith(status["next_available_date"])
    assert status["redeemed_today"] is True
    assert "Anime" in status["today_reward"]["name"]
    assert len(status["history"]) == 1
    assert "Anime" in status["history"][0]["name"]


def test_nexus_manager_understands_delete_expense_reward_and_goal_preset(tmp_path, monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "manager_universal.db"))
    svc.db.add_xp(1000)
    svc.db.add_transaction("expense", 150, "Tecnologia", "mousepad gamer", 5, occurred_at=date.today().isoformat())
    manager = NexusManagerSkill(svc)

    delete_msg = manager.handle_command("apague o gasto com mousepad de hoje")
    reward_msg = manager.handle_command("resgatar Episodio de Anime")
    preset_msg = manager.handle_command("crie um preset para passar no enem e conseguir shape")

    assert "removido" in delete_msg.lower()
    assert svc.db.list_finance_transactions(date.today().isoformat(), date.today().isoformat()) == []
    assert "Anime" in reward_msg
    assert "Plano IA" in preset_msg
    assert any("ENEM" in h["name"] or "Treino" in h["name"] for h in svc.db.get_habits())
    assert any(call[0] == "finance" and call[1]["animate"] == "finance_delete" for call in calls)


def test_lifestyle_preset_roundtrip_preserves_days_and_enqueues(tmp_path, monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "preset_roundtrip.db"))
    svc.db.add_habit("Redação ENEM", "Escrever 1 texto", 120, "[1, 3, 5]")

    save_msg = svc.save_lifestyle_preset("ENEM Elite")
    presets = svc.list_lifestyle_presets()
    assert "ENEM Elite" in save_msg
    assert presets[0]["name"] == "ENEM Elite"
    assert presets[0]["habit_count"] >= 1

    svc.db.add_habit("Ruído temporário", "não deve sobreviver", 5)
    load_msg = svc.load_lifestyle_preset("ENEM")

    habits = svc.db.get_habits()
    reda = next(h for h in habits if h["name"] == "Redação ENEM")
    assert reda["days_of_week"] == "[1, 3, 5]"
    assert "ativado" in load_msg
    assert calls[-1][0] == "habits"
    assert calls[-1][1]["animate"] == "preset"
    assert calls[-1][1]["receipt"]["kind"] == "preset"
    assert calls[-1][1]["receipt"]["name"] == "ENEM Elite"


def test_desktop_bridge_exposes_lifestyle_presets(tmp_path, monkeypatch):
    from src.ui import nexus_desktop_bridge as bridge

    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "bridge_presets.db"))
    svc.db.add_habit("Treino", "Forca e mobilidade", 80, "[1, 2, 3]")
    expected_count = len(svc.db.get_habits())
    monkeypatch.setattr(bridge, "get_nexus_service", lambda: svc)

    saved = json.loads(bridge.nexus_bridge_call("preset_save", '{"name":"Shape"}'))
    assert saved["ok"]
    assert "Shape" in saved["data"]["message"]

    listed = json.loads(bridge.nexus_bridge_call("presets_list", "{}"))
    assert listed["ok"]
    assert listed["data"][0]["name"] == "Shape"
    assert listed["data"][0]["habit_count"] == expected_count

    applied = json.loads(bridge.nexus_bridge_call("preset_apply", '{"name":"Sha"}'))
    assert applied["ok"]
    assert "ativado" in applied["data"]["message"]


def test_goal_based_preset_builds_goal_specific_habits(tmp_path, monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "goal_preset.db"))

    msg = svc.build_lifestyle_preset_from_goals(
        ["Passar no ENEM", "juntar dinheiro para investir", "conseguir shape dos sonhos"]
    )

    names = [h["name"] for h in svc.db.get_habits()]
    assert "Plano IA" in msg
    assert any("ENEM" in name for name in names)
    assert any("gastos" in name.lower() for name in names)
    assert any("Treino" in name for name in names)
    assert any(p["name"].startswith("Plano IA") for p in svc.list_lifestyle_presets())
    assert calls[-1][0] == "habits"
    assert calls[-1][1]["receipt"]["kind"] == "preset"
    assert calls[-1][1]["receipt"]["action"] == "preset_apply_goals"


def test_generate_flashcards_from_note_creates_due_cards(tmp_path, monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "note_flashcards.db"))
    svc.create_note(
        "Biologia",
        "Fotossintese",
        """
        # Fotossintese
        Fotossintese converte luz em energia quimica nos cloroplastos.
        - Fase clara produz ATP e NADPH.
        - Ciclo de Calvin fixa carbono.
        """,
    )
    note_id = svc._last_created_note_id

    result = svc.generate_flashcards_from_note(note_id, max_cards=4)

    cards = svc.db.list_flashcards_due(10)
    fronts = [c["front"] for c in cards]
    assert result["created"] >= 3
    assert any("Fotossintese" in f for f in fronts)
    assert any("Fase clara" in f for f in fronts)
    assert calls[-1][0] == "study"
    assert calls[-1][1]["animate"] == "flashcards_generate"
    assert calls[-1][1]["created"] == result["created"]


def test_desktop_bridge_generates_flashcards_from_note(tmp_path, monkeypatch):
    from src.ui import nexus_desktop_bridge as bridge

    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "bridge_flashcards.db"))
    svc.create_note(
        "Historia",
        "Revolucao Francesa",
        "Revolucao Francesa derrubou o Antigo Regime. - Queda da Bastilha marcou o processo.",
    )
    note_id = svc._last_created_note_id
    monkeypatch.setattr(bridge, "get_nexus_service", lambda: svc)

    generated = json.loads(
        bridge.nexus_bridge_call("flashcards_generate", json.dumps({"note_id": note_id}))
    )

    assert generated["ok"]
    assert generated["data"]["created"] >= 2
    assert svc.db.list_flashcards_due(10)


def test_summarize_note_appends_summary_and_enqueues(tmp_path, monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "note_summary.db"))
    svc.create_note(
        "Historia",
        "Era Vargas",
        """
        Era Vargas centralizou o poder politico e reorganizou o Estado brasileiro.
        A industrializacao ganhou impulso com empresas estatais e protecao ao mercado interno.
        A CLT consolidou direitos trabalhistas e aproximou Vargas dos trabalhadores urbanos.
        """,
    )
    note_id = svc._last_created_note_id

    result = svc.summarize_note(note_id, append=True, max_sentences=2)

    note = svc.db.get_study_note(note_id)
    assert result["note_id"] == note_id
    assert result["summary"]
    assert "## Resumo IA" in note["content"]
    assert "Era Vargas" in note["content"]
    assert calls[-1][0] == "notes"
    assert calls[-1][1]["animate"] == "note_summarize"
    assert calls[-1][1]["receipt"]["kind"] == "note"


def test_desktop_bridge_summarizes_note(tmp_path, monkeypatch):
    from src.ui import nexus_desktop_bridge as bridge

    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "bridge_note_summary.db"))
    svc.create_note(
        "Biologia",
        "Mitose",
        "Mitose gera duas celulas geneticamente iguais. Prophase condensa cromossomos. Citocinese separa o citoplasma.",
    )
    note_id = svc._last_created_note_id
    monkeypatch.setattr(bridge, "get_nexus_service", lambda: svc)

    summarized = json.loads(
        bridge.nexus_bridge_call("note_summarize", json.dumps({"note_id": note_id}))
    )

    assert summarized["ok"]
    assert summarized["data"]["summary"]
    assert "## Resumo IA" in svc.db.get_study_note(note_id)["content"]


def test_teach_note_builds_teacher_answer_and_enqueues(tmp_path, monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "note_teacher.db"))
    svc.create_note(
        "Fisica",
        "Leis de Newton",
        """
        A primeira lei explica a inercia: corpos tendem a manter seu estado de movimento.
        A segunda lei relaciona forca, massa e aceleracao.
        A terceira lei afirma que toda acao gera uma reacao de mesma intensidade.
        """,
    )
    note_id = svc._last_created_note_id

    result = svc.teach_note(note_id, question="Como usar a segunda lei?", max_points=3)

    assert result["note_id"] == note_id
    assert result["mode"] == "professor"
    assert result["question"] == "Como usar a segunda lei?"
    assert "Leis de Newton" in result["lesson"]
    assert any("segunda lei" in point.lower() for point in result["key_points"])
    assert len(result["check_questions"]) >= 2
    assert calls[-1][0] == "notes"
    assert calls[-1][1]["animate"] == "teacher_mode"
    assert calls[-1][1]["receipt"]["action"] == "note_teach"


def test_desktop_bridge_teaches_note(tmp_path, monkeypatch):
    from src.ui import nexus_desktop_bridge as bridge

    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "bridge_note_teacher.db"))
    svc.create_note(
        "Quimica",
        "Ligacoes quimicas",
        "Ligacao ionica envolve transferencia de eletrons. Ligacao covalente envolve compartilhamento de eletrons.",
    )
    note_id = svc._last_created_note_id
    monkeypatch.setattr(bridge, "get_nexus_service", lambda: svc)

    taught = json.loads(
        bridge.nexus_bridge_call(
            "note_teach",
            json.dumps({"note_id": note_id, "question": "Qual a diferenca principal?"}),
        )
    )

    assert taught["ok"]
    assert taught["data"]["lesson"]
    assert taught["data"]["key_points"]
    assert taught["data"]["check_questions"]


def test_teach_subject_builds_teacher_answer_and_enqueues(tmp_path, monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "subject_teacher.db"))
    svc.create_note(
        "Matematica",
        "Porcentagem",
        "Porcentagem compara uma parte com o todo. Aumentos sucessivos multiplicam fatores.",
    )
    first_note_id = svc._last_created_note_id
    svc.create_note(
        "Matematica",
        "Funcao afim",
        "Funcao afim tem taxa de variacao constante. O grafico e uma reta.",
    )
    svc.create_note(
        "Historia",
        "Era Vargas",
        "Estado Novo centralizou o poder politico.",
    )

    result = svc.teach_subject("Matematica", question="Como revisar antes do ENEM?", max_points=4)

    assert result["mode"] == "professor_subject"
    assert result["subject"] == "Matematica"
    assert result["note_count"] == 2
    assert result["question"] == "Como revisar antes do ENEM?"
    assert "Matematica" in result["lesson"]
    assert "Porcentagem" in result["lesson"]
    assert any("Funcao afim" in point for point in result["key_points"])
    assert len(result["check_questions"]) >= 2
    assert calls[-1][0] == "notes"
    assert calls[-1][1]["highlight_id"] == first_note_id
    assert calls[-1][1]["animate"] == "subject_teacher_mode"
    assert calls[-1][1]["receipt"]["action"] == "subject_teach"
    assert calls[-1][1]["receipt"]["subject"] == "Matematica"
    assert calls[-1][1]["receipt"]["note_count"] == 2


def test_desktop_bridge_teaches_subject(tmp_path, monkeypatch):
    from src.ui import nexus_desktop_bridge as bridge

    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "bridge_subject_teacher.db"))
    svc.create_note(
        "Biologia",
        "Ecologia",
        "Cadeias alimentares mostram fluxo de energia. Teias alimentares conectam varias cadeias.",
    )
    monkeypatch.setattr(bridge, "get_nexus_service", lambda: svc)

    taught = json.loads(
        bridge.nexus_bridge_call(
            "subject_teach",
            json.dumps({"subject": "Biologia", "question": "Como cairia no ENEM?"}),
        )
    )

    assert taught["ok"]
    assert taught["data"]["mode"] == "professor_subject"
    assert taught["data"]["lesson"]
    assert taught["data"]["key_points"]
    assert taught["data"]["check_questions"]


def test_structured_command_teaches_note(tmp_path):
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "structured_note_teacher.db"))
    svc.create_note(
        "Historia",
        "Republica Velha",
        "A politica dos governadores articulava apoio entre elites estaduais e governo federal.",
    )
    note_id = svc._last_created_note_id

    raw = svc.handle_structured_command(
        {"action": "note_teach", "note_id": note_id, "question": "Explique em linguagem simples"}
    )
    data = json.loads(raw)

    assert data["mode"] == "professor"
    assert "Republica Velha" in data["lesson"]


def test_structured_command_teaches_subject(tmp_path):
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "structured_subject_teacher.db"))
    svc.create_note(
        "Redacao",
        "Competencia 2",
        "A competencia 2 avalia repertorio sociocultural e compreensao do tema.",
    )

    raw = svc.handle_structured_command(
        {"action": "subject_teach", "subject": "Redacao", "question": "Como melhorar?"}
    )
    data = json.loads(raw)

    assert data["mode"] == "professor_subject"
    assert data["subject"] == "Redacao"
    assert "Competencia 2" in data["lesson"]


def test_attach_media_to_note_updates_media_content_and_enqueues(tmp_path, monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "note_media.db"))
    svc.create_note("Biologia", "Celula", "Membrana plasmatica controla trocas.")
    note_id = svc._last_created_note_id

    result = svc.attach_media_to_note(
        note_id,
        "https://example.com/celula.png",
        caption="Diagrama da celula",
    )

    note = svc.db.get_study_note(note_id)
    media = json.loads(note["media_links"])
    assert result["note_id"] == note_id
    assert result["attached"]["url"] == "https://example.com/celula.png"
    assert media[0]["caption"] == "Diagrama da celula"
    assert "![Diagrama da celula](https://example.com/celula.png)" in note["content"]
    assert calls[-1][0] == "notes"
    assert calls[-1][1]["animate"] == "note_media_attach"


def test_desktop_bridge_attaches_media_to_note(tmp_path, monkeypatch):
    from src.ui import nexus_desktop_bridge as bridge

    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "bridge_note_media.db"))
    svc.create_note("Geografia", "Clima", "Massas de ar influenciam o clima brasileiro.")
    note_id = svc._last_created_note_id
    monkeypatch.setattr(bridge, "get_nexus_service", lambda: svc)

    attached = json.loads(
        bridge.nexus_bridge_call(
            "note_attach_media",
            json.dumps(
                {
                    "note_id": note_id,
                    "media_url": "C:/imagens/clima.png",
                    "caption": "Mapa de massas de ar",
                }
            ),
        )
    )

    note = svc.db.get_study_note(note_id)
    assert attached["ok"]
    assert attached["data"]["attached"]["caption"] == "Mapa de massas de ar"
    assert "C:/imagens/clima.png" in note["content"]


def test_structured_command_attaches_media_to_note(tmp_path):
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "structured_note_media.db"))
    svc.create_note("Historia", "Era Vargas", "Estado Novo centralizou o poder.")
    note_id = svc._last_created_note_id

    raw = svc.handle_structured_command(
        {
            "action": "note_attach_media",
            "note_id": note_id,
            "media_url": "https://example.com/vargas.jpg",
            "caption": "Getulio Vargas",
        }
    )
    data = json.loads(raw)

    assert data["attached"]["url"] == "https://example.com/vargas.jpg"
    assert "Getulio Vargas" in svc.db.get_study_note(note_id)["content"]


def test_study_recommendations_rank_weak_subjects_and_due_reviews(tmp_path):
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "study_recommendations.db"))
    with svc.db._get_connection() as conn:
        conn.execute(
            "UPDATE study_stats SET total_questions = 10, correct_answers = 3 WHERE subject = ?",
            ("Matemática",),
        )
        conn.execute(
            "UPDATE study_stats SET total_questions = 10, correct_answers = 8 WHERE subject = ?",
            ("Ciências da Natureza",),
        )
        conn.execute(
            "INSERT INTO study_notes (subject, title, content) VALUES (?, ?, ?)",
            ("Matemática", "Funcoes", "Funcao afim tem taxa de variacao constante."),
        )
        note_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO flashcards (note_id, front, back) VALUES (?, ?, ?)",
            (note_id, "O que e funcao afim?", "Modelo com taxa constante."),
        )
        conn.commit()

    rec = svc.get_study_recommendations()

    assert rec["overall"]["questions"] >= 20
    assert rec["flashcards_due"] >= 1
    assert rec["weak_subjects"][0]["subject"] == "Matemática"
    assert rec["weak_subjects"][0]["accuracy"] == 30
    assert any("flashcards" in action.lower() for action in rec["next_actions"])


def test_update_habit_changes_name_and_days(tmp_path):
    db = NexusDatabase(db_path=str(tmp_path / "habit_update.db"))
    hid = db.add_habit("Academia", "Treino diario", 100, "[1, 3, 5]")

    updated = db.update_habit(hid, name="Musculacao", xp_reward=120, days_of_week="[0, 2, 4]")

    assert updated is not None
    assert updated["name"] == "Musculacao"
    assert updated["xp_reward"] == 120
    assert updated["days_of_week"] == "[0, 2, 4]"
    assert updated["description"] == "Treino diario"


def test_desktop_bridge_updates_habit(tmp_path, monkeypatch):
    from src.ui import nexus_desktop_bridge as bridge

    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "bridge_habit_update.db"))
    hid = svc.db.add_habit("Corrida", "30min", 60, "[1, 2, 3, 4, 5]")
    monkeypatch.setattr(bridge, "get_nexus_service", lambda: svc)

    result = json.loads(
        bridge.nexus_bridge_call(
            "habit_update",
            json.dumps({
                "habit_id": hid,
                "name": "Corrida matinal",
                "xp_reward": 80,
                "days_of_week": [1, 3, 5],
            }),
        )
    )

    assert result["ok"]
    habit = next(h for h in svc.db.get_habits() if h["id"] == hid)
    assert habit["name"] == "Corrida matinal"
    assert habit["xp_reward"] == 80


def test_nexus_manager_understands_edit_habit_days(tmp_path, monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "manager_habit_update.db"))
    svc.db.add_habit("Academia", "Treino", 100, "[0, 1, 2, 3, 4, 5, 6]")
    manager = NexusManagerSkill(svc)

    msg = manager.handle_command("mude academia para segunda quarta sexta")

    assert msg is not None
    habit = next(h for h in svc.db.get_habits() if "Academia" in h["name"])
    days = json.loads(habit["days_of_week"])
    assert 0 in days  # segunda
    assert 2 in days  # quarta
    assert 4 in days  # sexta


def test_nexus_manager_understands_compound_finance_habit_and_open(tmp_path, monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "compound.db"))
    manager = NexusManagerSkill(svc)

    msg = manager.handle_command(
        "jarvis, adicione o gasto de 500 reais em alimentação, "
        "adicione o hábito de caminhar às 14 horas, e abra a janela de estudos"
    )

    assert msg is not None
    assert "3" in msg
    assert [module for module, _ in calls] == ["finance", "habits", "notes"]
    assert svc.db.list_finance_transactions(None, None)[0]["category"].lower().startswith("alimenta")
    habit = next(h for h in svc.db.get_habits() if h["name"] == "Caminhar")
    assert "14:00" in habit["description"]


def test_nexus_manager_opens_requested_panel_by_natural_name(monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    manager = NexusManagerSkill(NexusService())

    assert manager.handle_command("abra o painel de hábitos")
    assert calls[-1][0] == "habits"

    assert manager.handle_command("abra a janela de finanças")
    assert calls[-1][0] == "finance"

    assert manager.handle_command("mostre a janela de estudos")
    assert calls[-1][0] == "notes"


def test_nexus_manager_preserves_compound_spoken_order(tmp_path, monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "compound_order.db"))
    manager = NexusManagerSkill(svc)

    msg = manager.handle_command(
        "jarvis, abra a janela de estudos, adicione o gasto de 20 reais em lanche"
    )

    assert msg is not None
    assert [module for module, _ in calls] == ["notes", "finance"]


def test_add_reward_creates_custom_reward(tmp_path):
    db = NexusDatabase(db_path=str(tmp_path / "reward_add.db"))
    rid = db.add_reward("Sorvete", 100, "Sorvete no final do dia")

    assert rid is not None
    rewards = db.list_rewards()
    custom = next(r for r in rewards if r["name"] == "Sorvete")
    assert custom["cost"] == 100
    assert custom["description"] == "Sorvete no final do dia"


def test_update_reward_changes_cost(tmp_path):
    db = NexusDatabase(db_path=str(tmp_path / "reward_update.db"))
    rid = db.add_reward("Cinema", 500, "Sessão de cinema")

    updated = db.update_reward(rid, cost=350)

    assert updated is not None
    assert updated["cost"] == 350
    assert updated["name"] == "Cinema"


def test_delete_reward_removes_entry(tmp_path):
    db = NexusDatabase(db_path=str(tmp_path / "reward_delete.db"))
    rid = db.add_reward("Folga", 1000, "Dia de folga")

    db.delete_reward(rid)

    rewards = db.list_rewards()
    assert not any(r["id"] == rid for r in rewards)


def test_bridge_reward_crud(tmp_path, monkeypatch):
    from src.ui import nexus_desktop_bridge as bridge

    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "bridge_reward_crud.db"))
    monkeypatch.setattr(bridge, "get_nexus_service", lambda: svc)

    added = json.loads(
        bridge.nexus_bridge_call(
            "reward_add",
            json.dumps({"name": "Sorvete", "cost": 150, "description": "Delícia"}),
        )
    )
    assert added["ok"]
    rid = added["data"]["id"]

    updated = json.loads(
        bridge.nexus_bridge_call(
            "reward_update",
            json.dumps({"reward_id": rid, "cost": 200}),
        )
    )
    assert updated["ok"]
    assert updated["data"]["reward"]["cost"] == 200

    deleted = json.loads(
        bridge.nexus_bridge_call(
            "reward_delete",
            json.dumps({"reward_id": rid}),
        )
    )
    assert deleted["ok"]


def test_capture_note_creates_note_with_source(tmp_path):
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "capture_note.db"))

    nid = svc.capture_note(
        title="Python Tips",
        content="Always use virtual environments.",
        url="https://python.org",
        subject="Programação"
    )

    assert nid > 0
    note = svc.db.get_study_note(nid)
    assert note["subject"] == "Programação"
    assert note["title"] == "Python Tips"
    assert "https://python.org" in note["content"]
    assert "Always use virtual environments." in note["content"]


def test_bridge_note_capture(tmp_path, monkeypatch):
    from src.ui import nexus_desktop_bridge as bridge

    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "bridge_note_capture.db"))
    monkeypatch.setattr(bridge, "get_nexus_service", lambda: svc)

    result = json.loads(
        bridge.nexus_bridge_call(
            "note_capture",
            json.dumps({
                "title": "Machine Learning",
                "content": "Supervised vs Unsupervised",
                "url": "https://wiki.ai",
                "subject": "IA"
            })
        )
    )

    assert result["ok"]
    assert result["data"]["note_id"] > 0
    note = svc.db.get_study_note(result["data"]["note_id"])
    assert "wiki.ai" in note["content"]
