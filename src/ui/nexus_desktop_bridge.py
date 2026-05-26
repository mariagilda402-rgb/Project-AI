"""Ponte única Nexus desktop ↔ SQLite (mesmo motor que a IA / REST)."""
from __future__ import annotations

import json
from typing import Any

from src.services.nexus_service import get_nexus_service
from src.utils.nexus_notifier import broadcast_nexus_state


def nexus_bridge_call(method: str, args_json: str = "{}") -> str:
    svc = get_nexus_service()
    args: dict[str, Any] = {}
    try:
        args = json.loads(args_json or "{}")
    except json.JSONDecodeError:
        return json.dumps({"ok": False, "error": "JSON inválido"}, ensure_ascii=False)

    def ok(data: Any = None) -> str:
        return json.dumps({"ok": True, "data": data}, ensure_ascii=False, default=str)

    def err(msg: str) -> str:
        return json.dumps({"ok": False, "error": msg}, ensure_ascii=False)

    try:
        m = (method or "").strip()

        if m == "user_stats":
            return ok(svc.db.get_user_stats())

        if m == "global_streak":
            return ok(svc.db.compute_global_streak())

        if m == "habits_list":
            return ok(svc.db.get_habits())

        if m == "habit_add":
            dow = args.get("days_of_week")
            if isinstance(dow, list):
                dow_s = json.dumps(dow)
            elif isinstance(dow, str) and dow.strip().startswith("["):
                dow_s = dow.strip()
            else:
                dow_s = None
            hid = svc.db.add_habit(
                (args.get("name") or "").strip(),
                (args.get("description") or "").strip(),
                int(args.get("xp_reward") or 50),
                dow_s,
            )
            broadcast_nexus_state(svc)
            return ok({"id": hid})

        if m == "habit_complete":
            target_date = args.get("target_date")
            msg = svc.complete_habit((args.get("habit_name") or "").strip(), target_date=target_date)
            return ok({"message": msg})

        if m == "habit_delete":
            svc.db.delete_habit(int(args["habit_id"]))
            broadcast_nexus_state(svc)
            return ok({})

        if m == "habit_update":
            hid = int(args["habit_id"])
            dow = args.get("days_of_week")
            if isinstance(dow, list):
                dow_s = json.dumps(dow)
            elif isinstance(dow, str) and dow.strip().startswith("["):
                dow_s = dow.strip()
            else:
                dow_s = None
            updated = svc.db.update_habit(
                hid,
                name=(args.get("name") or "").strip() or None,
                description=(args.get("description") or "").strip() or None,
                xp_reward=int(args["xp_reward"]) if args.get("xp_reward") not in (None, "") else None,
                days_of_week=dow_s,
            )
            broadcast_nexus_state(svc)
            return ok({"habit": updated})

        if m == "habit_history":
            days = int(args.get("days") or 30)
            year = int(args["year"]) if args.get("year") else None
            month = int(args["month"]) if args.get("month") else None
            return ok(svc.db.get_habit_history(days=days, year=year, month=month))

        if m == "presets_list":
            return ok(svc.list_lifestyle_presets())

        if m == "preset_save":
            msg = svc.save_lifestyle_preset((args.get("name") or "").strip())
            return ok({"message": msg, "presets": svc.list_lifestyle_presets()})

        if m == "preset_apply":
            msg = svc.load_lifestyle_preset((args.get("name") or "").strip())
            return ok({"message": msg, "habits": svc.db.get_habits()})

        if m == "preset_from_goals":
            msg = svc.build_lifestyle_preset_from_goals(
                args.get("goals") or args.get("objectives") or args.get("goal") or "",
                (args.get("name") or args.get("preset_name") or "").strip() or None,
            )
            return ok({"message": msg, "habits": svc.db.get_habits(), "presets": svc.list_lifestyle_presets()})

        if m == "finance_snapshot":
            y = int(args.get("year") or __import__("datetime").date.today().year)
            mo = int(args.get("month") or __import__("datetime").date.today().month)
            return ok(svc.get_finance_snapshot(year=y, month=mo))

        if m == "finance_add":
            out = svc.handle_structured_command({**args, "action": "finance_add"})
            return ok({"message": out})

        if m == "finance_update":
            has_id = bool(args.get("transaction_id"))
            result = svc.update_finance_transaction(
                transaction_id=int(args["transaction_id"]) if has_id else None,
                target_description=args.get("target_description") or args.get("match_description") or (None if has_id else args.get("description") or args.get("text")),
                target_category=args.get("target_category") or args.get("match_category") or (None if has_id else args.get("category")),
                target_type=args.get("target_type") or args.get("match_type") or (None if has_id else args.get("type")),
                target_occurred_at=args.get("target_occurred_at") or args.get("target_date") or args.get("match_date") or (None if has_id else args.get("occurred_at") or args.get("date")),
                target_amount=float(str(args.get("target_amount") or args.get("match_amount")).replace(",", ".")) if (args.get("target_amount") or args.get("match_amount")) not in (None, "") else None,
                tx_type=args.get("new_type") or (args.get("type") if has_id else None),
                amount=args.get("new_amount") if args.get("new_amount") not in (None, "") else (args.get("amount") if has_id else None),
                category=args.get("new_category") or (args.get("category") if has_id else None),
                description=args.get("new_description") or (args.get("description") if has_id else None),
                occurred_at=args.get("new_occurred_at") or args.get("new_date") or (args.get("occurred_at") if has_id else None),
                necessity=int(args.get("new_necessity") or args.get("necessity")) if (args.get("new_necessity") or args.get("necessity")) not in (None, "") and has_id else None,
                notes=args.get("new_notes") if "new_notes" in args else (args.get("notes") if has_id and "notes" in args else None),
                is_debt=int(args.get("new_is_debt") if "new_is_debt" in args else args.get("is_debt")) if (("new_is_debt" in args and args.get("new_is_debt") not in (None, "")) or (has_id and args.get("is_debt") not in (None, ""))) else None,
            )
            if result.get("ok"):
                return ok(result)
            return err(result.get("message") or "Movimento nao encontrado")

        if m == "finance_delete":
            raw_amount = args.get("amount")
            amount = None
            if raw_amount not in (None, ""):
                amount = float(str(raw_amount).replace(",", "."))
            result = svc.delete_finance_transaction(
                transaction_id=int(args["transaction_id"]) if args.get("transaction_id") else None,
                description=args.get("description") or args.get("text"),
                category=args.get("category"),
                tx_type=args.get("type"),
                occurred_at=args.get("occurred_at") or args.get("date"),
                amount=amount,
            )
            if result.get("ok"):
                return ok(result)
            return err(result.get("message") or "Movimento nao encontrado")

        if m == "notes_list":
            return ok(svc.db.list_study_notes(args.get("subject")))

        if m == "note_get":
            n = svc.db.get_study_note(int(args["note_id"]))
            return ok(n) if n else err("Nota não encontrada")

        if m == "note_save":
            msg = svc.create_note(
                (args.get("subject") or "Geral").strip(),
                (args.get("title") or "Sem título").strip(),
                (args.get("content") or "").strip(),
                args.get("media"),
                color=args.get("color"),
            )
            nid = getattr(svc, "_last_created_note_id", None)
            return ok({"message": msg, "id": nid})

        if m == "note_capture":
            nid = svc.capture_note(
                title=(args.get("title") or "Captura Rápida").strip(),
                content=(args.get("content") or "").strip(),
                url=(args.get("url") or "").strip() or None,
                subject=(args.get("subject") or "Captura").strip(),
            )
            return ok({"note_id": nid})

        if m == "news_briefing":
            return ok(
                svc.build_news_briefing(
                    args.get("query") or args.get("topic") or "",
                    limit=int(args.get("limit") or args.get("max_results") or 3),
                    results=args.get("results"),
                    open_window=False,
                )
            )

        if m == "news_history":
            return ok(svc.list_news_briefings(int(args.get("limit") or 8)))

        if m == "news_save_note":
            result = svc.save_news_item_to_note(
                item=args.get("item"),
                briefing=args.get("briefing"),
                item_index=int(args.get("item_index") or args.get("index") or 1),
                subject=args.get("subject") or "Noticias",
            )
            if result.get("ok"):
                return ok(result)
            return err(result.get("error") or "Noticia nao encontrada")

        if m == "news_followup_task":
            result = svc.create_news_followup_task(
                item=args.get("item"),
                briefing=args.get("briefing"),
                item_index=int(args.get("item_index") or args.get("index") or 1),
                due_date=args.get("due_date"),
            )
            if result.get("ok"):
                return ok(result)
            return err(result.get("error") or "Noticia nao encontrada")

        if m == "news_flashcards_generate":
            result = svc.create_news_flashcards(
                item=args.get("item"),
                briefing=args.get("briefing"),
                item_index=int(args.get("item_index") or args.get("index") or 1),
                subject=args.get("subject") or "Noticias",
                max_cards=int(args.get("max_cards") or args.get("limit") or 4),
            )
            if result.get("ok"):
                return ok(result)
            return err(result.get("error") or "Noticia nao encontrada")

        if m == "memory_graph":
            include_markdown = args.get("include_markdown", True)
            if isinstance(include_markdown, str):
                include_markdown = include_markdown.strip().lower() not in ("0", "false", "no", "nao")
            return ok(
                svc.build_memory_graph(
                    query=args.get("query") or args.get("text") or "",
                    limit=int(args.get("limit") or 120),
                    include_markdown=bool(include_markdown),
                )
            )

        if m == "memory_graph_context":
            include_markdown = args.get("include_markdown", True)
            if isinstance(include_markdown, str):
                include_markdown = include_markdown.strip().lower() not in ("0", "false", "no", "nao")
            return ok(
                svc.build_memory_graph_context(
                    query=args.get("query") or args.get("text") or args.get("question") or "",
                    limit=int(args.get("limit") or 8),
                    include_markdown=bool(include_markdown),
                )
            )

        if m == "memory_graph_export_obsidian":
            include_markdown = args.get("include_markdown", True)
            if isinstance(include_markdown, str):
                include_markdown = include_markdown.strip().lower() not in ("0", "false", "no", "nao")
            result = svc.export_memory_graph_obsidian(
                args.get("folder") or args.get("path") or "",
                query=args.get("query") or "",
                include_markdown=bool(include_markdown),
                limit=int(args.get("limit") or 160),
            )
            if result.get("ok"):
                return ok(result)
            return err(result.get("error") or "Falha ao exportar grafo.")

        if m == "memory_graph_import_obsidian":
            result = svc.import_obsidian_markdown(
                args.get("folder") or args.get("path") or "",
                subject=args.get("subject") or "Obsidian",
                limit=int(args.get("limit") or 80),
            )
            if result.get("ok"):
                return ok(result)
            return err(result.get("error") or "Falha ao importar markdown.")

        if m == "ops_dashboard":
            open_window = args.get("open_window", False)
            if isinstance(open_window, str):
                open_window = open_window.strip().lower() not in ("0", "false", "no", "nao")
            return ok(svc.build_ops_dashboard(open_window=bool(open_window)))

        if m == "ops_metric_set":
            result = svc.set_ops_metric(
                args.get("key") or args.get("metric") or args.get("name"),
                args.get("value") or args.get("amount"),
                label=args.get("label") or args.get("name"),
                unit=args.get("unit"),
                target=args.get("target"),
                trend=args.get("trend"),
                period=args.get("period"),
                notes=args.get("notes") or args.get("description"),
            )
            if result.get("ok"):
                return ok(result)
            return err(result.get("error") or "Falha ao atualizar metrica.")

        if m == "note_patch":
            nid = int(args["note_id"])
            svc.db.update_study_note(
                nid,
                title=args.get("title"),
                content=args.get("content"),
                subject=args.get("subject"),
                color=args.get("color"),
            )
            broadcast_nexus_state(svc)
            return ok({"note": svc.db.get_study_note(nid)})

        if m == "note_summarize":
            append = args.get("append_summary", args.get("append", True))
            if isinstance(append, str):
                append = append.strip().lower() not in ("0", "false", "nao", "não", "no")
            return ok(
                svc.summarize_note(
                    int(args["note_id"]),
                    append=bool(append),
                    max_sentences=int(args.get("max_sentences") or 4),
                )
            )

        if m == "note_teach":
            return ok(
                svc.teach_note(
                    int(args["note_id"]),
                    question=args.get("question") or args.get("text") or "",
                    max_points=int(args.get("max_points") or args.get("limit") or 4),
                )
            )

        if m == "subject_teach":
            return ok(
                svc.teach_subject(
                    args.get("subject") or args.get("materia") or "",
                    question=args.get("question") or args.get("text") or "",
                    max_points=int(args.get("max_points") or args.get("limit") or 6),
                )
            )

        if m == "note_attach_media":
            result = svc.attach_media_to_note(
                int(args["note_id"]),
                args.get("media_url") or args.get("url") or args.get("path") or "",
                caption=args.get("caption"),
                alt=args.get("alt"),
            )
            if result.get("error"):
                return err(result["error"])
            return ok(result)

        if m == "note_delete":
            svc.db.delete_study_note(int(args["note_id"]))
            broadcast_nexus_state(svc)
            return ok({})

        if m == "flashcards_due":
            lim = int(args.get("limit") or 30)
            return ok(svc.db.list_flashcards_due(lim))

        if m == "flashcards_generate":
            limit = int(args.get("max_cards") or args.get("limit") or 8)
            if args.get("note_id"):
                return ok(svc.generate_flashcards_from_note(int(args["note_id"]), limit))
            return ok(
                svc.generate_flashcards_from_subject(
                    (args.get("subject") or "").strip(),
                    limit,
                )
            )

        if m == "flashcard_review":
            msg = svc.review_flashcard_sm2(int(args["card_id"]), int(args.get("quality", 4)))
            return ok({"message": msg})

        if m == "srs_add_card_manual":
            front = (args.get("front") or "").strip()
            back = (args.get("back") or "").strip()
            if not front or not back:
                return err("Frente e verso são obrigatórios.")
            msg = svc.add_flashcard(None, front, back)
            if "Erro" in msg:
                return err(msg)
            return ok({"message": msg})

        if m == "task_history":
            days = int(args.get("days") or 30)
            year = int(args["year"]) if args.get("year") else None
            month = int(args["month"]) if args.get("month") else None
            return ok(svc.db.get_task_history(days=days, year=year, month=month))

        if m == "tasks_list":
            inc = args.get("include_done")
            if isinstance(inc, str):
                inc = inc.lower() in ("1", "true", "yes")
            target_date = args.get("target_date")
            if target_date:
                # "Viagem no tempo": mostra todas as tarefas que existiam naquele dia
                rows = svc.db.list_tasks(args.get("due_date"), include_done=True)
                from datetime import date as _date
                filtered = []
                for t in rows:
                    created_d = (t.get("created_at") or "2000-01-01")[:10]
                    if created_d > target_date:
                        continue
                    done_d = (t.get("done_at") or "")[:10] if t.get("done_at") else None
                    t["_was_done"] = bool(done_d and done_d <= target_date)
                    filtered.append(t)
                return ok(filtered)
            rows = svc.db.list_tasks(args.get("due_date"), include_done=bool(inc))
            return ok(rows)

        if m == "task_add":
            tid = svc.db.add_task(
                (args.get("title") or "").strip(),
                (args.get("due_date") or "").strip() or None,
                int(args.get("points_reward") or 10),
            )
            broadcast_nexus_state(svc)
            return ok({"id": tid})

        if m == "task_complete":
            tid = int(args["task_id"])
            # Toggle: se já está feita, desfaz; senão, completa
            task_row = svc.db.list_tasks(include_done=True)
            target = next((t for t in task_row if t["id"] == tid), None)
            if target and target.get("done_at"):
                svc.db.uncomplete_task(tid)
            else:
                svc.db.complete_task(tid)
            broadcast_nexus_state(svc)
            return ok({})

        if m == "system_reset_data":
            section = str(args.get("section") or "all")
            svc.db.reset_data(section)
            broadcast_nexus_state(svc)
            return ok({"message": f"Dados de {section} resetados com sucesso."})

        if m == "task_delete":
            svc.db.delete_task(int(args["task_id"]))
            broadcast_nexus_state(svc)
            return ok({})

        if m == "goals_list":
            return ok(svc.get_goals())

        if m == "rewards_list":
            return ok(svc.get_rewards())

        if m == "goal_add":
            msg = svc.add_goal(
                (args.get("name") or "").strip(),
                ((args.get("target_date") or "").strip() or None),
            )
            return ok({"message": msg})

        if m == "goal_progress":
            msg = svc.update_goal_progress(
                (args.get("name") or "").strip(),
                int(args.get("progress") or 0),
            )
            return ok({"message": msg})

        if m == "goal_update":
            msg = svc.update_goal_progress(
                (args.get("name") or args.get("goal") or "").strip(),
                int(args.get("progress") or 0),
            )
            return ok({"message": msg})

        if m == "reward_status":
            return ok(svc.get_reward_status(int(args.get("limit") or 7)))

        if m == "reward_redeem":
            ok_flag, msg = svc.process_reward((args.get("reward_name") or "").strip())
            if ok_flag:
                return ok({"message": msg})
            return err(msg)

        if m == "reward_add":
            rid = svc.add_reward(
                name=(args.get("name") or "").strip(),
                cost=int(args.get("cost") or 0),
                description=(args.get("description") or "").strip(),
            )
            return ok({"id": rid})

        if m == "reward_update":
            updated = svc.update_reward(
                reward_id=int(args["reward_id"]),
                name=(args.get("name") or "").strip() or None,
                cost=int(args["cost"]) if args.get("cost") is not None else None,
                description=(args.get("description") or "").strip() or None,
            )
            return ok({"reward": updated})

        if m == "reward_delete":
            svc.delete_reward(int(args["reward_id"]))
            return ok({})

        if m == "quiz_attempt_start":
            aid = svc.db.start_quiz_attempt(args.get("area"))
            return ok({"attempt_id": aid})

        if m == "quiz_attempt_answer":
            svc.db.add_quiz_answer(
                int(args["attempt_id"]),
                int(args["question_id"]),
                int(args["chosen_index"]),
                1 if int(args.get("correct") or 0) else 0,
            )
            return ok({})

        if m == "quiz_attempt_finish":
            svc.db.finish_quiz_attempt(
                int(args["attempt_id"]),
                float(args.get("score_pct") or 0.0),
            )
            return ok({})

        if m == "quiz_attempt_review":
            return ok(svc.review_quiz_attempt(int(args["attempt_id"])))

        if m == "quiz_flashcards_generate":
            only_wrong = args.get("only_wrong", True)
            if isinstance(only_wrong, str):
                only_wrong = only_wrong.strip().lower() not in ("0", "false", "no", "nao")
            return ok(
                svc.generate_flashcards_from_quiz_attempt(
                    int(args["attempt_id"]),
                    only_wrong=bool(only_wrong),
                    max_cards=int(args.get("max_cards") or args.get("limit") or 8),
                )
            )

        if m == "study_log_result":
            msg = svc.log_study_result(
                (args.get("subject") or "Geral").strip(),
                bool(args.get("correct", True)),
            )
            return ok({"message": msg})

        if m == "study_stats_list":
            return ok(svc.get_study_stats())

        if m == "study_recommendations":
            return ok(svc.get_study_recommendations(int(args.get("limit") or 4)))

        if m == "quiz_sample":
            svc.db.seed_quiz_if_empty()
            rows = svc.db.random_quiz_questions(int(args.get("n") or 5), args.get("area"))
            for r in rows:
                r["options"] = json.loads(r.get("options_json") or "[]")
                r.pop("options_json", None)
            return ok(rows)


        return err(f"Método desconhecido: {m}")
    except Exception as e:
        return err(str(e))
