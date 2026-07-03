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




class NexusOpsMixin:
    def handle_nexus_batch(self, steps, hold_ms: int = 1400) -> str:
        if isinstance(steps, str):
            try:
                steps = json.loads(steps)
            except json.JSONDecodeError:
                steps = []
        if not isinstance(steps, list) or not steps:
            return json.dumps(
                {"ok": False, "error": "nexus_batch requer uma lista steps."},
                ensure_ascii=False,
            )

        batch_id = "nx-" + datetime.now().strftime("%Y%m%d%H%M%S%f")
        previous = self._active_nexus_batch
        results = []
        total = len(steps)
        try:
            for idx, raw_step in enumerate(steps, 1):
                if not isinstance(raw_step, dict):
                    results.append(
                        {
                            "step": idx,
                            "action": "",
                            "ok": False,
                            "message": "Passo ignorado: formato invalido.",
                        }
                    )
                    continue
                step = dict(raw_step)
                action = (step.get("action") or "").strip().lower()
                if action == "nexus_batch":
                    results.append(
                        {
                            "step": idx,
                            "action": action,
                            "ok": False,
                            "message": "Batch aninhado ignorado.",
                        }
                    )
                    continue
                self._active_nexus_batch = {
                    "id": batch_id,
                    "step": idx,
                    "total": total,
                    "hold_ms": hold_ms,
                }
                message = self.handle_structured_command(step)
                ok = not str(message).startswith(("Erro Nexus:", "Acao desconhecida:"))
                results.append(
                    {
                        "step": idx,
                        "action": action,
                        "ok": ok,
                        "message": message,
                    }
                )
        finally:
            self._active_nexus_batch = previous

        # -- Emitir sinal para o HUD Animado --
        hud_items = []
        for i, res in enumerate(results):
            if res.get("ok"):
                raw_step = steps[i]
                action = res.get("action", "")
                label = raw_step.get("name") or raw_step.get("title") or raw_step.get("front") or raw_step.get("subject") or "Novo registro"
                
                t = "default"
                xp = 0
                if "habit" in action: 
                    t = "habit"
                    xp = 10
                elif "task" in action: 
                    t = "task"
                    xp = 15
                elif "note" in action or "flashcard" in action: 
                    t = "note"
                    xp = 5
                elif "finance" in action or "expense" in action or "income" in action: 
                    t = "finance"
                elif "goal" in action: 
                    t = "goal"
                    xp = 20
                    
                hud_items.append({"label": label, "type": t, "xp": xp})
                
        if hud_items and hasattr(self, "emit_hud_signal"):
            self.emit_hud_signal(
                title="Sincronização Neural",
                subtitle="Processando lote...",
                items=hud_items,
                done_subtitle="Registros inseridos no Nexus"
            )

        return json.dumps(
            {
                "ok": all(item.get("ok") for item in results),
                "batch_id": batch_id,
                "steps": results,
            },
            ensure_ascii=False,
        )

    def _ops_store_path(self) -> Path:
        db_path = Path(getattr(self.db, "db_path", "data/nexus.db"))
        return db_path.parent / "nexus_ops_dashboard.json"

    def _ops_metric_key(self, value: str | None) -> str:
        folded = self._fold_key(value)
        slug = re.sub(r"[^a-z0-9]+", "_", folded).strip("_")
        return (slug or "metric")[:64]

    def _parse_ops_number(self, value) -> float:
        if value in (None, ""):
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        raw = str(value).strip().replace("R$", "").replace("%", "")
        raw = re.sub(r"[^0-9,.\-]", "", raw)
        if "," in raw and raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", ".")
        return float(raw or 0)

    def _ops_metric_sort_key(self, metric: dict) -> tuple[int, str]:
        order = {
            "mrr": 0,
            "revenue": 1,
            "downloads": 2,
            "roas": 3,
            "refunds": 4,
            "churn": 5,
        }
        return (order.get(metric.get("key"), 50), str(metric.get("label") or metric.get("key") or ""))

    def _ops_format_value(self, value: float, unit: str | None) -> str:
        unit_key = (unit or "").strip().lower()
        if unit_key in ("brl", "r$", "real", "reais"):
            return "R$ " + f"{float(value):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
        if unit_key in ("percent", "pct", "%"):
            return f"{float(value):.1f}%".replace(".", ",")
        if unit_key in ("ratio", "roas", "x"):
            return f"{float(value):.2f}x".replace(".", ",")
        if abs(float(value) - round(float(value))) < 0.0001:
            return str(int(round(float(value))))
        return f"{float(value):.2f}".replace(".", ",")

    def _normalize_ops_metric(self, metric: dict) -> dict:
        key = self._ops_metric_key(str(metric.get("key") or metric.get("label") or "metric"))
        value = self._parse_ops_number(metric.get("value"))
        target_raw = metric.get("target")
        target = self._parse_ops_number(target_raw) if target_raw not in (None, "") else None
        label = str(metric.get("label") or key.replace("_", " ").title()).strip()[:80]
        unit = str(metric.get("unit") or "").strip()[:24]
        trend = str(metric.get("trend") or "flat").strip().lower()[:24]
        period = str(metric.get("period") or "atual").strip()[:48]
        notes = str(metric.get("notes") or metric.get("note") or "").strip()[:240]
        lower_is_better = key in {"refunds", "reembolsos", "churn", "cac", "bugs", "crashes"} or (
            trend == "down" and key not in {"downloads"}
        )
        target_hit = False
        progress = 0
        gap = 0.0
        if target is not None:
            if lower_is_better:
                target_hit = value <= target
                if target <= 0:
                    progress = 100 if value <= 0 else 0
                    gap = max(0.0, value - target)
                else:
                    progress = round(max(0.0, min(100.0, (1 - max(0.0, value - target) / target) * 100)))
                    gap = max(0.0, value - target)
            else:
                target_hit = value >= target
                progress = round(max(0.0, min(160.0, (value / target) * 100))) if target > 0 else 0
                gap = max(0.0, target - value)
        return {
            "key": key,
            "label": label,
            "value": value,
            "value_label": self._ops_format_value(value, unit),
            "unit": unit,
            "target": target,
            "target_label": self._ops_format_value(target, unit) if target is not None else "",
            "target_hit": target_hit,
            "lower_is_better": lower_is_better,
            "progress": progress,
            "gap": gap,
            "gap_label": self._ops_format_value(gap, unit),
            "trend": trend if trend in {"up", "down", "flat"} else "flat",
            "period": period,
            "notes": notes,
            "updated_at": str(metric.get("updated_at") or datetime.now().isoformat(timespec="seconds")),
        }

    def _load_ops_store(self) -> dict:
        path = self._ops_store_path()
        raw = {}
        if path.is_file():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                raw = {}
        metrics = {}
        for key, metric in dict(raw.get("metrics") or {}).items():
            if isinstance(metric, dict):
                normalized = self._normalize_ops_metric({**metric, "key": key})
                metrics[normalized["key"]] = normalized
        events = [e for e in list(raw.get("events") or []) if isinstance(e, dict)][-80:]
        return {"version": 1, "metrics": metrics, "events": events}

    def _save_ops_store(self, store: dict) -> None:
        path = self._ops_store_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "metrics": {
                key: metric
                for key, metric in sorted(dict(store.get("metrics") or {}).items())
            },
            "events": list(store.get("events") or [])[-80:],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _default_ops_metrics(self) -> list[dict]:
        return [
            self._normalize_ops_metric({"key": "mrr", "label": "MRR", "value": 0, "unit": "BRL", "target": 0, "period": "mes"}),
            self._normalize_ops_metric({"key": "downloads", "label": "Downloads", "value": 0, "unit": "count", "target": 0, "period": "7 dias"}),
            self._normalize_ops_metric({"key": "roas", "label": "ROAS anuncios", "value": 0, "unit": "ratio", "target": 1.2, "period": "7 dias"}),
            self._normalize_ops_metric({"key": "refunds", "label": "Reembolsos", "value": 0, "unit": "count", "target": 0, "trend": "down", "period": "7 dias"}),
        ]

    def _build_ops_recommendations(self, metrics: list[dict]) -> list[dict]:
        by_key = {m["key"]: m for m in metrics}
        recs: list[dict] = []
        mrr = by_key.get("mrr") or by_key.get("revenue")
        if mrr:
            if mrr.get("target_hit"):
                recs.append(
                    {
                        "priority": "alta",
                        "title": "Meta de receita batida",
                        "action": "Aumentar a proxima meta e proteger retencao antes de escalar mais aquisicao.",
                        "reason": f"{mrr['label']} esta em {mrr['value_label']} contra alvo de {mrr.get('target_label') or 'sem alvo'}.",
                    }
                )
            elif mrr.get("target") is not None:
                recs.append(
                    {
                        "priority": "alta",
                        "title": "Receita abaixo do alvo",
                        "action": f"Priorizar ofertas e canais que cubram {mrr['gap_label']} restantes.",
                        "reason": f"{mrr['label']} esta em {mrr['progress']}% da meta.",
                    }
                )
        roas = by_key.get("roas")
        if roas:
            if roas.get("value", 0) >= max(1.2, float(roas.get("target") or 1.2)):
                recs.append(
                    {
                        "priority": "media",
                        "title": "Anuncios com retorno positivo",
                        "action": "Dobrar ou aumentar gradualmente o budget do criativo vencedor e monitorar payback.",
                        "reason": f"ROAS atual em {roas['value_label']}.",
                    }
                )
            elif roas.get("value", 0) > 0:
                recs.append(
                    {
                        "priority": "media",
                        "title": "ROAS precisa de ajuste",
                        "action": "Pausar variacoes fracas e testar novo angulo de criativo antes de subir budget.",
                        "reason": f"ROAS atual em {roas['value_label']}.",
                    }
                )
        downloads = by_key.get("downloads")
        if downloads and downloads.get("value", 0) > 0:
            recs.append(
                {
                    "priority": "media",
                    "title": "Aquisicao em movimento",
                    "action": "Transformar o canal vencedor em checklist semanal de criativos e landing page.",
                    "reason": f"{downloads['value_label']} downloads no periodo {downloads.get('period') or 'atual'}.",
                }
            )
        refunds = by_key.get("refunds") or by_key.get("reembolsos")
        if refunds and refunds.get("target_hit"):
            recs.append(
                {
                    "priority": "baixa",
                    "title": "Qualidade operacional estavel",
                    "action": "Manter monitoramento de suporte e coletar depoimentos enquanto reembolsos estao zerados.",
                    "reason": f"Reembolsos em {refunds['value_label']}.",
                }
            )
        for metric in metrics:
            if len(recs) >= 6:
                break
            if metric.get("target") is not None and not metric.get("target_hit") and metric["key"] not in {"mrr", "revenue", "roas"}:
                recs.append(
                    {
                        "priority": "media",
                        "title": f"Ajustar {metric['label']}",
                        "action": f"Criar uma tarefa de acompanhamento para fechar gap de {metric['gap_label']}.",
                        "reason": f"{metric['label']} esta em {metric['progress']}% da meta.",
                    }
                )
        if not recs:
            recs.append(
                {
                    "priority": "baixa",
                    "title": "Sem dados suficientes",
                    "action": "Registrar MRR, downloads, ROAS e reembolsos para o Jarvis montar uma leitura executiva.",
                    "reason": "O painel Ops ainda esta vazio.",
                }
            )
        return recs[:6]

    def set_ops_metric(
        self,
        key: str | None,
        value,
        label: str | None = None,
        unit: str | None = None,
        target=None,
        trend: str | None = None,
        period: str | None = None,
        notes: str | None = None,
    ) -> dict:
        store = self._load_ops_store()
        metric = self._normalize_ops_metric(
            {
                "key": key or label or "metric",
                "label": label,
                "value": value,
                "unit": unit,
                "target": target,
                "trend": trend,
                "period": period,
                "notes": notes,
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
        store["metrics"][metric["key"]] = metric
        store.setdefault("events", []).append(
            {
                "type": "metric_set",
                "key": metric["key"],
                "label": metric["label"],
                "value_label": metric["value_label"],
                "created_at": metric["updated_at"],
            }
        )
        self._save_ops_store(store)
        log_nexus_event(f"OPS: {metric['label']} = {metric['value_label']}")
        return {
            "ok": True,
            "metric": metric,
            "message": f"Metrica {metric['label']} atualizada, Sir.",
        }

