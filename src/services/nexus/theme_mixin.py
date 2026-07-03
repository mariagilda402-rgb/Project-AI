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




class NexusThemeMixin:
    def _window_theme_store_path(self) -> Path:
        db_path = Path(getattr(self.db, "db_path", "data/nexus.db"))
        return db_path.parent / "nexus_window_themes.json"

    def _slug_theme_id(self, value: str | None, fallback: str = "tema-nexus") -> str:
        folded = self._fold_key(value)
        slug = re.sub(r"[^a-z0-9]+", "-", folded).strip("-")
        return (slug or fallback)[:64]

    def _clean_theme_tokens(self, tokens: dict | None) -> dict:
        if not isinstance(tokens, dict):
            return {}
        clean = {}
        for key in sorted(_NEXUS_THEME_TOKEN_KEYS):
            if key not in tokens:
                continue
            value = str(tokens.get(key) or "").strip()
            if not value:
                continue
            if any(ch in value for ch in ['"', "'", "<", ">", "{", "}"]):
                continue
            if len(value) > 96:
                continue
            clean[key] = value
        return clean

    def _normalize_theme_preset(self, preset: dict, custom: bool = False) -> dict:
        pid = self._slug_theme_id(preset.get("id") or preset.get("name"))
        mode = str(preset.get("mode") or "dark").strip().lower()
        return {
            "id": pid,
            "name": str(preset.get("name") or pid).strip()[:80],
            "mode": "light" if mode == "light" else "dark",
            "description": str(preset.get("description") or "").strip()[:180],
            "tokens": self._clean_theme_tokens(preset.get("tokens")),
            "custom": bool(custom),
        }

    def _load_window_theme_store(self) -> dict:
        path = self._window_theme_store_path()
        raw = {}
        if path.is_file():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                raw = {}
        modules = {}
        for module, preset_id in dict(raw.get("modules") or {}).items():
            mod = self._normalize_window_module(module)
            if mod:
                modules[mod] = self._slug_theme_id(str(preset_id or ""))
        custom_presets = {}
        for pid, preset in dict(raw.get("presets") or {}).items():
            if isinstance(preset, dict):
                normalized = self._normalize_theme_preset({**preset, "id": pid}, custom=True)
                custom_presets[normalized["id"]] = normalized
        presets = {
            pid: self._normalize_theme_preset(preset, custom=False)
            for pid, preset in _DEFAULT_WINDOW_THEME_PRESETS.items()
        }
        presets.update(custom_presets)
        modules = {
            module: preset_id
            for module, preset_id in modules.items()
            if preset_id in presets
        }
        return {
            "version": 1,
            "modules": modules,
            "custom_presets": custom_presets,
            "presets": presets,
        }

    def _save_window_theme_store(self, modules: dict, custom_presets: dict) -> None:
        path = self._window_theme_store_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "modules": {
                module: preset_id
                for module, preset_id in sorted(modules.items())
                if module in _NEXUS_WINDOW_MODULES
            },
            "presets": {
                pid: {
                    "id": preset["id"],
                    "name": preset["name"],
                    "mode": preset["mode"],
                    "description": preset.get("description") or "",
                    "tokens": self._clean_theme_tokens(preset.get("tokens")),
                }
                for pid, preset in sorted(custom_presets.items())
            },
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def list_window_themes(self) -> dict:
        store = self._load_window_theme_store()
        assignments = dict(store["modules"])
        presets = list(store["presets"].values())
        presets.sort(key=lambda item: (item.get("custom", False), item["name"].lower()))
        modules = []
        for module_id, label in _NEXUS_WINDOW_MODULES.items():
            preset_id = assignments.get(module_id, _DEFAULT_WINDOW_THEME_ID)
            preset = store["presets"].get(preset_id) or store["presets"][_DEFAULT_WINDOW_THEME_ID]
            modules.append(
                {
                    "id": module_id,
                    "label": label,
                    "preset_id": preset["id"],
                    "preset_name": preset["name"],
                }
            )
        return {
            "modules": modules,
            "presets": presets,
            "assignments": assignments,
        }

    def get_window_theme_boot(self, module: str | None) -> dict:
        mod = self._normalize_window_module(module) or "overview"
        store = self._load_window_theme_store()
        preset_id = store["modules"].get(mod, _DEFAULT_WINDOW_THEME_ID)
        preset = store["presets"].get(preset_id) or store["presets"][_DEFAULT_WINDOW_THEME_ID]
        return {
            "module": mod,
            "theme": preset["mode"],
            "theme_preset": preset["id"],
            "theme_name": preset["name"],
            "theme_tokens": self._clean_theme_tokens(preset.get("tokens")),
        }

    def apply_window_theme(self, module: str | None, preset_id: str | None) -> dict:
        mod = self._normalize_window_module(module)
        if not mod:
            return {"ok": False, "error": f"Modulo Nexus invalido: {module}"}
        store = self._load_window_theme_store()
        pid = self._slug_theme_id(preset_id)
        preset = store["presets"].get(pid)
        if not preset:
            return {"ok": False, "error": f"Preset de tema nao encontrado: {preset_id}"}
        modules = dict(store["modules"])
        modules[mod] = pid
        self._save_window_theme_store(modules, store["custom_presets"])
        broadcast_nexus_state(self)
        boot = self.get_window_theme_boot(mod)
        msg = f"Tema '{preset['name']}' aplicado em {_NEXUS_WINDOW_MODULES[mod]}."
        self._open_desktop_receipt(
            mod,
            {
                **boot,
                "animate": "theme_apply",
                "toast": msg,
                "receipt": {
                    "kind": "theme",
                    "action": "theme_apply",
                    "module": mod,
                    "preset_id": pid,
                    "name": preset["name"],
                },
            },
        )
        log_nexus_event(f"THEME: {mod} -> {pid}")
        return {
            "ok": True,
            "module": mod,
            "preset": preset,
            "assignment": {mod: pid},
            "boot": boot,
            "message": msg,
        }

    def _generated_theme_tokens(self, accent: str, mode: str) -> dict:
        palettes = {
            "#10b981": ("16,185,129", "#059669"),
            "#38bdf8": ("56,189,248", "#0ea5e9"),
            "#f59e0b": ("245,158,11", "#d97706"),
            "#f472b6": ("244,114,182", "#db2777"),
            "#ef4444": ("239,68,68", "#dc2626"),
            "#8b5cf6": ("139,92,246", "#7c3aed"),
        }
        rgb, hover = palettes.get(accent, palettes["#8b5cf6"])
        if mode == "light":
            return {
                "--bg": "#fbfcff",
                "--bg-panel": "#ffffff",
                "--surface": f"rgba({rgb},0.055)",
                "--surface-hover": f"rgba({rgb},0.095)",
                "--border": "rgba(15,23,42,0.12)",
                "--border-accent": f"rgba({rgb},0.42)",
                "--text": "#111827",
                "--text-dim": "#5b6475",
                "--text-muted": "#7a8496",
                "--muted": "#6b7280",
                "--accent": accent,
                "--accent-hover": hover,
                "--accent-glow": f"rgba({rgb},0.26)",
                "--accent-subtle": f"rgba({rgb},0.10)",
                "--sidebar": "#eef2ff",
                "--shadow": f"0 22px 55px rgba({rgb},0.14)",
            }
        return {
            "--bg": "#06070b",
            "--bg-panel": "#0d1118",
            "--surface": f"rgba({rgb},0.08)",
            "--surface-hover": f"rgba({rgb},0.14)",
            "--border": f"rgba({rgb},0.16)",
            "--border-accent": f"rgba({rgb},0.46)",
            "--text": "#f4f7fb",
            "--text-dim": "#9aa9ba",
            "--text-muted": "#667487",
            "--muted": "#8b98a8",
            "--accent": accent,
            "--accent-hover": hover,
            "--accent-glow": f"rgba({rgb},0.32)",
            "--accent-subtle": f"rgba({rgb},0.10)",
            "--sidebar": "#030509",
            "--shadow": f"0 0 34px rgba({rgb},0.16)",
        }

    def generate_window_theme_preset(self, module: str | None, prompt: str | None, name: str | None = None) -> dict:
        mod = self._normalize_window_module(module)
        if not mod:
            return {"ok": False, "error": f"Modulo Nexus invalido: {module}"}
        folded = self._fold_key(prompt)
        mode = "light" if any(word in folded for word in ["claro", "light", "clean", "branco", "solar"]) else "dark"
        if any(word in folded for word in ["verde", "financa", "dinheiro", "invest", "emerald"]):
            accent = "#10b981"
            mood = "Emerald"
        elif any(word in folded for word in ["azul", "estudo", "foco", "srs", "nota", "cyan"]):
            accent = "#38bdf8"
            mood = "Cyan"
        elif any(word in folded for word in ["dourado", "gold", "luxo", "premium", "solar"]):
            accent = "#f59e0b"
            mood = "Solar"
        elif any(word in folded for word in ["rosa", "pink", "anime", "magenta"]):
            accent = "#f472b6"
            mood = "Rose"
        elif any(word in folded for word in ["vermelho", "red", "stark"]):
            accent = "#ef4444"
            mood = "Redline"
        else:
            accent = "#8b5cf6"
            mood = "Neon"
        preset_name = (name or "").strip() or f"{mood} {_NEXUS_WINDOW_MODULES[mod]}"
        pid = self._slug_theme_id(preset_name)
        store = self._load_window_theme_store()
        if pid in _DEFAULT_WINDOW_THEME_PRESETS:
            pid = f"{pid}-custom"
        preset = {
            "id": pid,
            "name": preset_name[:80],
            "mode": mode,
            "description": f"Preset gerado para {_NEXUS_WINDOW_MODULES[mod]}.",
            "tokens": self._generated_theme_tokens(accent, mode),
            "custom": True,
        }
        custom_presets = dict(store["custom_presets"])
        custom_presets[pid] = preset
        modules = dict(store["modules"])
        modules[mod] = pid
        self._save_window_theme_store(modules, custom_presets)
        broadcast_nexus_state(self)
        boot = self.get_window_theme_boot(mod)
        msg = f"Tema '{preset_name}' gerado e aplicado em {_NEXUS_WINDOW_MODULES[mod]}."
        self._open_desktop_receipt(
            mod,
            {
                **boot,
                "animate": "theme_apply",
                "toast": msg,
                "receipt": {
                    "kind": "theme",
                    "action": "theme_generate",
                    "module": mod,
                    "preset_id": pid,
                    "name": preset_name,
                },
            },
        )
        log_nexus_event(f"THEME: generated {pid} for {mod}")
        return {
            "ok": True,
            "module": mod,
            "preset": preset,
            "assignment": {mod: pid},
            "boot": boot,
            "message": msg,
        }

