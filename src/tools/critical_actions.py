"""Lista única de ferramentas e ações que disparam confirmação crítica (UI + prompts)."""

from __future__ import annotations

# Ferramentas com tool.critical == True (manter sincronizado com as classes em src/tools).
CRITICAL_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "whatsapp_send",
        "desktop_automation",
        "file_manager",
    }
)

# Subcomandos do file_manager que exigem confirmação quando a confirmação crítica está ativa.
FILE_ACTIONS_NEED_CONFIRM: frozenset[str] = frozenset(
    {
        "delete_file",
        "move_file",
        "write_text_file",
        "rename_file",
    }
)


def critical_actions_reference() -> dict[str, Any]:
    """Resumo para o painel (Referência > Segurança)."""
    return {
        "critical_tool_names": sorted(CRITICAL_TOOL_NAMES),
        "file_actions_need_confirm": sorted(FILE_ACTIONS_NEED_CONFIRM),
        "voice_approve": ["confirmar", "sim", "ok", "autorizo"],
        "voice_deny": ["cancelar", "não", "nao", "negativo"],
    }
