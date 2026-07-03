from __future__ import annotations

import re
import unicodedata

from src.agent.runtime_modes import AgentMode, ModeResolution


_SHORT_GREETINGS = {
    "oi",
    "ola",
    "olá",
    "hey",
    "hi",
    "hello",
    "bom dia",
    "boa tarde",
    "boa noite",
}


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    no_marks = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return no_marks.lower()


class ModeResolver:
    def resolve(self, text: str) -> ModeResolution:
        raw = (text or "").strip()
        folded = _fold(raw)
        compact = folded.strip(" !?.\t\r\n")

        if compact in {_fold(x) for x in _SHORT_GREETINGS}:
            return ModeResolution(AgentMode.CHAT, 1.0, "short greeting")

        explicit = bool(
            re.search(r"\b(modo|mode|entra no modo|abre o modo|abrir o modo)\b", folded)
        )
        open_window = bool(
            re.search(r"\b(abre|abrir|mostra|mostrar|janela|painel|modo)\b", folded)
        )

        if self._has_any(
            folded, ["noticia", "noticias", "manchete", "jornal", "briefing"]
        ):
            return ModeResolution(
                AgentMode.NEWS,
                0.95 if explicit else 0.82,
                "news keywords",
                explicit,
                False,
                open_window,
            )

        if self._has_any(
            folded,
            [
                "psicologo",
                "terapia",
                "coach",
                "motivacional",
                "desanimado",
                "ansioso",
                "triste",
                "meu dia",
            ],
        ):
            return ModeResolution(
                AgentMode.PSYCH_COACH,
                0.82,
                "psych/coach keywords",
                explicit,
                False,
                False,
            )

        if self._has_any(
            folded,
            ["workflow", "rotina", "modo estudo", "modo dormir", "gravar", "salve isso como"],
        ):
            return ModeResolution(
                AgentMode.WORKFLOW, 0.86, "workflow keywords", explicit, False, open_window
            )

        if self._has_any(
            folded,
            [
                "arquivo",
                "pasta",
                "downloads",
                "documentos",
                "apaga",
                "delete",
                "deleta",
                "limpa",
            ],
        ):
            risky = self._has_any(
                folded, ["apaga", "delete", "deleta", "remove", "limpa", "sobrescreve"]
            )
            return ModeResolution(
                AgentMode.FILES, 0.82, "file keywords", explicit, risky, False
            )

        if self._has_any(
            folded,
            [
                "abre",
                "abrir",
                "fecha",
                "fechar",
                "spotify",
                "chrome",
                "notepad",
                "bloco de notas",
                "clipboard",
                "area de transferencia",
            ],
        ):
            return ModeResolution(
                AgentMode.PC, 0.78, "pc/app keywords", explicit, False, open_window
            )

        if self._has_any(
            folded,
            [
                "habito",
                "habitos",
                "treino",
                "flexao",
                "financa",
                "gasto",
                "receita",
                "nota",
                "flashcard",
                "quiz",
                "enem",
                "loja",
                "xp",
            ],
        ):
            return ModeResolution(
                AgentMode.NEXUS, 0.78, "nexus keywords", explicit, False, open_window
            )

        if self._has_any(
            folded, ["pesquise", "pesquisar", "procure", "buscar", "clima", "cotacao"]
        ):
            return ModeResolution(AgentMode.WEB, 0.72, "web/search keywords", explicit)

        if self._has_any(
            folded, ["tela", "monitor", "o que voce ve", "o que aparece"]
        ):
            return ModeResolution(AgentMode.VISION, 0.76, "vision keywords", explicit)

        return ModeResolution(AgentMode.CHAT, 0.55, "default chat")

    @staticmethod
    def _has_any(text: str, needles: list[str]) -> bool:
        return any(needle in text for needle in needles)
