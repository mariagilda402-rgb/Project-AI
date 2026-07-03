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




class NexusBaseMixin:
    def _decorate_nexus_payload(self, payload: dict | None) -> dict:
        out = dict(payload or {})
        batch = self._active_nexus_batch
        if batch:
            out.setdefault("batch_id", batch.get("id"))
            out.setdefault("batch_step", batch.get("step"))
            out.setdefault("batch_total", batch.get("total"))
            out.setdefault("hold_ms", batch.get("hold_ms", 1400))
        return out

    def _normalize_date_alias(self, value: str | None) -> str | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            return date.fromisoformat(raw[:10]).isoformat()
        except ValueError:
            pass
        key = unicodedata.normalize("NFKD", raw.lower())
        key = "".join(ch for ch in key if not unicodedata.combining(ch))
        key = " ".join(key.replace("-", " ").split())
        offsets = {
            "hoje": 0,
            "ontem": 1,
            "anteontem": 2,
            "ante ontem": 2,
            "antes de ontem": 2,
            "ontem de ontem": 2,
            "amanha": -1,
        }
        if key in offsets:
            return (date.today() - timedelta(days=offsets[key])).isoformat()
        return raw

    def get_summary(self):
        """Retorna um resumo rápido para o Jarvis falar."""
        stats = self.db.get_user_stats()
        return f"Sir, seu nível atual é {stats['level']} com {stats['points']} pontos disponíveis para troca."

    def set_focus_mode(self, active=True):
        """Ativa ou desativa o ambiente de foco (Silêncio + Música)."""
        import subprocess
        try:
            status = "ATIVADO" if active else "DESATIVADO"
            val = 0 if active else 1
            # Garante que a chave existe antes de setar
            setup_cmd = 'if (!(Test-Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings")) { New-Item -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings" -Force }'
            set_cmd = f'Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings" -Name "NOC_GLOBAL_SETTING_TOASTS_ENABLED" -Value {val}'

            subprocess.run(["powershell", "-Command", f"{setup_cmd}; {set_cmd}"], capture_output=True)

            if active:
                from src.tools.spotify import SpotifyTool
                sp = SpotifyTool()
                sp.search_and_play("Lofi Study Focus")

            log_nexus_event(f"PROTOCOL: Focus Mode {status}")
            broadcast_nexus_state(self)

            return f"Modo de Foco {status}, Sir. Ambiente preparado."
        except Exception as e:
            logger.error(f"Erro no modo foco: {e}")
            return "Falha ao ajustar o protocolo de foco."

    def _fold_text(self, value: str | None) -> str:
        raw = str(value or "").strip().lower()
        folded = unicodedata.normalize("NFKD", raw)
        return "".join(ch for ch in folded if not unicodedata.combining(ch))

    def teach_subject(self, subject: str | None, question: str | None = None, max_points: int = 6) -> dict:
        """Gera uma aula curta usando todas as notas de uma materia."""
        subject_name = re.sub(r"\s+", " ", str(subject or "").strip())
        subject_label = subject_name or "Todas as materias"
        raw_notes = self.db.list_study_notes(subject_name or None)
        notes = sorted(
            [
                note
                for note in raw_notes
                if not subject_name or (note.get("subject") or "").strip() == subject_name
            ],
            key=lambda note: int(note.get("id") or 0),
        )
        asked = re.sub(r"\s+", " ", (question or "").strip())
        if not notes:
            return {
                "subject": subject_label,
                "mode": "professor_subject",
                "question": asked,
                "lesson": "",
                "key_points": [],
                "check_questions": [],
                "note_count": 0,
                "note_ids": [],
                "error": "Materia sem notas salvas.",
            }

        limit = max(2, min(10, int(max_points or 6)))
        key_points: list[str] = []
        for note in notes[:8]:
            title = (note.get("title") or "Nota").strip()
            for sentence in self._summary_sentences_from_note(note.get("content") or "", 2):
                key_points.append(f"{title}: {sentence}")
                if len(key_points) >= limit:
                    break
            if len(key_points) >= limit:
                break
        if not key_points:
            key_points = [
                f"{(notes[0].get('title') or subject_label).strip()}: Revise as ideias principais e transforme cada topico em pergunta."
            ]

        titles = [(note.get("title") or "Nota").strip() for note in notes]
        first_point = key_points[0].rstrip(".")
        lesson_parts = [
            f"Modo Professor da materia: {subject_label}.",
            f"Base de leitura: {len(notes)} nota(s) - {', '.join(titles[:4])}.",
            f"Comece conectando a ideia central: {first_point}.",
        ]
        if asked:
            lesson_parts.append(
                "Para responder sua pergunta, atravesse as notas como uma trilha: conceito, exemplo, armadilha comum e exercicio."
            )
        if len(key_points) > 1:
            lesson_parts.append(
                "Roteiro de revisao: "
                + " ".join(f"{idx + 1}. {point}" for idx, point in enumerate(key_points[1:]))
            )
        lesson_parts.append("Finalize criando flashcards da materia e revisando os pontos que voce nao conseguir explicar em voz alta.")

        check_questions: list[str] = []
        for point in key_points:
            topic = self._topic_from_fact(point, subject_label)
            check_questions.append(f"Explique sem consultar: {topic}.")
            if len(check_questions) >= 4:
                break
        while len(check_questions) < 2:
            check_questions.append(f"Qual exemplo pratico voce usaria para lembrar {subject_label}?")

        first_note_id = int(notes[0].get("id") or 0)
        msg = f"Modo Professor da materia preparado para {subject_label}."
        log_nexus_event(f"MINDPALACE: {msg}")
        broadcast_nexus_state(self)
        self._open_desktop_receipt(
            "notes",
            {
                "highlight_id": first_note_id,
                "animate": "subject_teacher_mode",
                "toast": msg,
                "receipt": {
                    "kind": "note",
                    "action": "subject_teach",
                    "subject": subject_label,
                    "question": asked,
                    "note_count": len(notes),
                    "point_count": len(key_points),
                },
            },
        )
        return {
            "subject": subject_label,
            "mode": "professor_subject",
            "question": asked,
            "lesson": "\n".join(lesson_parts),
            "key_points": key_points,
            "check_questions": check_questions,
            "note_count": len(notes),
            "note_ids": [int(note.get("id") or 0) for note in notes],
            "next_step": "Gerar flashcards da materia e responder as perguntas de checagem.",
        }

    def _topic_from_fact(self, text: str, fallback: str) -> str:
        cleaned = re.sub(r"\s+", " ", (text or "")).strip(" .;:")
        if not cleaned:
            return fallback
        parts = re.split(
            r"\b(e|eh|sao|significa|converte|produz|fixa|marca|marcou|derrubou|absorve|gera|usa)\b",
            cleaned,
            maxsplit=1,
            flags=re.IGNORECASE,
        )
        topic = (parts[0] if parts else cleaned).strip(" .;:")
        if len(topic.split()) > 6 or len(topic) < 3:
            topic = " ".join(cleaned.split()[:6]).strip(" .;:")
        return topic or fallback

    def get_review_count(self):
        """Retorna quantos flashcards precisam de revisão hoje."""
        with self.db._get_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM flashcards WHERE datetime(next_review) <= datetime('now')"
            ).fetchone()[0]
            return count

    def _normalize_days_of_week(self, value) -> str | None:
        if value in (None, "", []):
            return None
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return None
            if raw.startswith("["):
                try:
                    value = json.loads(raw)
                except json.JSONDecodeError:
                    return raw
            else:
                return raw
        if isinstance(value, (list, tuple)):
            days = []
            for day in value:
                try:
                    day_int = int(day)
                except (TypeError, ValueError):
                    continue
                if 0 <= day_int <= 6 and day_int not in days:
                    days.append(day_int)
            return json.dumps(days) if days else None
        return None

    def save_lifestyle_preset(self, name):
        """Salva o estado atual de hábitos como um preset."""
        try:
            preset_name = (name or "").strip() or "Preset Nexus"
            habits = self.db.get_habits()
            config = json.dumps(
                [self._preset_habit_config(h) for h in habits],
                ensure_ascii=False,
            )
            with self.db._get_connection() as conn:
                row = conn.execute(
                    "SELECT id FROM lifestyle_presets WHERE name = ?",
                    (preset_name,),
                ).fetchone()
                if row:
                    conn.execute(
                        """
                        UPDATE lifestyle_presets
                        SET config_json = ?, created_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (config, row[0]),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO lifestyle_presets (name, config_json)
                        VALUES (?, ?)
                        """,
                        (preset_name, config),
                    )
                conn.commit()
            log_nexus_event(f"STRATEGY: Preset '{preset_name}' salvo.")
            return f"Preset de vida '{preset_name}' foi imortalizado, Sir."
        except Exception as e:
            logger.error(f"Erro ao salvar preset: {e}")
            return "Falha ao salvar configuração estratégica."

    def list_lifestyle_presets(self) -> list[dict]:
        """Lista presets salvos com contagem resumida para UI/IA."""
        with self.db._get_connection() as conn:
            conn.row_factory = __import__("sqlite3").Row
            rows = conn.execute(
                """
                SELECT id, name, config_json, is_active, created_at
                FROM lifestyle_presets
                ORDER BY is_active DESC, datetime(created_at) DESC, id DESC
                """
            ).fetchall()
        presets = []
        for row in rows:
            try:
                habits = json.loads(row["config_json"] or "[]")
            except json.JSONDecodeError:
                habits = []
            presets.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "habit_count": len(habits) if isinstance(habits, list) else 0,
                    "is_active": bool(row["is_active"]),
                    "created_at": row["created_at"],
                }
            )
        return presets

    def load_lifestyle_preset(self, name):
        """Carrega um preset de vida, substituindo os hábitos atuais."""
        try:
            search_name = (name or "").strip()
            with self.db._get_connection() as conn:
                row = conn.execute(
                    """
                    SELECT id, name, config_json
                    FROM lifestyle_presets
                    WHERE name LIKE ?
                    ORDER BY length(name) ASC, datetime(created_at) DESC
                    LIMIT 1
                    """,
                    (f"%{search_name}%",),
                ).fetchone()
                if not row:
                    return f"Não encontrei o preset '{search_name}', Sir."

                preset_id, preset_name, config_json = row
                new_habits = json.loads(config_json or "[]")
                conn.execute("UPDATE lifestyle_presets SET is_active = 0")
                conn.execute("UPDATE lifestyle_presets SET is_active = 1 WHERE id = ?", (preset_id,))
                conn.commit()

            habit_count = self._replace_active_habits(new_habits if isinstance(new_habits, list) else [])
            msg = f"Protocolo '{preset_name}' ativado. Todos os sistemas reconfigurados."
            log_nexus_event(f"STRATEGY: Preset '{preset_name}' ativado.")
            broadcast_nexus_state(self)
            self._open_desktop_receipt(
                "habits",
                {
                    "animate": "preset",
                    "toast": msg,
                    "receipt": {
                        "kind": "preset",
                        "action": "preset_apply",
                        "name": preset_name,
                        "habit_count": habit_count,
                    },
                },
            )
            return msg
        except Exception as e:
            logger.error(f"Erro ao carregar preset: {e}")
            return "Falha na reconfiguração estratégica."

    def _fold_key(self, value: str | None) -> str:
        folded = unicodedata.normalize("NFKD", (value or "").lower())
        folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
        return " ".join(re.sub(r"[^a-z0-9]+", " ", folded).split())

    def _normalize_window_module(self, module: str | None) -> str | None:
        raw = self._fold_key(module)
        if raw in _NEXUS_WINDOW_MODULES:
            return raw
        if raw in _NEXUS_WINDOW_MODULE_ALIASES:
            return _NEXUS_WINDOW_MODULE_ALIASES[raw]
        for key, value in _NEXUS_WINDOW_MODULE_ALIASES.items():
            if key and key in raw:
                return value
        return None

    def _obsidian_safe_filename(self, value: str | None, fallback: str = "Nexus Note") -> str:
        base = re.sub(r"[\\/:*?\"<>|]+", " ", str(value or fallback)).strip()
        base = re.sub(r"\s+", " ", base)[:90].strip(" .")
        return base or fallback

    def import_obsidian_markdown(
        self,
        folder,
        subject: str | None = "Obsidian",
        limit: int = 80,
    ) -> dict:
        root = Path(folder).expanduser()
        if not root.exists() or not root.is_dir():
            return {"ok": False, "count": 0, "note_ids": [], "error": "Pasta Obsidian nao encontrada."}
        note_ids: list[int] = []
        imported = 0
        for path in sorted(root.rglob("*.md"))[: max(1, min(200, int(limit or 80)))]:
            if path.name.lower() == "nexus memory graph.md":
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="ignore").strip()
            except OSError:
                continue
            if not content:
                continue
            title = path.stem
            for line in content.splitlines():
                clean = line.strip()
                if clean.startswith("# "):
                    title = clean.lstrip("#").strip() or title
                    break
            body = content + f"\n\n---\nFonte Obsidian: {path}"
            self.create_note(subject or "Obsidian", title[:180], body)
            if self._last_created_note_id:
                note_ids.append(int(self._last_created_note_id))
                imported += 1
        if imported:
            broadcast_nexus_state(self)
        return {
            "ok": True,
            "count": imported,
            "note_ids": note_ids,
            "subject": subject or "Obsidian",
            "message": f"{imported} arquivos Markdown importados para o MindPalace.",
        }

    def _news_sentences(self, text: str | None) -> list[str]:
        clean = re.sub(r"\s+", " ", str(text or "")).strip()
        if not clean:
            return []
        parts = re.split(r"(?<=[.!?])\s+", clean)
        return [p.strip(" .") for p in parts if p.strip(" .")]

    def _fetch_news_results(self, query: str, limit: int) -> list[dict]:
        try:
            from duckduckgo_search import DDGS
        except Exception:
            return []
        rows = []
        try:
            with DDGS() as ddgs:
                for item in ddgs.news(query, max_results=limit):
                    rows.append(item)
        except Exception as e:
            logger.warning("News search failed: %s", e)
        return rows

    def _news_history_store_path(self) -> Path:
        db_path = Path(getattr(self.db, "db_path", "data/nexus.db"))
        return db_path.parent / "nexus_news_briefings.json"

    def _load_news_history(self) -> list[dict]:
        path = self._news_history_store_path()
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        rows = raw.get("briefings") if isinstance(raw, dict) else raw
        if not isinstance(rows, list):
            return []
        return [row for row in rows if isinstance(row, dict)]

    def _save_news_history(self, rows: list[dict]) -> None:
        path = self._news_history_store_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"version": 1, "briefings": rows[:12]}
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as e:
            logger.warning("Could not save Nexus news history: %s", e)

    def _remember_news_briefing(self, briefing: dict) -> None:
        if not briefing.get("ok") or not briefing.get("items") or briefing.get("from_cache"):
            return
        query = (briefing.get("query") or "top news Brasil").strip()
        generated_at = briefing.get("generated_at") or datetime.now().isoformat(timespec="seconds")
        first_title = (briefing.get("items") or [{}])[0].get("title") or "noticias"
        record_id = f"{self._slug_theme_id(query, 'noticias')}-{self._slug_theme_id(first_title, 'briefing')}-{generated_at}"
        record = {
            "id": record_id,
            "query": query,
            "query_key": self._fold_key(query),
            "generated_at": generated_at,
            "items": briefing.get("items") or [],
            "narration": briefing.get("narration") or "",
        }
        history = [
            row
            for row in self._load_news_history()
            if row.get("id") != record_id
        ]
        history.insert(0, record)
        self._save_news_history(history)

    def _cached_news_briefing(self, query: str) -> dict | None:
        history = self._load_news_history()
        if not history:
            return None
        key = self._fold_key(query)
        for row in history:
            if row.get("query_key") == key:
                return json.loads(json.dumps(row, ensure_ascii=False))
        return json.loads(json.dumps(history[0], ensure_ascii=False))

    def list_news_briefings(self, limit: int = 8) -> list[dict]:
        try:
            lim = max(1, min(20, int(limit or 8)))
        except (TypeError, ValueError):
            lim = 8
        briefings = []
        for row in self._load_news_history()[:lim]:
            items = row.get("items") if isinstance(row.get("items"), list) else []
            first = items[0] if items and isinstance(items[0], dict) else {}
            briefings.append(
                {
                    "id": row.get("id") or "",
                    "query": row.get("query") or "",
                    "generated_at": row.get("generated_at") or "",
                    "item_count": len(items),
                    "top_title": first.get("title") or "",
                    "top_source": first.get("source") or "",
                }
            )
        return briefings

    def _news_impact_tags(self, title: str, body: str, query: str | None = None) -> list[str]:
        folded = self._fold_key(" ".join([query or "", title or "", body or ""]))
        tags: list[str] = []
        keyword_map = {
            "educacao": ["educacao", "ensino", "escola", "professor", "estudo", "enem"],
            "tecnologia": ["tecnologia", "ia", "digital", "plataforma", "software", "neural"],
            "economia": ["economia", "mercado", "consumo", "juros", "inflacao", "indicador"],
            "saude": ["saude", "hospital", "medico", "triagem", "paciente"],
            "politica": ["politica", "governo", "congresso", "eleicao", "regra"],
            "privacidade": ["privacidade", "dados", "seguranca"],
        }
        for tag, words in keyword_map.items():
            if any(word in folded for word in words):
                tags.append(tag)
        qtag = self._slug_theme_id(query or "", fallback="")
        if qtag and qtag not in tags:
            tags.insert(0, qtag)
        return tags[:5] or ["atualidades"]

    def _news_timeline(self, title: str, source: str, sentences: list[str]) -> list[dict]:
        context = sentences[0] if sentences else f"A noticia foi publicada por {source}."
        next_step = (
            sentences[2]
            if len(sentences) > 2
            else "Acompanhar a fonte original e observar os proximos desdobramentos."
        )
        return [
            {"label": "Contexto", "text": context},
            {"label": "Agora", "text": title},
            {"label": "Proximo passo", "text": next_step},
        ]

    def _news_actions(self) -> list[dict]:
        return [
            {"id": "save_note", "label": "Salvar no MindPalace", "action": "news_save_note"},
            {"id": "flashcards", "label": "Criar flashcards", "action": "news_flashcards_generate"},
            {"id": "follow_up", "label": "Criar tarefa", "action": "news_followup_task"},
            {"id": "deep_dive", "label": "Fale mais", "action": "expand_spotlight"},
        ]

    def _build_news_deck(self, query: str, items: list[dict]) -> dict:
        segments = []
        for idx, item in enumerate(items, 1):
            item_index = int(item.get("index") or idx)
            cue = f"[Noticia {item_index}]"
            title = str(item.get("title") or "Noticia").strip()
            source = str(item.get("source") or "Fonte desconhecida").strip()
            why = str(item.get("why_it_matters") or item.get("summary") or "").strip()
            summary = str(item.get("summary") or "").strip()
            script = (
                f"{cue} {title}. "
                f"Fonte: {source}. "
                f"{summary} "
                f"Por que importa: {why}"
            ).strip()
            word_count = max(1, len(script.split()))
            duration = max(10, min(45, int(round(word_count / 2.7))))
            segments.append(
                {
                    "cue": cue,
                    "item_index": item_index,
                    "title": title,
                    "source": source,
                    "script": script,
                    "duration_sec": duration,
                }
            )
        script = " ".join(seg["script"] for seg in segments).strip()
        first = items[0] if items else {}
        actions = first.get("actions") if isinstance(first.get("actions"), list) else []
        primary_action = next(
            (
                str(action.get("label") or "").strip()
                for action in actions
                if isinstance(action, dict) and action.get("id") == "save_note"
            ),
            "Salvar no MindPalace",
        )
        video = first.get("video") if isinstance(first.get("video"), dict) else {}
        sources = {
            str(item.get("source") or "").strip().lower()
            for item in items
            if str(item.get("source") or "").strip()
        }
        return {
            "mode": "spotlight",
            "spotlight_index": 1 if items else 0,
            "item_count": len(items),
            "source_count": len(sources),
            "estimated_duration_sec": sum(int(seg.get("duration_sec") or 0) for seg in segments),
            "segments": segments,
            "spotlight": {
                "item_index": int(first.get("index") or 0) if first else 0,
                "title": first.get("title") or "",
                "source": first.get("source") or "",
                "published_at": first.get("published_at") or "",
                "summary": first.get("summary") or "",
                "why_it_matters": first.get("why_it_matters") or "",
                "primary_action": primary_action,
                "source_url": first.get("url") or "",
                "video_url": video.get("url") or "",
            },
            "briefing_script": script,
            "next_action": "Escolha uma noticia para aprofundar, salvar ou acompanhar.",
            "query": query,
        }

    def _normalize_news_item(self, idx: int, raw: dict, query: str | None = None) -> dict:
        title = str(raw.get("title") or raw.get("headline") or "Sem titulo").strip()
        source = str(raw.get("source") or raw.get("publisher") or "Fonte desconhecida").strip()
        published = str(raw.get("date") or raw.get("published_at") or raw.get("published") or "").strip()
        url = str(raw.get("url") or raw.get("link") or raw.get("href") or "").strip()
        body = str(raw.get("body") or raw.get("snippet") or raw.get("description") or "").strip()
        sentences = self._news_sentences(body)
        summary = ". ".join(sentences[:2]).strip()
        if summary and not summary.endswith("."):
            summary += "."
        if not summary:
            summary = f"{title}. Fonte: {source}."
        past = sentences[0] if sentences else f"Fonte: {source}"
        future = sentences[1] if len(sentences) > 1 else "Proximo passo: abrir a fonte e acompanhar os desdobramentos."
        detail_lines = sentences[:4] or [summary.strip(" .")]
        deep_dive = (
            "Pontos principais: "
            + " ".join(line.strip(" .") + "." for line in detail_lines if line)
            + f" Fonte original: {source}."
        ).strip()
        why = (
            "Importa porque "
            + (sentences[1] if len(sentences) > 1 else summary).strip(" .")
            + "."
        )
        video_query = f"{title} {source} video"
        return {
            "index": idx,
            "title": title,
            "source": source,
            "published_at": published,
            "url": url,
            "body": body,
            "summary": summary,
            "deep_dive": deep_dive,
            "why_it_matters": why,
            "impact_tags": self._news_impact_tags(title, body, query),
            "timeline": self._news_timeline(title, source, sentences),
            "actions": self._news_actions(),
            "video": {
                "provider": "youtube-search",
                "url": "https://www.youtube.com/results?search_query=" + quote_plus(video_query),
                "query": video_query,
            },
            "transcript": {
                "past": past,
                "present": title,
                "future": future,
            },
        }

    def _coerce_news_payload(self, value) -> dict:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return {}
        return value if isinstance(value, dict) else {}

    def _select_news_item(self, item=None, briefing=None, item_index: int = 1) -> dict:
        item_data = self._coerce_news_payload(item)
        if item_data:
            return item_data
        briefing_data = self._coerce_news_payload(briefing)
        items = briefing_data.get("items") if isinstance(briefing_data.get("items"), list) else []
        try:
            idx = max(0, int(item_index or 1) - 1)
        except (TypeError, ValueError):
            idx = 0
        if 0 <= idx < len(items) and isinstance(items[idx], dict):
            return items[idx]
        return {}

    def build_news_briefing(
        self,
        query: str | None = "",
        limit: int = 3,
        results: list[dict] | str | None = None,
        open_window: bool = True,
    ) -> dict:
        q = (query or "").strip() or "top news Brasil"
        try:
            lim = max(1, min(5, int(limit or 3)))
        except (TypeError, ValueError):
            lim = 3
        if isinstance(results, str):
            try:
                results = json.loads(results)
            except json.JSONDecodeError:
                results = []
        rows = results if isinstance(results, list) else self._fetch_news_results(q, lim)
        items = [
            self._normalize_news_item(idx, raw, q)
            for idx, raw in enumerate(rows[:lim], 1)
            if isinstance(raw, dict)
        ]
        generated_at = datetime.now().isoformat(timespec="seconds")
        if not items:
            cached = self._cached_news_briefing(q)
            if cached:
                items = cached.get("items") if isinstance(cached.get("items"), list) else []
                deck = self._build_news_deck(cached.get("query") or q, items)
                narration = deck["briefing_script"] or cached.get("narration") or ""
                briefing = {
                    "ok": bool(items),
                    "query": cached.get("query") or q,
                    "generated_at": cached.get("generated_at") or generated_at,
                    "cached_generated_at": cached.get("generated_at") or "",
                    "from_cache": True,
                    "stale": True,
                    "items": items,
                    "deck": deck,
                    "narration": narration,
                    "error": "" if items else "Nenhuma noticia encontrada agora.",
                }
            else:
                briefing = {
                    "ok": False,
                    "query": q,
                    "generated_at": generated_at,
                    "from_cache": False,
                    "stale": False,
                    "items": [],
                    "deck": self._build_news_deck(q, []),
                    "narration": "",
                    "error": "Nenhuma noticia encontrada agora.",
                }
        else:
            deck = self._build_news_deck(q, items)
            narration = deck["briefing_script"]
            briefing = {
                "ok": True,
                "query": q,
                "generated_at": generated_at,
                "from_cache": False,
                "stale": False,
                "items": items,
                "deck": deck,
                "narration": narration,
                "error": "",
            }
            self._remember_news_briefing(briefing)
        if open_window:
            self._open_desktop_receipt(
                "news",
                {
                    "animate": "news_briefing",
                    "toast": "Briefing de noticias atualizado." if items else briefing["error"],
                    "briefing": briefing,
                    "receipt": {
                        "kind": "news",
                        "action": "news_briefing",
                        "query": q,
                        "count": len(items),
                    },
                },
            )
        return briefing

    def change_aura(self, color_name):
        """Muda a cor do HUD (Aura)."""
        mapping = {
            "ciano": "cyan",
            "vermelho": "red",
            "roxo": "purple",
            "esmeralda": "emerald",
            "verde": "emerald",
            "stark": "red"
        }
        theme = mapping.get(color_name.lower(), "cyan")
        payload = {
            "type": "theme_change",
            "theme": theme
        }
        from src.utils.nexus_notifier import notify_nexus_update
        notify_nexus_update(payload)
        log_nexus_event(f"AURA: Mudança para {theme.upper()}")
        return f"Aura alterada para {color_name}, Sir. Sistemas recalibrados."

    def change_hud_tab(self, tab_name):
        """Sincroniza aba (HUD web opcional) e abre módulo desktop correspondente."""
        try:
            from src.ui.nexus_signals import enqueue_nexus_desktop_open

            mp = {
                "dashboard": "overview",
                "notes": "notes",
                "memory_graph": "memory_graph",
                "grafo": "memory_graph",
                "grafo neural": "memory_graph",
                "memoria": "memory_graph",
                "rede neural": "memory_graph",
                "board": "tasks",
                "finance": "finance",
                "study": "study",
                "progress": "progress",
                "goals": "goals",
                "rewards": "goals",
                "quiz": "quiz",
                "news": "news",
                "noticias": "news",
                "ops": "ops",
                "business": "ops",
                "negocios": "ops",
                "operacoes": "ops",
            }
            enqueue_nexus_desktop_open(mp.get(str(tab_name).lower(), "overview"), {})
        except Exception:
            pass
        payload = {
            "type": "tab_change",
            "tab": tab_name,
        }
        from src.utils.nexus_notifier import notify_nexus_update

        notify_nexus_update(payload)
        log_nexus_event(f"NAV: Alternado para aba {str(tab_name).upper()}")
        return True

    def open_nexus_ui(self, tab: str | None = None):
        """Abre janela Nexus no desktop (pywebview); fallback para HUD web se necessário."""
        raw = (tab or "dashboard").strip().lower()
        mp = {
            "dashboard": "overview",
            "overview": "overview",
            "home": "overview",
            "inicio": "overview",
            "início": "overview",
            "habits": "habits",
            "habitos": "habits",
            "hábitos": "habits",
            "notes": "notes",
            "note": "notes",
            "notas": "notes",
            "mindpalace": "notes",
            "memory_graph": "memory_graph",
            "memory graph": "memory_graph",
            "grafo": "memory_graph",
            "grafo neural": "memory_graph",
            "memoria": "memory_graph",
            "memorias": "memory_graph",
            "rede neural": "memory_graph",
            "neural": "memory_graph",
            "board": "tasks",
            "tasks": "tasks",
            "tarefas": "tasks",
            "finance": "finance",
            "financas": "finance",
            "finanças": "finance",
            "study": "study",
            "srs": "study",
            "flashcards": "study",
            "progress": "progress",
            "progresso": "progress",
            "goals": "goals",
            "metas": "goals",
            "rewards": "goals",
            "loja": "goals",
            "recompensas": "goals",
            "quiz": "quiz",
            "simulado": "quiz",
            "simulados": "quiz",
            "news": "news",
            "noticias": "news",
            "notÃ­cias": "news",
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
        mod = mp.get(raw, "overview")
        try:
            from src.ui.nexus_signals import enqueue_nexus_desktop_open

            enqueue_nexus_desktop_open(
                mod,
                self._decorate_nexus_payload(
                    {"animate": "open_module", "source": "open_ui", "tab": raw}
                ),
            )
            log_nexus_event(f"SYSTEM: Janela Nexus desktop ({mod}).")
            return f"Abrindo Nexus ({mod}), Sir."
        except Exception as e:
            logger.warning("Nexus desktop indisponível: %s", e)
        import webbrowser

        webbrowser.open("http://localhost:5123/nexus/")
        log_nexus_event("SYSTEM: Interface Nexus (navegador) como fallback.")
        return "Abrindo a interface Nexus no navegador, Sir."

    def add_calendar_event(self, title: str, event_date: str, time_str: str, duration: int, reminder: int) -> str:
        with self.db._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO calendar_events (title, date, time, duration_minutes, reminder_minutes) VALUES (?, ?, ?, ?, ?)",
                       (title, event_date, time_str, duration, reminder))
            conn.commit()
            return f"Evento '{title}' agendado para {event_date} às {time_str} ({duration} min)."

    def get_calendar_events(self, period="today") -> str:
        import datetime
        today = datetime.date.today()
        if period == "today":
            target_dates = [today.isoformat()]
        else:
            # week
            target_dates = [(today + datetime.timedelta(days=i)).isoformat() for i in range(7)]

        with self.db._get_connection() as conn:
            cur = conn.cursor()
            placeholders = ",".join("?" for _ in target_dates)
            cur.execute(f"SELECT id, title, date, time FROM calendar_events WHERE date IN ({placeholders}) ORDER BY date, time", target_dates)
            events = cur.fetchall()

            if not events:
                return f"Nenhum evento para {period}."

            result = []
            for ev in events:
                result.append({"id": ev[0], "title": ev[1], "date": ev[2], "time": ev[3]})
            return json.dumps(result, ensure_ascii=False)

    def log_workout(self, plan_id: int, exercises: list) -> str:
        # exercises is a list of dicts: {"name": str, "sets": int, "reps": int, "weight": float}
        with self.db._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO workout_sessions (plan_id, date) VALUES (?, date('now', 'localtime'))", (plan_id,))
            session_id = cur.lastrowid

            if exercises:
                for ex in exercises:
                    cur.execute(
                        "INSERT INTO workout_sets (session_id, exercise_name, sets, reps, weight) VALUES (?, ?, ?, ?, ?)",
                        (session_id, ex.get("name"), ex.get("sets", 1), ex.get("reps", 1), ex.get("weight", 0))
                    )
            conn.commit()
            return f"Treino registrado com sucesso (Sessão {session_id})."

    def handle_structured_command(self, data: dict) -> str:
        act = (data.get("action") or "").strip().lower()
        try:
            if act == "nexus_batch":
                try:
                    hold_ms = int(data.get("hold_ms") or 1400)
                except (TypeError, ValueError):
                    hold_ms = 1400
                return self.handle_nexus_batch(data.get("steps"), hold_ms=hold_ms)
            if act == "get_routines":
                with self.db._get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT id, name, description, time_of_day FROM nexus_routines WHERE active=1")
                    rows = cur.fetchall()
                    res = []
                    for r in rows:
                        cur.execute("SELECT title, duration_min FROM nexus_routine_steps WHERE routine_id=? ORDER BY step_order", (r[0],))
                        steps = [{"title": s[0], "duration": s[1]} for s in cur.fetchall()]
                        res.append({"id": r[0], "name": r[1], "desc": r[2], "time": r[3], "steps": steps})
                    return json.dumps(res, ensure_ascii=False)

            if act == "create_routine":
                name = data.get("name")
                time_of_day = data.get("time_of_day", "Morning")
                steps = data.get("steps", [])
                if not name: return json.dumps({"error": "Name required"})
                with self.db._get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute("INSERT INTO nexus_routines (name, time_of_day) VALUES (?, ?)", (name, time_of_day))
                    rid = cur.lastrowid
                    for i, step in enumerate(steps):
                        cur.execute("INSERT INTO nexus_routine_steps (routine_id, step_order, title, duration_min) VALUES (?, ?, ?, ?)",
                            (rid, i+1, step.get("title"), step.get("duration", 5)))
                    conn.commit()
                return json.dumps({"ok": True})

            if act == "delete_routine":
                rid = data.get("id")
                if rid:
                    with self.db._get_connection() as conn:
                        cur = conn.cursor()
                        cur.execute("UPDATE nexus_routines SET active=0 WHERE id=?", (rid,))
                        conn.commit()
                    return json.dumps({"ok": True})

            if act == "cron_add":
                from src.services.cron_scheduler import NexusCronScheduler
                scheduler = NexusCronScheduler()
                name = data.get("name", "Unnamed Cron")
                schedule = data.get("schedule", "0 * * * *")
                command = data.get("command", "")
                job_id = scheduler.add_job(name, schedule, command)
                return f"Cron job '{name}' adicionado com sucesso (ID: {job_id})."
            if act == "cron_remove":
                from src.services.cron_scheduler import NexusCronScheduler
                scheduler = NexusCronScheduler()
                job_id = data.get("job_id")
                if job_id:
                    scheduler.remove_job(int(job_id))
                    return f"Cron job {job_id} removido."
                return "ID do job não fornecido."
            if act == "cron_list":
                from src.services.cron_scheduler import NexusCronScheduler
                scheduler = NexusCronScheduler()
                jobs = scheduler.get_jobs()
                return json.dumps(jobs, ensure_ascii=False)
            if act == "calendar_add":
                return self.add_calendar_event(
                    data.get("title", ""),
                    data.get("date", date.today().isoformat()),
                    data.get("time", "12:00"),
                    int(data.get("duration", 60)),
                    int(data.get("reminder", 15))
                )
            if act == "calendar_today":
                return self.get_calendar_events("today")
            if act == "calendar_week":
                return self.get_calendar_events("week")
            if act == "agent_delegate":
                from src.agent.worker_agent import agent_delegate
                return agent_delegate(data.get("goal", ""), data.get("context", ""))
            if act == "agent_status":
                from src.agent.worker_agent import agent_status
                return agent_status(data.get("worker_id", ""))
            if act == "habit_stats":
                return self.get_habit_stats(int(data.get("habit_id", 0)))
            if act == "habit_heatmap":
                return self.get_habit_heatmap(int(data.get("year", date.today().year)))
            if act == "finance_budget_set":
                limit = float(str(data.get("amount", 0)).replace(",", "."))
                return self.set_finance_budget(data.get("category", "Geral"), limit)
            if act == "finance_budget_status":
                return self.get_finance_budget_status()
            if act == "finance_investment_add":
                qty = float(str(data.get("quantity", 0)).replace(",", "."))
                price = float(str(data.get("price", 0)).replace(",", "."))
                return self.add_finance_investment(data.get("ticker", ""), data.get("type", "stock"), qty, price)
            if act == "finance_investment_portfolio":
                return self.get_finance_portfolio()
            if act == "workout_log":
                return self.log_workout(data.get("plan_id"), data.get("exercises"))
            if act == "finance_add":
                t = (data.get("type") or "expense").lower()
                raw_amt = data.get("amount")
                if isinstance(raw_amt, str):
                    amount = float(raw_amt.replace(",", ".").strip() or 0)
                else:
                    amount = float(raw_amt or 0)
                cat = (data.get("category") or "Geral").strip()
                desc = (data.get("description") or "").strip() or "Via nexus_command"
                od = self._normalize_date_alias(data.get("occurred_at"))
                notes = (data.get("notes") or "").strip() or None
                is_debt = int(data.get("is_debt") or 0)
                if t == "income":
                    msg = self.add_income(amount, cat, desc, occurred_at=od, notes=notes)
                else:
                    msg = self.add_expense(
                        amount, cat, desc, necessity=int(data.get("necessity") or 5),
                        occurred_at=od, notes=notes, is_debt=is_debt,
                    )
                self._open_desktop_receipt(
                    "finance",
                    {
                        "highlight_id": self._last_created_finance_id,
                        "animate": "finance_add",
                        "toast": (msg or "")[:120],
                        "receipt": {
                            "kind": "finance",
                            "action": "finance_add",
                            "id": self._last_created_finance_id,
                            "type": t,
                            "amount": amount,
                            "category": cat,
                            "description": desc,
                            "occurred_at": od or date.today().isoformat(),
                            "notes": notes,
                            "is_debt": is_debt,
                        },
                    },
                )
                return msg
            if act == "finance_list":
                od = data.get("date_from")
                do = data.get("date_to")
                rows = self.db.list_finance_transactions(od, do)
                return json.dumps(rows, ensure_ascii=False)[:8000]
            if act == "finance_update":
                has_id = bool(data.get("transaction_id"))
                target_amount = self._parse_finance_amount(data.get("target_amount") or data.get("match_amount"))
                new_amount = data.get("new_amount")
                if new_amount in (None, "") and has_id:
                    new_amount = data.get("amount")
                new_notes = data.get("new_notes") if "new_notes" in data else (data.get("notes") if has_id and "notes" in data else None)
                new_is_debt = data.get("new_is_debt") if "new_is_debt" in data else (data.get("is_debt") if has_id and "is_debt" in data else None)
                new_necessity = data.get("new_necessity") if "new_necessity" in data else (data.get("necessity") if has_id and "necessity" in data else None)
                result = self.update_finance_transaction(
                    transaction_id=int(data["transaction_id"]) if has_id else None,
                    target_description=(
                        data.get("target_description")
                        or data.get("match_description")
                        or (None if has_id else data.get("description") or data.get("text"))
                    ),
                    target_category=(
                        data.get("target_category")
                        or data.get("match_category")
                        or (None if has_id else data.get("category"))
                    ),
                    target_type=data.get("target_type") or data.get("match_type") or (None if has_id else data.get("type")),
                    target_occurred_at=(
                        data.get("target_occurred_at")
                        or data.get("target_date")
                        or data.get("match_date")
                        or (None if has_id else data.get("occurred_at") or data.get("date"))
                    ),
                    target_amount=target_amount,
                    tx_type=data.get("new_type") or (data.get("type") if has_id else None),
                    amount=new_amount,
                    category=data.get("new_category") or (data.get("category") if has_id else None),
                    description=data.get("new_description") or (data.get("description") if has_id else None),
                    occurred_at=data.get("new_occurred_at") or data.get("new_date") or (data.get("occurred_at") if has_id else None),
                    necessity=int(new_necessity) if new_necessity not in (None, "") else None,
                    notes=new_notes,
                    is_debt=int(new_is_debt) if new_is_debt not in (None, "") else None,
                )
                return result["message"]
            if act == "finance_delete":
                raw_amount = data.get("amount")
                amount = None
                if raw_amount not in (None, ""):
                    amount = float(str(raw_amount).replace(",", "."))
                result = self.delete_finance_transaction(
                    transaction_id=int(data["transaction_id"]) if data.get("transaction_id") else None,
                    description=data.get("description") or data.get("text"),
                    category=data.get("category"),
                    tx_type=data.get("type"),
                    occurred_at=data.get("occurred_at") or data.get("date"),
                    amount=amount,
                )
                return result["message"]
            if act == "habit_complete":
                return self.complete_habit((data.get("habit_name") or "").strip())
            if act == "habit_add":
                dow = data.get("days_of_week")
                if isinstance(dow, list):
                    dow_s = json.dumps(dow)
                elif isinstance(dow, str) and dow.strip().startswith("["):
                    dow_s = dow.strip()
                else:
                    dow_s = None
                hid = self.db.add_habit(
                    (data.get("name") or "").strip(),
                    (data.get("description") or "").strip(),
                    int(data.get("xp_reward") or 50),
                    dow_s,
                )
                broadcast_nexus_state(self)
                self._open_desktop_receipt(
                    "habits",
                    {
                        "highlight_id": hid,
                        "animate": "habit_add",
                        "toast": f"Hábito criado: {(data.get('name') or '').strip()}",
                        "receipt": {
                            "kind": "habit",
                            "action": "habit_add",
                            "id": hid,
                            "name": (data.get("name") or "").strip(),
                            "description": (data.get("description") or "").strip(),
                            "xp": int(data.get("xp_reward") or 50),
                            "days_of_week": dow_s,
                        },
                    },
                )
                return f"Habito criado id={hid}, Sir."
            if act == "task_add":
                tid = self.db.add_task(
                    (data.get("title") or "").strip(),
                    (data.get("due_date") or "").strip() or None,
                    int(data.get("points_reward") or 10),
                )
                broadcast_nexus_state(self)
                try:
                    from src.ui.nexus_signals import enqueue_nexus_desktop_open

                    enqueue_nexus_desktop_open("tasks", {"highlight_id": tid, "animate": "add"})
                except Exception:
                    pass
                return f"Tarefa #{tid} criada, Sir."
            if act == "task_complete":
                self.db.complete_task(int(data.get("task_id")))
                broadcast_nexus_state(self)
                return "Tarefa concluida."
            if act == "task_delete":
                self.db.delete_task(int(data.get("task_id")))
                broadcast_nexus_state(self)
                return "Tarefa removida."
            if act == "task_list":
                inc = data.get("include_done")
                if isinstance(inc, str):
                    inc = inc.lower() in ("1", "true", "yes")
                rows = self.db.list_tasks(data.get("due_date"), include_done=bool(inc))
                return json.dumps(rows, ensure_ascii=False)
            if act == "goal_add":
                return self.add_goal(
                    (data.get("name") or data.get("goal") or "").strip(),
                    (data.get("target_date") or "").strip() or None,
                )
            if act == "goal_update":
                return self.update_goal_progress(
                    (data.get("name") or data.get("goal") or "").strip(),
                    int(data.get("progress") or 0),
                )
            if act == "reward_redeem":
                ok_flag, msg = self.process_reward((data.get("reward_name") or data.get("name") or "").strip())
                return json.dumps({"ok": ok_flag, "message": msg}, ensure_ascii=False)
            if act == "reward_status":
                return json.dumps(
                    self.get_reward_status(int(data.get("limit") or 7)),
                    default=str,
                    ensure_ascii=False,
                )
            if act == "preset_apply_json":
                habits = data.get("habits")
                if isinstance(habits, str):
                    habits = json.loads(habits)
                return self.apply_preset_habits_json(habits or [])
            if act == "preset_save":
                return self.save_lifestyle_preset((data.get("name") or "").strip())
            if act == "preset_apply":
                return self.load_lifestyle_preset((data.get("name") or "").strip())
            if act == "preset_from_goals":
                goals = data.get("goals") or data.get("objectives") or data.get("goal") or ""
                return self.build_lifestyle_preset_from_goals(
                    goals,
                    (data.get("name") or data.get("preset_name") or "").strip() or None,
                )
            if act == "presets_list":
                return json.dumps(self.list_lifestyle_presets(), ensure_ascii=False)
            if act == "theme_list":
                return json.dumps(self.list_window_themes(), ensure_ascii=False)
            if act == "theme_apply":
                result = self.apply_window_theme(
                    data.get("module") or data.get("tab") or data.get("window"),
                    data.get("preset_id") or data.get("preset") or data.get("name"),
                )
                return json.dumps(result, ensure_ascii=False)
            if act == "theme_generate":
                result = self.generate_window_theme_preset(
                    data.get("module") or data.get("tab") or data.get("window"),
                    data.get("prompt") or data.get("description") or data.get("text") or "",
                    name=(data.get("name") or data.get("preset_name") or "").strip() or None,
                )
                return json.dumps(result, ensure_ascii=False)
            if act == "news_history":
                return json.dumps(
                    self.list_news_briefings(int(data.get("limit") or 8)),
                    ensure_ascii=False,
                )
            if act == "news_briefing":
                return json.dumps(
                    self.build_news_briefing(
                        data.get("query") or data.get("topic") or "",
                        limit=int(data.get("limit") or data.get("max_results") or 3),
                        results=data.get("results"),
                    ),
                    ensure_ascii=False,
                )
            if act == "news_save_note":
                return json.dumps(
                    self.save_news_item_to_note(
                        item=data.get("item"),
                        briefing=data.get("briefing"),
                        item_index=int(data.get("item_index") or data.get("index") or 1),
                        subject=data.get("subject") or "Noticias",
                    ),
                    ensure_ascii=False,
                )
            if act == "news_followup_task":
                return json.dumps(
                    self.create_news_followup_task(
                        item=data.get("item"),
                        briefing=data.get("briefing"),
                        item_index=int(data.get("item_index") or data.get("index") or 1),
                        due_date=data.get("due_date"),
                    ),
                    ensure_ascii=False,
                )
            if act == "news_flashcards_generate":
                return json.dumps(
                    self.create_news_flashcards(
                        item=data.get("item"),
                        briefing=data.get("briefing"),
                        item_index=int(data.get("item_index") or data.get("index") or 1),
                        subject=data.get("subject") or "Noticias",
                        max_cards=int(data.get("max_cards") or data.get("limit") or 4),
                    ),
                    ensure_ascii=False,
                )
            if act == "memory_graph":
                include_markdown = data.get("include_markdown", True)
                if isinstance(include_markdown, str):
                    include_markdown = include_markdown.strip().lower() not in ("0", "false", "no", "nao")
                return json.dumps(
                    self.build_memory_graph(
                        query=data.get("query") or data.get("text") or "",
                        limit=int(data.get("limit") or 120),
                        include_markdown=bool(include_markdown),
                    ),
                    default=str,
                    ensure_ascii=False,
                )
            if act in ("memory_graph_context", "memory_context"):
                include_markdown = data.get("include_markdown", True)
                if isinstance(include_markdown, str):
                    include_markdown = include_markdown.strip().lower() not in ("0", "false", "no", "nao")
                return json.dumps(
                    self.build_memory_graph_context(
                        query=data.get("query") or data.get("text") or data.get("question") or "",
                        limit=int(data.get("limit") or 8),
                        include_markdown=bool(include_markdown),
                    ),
                    default=str,
                    ensure_ascii=False,
                )
            if act == "memory_graph_export_obsidian":
                include_markdown = data.get("include_markdown", True)
                if isinstance(include_markdown, str):
                    include_markdown = include_markdown.strip().lower() not in ("0", "false", "no", "nao")
                return json.dumps(
                    self.export_memory_graph_obsidian(
                        data.get("folder") or data.get("path") or "",
                        query=data.get("query") or "",
                        include_markdown=bool(include_markdown),
                        limit=int(data.get("limit") or 160),
                    ),
                    default=str,
                    ensure_ascii=False,
                )
            if act == "memory_graph_import_obsidian":
                return json.dumps(
                    self.import_obsidian_markdown(
                        data.get("folder") or data.get("path") or "",
                        subject=data.get("subject") or "Obsidian",
                        limit=int(data.get("limit") or 80),
                    ),
                    default=str,
                    ensure_ascii=False,
                )
            if act == "ops_dashboard":
                open_window = data.get("open_window", True)
                if isinstance(open_window, str):
                    open_window = open_window.strip().lower() not in ("0", "false", "no", "nao")
                return json.dumps(
                    self.build_ops_dashboard(open_window=bool(open_window)),
                    default=str,
                    ensure_ascii=False,
                )
            if act in ("ops_metric_set", "ops_metric_update"):
                return json.dumps(
                    self.set_ops_metric(
                        data.get("key") or data.get("metric") or data.get("name"),
                        data.get("value") or data.get("amount"),
                        label=data.get("label") or data.get("name"),
                        unit=data.get("unit"),
                        target=data.get("target"),
                        trend=data.get("trend"),
                        period=data.get("period"),
                        notes=data.get("notes") or data.get("description"),
                    ),
                    default=str,
                    ensure_ascii=False,
                )
            if act == "open_ui":
                tab = (data.get("tab") or "dashboard").strip()
                return self.open_nexus_ui(tab)
            if act == "note_list":
                rows = self.db.list_study_notes(data.get("subject"))
                return json.dumps(rows, default=str, ensure_ascii=False)[:12000]
            if act == "note_get":
                n = self.db.get_study_note(int(data.get("note_id")))
                return json.dumps(n, default=str, ensure_ascii=False) if n else "Nao encontrado."
            if act == "note_save":
                msg = self.create_note(
                    (data.get("subject") or "Geral").strip(),
                    (data.get("title") or "Sem titulo").strip(),
                    (data.get("content") or "").strip(),
                    data.get("media"),
                )
                nid = getattr(self, "_last_created_note_id", None)
                try:
                    from src.ui.nexus_signals import enqueue_nexus_desktop_open

                    enqueue_nexus_desktop_open(
                        "notes", {"highlight_id": nid, "animate": "add"}
                    )
                except Exception:
                    pass
                return msg
            if act == "note_append":
                nid = int(data.get("note_id"))
                n = self.db.get_study_note(nid)
                if not n:
                    return "Nota nao encontrada."
                newc = (n.get("content") or "") + "\n\n" + (data.get("text") or "")
                self.db.update_study_note(nid, content=newc)
                broadcast_nexus_state(self)
                return "Nota atualizada."
            if act == "note_summarize":
                append = data.get("append_summary", data.get("append", True))
                if isinstance(append, str):
                    append = append.strip().lower() not in ("0", "false", "nao", "não", "no")
                return json.dumps(
                    self.summarize_note(
                        int(data.get("note_id")),
                        append=bool(append),
                        max_sentences=int(data.get("max_sentences") or 4),
                    ),
                    default=str,
                    ensure_ascii=False,
                )
            if act == "note_teach":
                return json.dumps(
                    self.teach_note(
                        int(data.get("note_id")),
                        question=data.get("question") or data.get("text") or "",
                        max_points=int(data.get("max_points") or data.get("limit") or 4),
                    ),
                    default=str,
                    ensure_ascii=False,
                )
            if act == "subject_teach":
                return json.dumps(
                    self.teach_subject(
                        data.get("subject") or data.get("materia") or "",
                        question=data.get("question") or data.get("text") or "",
                        max_points=int(data.get("max_points") or data.get("limit") or 6),
                    ),
                    default=str,
                    ensure_ascii=False,
                )
            if act == "note_attach_media":
                return json.dumps(
                    self.attach_media_to_note(
                        int(data.get("note_id")),
                        data.get("media_url") or data.get("url") or data.get("path") or "",
                        caption=data.get("caption"),
                        alt=data.get("alt"),
                    ),
                    default=str,
                    ensure_ascii=False,
                )
            if act == "flashcard_review":
                return self.review_flashcard_sm2(int(data["card_id"]), int(data.get("quality", 4)))
            if act == "flashcards_due":
                rows = self.db.list_flashcards_due(int(data.get("limit") or 20))
                return json.dumps(rows, default=str, ensure_ascii=False)
            if act == "flashcards_generate":
                limit = int(data.get("max_cards") or data.get("limit") or 8)
                if data.get("note_id"):
                    return json.dumps(
                        self.generate_flashcards_from_note(int(data["note_id"]), limit),
                        default=str,
                        ensure_ascii=False,
                    )
                return json.dumps(
                    self.generate_flashcards_from_subject((data.get("subject") or "").strip(), limit),
                    default=str,
                    ensure_ascii=False,
                )
            if act == "quiz_random":
                self.db.seed_quiz_if_empty()
                rows = self.db.random_quiz_questions(int(data.get("n") or 5), data.get("area"))
                return json.dumps(rows, default=str, ensure_ascii=False)
            if act == "quiz_attempt_review":
                return json.dumps(
                    self.review_quiz_attempt(int(data.get("attempt_id"))),
                    default=str,
                    ensure_ascii=False,
                )
            if act == "quiz_flashcards_generate":
                only_wrong = data.get("only_wrong", True)
                if isinstance(only_wrong, str):
                    only_wrong = only_wrong.strip().lower() not in ("0", "false", "no", "nao")
                return json.dumps(
                    self.generate_flashcards_from_quiz_attempt(
                        int(data.get("attempt_id")),
                        only_wrong=bool(only_wrong),
                        max_cards=int(data.get("max_cards") or data.get("limit") or 8),
                    ),
                    default=str,
                    ensure_ascii=False,
                )
            if act == "study_recommendations":
                return json.dumps(
                    self.get_study_recommendations(int(data.get("limit") or 4)),
                    default=str,
                    ensure_ascii=False,
                )
            if act == "morning_briefing":
                return self.generate_morning_briefing()
            if act == "proactive_suggestions":
                return self.get_proactive_suggestions()
        except Exception as e:
            logger.exception("nexus_command")
            return f"Erro Nexus: {e}"
        return f"Acao desconhecida: {act}"

    def generate_morning_briefing(self) -> str:
        """Agrega dados do dia e retorna JSON com resumo matinal estruturado."""
        today = date.today()
        today_str = today.isoformat()

        # --- tarefas pendentes de hoje ---
        with self.db._get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT title, priority, due_date FROM tasks
                WHERE is_deleted = 0 AND status != 'done'
                ORDER BY due_date ASC LIMIT 10
            """)
            tasks = [{"title": r[0], "priority": r[1], "due_date": r[2]} for r in c.fetchall()]

            # --- habitos ativos e streak ---
            c.execute("""
                SELECT name, current_streak, target_days FROM habits
                WHERE active = 1 AND is_deleted = 0
                ORDER BY current_streak DESC LIMIT 10
            """)
            habits = [{"name": r[0], "streak": r[1], "target": r[2]} for r in c.fetchall()]

            # --- eventos de hoje ---
            c.execute("""
                SELECT title, event_time, duration_minutes FROM calendar_events
                WHERE event_date = ? ORDER BY event_time ASC LIMIT 10
            """, (today_str,))
            events = [{"title": r[0], "time": r[1], "duration": r[2]} for r in c.fetchall()]

            # --- balanco financeiro do mes ---
            month_start = today.replace(day=1).isoformat()
            c.execute("""
                SELECT type, SUM(amount) FROM finance_transactions
                WHERE is_deleted = 0 AND occurred_at >= ?
                GROUP BY type
            """, (month_start,))
            fin_rows = {r[0]: float(r[1]) for r in c.fetchall()}
            income = fin_rows.get("income", 0)
            expense = fin_rows.get("expense", 0)
            balance = income - expense

        briefing = {
            "date": today_str,
            "greeting": f"Bom dia! Hoje é {today.strftime('%A, %d de %B de %Y')}.",
            "tasks_pending": tasks,
            "habits_active": habits,
            "events_today": events,
            "finance_month": {
                "income": income,
                "expense": expense,
                "balance": balance,
            },
            "summary": (
                f"{len(tasks)} tarefas pendentes, {len(habits)} hábitos ativos, "
                f"{len(events)} evento(s) hoje. "
                f"Balanço do mês: R$ {balance:+.2f}."
            ),
        }
        return json.dumps(briefing, ensure_ascii=False, default=str)

    def get_proactive_suggestions(self) -> str:
        """Analisa padrões e retorna sugestões acionáveis para o Jarvis."""
        suggestions = []
        today = date.today()
        seven_days_ago = (today - timedelta(days=7)).isoformat()

        with self.db._get_connection() as conn:
            c = conn.cursor()

            # 1. Hábitos com streak quebrando (último log > 1 dia atrás)
            c.execute("""
                SELECT h.name, h.current_streak, MAX(hl.completed_at) as last_log
                FROM habits h
                LEFT JOIN habit_logs hl ON hl.habit_id = h.id
                WHERE h.active = 1 AND h.is_deleted = 0
                GROUP BY h.id
                HAVING last_log IS NULL OR last_log < date('now', '-1 day')
                LIMIT 5
            """)
            for row in c.fetchall():
                name, streak, last = row
                suggestions.append({
                    "type": "habit_at_risk",
                    "priority": "high",
                    "message": f"⚠️ Hábito '{name}' (streak: {streak}) não foi registrado ontem. Risco de quebra!",
                    "action": f"Registre '{name}' hoje para manter o streak.",
                })

            # 2. Tarefas com prazo expirado
            c.execute("""
                SELECT title, due_date FROM tasks
                WHERE is_deleted = 0 AND status != 'done'
                  AND due_date < date('now') AND due_date IS NOT NULL
                ORDER BY due_date ASC LIMIT 5
            """)
            for row in c.fetchall():
                title, due = row
                suggestions.append({
                    "type": "overdue_task",
                    "priority": "high",
                    "message": f"🔴 Tarefa atrasada: '{title}' (prazo: {due}).",
                    "action": f"Complete ou reagende '{title}'.",
                })

            # 3. Gastos acima de 80% do budget da categoria
            c.execute("""
                SELECT fb.category, fb.monthly_limit,
                       COALESCE(SUM(ft.amount), 0) as spent
                FROM finance_budgets fb
                LEFT JOIN finance_transactions ft
                  ON ft.category = fb.category
                  AND ft.type = 'expense'
                  AND ft.occurred_at >= date('now', 'start of month')
                  AND ft.is_deleted = 0
                GROUP BY fb.category
                HAVING spent >= fb.monthly_limit * 0.8
                LIMIT 5
            """)
            for row in c.fetchall():
                cat, limit, spent = row
                pct = int((spent / limit) * 100) if limit else 0
                suggestions.append({
                    "type": "budget_alert",
                    "priority": "medium",
                    "message": f"💸 Categoria '{cat}': {pct}% do budget mensal usado (R$ {spent:.2f} / R$ {limit:.2f}).",
                    "action": "Revise seus gastos ou ajuste o orçamento.",
                })

            # 4. Sem treino nos últimos 3 dias
            c.execute("""
                SELECT COUNT(*) FROM fitness_workouts
                WHERE is_deleted = 0 AND started_at >= date('now', '-3 days')
            """)
            recent_workouts = c.fetchone()[0]
            if recent_workouts == 0:
                suggestions.append({
                    "type": "fitness_gap",
                    "priority": "medium",
                    "message": "🏋️ Nenhum treino registrado nos últimos 3 dias.",
                    "action": "Que tal um treino hoje? Registre no app!",
                })

            # 5. Metas sem progresso recente
            c.execute("""
                SELECT name, progress_pct FROM nexus_goals
                WHERE is_deleted = 0 AND progress_pct < 100
                  AND updated_at < date('now', '-7 days')
                LIMIT 3
            """)
            for row in c.fetchall():
                name, pct = row
                suggestions.append({
                    "type": "stale_goal",
                    "priority": "low",
                    "message": f"🎯 Meta '{name}' está em {pct}% sem atualização há mais de 7 dias.",
                    "action": f"Atualize o progresso da meta '{name}'.",
                })

        result = {
            "generated_at": datetime.now().isoformat(),
            "total": len(suggestions),
            "suggestions": suggestions,
        }
        return json.dumps(result, ensure_ascii=False, default=str)

