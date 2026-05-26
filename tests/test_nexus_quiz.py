import json

from src.database.nexus_db import NexusDatabase
from src.services.nexus_service import NexusService


def test_quiz_seed_has_enem_like_metadata_and_explanations(tmp_path):
    db = NexusDatabase(db_path=str(tmp_path / "quiz_seed.db"))
    db.seed_quiz_if_empty()

    rows = db.random_quiz_questions(20, None)

    assert len(rows) >= 10
    assert any(r["area"] == "Ciências Humanas" for r in rows)
    assert all(r.get("explanation") for r in rows)
    assert all(r.get("skill") for r in rows)
    assert all(r.get("difficulty") for r in rows)
    assert any("ENEM" in (r.get("source") or "") for r in rows)


def test_quiz_attempt_review_explains_mistakes_and_next_actions(tmp_path, monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "quiz_review.db"))
    svc.db.seed_quiz_if_empty()
    q = svc.db.random_quiz_questions(1, "Matemática")[0]
    options = json.loads(q["options_json"])
    wrong = 0 if q["correct_index"] != 0 else 1
    attempt_id = svc.db.start_quiz_attempt("Matemática")
    svc.db.add_quiz_answer(attempt_id, q["id"], wrong, 0)
    svc.db.finish_quiz_attempt(attempt_id, 0)

    review = svc.review_quiz_attempt(attempt_id)

    assert review["attempt_id"] == attempt_id
    assert review["score_pct"] == 0
    assert review["wrong_count"] == 1
    assert review["items"][0]["chosen_option"] == options[wrong]
    assert review["items"][0]["correct_option"] == options[q["correct_index"]]
    assert review["items"][0]["explanation"]
    assert review["items"][0]["skill"] == q["skill"]
    assert any("flashcards" in action.lower() for action in review["next_actions"])
    assert calls[-1][0] == "quiz"
    assert calls[-1][1]["animate"] == "quiz_review"


def test_desktop_bridge_returns_quiz_attempt_review(tmp_path, monkeypatch):
    from src.ui import nexus_desktop_bridge as bridge

    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "bridge_quiz_review.db"))
    svc.db.seed_quiz_if_empty()
    q = svc.db.random_quiz_questions(1, "Português")[0]
    wrong = 0 if q["correct_index"] != 0 else 1
    attempt_id = svc.db.start_quiz_attempt("Português")
    svc.db.add_quiz_answer(attempt_id, q["id"], wrong, 0)
    svc.db.finish_quiz_attempt(attempt_id, 0)
    monkeypatch.setattr(bridge, "get_nexus_service", lambda: svc)

    raw = bridge.nexus_bridge_call(
        "quiz_attempt_review", json.dumps({"attempt_id": attempt_id})
    )
    payload = json.loads(raw)

    assert payload["ok"]
    assert payload["data"]["wrong_count"] == 1
    assert payload["data"]["items"][0]["explanation"]


def test_structured_command_returns_quiz_attempt_review(tmp_path):
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "structured_quiz_review.db"))
    svc.db.seed_quiz_if_empty()
    q = svc.db.random_quiz_questions(1, None)[0]
    wrong = 0 if q["correct_index"] != 0 else 1
    attempt_id = svc.db.start_quiz_attempt(q["area"])
    svc.db.add_quiz_answer(attempt_id, q["id"], wrong, 0)
    svc.db.finish_quiz_attempt(attempt_id, 0)

    raw = svc.handle_structured_command(
        {"action": "quiz_attempt_review", "attempt_id": attempt_id}
    )
    review = json.loads(raw)

    assert review["attempt_id"] == attempt_id
    assert review["wrong_count"] == 1
    assert review["items"][0]["correct_option"]


def test_quiz_flashcards_from_wrong_answers_create_due_cards(tmp_path, monkeypatch):
    calls = []

    def fake_enqueue(module, payload=None):
        calls.append((module, payload or {}))

    monkeypatch.setattr("src.ui.nexus_signals.enqueue_nexus_desktop_open", fake_enqueue)
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "quiz_flashcards.db"))
    svc.db.seed_quiz_if_empty()
    q = svc.db.random_quiz_questions(1, None)[0]
    wrong = 0 if q["correct_index"] != 0 else 1
    attempt_id = svc.db.start_quiz_attempt(q["area"])
    svc.db.add_quiz_answer(attempt_id, q["id"], wrong, 0)
    svc.db.finish_quiz_attempt(attempt_id, 0)

    result = svc.generate_flashcards_from_quiz_attempt(attempt_id, only_wrong=True, max_cards=5)
    due = svc.db.list_flashcards_due(10)

    assert result["attempt_id"] == attempt_id
    assert result["created"] == 1
    assert result["cards"][0]["question_id"] == q["id"]
    assert result["cards"][0]["front"]
    assert result["cards"][0]["back"]
    assert due
    assert due[0]["note_id"] is None
    assert q["stem"][:40] in due[0]["front"]
    assert result["cards"][0]["correct_option"] in due[0]["back"]
    assert calls[-1][0] == "quiz"
    assert calls[-1][1]["animate"] == "quiz_flashcards_generate"


def test_quiz_flashcards_generation_is_idempotent_for_same_attempt(tmp_path):
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "quiz_flashcards_idempotent.db"))
    svc.db.seed_quiz_if_empty()
    q = svc.db.random_quiz_questions(1, None)[0]
    wrong = 0 if q["correct_index"] != 0 else 1
    attempt_id = svc.db.start_quiz_attempt(q["area"])
    svc.db.add_quiz_answer(attempt_id, q["id"], wrong, 0)
    svc.db.finish_quiz_attempt(attempt_id, 0)

    first = svc.generate_flashcards_from_quiz_attempt(attempt_id)
    second = svc.generate_flashcards_from_quiz_attempt(attempt_id)

    assert first["created"] == 1
    assert second["created"] == 0
    assert len(svc.db.list_flashcards_due(10)) == 1


def test_desktop_bridge_generates_quiz_flashcards(tmp_path, monkeypatch):
    from src.ui import nexus_desktop_bridge as bridge

    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "bridge_quiz_flashcards.db"))
    svc.db.seed_quiz_if_empty()
    q = svc.db.random_quiz_questions(1, None)[0]
    wrong = 0 if q["correct_index"] != 0 else 1
    attempt_id = svc.db.start_quiz_attempt(q["area"])
    svc.db.add_quiz_answer(attempt_id, q["id"], wrong, 0)
    svc.db.finish_quiz_attempt(attempt_id, 0)
    monkeypatch.setattr(bridge, "get_nexus_service", lambda: svc)

    raw = bridge.nexus_bridge_call(
        "quiz_flashcards_generate",
        json.dumps({"attempt_id": attempt_id, "only_wrong": True, "max_cards": 3}),
    )
    payload = json.loads(raw)

    assert payload["ok"]
    assert payload["data"]["created"] == 1
    assert svc.db.list_flashcards_due(10)


def test_structured_command_generates_quiz_flashcards(tmp_path):
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "structured_quiz_flashcards.db"))
    svc.db.seed_quiz_if_empty()
    q = svc.db.random_quiz_questions(1, None)[0]
    wrong = 0 if q["correct_index"] != 0 else 1
    attempt_id = svc.db.start_quiz_attempt(q["area"])
    svc.db.add_quiz_answer(attempt_id, q["id"], wrong, 0)
    svc.db.finish_quiz_attempt(attempt_id, 0)

    raw = svc.handle_structured_command(
        {
            "action": "quiz_flashcards_generate",
            "attempt_id": attempt_id,
            "only_wrong": True,
            "max_cards": 3,
        }
    )
    result = json.loads(raw)

    assert result["attempt_id"] == attempt_id
    assert result["created"] == 1
    assert result["cards"][0]["skill"]


def test_quiz_modes_filter_by_count(tmp_path):
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "quiz_modes.db"))
    svc.db.seed_quiz_if_empty()

    # The random_quiz_questions accepts n
    q10 = svc.db.random_quiz_questions(10, None)
    assert len(q10) <= 10

    q5 = svc.db.random_quiz_questions(5, None)
    assert len(q5) == 5

def test_quiz_result_breakdown_by_area(tmp_path):
    svc = NexusService()
    svc.db = NexusDatabase(db_path=str(tmp_path / "quiz_breakdown.db"))
    svc.db.seed_quiz_if_empty()

    aid = svc.db.start_quiz_attempt(None)
    questions = svc.db.random_quiz_questions(2, None)
    if len(questions) >= 2:
        svc.db.add_quiz_answer(aid, questions[0]["id"], 0, 1)
        svc.db.add_quiz_answer(aid, questions[1]["id"], 1, 0)
    svc.db.finish_quiz_attempt(aid, 50.0)

    review = svc.review_quiz_attempt(aid)
    assert "breakdown" in review
    assert isinstance(review["breakdown"], dict)
