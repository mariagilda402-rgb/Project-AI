from __future__ import annotations

from src.tools.base import Tool, ToolResult


class ToolRegistry:
    def __init__(self, tools: list[Tool], require_critical_confirmation: bool = True) -> None:
        self.tools = tools
        self.require_critical_confirmation = require_critical_confirmation

    def _find_tool(self, name: str) -> Tool | None:
        for tool in self.tools:
            if getattr(tool, "name", None) == name:
                return tool
        return None

    def _confirm(self, tool: Tool) -> bool:
        if not tool.critical or not self.require_critical_confirmation:
            return True
        ok = input(f"Confirmar acao critica '{tool.name}'? (s/n): ").strip().lower()
        return ok in {"s", "sim", "y", "yes"}

    def run_by_marker(self, kind: str, arg: str | None, user_line: str) -> ToolResult:
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
            "prod": "productivity",
            "fin": "finance",
            "spot": "spotify",
            "file": "file_manager",
            "fs": "file_manager",
            "apps": "app_manager",
        }
        if kind_l in compact_map:
            kind_l = compact_map[kind_l]

        # ── Desktop ──
        if kind_l in ("open_app", "app"):
            if not desktop: return ToolResult(False, "Desktop indisponivel.")
            return desktop.run_open_app(arg or "")

        if kind_l in ("open_browser", "browser"):
            if not desktop: return ToolResult(False, "Desktop indisponivel.")
            return desktop.run("abra o navegador")

        if kind_l == "notepad":
            if not desktop: return ToolResult(False, "Desktop indisponivel.")
            return desktop.run("abra o bloco de notas")

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
            return fm.run(arg or user_line)

        # ── App Manager ──
        if kind_l == "app_manager":
            am = self._find_tool("app_manager")
            if not am: return ToolResult(False, "App Manager indisponivel.")
            return am.run(arg or user_line)

        return ToolResult(False, f"Ferramenta desconhecida: {kind}.")


    def run_first_match(self, command: str) -> ToolResult:
        lowered = command.lower()
        for tool in self.tools:
            if self._is_candidate(tool.name, lowered):
                if tool.critical and self.require_critical_confirmation:
                    ok = input(f"Confirmar acao critica '{tool.name}'? (s/n): ").strip().lower()
                    if ok not in {"s", "sim", "y", "yes"}:
                        return ToolResult(False, "Acao cancelada por seguranca.")
                result = tool.run(command)
                if result.ok:
                    return result
        return ToolResult(False, "Nenhuma tool conseguiu executar o comando.")

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
        return False
