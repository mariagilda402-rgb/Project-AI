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




class NexusNotesMixin:
    def create_note(self, subject, title, content, media=None, color=None):
        """Cria uma nova nota de estudo."""
        self._last_created_note_id = None
        try:
            with self.db._get_connection() as conn:
                cur = conn.execute(
                    """
                    INSERT INTO study_notes (subject, title, content, media_links, color)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (subject, title, content, json.dumps(media or []), color),
                )
                conn.commit()
                try:
                    self._last_created_note_id = int(cur.lastrowid)
                except (TypeError, ValueError):
                    self._last_created_note_id = None
            log_nexus_event(f"MINDPALACE: Nota '{title}' arquivada.")
            broadcast_nexus_state(self)
            return f"Nota '{title}' sobre {subject} foi salva no seu MindPalace, Sir."
        except Exception as e:
            logger.error(f"Erro ao criar nota: {e}")
            return "Erro ao arquivar nota."

    def capture_note(self, title: str, content: str, url: str | None = None, subject: str | None = None) -> int:
        """Captura conteúdo externo e transforma em nota no MindPalace."""
        final_content = content.strip()
        if url:
            final_content += f"\n\n---\n**Fonte:** {url.strip()}"

        self.create_note(subject or "Captura", title.strip(), final_content)
        return self._last_created_note_id or -1

    def _note_media_list(self, note: dict | None) -> list[dict]:
        if not note:
            return []
        try:
            media = json.loads(note.get("media_links") or "[]")
            return media if isinstance(media, list) else []
        except (TypeError, json.JSONDecodeError):
            return []

    def attach_media_to_note(
        self,
        note_id: int,
        media_url: str,
        caption: str | None = None,
        alt: str | None = None,
        append_markdown: bool = True,
    ) -> dict:
        """Anexa uma imagem/link na nota e opcionalmente insere um bloco markdown."""
        note = self.db.get_study_note(int(note_id))
        if not note:
            return {
                "note_id": int(note_id),
                "attached": None,
                "media": [],
                "content_appended": False,
                "error": "Nota nao encontrada.",
            }

        url = re.sub(r"\s+", " ", str(media_url or "")).strip()
        if not url:
            return {
                "note_id": int(note_id),
                "attached": None,
                "media": self._note_media_list(note),
                "content_appended": False,
                "error": "URL ou caminho da midia vazio.",
            }

        label = re.sub(r"\s+", " ", str(caption or alt or "Imagem da nota")).strip()
        item = {
            "url": url,
            "caption": label,
            "alt": re.sub(r"\s+", " ", str(alt or caption or label)).strip(),
        }
        media = self.db.append_study_note_media(int(note_id), item) or []

        content_appended = False
        if append_markdown:
            current = note.get("content") or ""
            block = f"![{label}]({url})"
            if block not in current:
                new_content = f"{current.rstrip()}\n\n{block}".strip()
                self.db.update_study_note(int(note_id), content=new_content)
                content_appended = True

        msg = f"Midia anexada em {note.get('title') or 'nota'}."
        log_nexus_event(f"MINDPALACE: {msg}")
        broadcast_nexus_state(self)
        self._open_desktop_receipt(
            "notes",
            {
                "highlight_id": int(note_id),
                "animate": "note_media_attach",
                "toast": msg,
                "receipt": {
                    "kind": "note",
                    "action": "note_attach_media",
                    "id": int(note_id),
                    "title": note.get("title") or "",
                    "url": url,
                    "caption": label,
                },
            },
        )
        return {
            "note_id": int(note_id),
            "attached": item,
            "media": media,
            "content_appended": content_appended,
        }

    def _summary_sentences_from_note(self, content: str, max_sentences: int = 4) -> list[str]:
        body = re.sub(r"(?is)\n## Resumo IA\b.*$", "", content or "").strip()
        lines = self._study_lines(body)
        candidates: list[str] = []
        seen: set[str] = set()
        for kind, text in lines:
            if kind == "heading":
                continue
            for sentence in re.split(r"(?<=[.!?])\s+", text):
                cleaned = re.sub(r"\s+", " ", sentence).strip(" -*")
                if len(cleaned) < 24:
                    continue
                key = cleaned.lower()
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(cleaned.rstrip(".;:") + ".")
        if not candidates and body:
            fallback = re.sub(r"\s+", " ", body).strip()
            if fallback:
                candidates.append(fallback[:520].rstrip(".;:") + ".")
        limit = max(1, min(8, int(max_sentences or 4)))
        return candidates[:limit]

    def summarize_note(self, note_id: int, append: bool = True, max_sentences: int = 4) -> dict:
        """Cria um resumo curto e opcionalmente grava na nota."""
        note = self.db.get_study_note(int(note_id))
        if not note:
            return {"note_id": note_id, "summary": "", "appended": False, "error": "Nota nao encontrada."}

        sentences = self._summary_sentences_from_note(note.get("content") or "", max_sentences)
        summary = "\n".join(f"- {sentence}" for sentence in sentences)
        if not summary:
            summary = "- Sem conteudo suficiente para resumir."

        appended = False
        if append:
            current = re.sub(r"(?is)\n## Resumo IA\b.*$", "", note.get("content") or "").rstrip()
            new_content = f"{current}\n\n## Resumo IA\n{summary}".strip()
            self.db.update_study_note(int(note_id), content=new_content)
            appended = True

        msg = f"Resumo IA gerado para {note.get('title') or 'nota'}."
        log_nexus_event(f"MINDPALACE: {msg}")
        broadcast_nexus_state(self)
        self._open_desktop_receipt(
            "notes",
            {
                "highlight_id": int(note_id),
                "animate": "note_summarize",
                "toast": msg,
                "receipt": {
                    "kind": "note",
                    "action": "note_summarize",
                    "id": int(note_id),
                    "title": note.get("title") or "",
                    "appended": appended,
                },
            },
        )
        return {"note_id": int(note_id), "summary": summary, "appended": appended}

    def teach_note(self, note_id: int, question: str | None = None, max_points: int = 4) -> dict:
        """Gera uma explicacao estilo professor a partir de uma nota salva."""
        note = self.db.get_study_note(int(note_id))
        if not note:
            return {
                "note_id": note_id,
                "mode": "professor",
                "question": (question or "").strip(),
                "lesson": "",
                "key_points": [],
                "check_questions": [],
                "error": "Nota nao encontrada.",
            }

        limit = max(2, min(8, int(max_points or 4)))
        title = (note.get("title") or "Nota").strip()
        subject = (note.get("subject") or "Geral").strip()
        key_points = self._summary_sentences_from_note(note.get("content") or "", limit)
        if not key_points:
            key_points = ["Revise a nota completa e destaque as ideias principais antes de praticar."]

        asked = re.sub(r"\s+", " ", (question or "").strip())
        first_point = key_points[0].rstrip(".")
        lesson_parts = [
            f"Modo Professor: {title} ({subject}).",
            f"Comece pela ideia central: {first_point}.",
        ]
        if asked:
            lesson_parts.append(
                f"Sobre sua pergunta, conecte a duvida com este ponto da nota e explique usando um exemplo simples."
            )
        if len(key_points) > 1:
            lesson_parts.append(
                "Depois organize o raciocinio nestes passos: "
                + " ".join(f"{idx + 1}. {point}" for idx, point in enumerate(key_points[1:]))
            )
        lesson_parts.append("Feche tentando responder sem olhar e marque o que ainda ficou fraco para revisar depois.")

        check_questions: list[str] = []
        for point in key_points:
            topic = self._topic_from_fact(point, title)
            check_questions.append(f"Explique com suas palavras: {topic}.")
            if len(check_questions) >= 3:
                break
        while len(check_questions) < 2:
            check_questions.append(f"Qual exemplo voce usaria para lembrar {title}?")

        msg = f"Modo Professor preparado para {title}."
        log_nexus_event(f"MINDPALACE: {msg}")
        broadcast_nexus_state(self)
        self._open_desktop_receipt(
            "notes",
            {
                "highlight_id": int(note_id),
                "animate": "teacher_mode",
                "toast": msg,
                "receipt": {
                    "kind": "note",
                    "action": "note_teach",
                    "id": int(note_id),
                    "title": title,
                    "question": asked,
                    "point_count": len(key_points),
                },
            },
        )
        return {
            "note_id": int(note_id),
            "title": title,
            "subject": subject,
            "mode": "professor",
            "question": asked,
            "lesson": "\n".join(lesson_parts),
            "key_points": key_points,
            "check_questions": check_questions,
            "next_step": "Gerar flashcards ou revisar as perguntas de checagem.",
        }

    def save_news_item_to_note(
        self,
        item=None,
        briefing=None,
        item_index: int = 1,
        subject: str | None = "Noticias",
    ) -> dict:
        news_item = self._select_news_item(item=item, briefing=briefing, item_index=item_index)
        if not news_item:
            return {"ok": False, "note_id": None, "error": "Noticia nao encontrada."}
        title = str(news_item.get("title") or "Noticia").strip()[:180]
        source = str(news_item.get("source") or "Fonte desconhecida").strip()
        url = str(news_item.get("url") or "").strip()
        video = news_item.get("video") if isinstance(news_item.get("video"), dict) else {}
        video_url = str(video.get("url") or "").strip()
        video_query = str(video.get("query") or title).strip()
        summary = str(news_item.get("summary") or "").strip()
        deep_dive = str(news_item.get("deep_dive") or news_item.get("body") or "").strip()
        content_parts = [
            f"# {title}",
            "## Resumo",
            summary or f"Fonte: {source}.",
            "## Por que importa",
            str(news_item.get("why_it_matters") or "A noticia pode impactar decisoes e estudos futuros.").strip(),
            "## Detalhes para revisar",
            deep_dive or "Abra a fonte original para aprofundar.",
            "## Linha do tempo",
            "\n".join(
                f"- **{row.get('label', 'Etapa')}:** {row.get('text', '')}"
                for row in (news_item.get("timeline") if isinstance(news_item.get("timeline"), list) else [])
                if isinstance(row, dict)
            )
            or "- Contexto indisponivel.",
            "## Fonte",
            f"- Veiculo: {source}",
        ]
        if url:
            content_parts.append(f"- Link: {url}")
        if video_url:
            content_parts.append(f"- Video sugerido: {video_url}")
        if video_query:
            content_parts.append(f"- Consulta de video: {video_query}")
        media = []
        if url:
            media.append({"type": "source", "url": url, "caption": source, "alt": title})
        if video_url:
            media.append({"type": "video_search", "url": video_url, "caption": video_query, "alt": title})
        note_subject = (subject or "Noticias").strip() or "Noticias"
        self.create_note(note_subject, title, "\n\n".join(content_parts), media=media)
        note_id = self._last_created_note_id or -1
        ok = note_id > 0
        if ok:
            msg = f"Noticia '{title}' salva no MindPalace."
            self._open_desktop_receipt(
                "notes",
                {
                    "highlight_id": note_id,
                    "animate": "news_save_note",
                    "toast": msg,
                    "receipt": {
                        "kind": "note",
                        "action": "news_save_note",
                        "id": note_id,
                        "title": title,
                        "source": source,
                    },
                },
            )
            return {
                "ok": True,
                "note_id": note_id,
                "title": title,
                "subject": note_subject,
                "message": msg,
            }
        return {"ok": False, "note_id": None, "error": "Erro ao salvar noticia no MindPalace."}

