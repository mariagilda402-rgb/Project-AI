"""Rotas HTTP REST do Nexus no processo do visualizador Flask."""
from __future__ import annotations

import json
from pathlib import Path

from flask import jsonify, request

from src.services.nexus_service import get_nexus_service
from src.utils.nexus_notifier import broadcast_nexus_state


def _log(ev: str, payload: dict) -> None:
    try:
        from src.telemetry.events import log_event

        log_event(ev, payload)
    except Exception:
        pass


def register_nexus_routes(app) -> None:
    svc = get_nexus_service()

    @app.route("/api/nexus/finance", methods=["GET", "OPTIONS"])
    def nexus_finance_get():
        if request.method == "OPTIONS":
            return "", 204
        y = request.args.get("year", type=int)
        m = request.args.get("month", type=int)
        df = request.args.get("from")
        dt = request.args.get("to")
        if df or dt:
            rows = svc.db.list_finance_transactions(df, dt)
            return jsonify({"transactions": rows})
        snap = svc.get_finance_snapshot(year=y, month=m)
        return jsonify(snap)

    @app.route("/api/nexus/finance", methods=["POST"])
    def nexus_finance_post():
        data = request.get_json(silent=True) or {}
        action = (data.get("action") or "finance_add").lower()
        out = svc.handle_structured_command({**data, "action": action})
        _log("nexus_finance", {"action": action, "ok": True})
        return jsonify({"ok": True, "message": out})

    @app.route("/api/nexus/notes", methods=["GET", "OPTIONS"])
    def nexus_notes_list():
        if request.method == "OPTIONS":
            return "", 204
        sub = request.args.get("subject")
        rows = svc.db.list_study_notes(sub)
        return jsonify({"notes": rows})

    @app.route("/api/nexus/notes/<int:nid>", methods=["GET", "PATCH", "DELETE", "OPTIONS"])
    def nexus_note_one(nid: int):
        if request.method == "OPTIONS":
            return "", 204
        if request.method == "GET":
            n = svc.db.get_study_note(nid)
            return jsonify(n) if n else ("", 404)
        if request.method == "DELETE":
            svc.db.delete_study_note(nid)
            _log("study_note_edit", {"action": "delete", "note_id": nid})
            broadcast_nexus_state(svc)
            return jsonify({"ok": True})
        data = request.get_json(silent=True) or {}
        svc.db.update_study_note(
            nid,
            title=data.get("title"),
            content=data.get("content"),
            subject=data.get("subject"),
        )
        _log("study_note_edit", {"action": "patch", "note_id": nid})
        broadcast_nexus_state(svc)
        return jsonify({"ok": True, "note": svc.db.get_study_note(nid)})

    @app.route("/api/nexus/notes", methods=["POST"])
    def nexus_notes_create():
        data = request.get_json(silent=True) or {}
        msg = svc.create_note(
            (data.get("subject") or "Geral").strip(),
            (data.get("title") or "Sem titulo").strip(),
            (data.get("content") or "").strip(),
            data.get("media"),
        )
        _log("study_note_edit", {"action": "create"})
        return jsonify({"ok": True, "message": msg})

    @app.route("/api/nexus/flashcards/due", methods=["GET"])
    def nexus_fc_due():
        lim = request.args.get("limit", default=30, type=int)
        rows = svc.db.list_flashcards_due(lim)
        return jsonify({"cards": rows})

    @app.route("/api/nexus/flashcards/review", methods=["POST"])
    def nexus_fc_review():
        data = request.get_json(silent=True) or {}
        msg = svc.review_flashcard_sm2(
            int(data.get("card_id")),
            int(data.get("quality", 4)),
        )
        _log("study_flashcard_review", {"card_id": data.get("card_id")})
        return jsonify({"ok": True, "message": msg})

    @app.route("/api/nexus/tasks", methods=["GET"])
    def nexus_tasks_get():
        due = request.args.get("due")
        inc = request.args.get("include_done", "").lower() in ("1", "true", "yes")
        return jsonify({"tasks": svc.db.list_tasks(due, include_done=inc)})

    @app.route("/api/nexus/tasks", methods=["POST"])
    def nexus_tasks_post():
        data = request.get_json(silent=True) or {}
        tid = svc.db.add_task(
            (data.get("title") or "").strip(),
            (data.get("due_date") or "").strip() or None,
            int(data.get("points_reward") or 10),
        )
        broadcast_nexus_state(svc)
        return jsonify({"ok": True, "id": tid})

    @app.route("/api/nexus/tasks/<int:tid>/complete", methods=["POST"])
    def nexus_tasks_complete(tid: int):
        svc.db.complete_task(tid)
        broadcast_nexus_state(svc)
        return jsonify({"ok": True})

    @app.route("/api/nexus/tasks/<int:tid>", methods=["DELETE"])
    def nexus_tasks_delete(tid: int):
        svc.db.delete_task(tid)
        broadcast_nexus_state(svc)
        return jsonify({"ok": True})

    @app.route("/api/nexus/quiz/sample", methods=["GET"])
    def nexus_quiz_sample():
        svc.db.seed_quiz_if_empty()
        n = request.args.get("n", default=5, type=int)
        area = request.args.get("area")
        rows = svc.db.random_quiz_questions(n, area)
        for r in rows:
            r["options"] = json.loads(r.get("options_json") or "[]")
            r.pop("options_json", None)
        return jsonify({"questions": rows})

    @app.route("/api/nexus/active_note", methods=["GET", "POST"])
    def nexus_active_note():
        path = Path("data/nexus_active_note.json")
        if request.method == "GET":
            if not path.exists():
                return jsonify({"note_id": None})
            return jsonify(json.loads(path.read_text(encoding="utf-8")))
        data = request.get_json(silent=True) or {}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return jsonify({"ok": True})
