from __future__ import annotations

import threading
import time

from src.tools.base import Tool, ToolResult
from src.tools.critical_actions import FILE_ACTIONS_NEED_CONFIRM
from src.tools.critical_confirm import CriticalConfirmationBus
from src.telemetry.events import log_event


class ToolRegistry:
    def __init__(
        self,
        tools: list[Tool],
        require_critical_confirmation: bool = True,
        confirm_bus: CriticalConfirmationBus | None = None,
    ) -> None:
        self.tools = tools
        self.require_critical_confirmation = require_critical_confirmation
        self._confirm_bus = confirm_bus
        self._recent_lock = threading.Lock()
        self._recent_tools: list[dict] = []

    def _append_recent_tool(self, entry: dict) -> None:
        with self._recent_lock:
            self._recent_tools.append(entry)
            if len(self._recent_tools) > 12:
                del self._recent_tools[: len(self._recent_tools) - 12]

    def get_recent_tool_events(self) -> list[dict]:
        with self._recent_lock:
            return [dict(x) for x in self._recent_tools]

    def _record_tool_run(
        self, name: str, preview: str, result: ToolResult, t0: float
    ) -> None:
        ms = int((time.perf_counter() - t0) * 1000)
        entry = {
            "tool": name,
            "ok": result.ok,
            "ms": ms,
            "preview": (preview or "")[:400],
        }
        self._append_recent_tool(entry)
        try:
            log_event(
                "tool_run",
                {"tool": name, "ok": result.ok, "ms": ms, "preview": (preview or "")[:500]},
            )
        except Exception:
            pass

    def _find_tool(self, name: str) -> Tool | None:
        for tool in self.tools:
            if getattr(tool, "name", None) == name:
                return tool
        return None

    @staticmethod
    def _drives_visualizer(kind: str) -> bool:
        return (kind or "").lower().strip() not in {"visualizer_control", "viz"}

    @staticmethod
    def _visualizer_detail(kind: str, preview: str | None = None) -> str:
        label = (kind or "tool").strip() or "tool"
        friendly = {
            "fin": "nexus",
            "prod": "nexus",
            "nexus": "nexus",
            "search": "busca web",
            "web_search": "busca web",
            "apps": "apps",
            "app": "app",
            "open_app": "app",
            "spot": "spotify",
            "spotify": "spotify",
            "file": "arquivos",
            "fs": "arquivos",
            "file_manager": "arquivos",
            "note": "notas",
            "notes": "notas",
        }.get(label.lower(), label)
        suffix = (preview or "").strip().replace("\n", " ")[:70]
        if suffix:
            return f"Executando {friendly}: {suffix}"
        return f"Executando {friendly}"

    def _set_visualizer_executing(self, kind: str, preview: str | None = None) -> None:
        if not self._drives_visualizer(kind):
            return
        try:
            from src.services import visualizer

            visualizer.set_executing(self._visualizer_detail(kind, preview))
        except Exception:
            pass

    def _set_visualizer_result(self, kind: str, result: ToolResult) -> None:
        if not self._drives_visualizer(kind):
            return
        try:
            from src.services import visualizer

            detail = f"{kind}: {(result.message or '').strip()[:90]}"
            if result.ok:
                visualizer.set_success(detail)
            else:
                visualizer.set_alert(detail)
        except Exception:
            pass

    def _confirmation_effective(self) -> bool:
        """Confirmação crítica ativa (painel/voz/terminal) — respeita o interruptor do bus."""
        if self._confirm_bus is not None:
            return self._confirm_bus.enabled
        return self.require_critical_confirmation

    def confirm_if_critical(self, tool: Tool | None) -> bool:
        """Para chamadas externas (ex.: orchestrator) antes de executar tool crítica."""
        if tool is None:
            return True
        return self._confirm(tool)

    def _confirm(self, tool: Tool) -> bool:
        if not tool.critical:
            return True
        if not self._confirmation_effective():
            return True
        if self._confirm_bus:
            detail = (
                f'Confirmar execução da ferramenta "{getattr(tool, "name", "?")}"? '
                "Esta ação pode alterar arquivos, apps ou enviar dados."
            )
            return self._confirm_bus.request(getattr(tool, "name", "tool"), detail)
        try:
            ok = input(f"Confirmar acao critica '{tool.name}'? (s/n): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        return ok in {"s", "sim", "y", "yes"}

    @staticmethod
    def _file_command_needs_confirm(command: str) -> bool:
        parts = (command or "").strip().split("|")
        if not parts:
            return False
        return parts[0].strip().lower() in FILE_ACTIONS_NEED_CONFIRM

    def run_by_marker(self, kind: str, arg: str | None, user_line: str) -> ToolResult:
        t0 = time.perf_counter()
        self._set_visualizer_executing(kind, arg or user_line)
        res = self._dispatch_marker(kind, arg, user_line)
        self._set_visualizer_result(kind, res)
        self._record_tool_run(
            f"marker:{kind}",
            f"{arg or ''}"[:300],
            res,
            t0,
        )
        return res

    def _dispatch_marker(self, kind: str, arg: str | None, user_line: str) -> ToolResult:
        """Executa ferramenta pedida pela LLM via marcador (suporta nomes longos e compactos)."""
        kind_l = kind.lower().strip()
        desktop = self._find_tool("desktop_automation")

        # Mapeamento de nomes compactos
        compact_map = {
            "viz": "visualizer_control",
            "search": "web_search",
            "wa": "whatsapp_send",
            "clippy": "clipboard",
            "info": "system_info",
            "mem": "memory_manager",
            "note": "notes",
            "vol": "media_control",
            "prod": "nexus",
            "fin": "nexus",
            "nexus": "nexus",
            "spot": "spotify",
            "file": "file_manager",
            "fs": "file_manager",
            "apps": "app_manager",
            "wf": "workflow",
        }
        if kind_l in compact_map:
            kind_l = compact_map[kind_l]

        # ── App Manager ──
        am = self._find_tool("app_manager")
        if kind_l in ("open_app", "app"):
            if not am: return ToolResult(False, "App Manager indisponivel.")
            return am.open_app(arg or "")

        if kind_l in ("open_browser", "browser"):
            if arg:
                import webbrowser
                url = arg if "://" in arg else f"https://{arg}"
                webbrowser.open(url)
                return ToolResult(True, f"Aberto navegador na url: {url}")
            if not am: return ToolResult(False, "App Manager indisponivel.")
            return am.open_app("chrome")

        if kind_l == "notepad":
            if not am: return ToolResult(False, "App Manager indisponivel.")
            return am.open_app("notepad")

        # ── Pesquisa Web ──
        if kind_l in ("web_search", "search_web"):
            ws = self._find_tool("web_search")
            if not ws: return ToolResult(False, "Busca web indisponivel.")
            return ws.search(arg or user_line)

        if kind_l in ("open_browser_url", "browser_url"):
            ws = self._find_tool("web_search")
            if not ws: return ToolResult(False, "Busca web indisponivel.")
            url = (arg or "").strip()
            if not url: return ToolResult(False, "URL vazia.")
            if url.startswith(("http", "www.")) or "." in url.split("/")[0]:
                return ws.open_url(url)
            return ws.search_and_open(url)

        # ── Clipboard ──
        if kind_l == "clipboard":
            cb = self._find_tool("clipboard")
            if not cb: return ToolResult(False, "Clipboard indisponivel.")
            return cb.run(arg or user_line)

        # ── Timer ──
        if kind_l == "timer":
            tm = self._find_tool("timer")
            if not tm: return ToolResult(False, "Timer indisponivel.")
            return tm.run(arg or user_line)

        # ── System Info ──
        if kind_l == "system_info":
            si = self._find_tool("system_info")
            if not si: return ToolResult(False, "SystemInfo indisponivel.")
            return si.get_info()

        # ── Notes ──
        if kind_l == "notes":
            nt = self._find_tool("notes")
            if not nt: return ToolResult(False, "Notas indisponivel.")
            return nt.run(arg or user_line)

        # ── Media Control ──
        if kind_l == "media_control":
            mc = self._find_tool("media_control")
            if not mc: return ToolResult(False, "MediaControl indisponivel.")
            return mc.run(arg or user_line)

        # ── Memory ──
        if kind_l == "memory_manager":
            mm = self._find_tool("memory_manager")
            if not mm: return ToolResult(False, "Memoria indisponivel.")
            # Map simple sub-actions
            if arg and ":" in arg:
                p = arg.split(":", 1)
                action, val = p[0].strip().lower(), p[1].strip()
                if action == "save": return mm.save_fact(val, "geral")
                if action == "find": return mm.search_facts(val)
                if action == "list": return mm.list_facts(val)
                if action == "del": return mm.delete_fact(val)
            return mm.run(arg or user_line)

        # ── WhatsApp ──
        if kind_l in ("whatsapp_send", "whatsapp"):
            wa = self._find_tool("whatsapp")
            if not wa: return ToolResult(False, "WhatsApp indisponivel.")
            if not self._confirm(wa):
                return ToolResult(False, "Acao cancelada por seguranca.")
            return wa.run(arg or user_line)

        # ── Visualizer Control ──
        if kind_l == "visualizer_control":
            vc = self._find_tool("visualizer_control")
            if not vc: return ToolResult(False, "Controle visualizador indisponivel.")
            return vc.run(arg or user_line)

        # ── Produtividade & Financas ──
        if kind_l == "productivity":
            prod = self._find_tool("productivity")
            if not prod: return ToolResult(False, "Produtividade indisponivel.")
            return prod.run(arg or user_line)

        if kind_l == "finance":
            fin = self._find_tool("finance")
            if not fin: return ToolResult(False, "Financas indisponivel.")
            return fin.run(arg or user_line)

        # ── Spotify ──
        if kind_l == "spotify":
            sp = self._find_tool("spotify")
            if not sp: return ToolResult(False, "Spotify indisponivel.")
            return sp.run(arg or user_line)

        # ── File Manager ──
        if kind_l == "file_manager":
            fm = self._find_tool("file_manager")
            if not fm: return ToolResult(False, "File Manager indisponivel.")
            cmd = arg or user_line
            if self._file_command_needs_confirm(cmd) and not self._confirm(fm):
                return ToolResult(False, "Acao cancelada por seguranca.")
            return fm.run(cmd)

        # ── App Manager ──
        if kind_l == "app_manager":
            am = self._find_tool("app_manager")
            if not am: return ToolResult(False, "App Manager indisponivel.")
            return am.run(arg or user_line)

        # ── Nexus (finanças Aether, hábitos, estudos, presets, UI) ──
        if kind_l == "nexus":
            nx = self._find_tool("nexus")
            if not nx: return ToolResult(False, "Nexus indisponivel.")
            return nx.run(arg or user_line)

        # ── Workflow ──
        if kind_l == "workflow":
            wf = self._find_tool("workflow")
            if not wf: return ToolResult(False, "Workflow indisponivel.")
            return wf.run(arg or user_line)

        return ToolResult(False, f"Ferramenta desconhecida: {kind}.")


    def run_first_match(self, command: str) -> ToolResult:
        t0 = time.perf_counter()
        lowered = command.lower()
        for tool in self.tools:
            if self._is_candidate(tool.name, lowered):
                if tool.critical and self._confirmation_effective():
                    if not self._confirm(tool):
                        res = ToolResult(False, "Acao cancelada por seguranca.")
                        self._record_tool_run(tool.name, command[:300], res, t0)
                        return res
                self._set_visualizer_executing(tool.name, command)
                result = tool.run(command)
                self._set_visualizer_result(tool.name, result)
                self._record_tool_run(tool.name, command[:300], result, t0)
                if result.ok:
                    return result
        res = ToolResult(False, "Nenhuma tool conseguiu executar o comando.")
        self._record_tool_run("run_first_match", command[:300], res, t0)
        return res

    @staticmethod
    def _is_candidate(tool_name: str, lowered: str) -> bool:
        if tool_name == "desktop_automation":
            return any(
                x in lowered
                for x in [
                    "abra ",
                    "abrir ",
                    "alarme",
                    "navegador",
                    "bloco de notas",
                    "bloco de nota",
                ]
            )
        if tool_name == "productivity":
            return any(x in lowered for x in ["habito", "hábito", "tarefa", "todo ", "lista de tarefa"])
        if tool_name == "finance":
            return any(
                x in lowered
                for x in [
                    "gasto",
                    "gastei",
                    "despesa",
                    "quanto gast",
                    "registrar compra",
                    "anota compra",
                    "financ",
                ]
            )
        if tool_name == "web_search":
            return any(x in lowered for x in ["pesquis", "busca", "search", "clima", "noticia"])
        if tool_name == "clipboard":
            return any(x in lowered for x in ["clipboard", "copiar", "colar", "colei", "copiado"])
        if tool_name == "timer":
            return any(x in lowered for x in ["timer", "temporizador", "alarme", "me avise em"])
        if tool_name == "system_info":
            return any(x in lowered for x in ["sistema", "cpu", "ram", "disco", "bateria", "pc"])
        if tool_name == "notes":
            return any(x in lowered for x in ["nota", "anota", "anotacao", "anotação"])
        if tool_name == "media_control":
            # Nao intercepta se o usuario mencionou Spotify explicitamente
            if "spotify" in lowered:
                return False
            return any(
                x in lowered
                for x in [
                    "volume",
                    "mudo",
                    "mute",
                    "play",
                    "pause",
                    "pausa",
                    "proxima musica",
                    "próxima música",
                    "pula",
                ]
            )
        if tool_name == "spotify":
            return any(
                x in lowered
                for x in [
                    "spotify",
                    "que musica",
                    "que música",
                    "tocando",
                    "toque ",
                    "tocar ",
                ]
            )
        if tool_name == "file_manager":
            return any(
                x in lowered
                for x in [
                    "pasta ",
                    "arquivo",
                    "downloads",
                    "documentos",
                    "quantos arquivo",
                    "liste a pasta",
                    "mover ",
                    "copiar ",
                    "deletar ",
                    "renomear ",
                ]
            )
        if tool_name == "app_manager":
            return any(
                x in lowered
                for x in [
                    "apps instalad",
                    "programas aberto",
                    "janelas aberta",
                    "feche o ",
                    "fecha o ",
                    "traga o ",
                    "escreva no bloco",
                ]
            )
        if tool_name == "workflow":
            return any(
                x in lowered
                for x in [
                    "workflow",
                    "modo de ",
                    "meu modo",
                ]
            )
        if tool_name == "health_journal":
            return any(
                x in lowered
                for x in [
                    "treino",
                    "academia",
                    "peso",
                    "caloria",
                    "proteina",
                    "diario",
                    "diário",
                    "psicologo",
                    "psicólogo",
                    "humor",
                    "sentindo",
                ]
            )
        if tool_name == "nexus":
            return any(
                x in lowered
                for x in [
                    "abrir nexus",
                    "painel nexus",
                    "preset",
                    "protocolo",
                    "recompensa",
                    "loja nexus",
                    "acertei quest",
                    "errei quest",
                    "mindpalace",
                    "modo foco",
                    "ganhei ",
                    "recebi ",
                    "saldo nexus",
                    "ativar preset",
                    "salvar preset",
                    "grand objective",
                    "meta nexus",
                ]
            ) or (
                ("gastei " in lowered or "paguei " in lowered)
                and "reais" in lowered
            )
        return False
