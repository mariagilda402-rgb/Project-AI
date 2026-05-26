# Nexus Neural Memory Graph Design

## Goal

Create a Nexus window that turns the user's local knowledge into a visual graph. The graph should make MindPalace notes, flashcards, memories, habits, tasks, goals, rewards, news notes, and selected Markdown files visible even when their original windows are closed.

## Scope

- Add a `memory_graph` Nexus module and aliases such as `grafo`, `memoria`, `rede neural`, and `neural`.
- Build the graph from local sources only:
  - `study_notes`
  - flashcards linked to notes
  - structured memory from `data/structured_memory.json`
  - active habits, tasks, goals, rewards
  - relevant Markdown context files from the project and `data/persona`
- Return a compact graph payload with `nodes`, `edges`, `clusters`, and `stats`.
- Add local, explainable relationship inference by shared keywords across notes, tasks, habits, goals, rewards, memories, and Markdown files.
- Return `ranked_matches` for searches and expose `memory_graph_context` for Jarvis answers that need local study/memory context without opening Notes.
- Expose the graph through the desktop bridge and `nexus_command`.
- Render the graph in `memory_graph.html` using inline CSS and a Canvas 2D force-style layout.
- Include search, type filters, relevance spotlight, node details, and action buttons that can open Notes, Study, Tasks, Goals, or the Dashboard.

## Out Of Scope For This Slice

- Full Obsidian import/export.
- Semantic embeddings or vector similarity.
- WebGL particle core.
- Editing graph relationships manually.

## Data Shape

Nodes use:

- `id`
- `type`
- `label`
- `subtitle`
- `weight`
- `cluster`
- `details`
- `source`
- `keywords`
- `relevance`

Edges use:

- `id`
- `source`
- `target`
- `type`
- `label`
- `weight`

The graph always includes a central `nexus:core` node. Source nodes connect to the core, and content nodes connect to their source, subject, tags, or linked note.

The smart relation layer adds `relates` edges when two actionable content nodes share strong keywords. Utility nodes such as tags and subjects remain visible but are not preferred in `ranked_matches`, so Jarvis answers point to real notes, tasks, habits, goals, memories, or files.

`memory_graph_context` returns:

- `matches`
- per-match `related` neighbors
- `suggested_modules`
- `context_text`
- `graph_stats`

## Error Handling

- Missing JSON memory files return an empty memory section.
- Invalid JSON is ignored rather than breaking the graph.
- Missing optional tables or fields produce fewer nodes, not a failed graph.
- The UI shows an empty-state message if no nodes are returned.

## Testing

- Service test: graph includes core, subject, note, tag, memory, habit, task, goal, and reward nodes with connecting edges.
- Structured command test: `memory_graph` returns JSON graph data.
- Bridge test: `memory_graph` returns the same payload shape.
- Static UI test: module declares canvas, search, filters, details, and `memory_graph` bridge call.
- Schema/prompt test: Jarvis tool descriptions and prompts mention `memory_graph`.
- Smart graph test: shared concepts create `relates` edges and ranked matches.
- Context test: `memory_graph_context` returns ranked matches, neighbors, suggested modules, and a compact context string.
