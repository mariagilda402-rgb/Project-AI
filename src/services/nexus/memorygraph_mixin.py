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




class NexusMemoryGraphMixin:
    def _graph_node(
        self,
        nodes: dict[str, dict],
        node_id: str,
        node_type: str,
        label: str,
        subtitle: str = "",
        cluster: str = "nexus",
        weight: float = 1.0,
        details: str = "",
        source: dict | None = None,
    ) -> None:
        if not node_id or node_id in nodes:
            return
        nodes[node_id] = {
            "id": node_id,
            "type": node_type,
            "label": str(label or node_type).strip()[:120],
            "subtitle": str(subtitle or "").strip()[:180],
            "cluster": str(cluster or node_type).strip()[:80],
            "weight": float(weight or 1.0),
            "details": str(details or "").strip()[:900],
            "source": source or {},
        }

    def _graph_edge(
        self,
        edges: dict[str, dict],
        source: str,
        target: str,
        edge_type: str,
        label: str = "",
        weight: float = 1.0,
    ) -> None:
        if not source or not target or source == target:
            return
        edge_id = f"{source}->{target}:{edge_type}"
        if edge_id in edges:
            return
        edges[edge_id] = {
            "id": edge_id,
            "source": source,
            "target": target,
            "type": edge_type,
            "label": str(label or edge_type).strip()[:80],
            "weight": float(weight or 1.0),
        }

    def _graph_text_summary(self, text: str | None, limit: int = 220) -> str:
        clean = re.sub(r"\s+", " ", str(text or "")).strip()
        if len(clean) <= limit:
            return clean
        return clean[: limit - 1].rstrip() + "..."

    def _graph_slug(self, value: str | None, fallback: str = "item") -> str:
        key = self._fold_key(value)
        if not key:
            key = self._fold_key(fallback)
        return key.replace(" ", "-") or "item"

    def _graph_keywords(self, *texts: str, limit: int = 5) -> list[str]:
        stop = {
            "sobre", "para", "como", "mais", "com", "uma", "que", "por", "dos", "das",
            "de", "da", "do", "em", "no", "na", "os", "as", "um", "ao", "aos", "e",
            "o", "a", "the", "and", "with", "from", "this", "that", "sem", "ser",
            "ter", "esta", "este", "isso", "essa", "esse", "todo", "todos",
        }
        raw = self._fold_key(" ".join(str(t or "") for t in texts))
        counts: dict[str, int] = {}
        for word in raw.split():
            if len(word) < 4 or word in stop:
                continue
            counts[word] = counts.get(word, 0) + 1
        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return [word for word, _ in ranked[: max(1, int(limit or 5))]]

    def _graph_semantic_topics(self, *texts: str) -> list[str]:
        folded = self._fold_key(" ".join(str(t or "") for t in texts))
        if not folded:
            return []
        topic_map = {
            "energia_solar": {
                "solar", "solares", "fotovoltaica", "fotovoltaicas", "placas",
                "radiacao", "renovavel", "eletricidade", "energia",
            },
            "enem_estudos": {
                "enem", "simulado", "simulados", "redacao", "vestibular",
                "questoes", "revisao", "revisoes", "flashcards", "estudo",
            },
            "ia_tecnologia": {
                "ia", "inteligencia", "artificial", "modelo", "modelos",
                "software", "digital", "algoritmo", "neural",
            },
            "financas": {
                "gasto", "gastos", "receita", "dinheiro", "orcamento",
                "divida", "cartao", "mercado", "investimento",
            },
            "saude_rotina": {
                "saude", "sono", "treino", "academia", "caminhar",
                "meditar", "habito", "rotina",
            },
        }
        topics = []
        words = set(folded.split())
        for topic, aliases in topic_map.items():
            if words & aliases:
                topics.append(topic)
        return topics

    def _graph_local_embedding(self, *texts: str, dimensions: int = 32) -> list[float]:
        terms = self._graph_keywords(*texts, limit=16) + self._graph_semantic_topics(*texts)
        if not terms:
            return []
        dims = max(8, min(96, int(dimensions or 32)))
        vec = [0.0] * dims
        for term in terms:
            slot = sum(ord(ch) for ch in term) % dims
            vec[slot] += 1.0 + min(1.0, len(term) / 14.0)
        norm = sum(value * value for value in vec) ** 0.5 or 1.0
        return [round(value / norm, 4) for value in vec]

    def _graph_vector_similarity(self, left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        return sum(a * b for a, b in zip(left, right))

    def _graph_node_search_text(self, node: dict) -> str:
        source = node.get("source") if isinstance(node.get("source"), dict) else {}
        source_text = " ".join(str(v) for v in source.values() if isinstance(v, (str, int, float)))
        return " ".join(
            str(part or "")
            for part in (
                node.get("label"),
                node.get("subtitle"),
                node.get("details"),
                node.get("type"),
                node.get("cluster"),
                source_text,
            )
        )

    def _graph_query_terms(self, query: str | None) -> list[str]:
        return self._graph_keywords(query or "", limit=8) if str(query or "").strip() else []

    def _graph_relevance_score(self, node: dict, query: str, terms: list[str]) -> float:
        if not terms:
            return 0.0
        text = self._fold_key(self._graph_node_search_text(node))
        label = self._fold_key(node.get("label"))
        folded_query = self._fold_key(query)
        keywords = set(node.get("keywords") or [])
        score = 0.0
        if folded_query and folded_query in label:
            score += 8.0
        elif folded_query and folded_query in text:
            score += 5.0
        for term in terms:
            if term in keywords:
                score += 2.4
            if term in label:
                score += 2.0
            elif term in text:
                score += 1.0
        type_bias = {
            "note": 1.8,
            "memory": 1.4,
            "markdown": 1.2,
            "flashcard": 0.9,
            "subject": 0.6,
            "task": 0.5,
            "habit": 0.4,
            "goal": 0.4,
            "reward": 0.2,
        }
        if score > 0:
            score += type_bias.get(str(node.get("type") or ""), 0.0)
        return round(score, 2)

    def _graph_match_payload(self, node: dict) -> dict:
        return {
            "id": node.get("id"),
            "type": node.get("type"),
            "label": node.get("label"),
            "subtitle": node.get("subtitle"),
            "details": node.get("details"),
            "cluster": node.get("cluster"),
            "source": node.get("source") or {},
            "keywords": list(node.get("keywords") or [])[:8],
            "relevance": float(node.get("relevance") or 0),
        }

    def _graph_add_semantic_edges(
        self,
        nodes: dict[str, dict],
        edges: dict[str, dict],
        query_terms: list[str],
        limit: int = 90,
    ) -> int:
        skip_types = {"core", "subject", "tag", "memory_category"}
        candidates = [
            node for node in nodes.values()
            if node.get("type") not in skip_types and node.get("keywords")
        ]
        existing_pairs = {
            frozenset((edge["source"], edge["target"]))
            for edge in edges.values()
            if edge.get("source") and edge.get("target")
        }
        scored: list[tuple[float, dict, dict, list[str]]] = []
        q_terms = set(query_terms or [])
        for idx, left in enumerate(candidates):
            left_terms = set(left.get("keywords") or [])
            left_topics = set(left.get("semantic_topics") or [])
            if not left_terms:
                continue
            for right in candidates[idx + 1:]:
                pair = frozenset((left["id"], right["id"]))
                if pair in existing_pairs:
                    continue
                right_terms = set(right.get("keywords") or [])
                right_topics = set(right.get("semantic_topics") or [])
                common = sorted(left_terms & right_terms)
                common_topics = sorted(left_topics & right_topics)
                vector_score = self._graph_vector_similarity(
                    left.get("_semantic_vector") or [],
                    right.get("_semantic_vector") or [],
                )
                if not common and not common_topics and vector_score < 0.52:
                    continue
                score = len(common) * 0.55
                score += len(common_topics) * 1.05
                score += max(0.0, vector_score - 0.38)
                if q_terms and (q_terms & set(common)):
                    score += 0.6
                if q_terms and common_topics:
                    score += 0.4
                if left.get("type") != right.get("type"):
                    score += 0.25
                if left.get("cluster") != right.get("cluster"):
                    score += 0.15
                if score < 0.95:
                    continue
                label_terms = common[:3] or common_topics[:2] or ["vetor-local"]
                edge_type = "semantic" if common_topics or (not common and vector_score >= 0.52) else "relates"
                scored.append((score, left, right, label_terms, edge_type))
        scored.sort(key=lambda row: (-row[0], row[1]["id"], row[2]["id"]))
        added = 0
        for score, left, right, common, edge_type in scored[: max(1, int(limit or 90))]:
            label = ", ".join(common[:3])
            before = len(edges)
            self._graph_edge(
                edges,
                left["id"],
                right["id"],
                edge_type,
                label or ("semantica local" if edge_type == "semantic" else "relacionado"),
                min(2.6, 0.75 + score),
            )
            if len(edges) > before:
                added += 1
        return added

    def _graph_structured_memory_path(self) -> Path:
        db_path = Path(getattr(self.db, "db_path", "data/nexus.db"))
        local = db_path.parent / "structured_memory.json"
        if local.exists():
            return local
        return Path("data/structured_memory.json")

    def _load_graph_structured_memory(self) -> dict:
        path = self._graph_structured_memory_path()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _graph_markdown_files(self, limit: int = 8) -> list[Path]:
        db_path = Path(getattr(self.db, "db_path", "data/nexus.db"))
        roots = [db_path.parent, Path("data/persona"), Path("docs"), Path(".")]
        seen: set[str] = set()
        out: list[Path] = []
        blocked = {".git", ".pytest_cache", "node_modules", "venv", ".venv", "ProjetosGithub"}
        for root in roots:
            try:
                root = root.resolve()
            except Exception:
                continue
            if not root.exists():
                continue
            for path in root.rglob("*.md"):
                parts = set(path.parts)
                if blocked & parts:
                    continue
                key = str(path.resolve()).lower()
                if key in seen:
                    continue
                seen.add(key)
                out.append(path)
                if len(out) >= limit:
                    return out
        return out

    def build_memory_graph(
        self,
        query: str | None = None,
        limit: int = 120,
        include_markdown: bool = True,
    ) -> dict:
        lim = max(20, min(240, int(limit or 120)))
        q = str(query or "").strip()
        nodes: dict[str, dict] = {}
        edges: dict[str, dict] = {}
        self._graph_node(
            nodes,
            "nexus:core",
            "core",
            "Nexus Life OS",
            "Memoria operacional local",
            "core",
            4.0,
            "Centro do grafo: notas, flashcards, memoria, rotinas e objetivos.",
        )

        notes = self.db.list_study_notes(None)[:lim]
        for note in notes:
            note_id = int(note.get("id") or 0)
            if not note_id:
                continue
            subject = (note.get("subject") or "Geral").strip() or "Geral"
            subject_id = f"subject:{self._graph_slug(subject)}"
            node_id = f"note:{note_id}"
            self._graph_node(nodes, subject_id, "subject", subject, "Materia / area", "study", 2.0)
            self._graph_edge(edges, "nexus:core", subject_id, "contains", "area", 1.5)
            self._graph_node(
                nodes,
                node_id,
                "note",
                note.get("title") or "Nota",
                subject,
                "study",
                2.4,
                self._graph_text_summary(note.get("content"), 420),
                {"note_id": note_id, "module": "notes"},
            )
            self._graph_edge(edges, subject_id, node_id, "contains", "nota", 2.0)
            for keyword in self._graph_keywords(note.get("title"), note.get("content"), limit=4):
                tag_id = f"tag:{keyword}"
                self._graph_node(nodes, tag_id, "tag", keyword, "Conceito recorrente", "tags", 1.2)
                self._graph_edge(edges, node_id, tag_id, "mentions", "menciona", 0.8)

        for card in self._graph_flashcards(max(10, lim // 3)):
            card_id = int(card.get("id") or 0)
            if not card_id:
                continue
            node_id = f"flashcard:{card_id}"
            note_id = int(card.get("note_id") or 0)
            self._graph_node(
                nodes,
                node_id,
                "flashcard",
                card.get("front") or "Flashcard",
                card.get("subject") or "SRS",
                "srs",
                1.6,
                self._graph_text_summary(card.get("back"), 260),
                {"card_id": card_id, "note_id": note_id, "module": "study"},
            )
            self._graph_edge(edges, f"note:{note_id}" if note_id else "nexus:core", node_id, "generates", "card", 1.2)

        for habit in self.db.get_habits()[: max(6, lim // 6)]:
            hid = int(habit.get("id") or 0)
            node_id = f"habit:{hid}"
            self._graph_node(
                nodes,
                node_id,
                "habit",
                habit.get("name") or "Habito",
                f"+{int(habit.get('xp_reward') or 0)} XP",
                "routine",
                1.8,
                habit.get("description") or "",
                {"habit_id": hid, "module": "habits"},
            )
            self._graph_edge(edges, "nexus:core", node_id, "drives", "rotina", 1.0)

        for task in self.db.list_tasks(include_done=False)[: max(6, lim // 6)]:
            tid = int(task.get("id") or 0)
            node_id = f"task:{tid}"
            self._graph_node(
                nodes,
                node_id,
                "task",
                task.get("title") or "Tarefa",
                task.get("due_date") or "Sem prazo",
                "tasks",
                1.7,
                f"Recompensa: {int(task.get('points_reward') or 0)} pontos",
                {"task_id": tid, "module": "tasks"},
            )
            self._graph_edge(edges, "nexus:core", node_id, "queues", "acao", 1.0)

        for goal in self.get_goals()[: max(5, lim // 8)]:
            gid = int(goal.get("id") or 0)
            node_id = f"goal:{gid}"
            self._graph_node(
                nodes,
                node_id,
                "goal",
                goal.get("name") or "Meta",
                f"{int(goal.get('progress') or 0)}% concluido",
                "goals",
                2.0,
                f"Data alvo: {goal.get('target_date') or 'sem data'}",
                {"goal_id": gid, "module": "goals"},
            )
            self._graph_edge(edges, "nexus:core", node_id, "aims", "meta", 1.2)

        for reward in self.get_rewards()[: max(5, lim // 8)]:
            rid = int(reward.get("id") or 0)
            node_id = f"reward:{rid}"
            self._graph_node(
                nodes,
                node_id,
                "reward",
                reward.get("name") or "Recompensa",
                f"{int(reward.get('cost') or 0)} pontos",
                "rewards",
                1.4,
                reward.get("description") or "",
                {"reward_id": rid, "module": "goals"},
            )
            self._graph_edge(edges, "nexus:core", node_id, "unlocks", "loja", 0.9)

        memory = self._load_graph_structured_memory()
        for category, rows in list(memory.items())[:10]:
            if not isinstance(rows, dict):
                continue
            category_id = f"memory-category:{self._graph_slug(category)}"
            self._graph_node(nodes, category_id, "memory_category", str(category), "Memoria estruturada", "memory", 1.6)
            self._graph_edge(edges, "nexus:core", category_id, "remembers", "memoria", 1.0)
            for key, value in list(rows.items())[:12]:
                if isinstance(value, dict):
                    detail = str(value.get("value") or "")
                    updated = str(value.get("updated") or "")
                else:
                    detail = str(value)
                    updated = ""
                memory_id = f"memory:{self._graph_slug(category)}:{self._graph_slug(key)}"
                self._graph_node(
                    nodes,
                    memory_id,
                    "memory",
                    str(key).replace("_", " "),
                    updated,
                    "memory",
                    1.7,
                    self._graph_text_summary(detail, 360),
                    {"category": category, "key": key},
                )
                self._graph_edge(edges, category_id, memory_id, "stores", "fato", 1.0)

        if include_markdown:
            for path in self._graph_markdown_files(max(4, lim // 12)):
                try:
                    content = path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                rel = str(path)
                node_id = f"markdown:{self._graph_slug(rel)}"
                title = path.stem.replace("_", " ").replace("-", " ")
                first = next((line.strip("# ").strip() for line in content.splitlines() if line.strip()), "")
                self._graph_node(
                    nodes,
                    node_id,
                    "markdown",
                    title,
                    rel,
                    "markdown",
                    1.5,
                    self._graph_text_summary(first or content, 280),
                    {"path": rel},
                )
                self._graph_edge(edges, "nexus:core", node_id, "documents", "md", 0.8)

        query_terms = self._graph_query_terms(q)
        for node in nodes.values():
            search_text = self._graph_node_search_text(node)
            folded_text = self._fold_key(search_text)
            keywords = self._graph_keywords(search_text, limit=10)
            for term in query_terms:
                if term in folded_text and term not in keywords:
                    keywords.append(term)
            node["keywords"] = keywords
            node["semantic_topics"] = self._graph_semantic_topics(search_text)
            node["_semantic_vector"] = self._graph_local_embedding(search_text)
            node["relevance"] = self._graph_relevance_score(node, q, query_terms)
        smart_edges = self._graph_add_semantic_edges(nodes, edges, query_terms, max(30, lim))

        utility_types = {"core", "tag", "subject", "memory_category"}
        ranked_nodes = sorted(
            (
                node for node in nodes.values()
                if float(node.get("relevance") or 0) > 0 and node.get("type") not in utility_types
            ),
            key=lambda node: (-float(node.get("relevance") or 0), -float(node.get("weight") or 0), str(node.get("label") or "")),
        )
        ranked_matches = [self._graph_match_payload(node) for node in ranked_nodes[:12]]
        if ranked_nodes:
            ranked_ids = {node["id"] for node in ranked_nodes}
            ordered_nodes = [nodes["nexus:core"]] + ranked_nodes + [
                node for node in nodes.values()
                if node["id"] != "nexus:core" and node["id"] not in ranked_ids
            ]
        else:
            ordered_nodes = list(nodes.values())

        node_list = ordered_nodes[:lim]
        node_ids = {node["id"] for node in node_list}
        edge_list = [
            edge for edge in edges.values()
            if edge["source"] in node_ids and edge["target"] in node_ids
        ]
        smart_edges = sum(1 for edge in edge_list if edge.get("type") == "relates")
        semantic_edges = sum(1 for edge in edge_list if edge.get("type") == "semantic")
        for node in node_list:
            node.pop("_semantic_vector", None)
        type_counts: dict[str, int] = {}
        cluster_counts: dict[str, int] = {}
        for node in node_list:
            type_counts[node["type"]] = type_counts.get(node["type"], 0) + 1
            cluster_counts[node["cluster"]] = cluster_counts.get(node["cluster"], 0) + 1
        return {
            "ok": True,
            "query": q,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "nodes": node_list,
            "edges": edge_list,
            "clusters": cluster_counts,
            "ranked_matches": ranked_matches,
            "stats": {
                "nodes": len(node_list),
                "edges": len(edge_list),
                "smart_edges": smart_edges,
                "semantic_edges": semantic_edges,
                "semantic_mode": "local",
                "types": type_counts,
                "clusters": cluster_counts,
            },
        }

    def export_memory_graph_obsidian(
        self,
        folder,
        query: str | None = "",
        include_markdown: bool = True,
        limit: int = 160,
    ) -> dict:
        target = Path(folder).expanduser()
        if target.exists() and not target.is_dir():
            return {"ok": False, "count": 0, "files": [], "error": "Destino nao e uma pasta."}
        target.mkdir(parents=True, exist_ok=True)
        graph = self.build_memory_graph(query=query, limit=limit, include_markdown=include_markdown)
        utility = {"core", "tag", "subject", "memory_category"}
        export_nodes = [node for node in graph.get("nodes", []) if node.get("type") not in utility]
        filename_by_id: dict[str, str] = {}
        used: set[str] = set()
        for node in export_nodes:
            base = self._obsidian_safe_filename(node.get("label") or node.get("id"), "Nexus Note")
            name = base
            suffix = 2
            while name.lower() in used:
                name = f"{base} {suffix}"
                suffix += 1
            used.add(name.lower())
            filename_by_id[node["id"]] = name

        files: list[str] = []
        index_lines = [
            "# Nexus Memory Graph",
            "",
            f"- Query: {query or 'tudo'}",
            f"- Gerado em: {datetime.now().isoformat(timespec='seconds')}",
            f"- Nos exportados: {len(export_nodes)}",
            "",
            "## Nos",
        ]
        for node in export_nodes:
            file_stem = filename_by_id[node["id"]]
            index_lines.append(f"- [[{file_stem}]] - {node.get('type')} - {node.get('subtitle') or ''}")
        index_path = target / "Nexus Memory Graph.md"
        index_path.write_text("\n".join(index_lines).strip() + "\n", encoding="utf-8")
        files.append(str(index_path))

        edge_map: dict[str, list[dict]] = {}
        for edge in graph.get("edges", []):
            if edge.get("source") in filename_by_id and edge.get("target") in filename_by_id:
                edge_map.setdefault(edge["source"], []).append(edge)
                edge_map.setdefault(edge["target"], []).append(edge)

        for node in export_nodes:
            file_stem = filename_by_id[node["id"]]
            path = target / f"{file_stem}.md"
            source = node.get("source") if isinstance(node.get("source"), dict) else {}
            topics = ", ".join(node.get("semantic_topics") or [])
            lines = [
                "---",
                f'nexus_id: "{node.get("id")}"',
                f'type: "{node.get("type")}"',
                f'cluster: "{node.get("cluster")}"',
                f'semantic_topics: "{topics}"',
                "---",
                "",
                f"# {node.get('label') or file_stem}",
                "",
                node.get("details") or node.get("subtitle") or "Sem detalhes.",
                "",
                "## Origem",
            ]
            for key, value in source.items():
                lines.append(f"- {key}: {value}")
            lines.extend(["", "## Conexoes"])
            connections = edge_map.get(node["id"], [])
            if connections:
                for edge in connections[:24]:
                    other = edge["target"] if edge.get("source") == node["id"] else edge.get("source")
                    other_name = filename_by_id.get(other)
                    if other_name:
                        lines.append(f"- [[{other_name}]] ({edge.get('type')}: {edge.get('label')})")
            else:
                lines.append("- Sem conexoes exportadas.")
            path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
            files.append(str(path))

        return {
            "ok": True,
            "folder": str(target),
            "count": len(export_nodes),
            "files": files,
            "message": f"{len(export_nodes)} notas exportadas para Obsidian.",
        }

    def build_memory_graph_context(
        self,
        query: str | None,
        limit: int = 8,
        include_markdown: bool = True,
    ) -> dict:
        q = str(query or "").strip()
        match_limit = max(1, min(12, int(limit or 8)))
        graph = self.build_memory_graph(
            query=q,
            limit=max(80, match_limit * 24),
            include_markdown=include_markdown,
        )
        node_by_id = {node["id"]: node for node in graph.get("nodes", [])}
        ranked = graph.get("ranked_matches") or [
            self._graph_match_payload(node)
            for node in sorted(
                graph.get("nodes", []),
                key=lambda node: (-float(node.get("weight") or 0), str(node.get("label") or "")),
            )
            if node.get("type") != "core"
        ]
        matches: list[dict] = []
        suggested_modules: set[str] = set()
        for match in ranked[:match_limit]:
            node_id = match.get("id")
            related: list[dict] = []
            for edge in graph.get("edges", []):
                other_id = ""
                if edge.get("source") == node_id:
                    other_id = edge.get("target") or ""
                elif edge.get("target") == node_id:
                    other_id = edge.get("source") or ""
                if not other_id or other_id == "nexus:core" or other_id not in node_by_id:
                    continue
                other = node_by_id[other_id]
                related.append(
                    {
                        "id": other.get("id"),
                        "type": other.get("type"),
                        "label": other.get("label"),
                        "subtitle": other.get("subtitle"),
                        "details": other.get("details"),
                        "source": other.get("source") or {},
                        "edge_type": edge.get("type"),
                        "edge_label": edge.get("label"),
                        "weight": float(edge.get("weight") or 1),
                    }
                )
            related.sort(key=lambda item: (-float(item.get("weight") or 0), str(item.get("label") or "")))
            source = match.get("source") or {}
            if source.get("module"):
                suggested_modules.add(str(source["module"]))
            for item in related[:4]:
                module = (item.get("source") or {}).get("module")
                if module:
                    suggested_modules.add(str(module))
            enriched = dict(match)
            enriched["related"] = related[:5]
            matches.append(enriched)

        lines = [f"Contexto do grafo para '{q or 'visao geral'}':"]
        for match in matches:
            title = match.get("label") or match.get("id")
            node_type = match.get("type") or "item"
            detail = match.get("details") or match.get("subtitle") or ""
            lines.append(f"- {title} ({node_type}): {self._graph_text_summary(detail, 180)}")
            for item in match.get("related", [])[:3]:
                rel = item.get("edge_label") or item.get("edge_type") or "relacionado"
                lines.append(f"  conectado a {item.get('label')}: {rel}")

        return {
            "ok": True,
            "query": q,
            "generated_at": graph.get("generated_at"),
            "matches": matches,
            "suggested_modules": sorted(suggested_modules),
            "context_text": "\n".join(lines)[:5000],
            "graph_stats": graph.get("stats") or {},
        }

