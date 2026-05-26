# Nexus News Memory + MindPalace Design

The News Briefing Studio MVP already opens a Nexus window, builds a structured briefing, shows a video-search slot, and exposes a three-line transcript lane. This continuation makes the feature useful after the first fetch: briefings get local history/cache, the user can preserve any story into MindPalace, and Jarvis learns the structured commands for those actions.

## Scope

- Persist successful news briefings beside the active Nexus database in `nexus_news_briefings.json`.
- Return the latest cached briefing for the same query when the live provider has no results, clearly marking it as cached/stale.
- Add a service action to save the selected news item as a MindPalace note with title, summary, source URL, suggested video query/link, and a deeper reading block.
- Expose the new action through the desktop bridge, structured `nexus_command`, Gemini/OpenAI schemas, and the News UI.
- Keep the module honest: the app suggests video search and transcript-like briefing lines, but does not claim real video transcription or automatic clipping until a real transcript source exists.

## Architecture

`NexusService` remains the source of truth. News history is stored as a compact JSON list keyed by generated timestamp and query. `build_news_briefing()` normalizes fresh rows, adds richer item detail, persists successful briefings, and falls back to cached history when live search returns nothing. `save_news_item_to_note()` converts a normalized news item into a regular `study_notes` record, preserving source metadata in Markdown and media links.

The desktop bridge adds `news_history` and `news_save_note`. The News HTML keeps local state for the selected item, renders cache status, and adds a "Salvar no MindPalace" control. Agent prompts and tool schemas advertise `news_save_note` so voice or function-calling requests can preserve a story without using agent memory.

## Data Shape

Each briefing contains:

- `ok`, `query`, `generated_at`, `items`, `narration`, `error`
- `from_cache`, `stale`, `cached_generated_at` when fallback history is used
- item fields: `title`, `source`, `published_at`, `url`, `body`, `summary`, `deep_dive`, `video`, `transcript`

## Error Handling

- Invalid JSON inputs become empty objects/lists instead of crashing the bridge.
- Saving a missing news item returns `{ ok: false, error: "Noticia nao encontrada." }`.
- Empty live results with no cache return the existing empty-state error.
- Cache write failures are non-fatal.

## Testing

- Service tests for history persistence and stale fallback.
- Service/structured-command/bridge tests for saving news into MindPalace.
- Static UI contract tests for history/cache/status/save controls.
- Tool schema and prompt tests for `news_save_note`.
