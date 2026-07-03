from __future__ import annotations

from typing import Any


SUPPORTED_BLOCKS = {
    "text",
    "markdown",
    "image",
    "video_youtube",
    "table",
    "metric_grid",
    "chart_line",
    "chart_bar",
    "progress",
    "timeline",
    "tool_status",
    "assistant_transcript",
}


def validate_block(block: dict[str, Any]) -> dict[str, Any]:
    block_type = str(block.get("type") or "")
    if block_type not in SUPPORTED_BLOCKS:
        return {"ok": False, "error": f"Unsupported block type: {block_type}"}
    return {"ok": True}


def make_dashboard(surface_id: str, title: str, blocks: list[dict[str, Any]]) -> dict[str, Any]:
    valid_blocks = [block for block in blocks if validate_block(block)["ok"]]
    return {
        "surface_id": surface_id,
        "type": "dashboard",
        "title": title,
        "blocks": valid_blocks,
    }


def make_render_update(
    surface_id: str,
    op: str,
    block: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "type": "render_update",
        "payload": {
            "surface_id": surface_id,
            "op": op,
            "block": block or {},
        },
    }

