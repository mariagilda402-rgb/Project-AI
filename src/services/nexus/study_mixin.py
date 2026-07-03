from src.database.nexus_db import NexusDatabase
from src.utils.nexus_notifier import broadcast_nexus_state, log_nexus_event
import logging
from datetime import datetime, date, timedelta
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

_SUBJECT_ALIASES = {
    "geral": "Geral",
    "matemática": "Matemática",
    "matematica": "Matemática",
    "português": "Português",
    "portugues": "Português",
    "natureza": "Ciências da Natureza",
    "ciências da natureza": "Ciências da Natureza",
    "humanas": "Ciências Humanas",
    "ciências humanas": "Ciências Humanas",
}

_NEXUS_WINDOW_MODULES = {
    "overview": "Visao geral",
    "habits": "Habitos",
    "finance": "Financas",
    "notes": "MindPalace",
    "memory_graph": "Grafo neural",
    "study": "SRS",
    "tasks": "Tarefas",
    "progress": "Progresso",
    "goals": "Metas e recompensas",
    "quiz": "Quiz",
    "news": "Noticias",
    "ops": "Operacoes",
}

_NEXUS_WINDOW_MODULE_ALIASES = {
    "dashboard": "overview",
    "home": "overview",
    "inicio": "overview",
    "visao geral": "overview",
    "habito": "habits",
    "habitos": "habits",
    "rotina": "habits",
    "financa": "finance",
    "financas": "finance",
    "financeiro": "finance",
    "aether": "finance",
    "nota": "notes",
    "notas": "notes",
    "mindpalace": "notes",
    "grafo": "memory_graph",
    "grafo neural": "memory_graph",
    "memoria": "memory_graph",
    "memorias": "memory_graph",
    "rede neural": "memory_graph",
    "neural": "memory_graph",
    "estudo": "notes",
    "estudos": "notes",
    "flashcard": "study",
    "flashcards": "study",
    "srs": "study",
    "board": "tasks",
    "tarefa": "tasks",
    "tarefas": "tasks",
    "progresso": "progress",
    "meta": "goals",
    "metas": "goals",
    "loja": "goals",
    "recompensa": "goals",
    "recompensas": "goals",
    "simulado": "quiz",
    "simulados": "quiz",
    "news": "news",
    "noticia": "news",
    "noticias": "news",
    "manchete": "news",
    "manchetes": "news",
    "jornal": "news",
    "ops": "ops",
    "business": "ops",
    "negocios": "ops",
    "negócios": "ops",
    "operacoes": "ops",
    "operações": "ops",
    "dashboard ops": "ops",
    "painel ops": "ops",
}

_NEXUS_THEME_TOKEN_KEYS = {
    "--bg",
    "--bg-panel",
    "--surface",
    "--surface-hover",
    "--border",
    "--border-accent",
    "--text",
    "--text-dim",
    "--text-muted",
    "--muted",
    "--accent",
    "--accent-hover",
    "--accent-glow",
    "--accent-subtle",
    "--danger",
    "--success",
    "--warning",
    "--sidebar",
    "--shadow",
}

_DEFAULT_WINDOW_THEME_ID = "dark-neon"

_DEFAULT_WINDOW_THEME_PRESETS = {
    "dark-neon": {
        "id": "dark-neon",
        "name": "Dark Neon",
        "mode": "dark",
        "description": "Base escura Nexus com roxo e ciano.",
        "tokens": {
            "--bg": "#0a0a0a",
            "--bg-panel": "#111111",
            "--surface": "rgba(255,255,255,0.04)",
            "--surface-hover": "rgba(255,255,255,0.08)",
            "--border": "rgba(255,255,255,0.08)",
            "--border-accent": "rgba(139,92,246,0.35)",
            "--text": "#e4e4e7",
            "--text-dim": "#71717a",
            "--text-muted": "#52525b",
            "--muted": "#71717a",
            "--accent": "#8b5cf6",
            "--accent-hover": "#7c3aed",
            "--accent-glow": "rgba(139,92,246,0.30)",
            "--accent-subtle": "rgba(139,92,246,0.08)",
            "--sidebar": "#080808",
            "--shadow": "0 0 25px rgba(0,0,0,0.80)",
        },
    },
    "light-crystal": {
        "id": "light-crystal",
        "name": "Light Crystal",
        "mode": "light",
        "description": "Tema claro limpo com acento violeta.",
        "tokens": {
            "--bg": "#f6f8fc",
            "--bg-panel": "#ffffff",
            "--surface": "rgba(15,23,42,0.045)",
            "--surface-hover": "rgba(15,23,42,0.08)",
            "--border": "rgba(15,23,42,0.12)",
            "--border-accent": "rgba(6,182,212,0.34)",
            "--text": "#111827",
            "--text-dim": "#5b6475",
            "--text-muted": "#7a8496",
            "--muted": "#6b7280",
            "--accent": "#7c3aed",
            "--accent-hover": "#6d28d9",
            "--accent-glow": "rgba(6,182,212,0.24)",
            "--accent-subtle": "rgba(124,58,237,0.08)",
            "--sidebar": "#eef2ff",
            "--shadow": "0 22px 55px rgba(15,23,42,0.20)",
        },
    },
    "emerald-ledger": {
        "id": "emerald-ledger",
        "name": "Emerald Ledger",
        "mode": "dark",
        "description": "Verde financeiro para Aether e rotinas de dinheiro.",
        "tokens": {
            "--bg": "#03130f",
            "--bg-panel": "#071b16",
            "--surface": "rgba(16,185,129,0.08)",
            "--surface-hover": "rgba(16,185,129,0.14)",
            "--border": "rgba(110,231,183,0.14)",
            "--border-accent": "rgba(16,185,129,0.46)",
            "--text": "#e6fff5",
            "--text-dim": "#8dcfba",
            "--text-muted": "#5f8f81",
            "--muted": "#7bb09f",
            "--accent": "#10b981",
            "--accent-hover": "#059669",
            "--accent-glow": "rgba(16,185,129,0.32)",
            "--accent-subtle": "rgba(16,185,129,0.10)",
            "--sidebar": "#020b08",
            "--shadow": "0 0 34px rgba(16,185,129,0.16)",
        },
    },
    "study-cyan": {
        "id": "study-cyan",
        "name": "Study Cyan",
        "mode": "dark",
        "description": "Azul frio para foco, SRS e MindPalace.",
        "tokens": {
            "--bg": "#06111f",
            "--bg-panel": "#091827",
            "--surface": "rgba(56,189,248,0.08)",
            "--surface-hover": "rgba(56,189,248,0.14)",
            "--border": "rgba(125,211,252,0.15)",
            "--border-accent": "rgba(56,189,248,0.46)",
            "--text": "#eef8ff",
            "--text-dim": "#9cc9df",
            "--text-muted": "#6f93a6",
            "--muted": "#8ab2c6",
            "--accent": "#38bdf8",
            "--accent-hover": "#0ea5e9",
            "--accent-glow": "rgba(56,189,248,0.30)",
            "--accent-subtle": "rgba(56,189,248,0.10)",
            "--sidebar": "#030914",
            "--shadow": "0 0 34px rgba(14,165,233,0.16)",
        },
    },
    "solar-premium": {
        "id": "solar-premium",
        "name": "Solar Premium",
        "mode": "light",
        "description": "Claro dourado para revisoes e planejamento calmo.",
        "tokens": {
            "--bg": "#fbfaf5",
            "--bg-panel": "#fffdf7",
            "--surface": "rgba(180,83,9,0.055)",
            "--surface-hover": "rgba(180,83,9,0.095)",
            "--border": "rgba(120,53,15,0.14)",
            "--border-accent": "rgba(245,158,11,0.48)",
            "--text": "#231a10",
            "--text-dim": "#6d5a43",
            "--text-muted": "#927f66",
            "--muted": "#78644d",
            "--accent": "#f59e0b",
            "--accent-hover": "#d97706",
            "--accent-glow": "rgba(245,158,11,0.28)",
            "--accent-subtle": "rgba(245,158,11,0.12)",
            "--sidebar": "#f7efe0",
            "--shadow": "0 22px 55px rgba(120,53,15,0.16)",
        },
    },
}




class NexusStudyMixin:
    def add_flashcard(self, note_id, front, back):
        """Adiciona um flashcard a uma nota específica."""
        try:
            with self.db._get_connection() as conn:
                conn.execute("""
                    INSERT INTO flashcards (note_id, front, back)
                    VALUES (?, ?, ?)
                """, (note_id, front, back))
                conn.commit()
            log_nexus_event(f"MINDPALACE: Flashcard gerado.")
            return "Flashcard adicionado com sucesso."
        except Exception as e:
            logger.error(f"Erro ao adicionar flashcard: {e}")
            return "Erro ao criar flashcard."

    def _study_lines(self, content: str) -> list[tuple[str, str]]:
        lines: list[tuple[str, str]] = []
        for raw in (content or "").splitlines():
            text = raw.strip()
            if not text:
                continue
            if text.startswith("#"):
                heading = text.lstrip("#").strip()
                if heading:
                    lines.append(("heading", heading))
                continue
            chunks = re.split(r"\s+-\s+", text)
            for chunk in chunks:
                item = chunk.strip().lstrip("-*").strip()
                if item:
                    kind = "bullet" if text.startswith(("-", "*")) or chunk != chunks[0] else "text"
                    lines.append((kind, item))
        return lines

    def _flashcard_candidates_from_note(self, note: dict, max_cards: int = 8) -> list[dict]:
        title = (note.get("title") or "Nota").strip()
        lines = self._study_lines(note.get("content") or "")
        cards: list[dict] = []
        seen: set[str] = set()

        def add(front: str, back: str) -> None:
            front = re.sub(r"\s+", " ", front).strip()
            back = re.sub(r"\s+", " ", back).strip()
            key = front.lower()
            if not front or not back or key in seen or len(cards) >= max_cards:
                return
            seen.add(key)
            cards.append({"front": front[:220], "back": back[:600]})

        for idx, (kind, text) in enumerate(lines):
            if len(cards) >= max_cards:
                break
            if kind == "heading":
                answer = next((line for k, line in lines[idx + 1 :] if k != "heading"), title)
                add(f"O que estudar em {text}?", answer)
                continue
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
            for sentence in sentences or [text]:
                topic = self._topic_from_fact(sentence, title)
                if kind == "bullet":
                    add(f"O que lembrar sobre {topic}?", sentence)
                else:
                    add(f"Qual e a ideia central de {topic}?", sentence)
                if len(cards) >= max_cards:
                    break

        if not cards and title:
            add(f"Qual e o resumo de {title}?", note.get("content") or f"Revisar {title}.")
        return cards

    def _insert_flashcards(self, note_id: int | None, cards: list[dict]) -> list[dict]:
        created: list[dict] = []
        with self.db._get_connection() as conn:
            if note_id is None:
                rows = conn.execute("SELECT front FROM flashcards WHERE note_id IS NULL").fetchall()
            else:
                rows = conn.execute(
                    "SELECT front FROM flashcards WHERE note_id = ?",
                    (note_id,),
                ).fetchall()
            existing = {row[0] for row in rows}
            for card in cards:
                if card["front"] in existing:
                    continue
                cur = conn.execute(
                    """
                    INSERT INTO flashcards (note_id, front, back)
                    VALUES (?, ?, ?)
                    """,
                    (note_id, card["front"], card["back"]),
                )
                created.append({**card, "id": cur.lastrowid, "note_id": note_id})
                existing.add(card["front"])
            conn.commit()
        return created

    def generate_flashcards_from_note(self, note_id: int, max_cards: int = 8) -> dict:
        """Gera flashcards SRS a partir do conteudo de uma nota."""
        note = self.db.get_study_note(int(note_id))
        if not note:
            return {"note_id": note_id, "created": 0, "cards": [], "error": "Nota nao encontrada."}
        limit = max(1, min(20, int(max_cards or 8)))
        cards = self._flashcard_candidates_from_note(note, limit)
        created = self._insert_flashcards(int(note_id), cards)
        msg = f"{len(created)} flashcards gerados para {note.get('title') or 'nota'}."
        log_nexus_event(f"MINDPALACE: {msg}")
        if created:
            broadcast_nexus_state(self)
        self._open_desktop_receipt(
            "study",
            {
                "animate": "flashcards_generate",
                "toast": msg,
                "note_id": int(note_id),
                "created": len(created),
            },
        )
        return {"note_id": int(note_id), "created": len(created), "cards": created}

    def generate_flashcards_from_subject(self, subject: str, max_cards: int = 20) -> dict:
        """Gera flashcards para todas as notas de uma materia/assunto."""
        subject_name = (subject or "").strip()
        notes = self.db.list_study_notes(subject_name or None)
        total = 0
        created_cards: list[dict] = []
        remaining = max(1, min(50, int(max_cards or 20)))
        for note in notes:
            if subject_name and (note.get("subject") or "") != subject_name:
                continue
            result = self.generate_flashcards_from_note(note["id"], remaining)
            total += int(result.get("created") or 0)
            created_cards.extend(result.get("cards") or [])
            remaining -= int(result.get("created") or 0)
            if remaining <= 0:
                break
        return {"subject": subject_name or None, "created": total, "cards": created_cards}

    def log_study_result(self, subject, correct=True):
        """Registra o resultado de uma questão de estudo."""
        key = (subject or "Geral").strip().lower()
        subject_db = _SUBJECT_ALIASES.get(key, subject)
        try:
            with self.db._get_connection() as conn:
                conn.execute("""
                    INSERT OR IGNORE INTO study_stats (subject, total_questions, correct_answers)
                    VALUES (?, 0, 0)
                """, (subject_db,))

                if correct:
                    conn.execute("""
                        UPDATE study_stats
                        SET total_questions = total_questions + 1, correct_answers = correct_answers + 1, last_attempt = CURRENT_TIMESTAMP
                        WHERE subject = ?
                    """, (subject_db,))
                else:
                    conn.execute("""
                        UPDATE study_stats
                        SET total_questions = total_questions + 1, last_attempt = CURRENT_TIMESTAMP
                        WHERE subject = ?
                    """, (subject_db,))
                conn.commit()

            xp = 30 if correct else 10
            self.db.add_xp(xp)

            status = "ACERTOU" if correct else "ERROU"
            log_nexus_event(f"ESTUDO: {subject_db} ({status})")
            broadcast_nexus_state(self)

            return f"Resultado registrado, Sir. +{xp} XP em {subject_db}."
        except Exception as e:
            logger.error(f"Erro ao registrar estudo: {e}")
            return "Falha ao salvar desempenho."

    def get_study_stats(self):
        """Retorna as estatísticas de estudo para o HUD."""
        import sqlite3
        with self.db._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM study_stats").fetchall()
            return [dict(r) for r in rows]

    def get_study_recommendations(self, limit: int = 4) -> dict:
        """Analisa desempenho e devolve proximas acoes de estudo."""
        stats = self.get_study_stats()
        total_questions = sum(int(s.get("total_questions") or 0) for s in stats)
        correct_answers = sum(int(s.get("correct_answers") or 0) for s in stats)
        overall_accuracy = round((correct_answers / total_questions) * 100) if total_questions else 0
        due_cards = self.db.list_flashcards_due(50)

        candidates = []
        for stat in stats:
            subject = stat.get("subject") or "Geral"
            total = int(stat.get("total_questions") or 0)
            correct = int(stat.get("correct_answers") or 0)
            accuracy = round((correct / total) * 100) if total else 0
            if total == 0:
                bucket = 1
                reason = "Ainda sem simulado registrado."
                action = f"Fazer 5 questoes diagnosticas de {subject}."
            elif accuracy < 50:
                bucket = 0
                reason = "Taxa de acerto critica."
                action = f"Revisar teoria e fazer uma lista curta de {subject}."
            elif accuracy < 70:
                bucket = 0
                reason = "Abaixo da meta de 70%."
                action = f"Refazer erros recentes de {subject}."
            else:
                bucket = 2
                reason = "Manter ritmo."
                action = f"Manter revisao leve de {subject}."
            candidates.append(
                {
                    "subject": subject,
                    "total": total,
                    "correct": correct,
                    "accuracy": accuracy,
                    "priority": "high" if bucket == 0 else "medium" if bucket == 1 else "low",
                    "reason": reason,
                    "suggested_action": action,
                    "_sort": (bucket, accuracy if total else 101, -total),
                }
            )

        candidates.sort(key=lambda item: item["_sort"])
        weak_subjects = []
        for item in candidates:
            item = dict(item)
            item.pop("_sort", None)
            if item["priority"] != "low" or len(weak_subjects) < limit:
                weak_subjects.append(item)
            if len(weak_subjects) >= limit:
                break

        next_actions = []
        if due_cards:
            next_actions.append(f"Revisar {len(due_cards)} flashcards pendentes hoje.")
        for item in weak_subjects[:3]:
            next_actions.append(item["suggested_action"])
        if not next_actions:
            next_actions.append("Fazer um simulado curto para atualizar o diagnostico.")

        return {
            "overall": {
                "questions": total_questions,
                "correct": correct_answers,
                "accuracy": overall_accuracy,
            },
            "flashcards_due": len(due_cards),
            "weak_subjects": weak_subjects,
            "next_actions": next_actions,
        }

    def review_quiz_attempt(self, attempt_id: int, emit_receipt: bool = True) -> dict:
        """Monta revisao do simulado com explicacao, resposta correta e acoes."""
        attempt = self.db.get_quiz_attempt(int(attempt_id))
        rows = self.db.list_quiz_attempt_answers(int(attempt_id))
        total = len(rows)
        correct_count = sum(1 for row in rows if int(row.get("correct") or 0))
        score_pct = round((correct_count / total) * 100) if total else 0
        if attempt and attempt.get("score_pct") is not None:
            try:
                score_pct = round(float(attempt.get("score_pct") or 0))
            except (TypeError, ValueError):
                pass

        items = []
        weak_skills: dict[str, int] = {}
        weak_areas: dict[str, int] = {}
        for row in rows:
            try:
                options = json.loads(row.get("options_json") or "[]")
            except (TypeError, json.JSONDecodeError):
                options = []
            chosen = int(row.get("chosen_index") or 0)
            correct_idx = int(row.get("correct_index") or 0)
            area = row.get("area") or "Geral"
            skill = row.get("skill") or area
            is_correct = bool(int(row.get("correct") or 0))
            if not is_correct:
                weak_skills[skill] = weak_skills.get(skill, 0) + 1
                weak_areas[area] = weak_areas.get(area, 0) + 1
            items.append(
                {
                    "question_id": row.get("question_id"),
                    "area": area,
                    "skill": skill,
                    "difficulty": row.get("difficulty") or "media",
                    "stem": row.get("stem") or "",
                    "chosen_index": chosen,
                    "chosen_option": options[chosen] if 0 <= chosen < len(options) else "",
                    "correct_index": correct_idx,
                    "correct_option": options[correct_idx] if 0 <= correct_idx < len(options) else "",
                    "correct": is_correct,
                    "explanation": row.get("explanation")
                    or "Revise o conceito central desta questao e tente explicar o raciocinio em voz alta.",
                    "source": row.get("source") or "",
                }
            )

        wrong_count = total - correct_count
        top_skills = sorted(weak_skills.items(), key=lambda item: (-item[1], item[0]))
        top_areas = sorted(weak_areas.items(), key=lambda item: (-item[1], item[0]))
        next_actions = []
        for skill, count in top_skills[:3]:
            next_actions.append(f"Revisar {skill} e criar flashcards dos {count} erro(s).")
        if wrong_count:
            next_actions.append("Refazer apenas as questoes erradas antes de iniciar outro simulado.")
        else:
            next_actions.append("Aumentar a dificuldade ou fazer um simulado com mais questoes.")

        breakdown = {}
        for item in items:
            area = item["area"]
            if area not in breakdown:
                breakdown[area] = {"total": 0, "correct": 0, "pct": 0}
            breakdown[area]["total"] += 1
            if item["correct"]:
                breakdown[area]["correct"] += 1

        for area, data in breakdown.items():
            data["pct"] = round((data["correct"] / data["total"]) * 100) if data["total"] else 0

        review = {
            "attempt_id": int(attempt_id),
            "area": (attempt or {}).get("area"),
            "score_pct": score_pct,
            "total": total,
            "correct_count": correct_count,
            "wrong_count": wrong_count,
            "weak_skills": [{"skill": skill, "misses": count} for skill, count in top_skills],
            "weak_areas": [{"area": area, "misses": count} for area, count in top_areas],
            "items": items,
            "breakdown": breakdown,
            "next_actions": next_actions,
        }
        if emit_receipt:
            log_nexus_event(f"QUIZ REVIEW: tentativa #{attempt_id} {score_pct}%")
            self._open_desktop_receipt(
                "quiz",
                {
                    "animate": "quiz_review",
                    "toast": f"Revisao do simulado pronta: {score_pct}%",
                    "receipt": {
                        "kind": "quiz",
                        "action": "quiz_review",
                        "attempt_id": int(attempt_id),
                        "score_pct": score_pct,
                        "wrong_count": wrong_count,
                    },
                },
            )
        return review

    def generate_flashcards_from_quiz_attempt(
        self,
        attempt_id: int,
        only_wrong: bool = True,
        max_cards: int = 8,
    ) -> dict:
        """Cria flashcards SRS a partir da revisao de um simulado."""
        if isinstance(only_wrong, str):
            only_wrong = only_wrong.strip().lower() not in ("0", "false", "no", "nao")
        limit = max(1, min(20, int(max_cards or 8)))
        review = self.review_quiz_attempt(int(attempt_id), emit_receipt=False)
        source_items = [
            item
            for item in (review.get("items") or [])
            if (not only_wrong or not item.get("correct"))
        ]

        cards: list[dict] = []
        for item in source_items[:limit]:
            skill = item.get("skill") or item.get("area") or "Geral"
            stem = " ".join(str(item.get("stem") or "").split())
            correct_option = str(item.get("correct_option") or "").strip()
            explanation = str(item.get("explanation") or "").strip()
            front = f"Quiz ENEM - {skill}: {stem}"[:220]
            back_parts = []
            if correct_option:
                back_parts.append(f"Resposta correta: {correct_option}")
            if explanation:
                back_parts.append(f"Explicacao: {explanation}")
            back_parts.append(f"Skill: {skill}")
            cards.append(
                {
                    "front": front,
                    "back": "\n\n".join(back_parts)[:600],
                    "question_id": item.get("question_id"),
                    "skill": skill,
                    "area": item.get("area") or "Geral",
                    "correct_option": correct_option,
                }
            )

        created = self._insert_flashcards(None, cards)
        msg = f"{len(created)} flashcards dos erros do simulado criados."
        log_nexus_event(f"QUIZ FLASHCARDS: tentativa #{attempt_id} {len(created)} card(s)")
        if created:
            broadcast_nexus_state(self)
        self._open_desktop_receipt(
            "quiz",
            {
                "animate": "quiz_flashcards_generate",
                "toast": msg,
                "attempt_id": int(attempt_id),
                "created": len(created),
                "only_wrong": bool(only_wrong),
            },
        )
        return {
            "attempt_id": int(attempt_id),
            "created": len(created),
            "source_count": len(source_items),
            "only_wrong": bool(only_wrong),
            "cards": created,
        }

    def _graph_flashcards(self, limit: int) -> list[dict]:
        try:
            with self.db._get_connection() as conn:
                conn.row_factory = __import__("sqlite3").Row
                rows = conn.execute(
                    """
                    SELECT f.id, f.note_id, f.front, f.back, f.next_review,
                           n.title AS note_title, n.subject
                    FROM flashcards f
                    LEFT JOIN study_notes n ON n.id = f.note_id
                    ORDER BY datetime(f.next_review) ASC, f.id DESC
                    LIMIT ?
                    """,
                    (max(1, int(limit or 30)),),
                ).fetchall()
                return [dict(r) for r in rows]
        except Exception:
            return []

    def create_news_flashcards(
        self,
        item=None,
        briefing=None,
        item_index: int = 1,
        subject: str | None = "Noticias",
        max_cards: int = 4,
    ) -> dict:
        news_item = self._select_news_item(item=item, briefing=briefing, item_index=item_index)
        if not news_item:
            return {"ok": False, "note_id": None, "created": 0, "cards": [], "error": "Noticia nao encontrada."}

        saved = self.save_news_item_to_note(
            item=news_item,
            subject=(subject or "Noticias").strip() or "Noticias",
        )
        if not saved.get("ok"):
            return {
                "ok": False,
                "note_id": saved.get("note_id"),
                "created": 0,
                "cards": [],
                "error": saved.get("error") or "Nao consegui salvar a noticia antes dos flashcards.",
            }

        limit = max(1, min(12, int(max_cards or 4)))
        generated = self.generate_flashcards_from_note(int(saved["note_id"]), limit)
        created = int(generated.get("created") or 0)
        msg = f"{created} flashcards criados a partir da noticia '{saved.get('title')}'."
        self._open_desktop_receipt(
            "study",
            {
                "highlight_id": saved["note_id"],
                "animate": "news_flashcards_generate",
                "toast": msg,
                "note_id": int(saved["note_id"]),
                "created": created,
                "receipt": {
                    "kind": "study",
                    "action": "news_flashcards_generate",
                    "title": saved.get("title"),
                    "note_id": int(saved["note_id"]),
                    "created": created,
                },
            },
        )
        return {
            "ok": True,
            "note_id": int(saved["note_id"]),
            "title": saved.get("title"),
            "subject": saved.get("subject"),
            "created": created,
            "cards": generated.get("cards") or [],
            "message": msg,
        }

    def review_flashcard_sm2(self, card_id: int, quality: int) -> str:
        """quality 0-5 (SM-2 simplificado)."""
        with self.db._get_connection() as conn:
            conn.row_factory = __import__("sqlite3").Row
            row = conn.execute("SELECT * FROM flashcards WHERE id = ?", (card_id,)).fetchone()
            if not row:
                return "Flashcard nao encontrado."
            r = dict(row)
        q = max(0, min(5, int(quality)))
        ef = float(r.get("ease_factor") or 2.5)
        reps = int(r.get("repetitions") or 0)
        interval = int(r.get("interval") or 0)
        if q < 3:
            reps = 0
            interval = 0
        else:
            if reps == 0:
                interval = 1
            elif reps == 1:
                interval = 6
            else:
                interval = max(1, round(interval * ef))
            reps += 1
        ef = max(1.3, ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)))
        next_d = (date.today() + timedelta(days=max(1, interval))).isoformat() + "T09:00:00"
        self.db.update_flashcard_srs(card_id, ef, interval, reps, next_d)
        broadcast_nexus_state(self)
        return f"Revisao gravada. Proxima em {interval} dia(s), Sir."

