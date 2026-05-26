# Nexus Window Theme Presets Design

The user wants every Nexus desktop window to be individually themeable from the main panel and through Jarvis commands. The selected direction is a local, deterministic preset system: presets are saved in Nexus data files, assignments are per module, and the desktop window compositor injects safe CSS tokens when each module opens.

## Scope

This milestone implements theme presets for current Nexus modules: overview, habits, finance, notes, study, tasks, progress, goals, and quiz. It adds:

- a theme list/apply/generate API in `NexusService`
- `nexus_command` actions for voice/tool usage
- main panel controls inside Configuracoes
- boot payload support in the pywebview window compositor
- JS/CSS contract updates so custom tokens apply without external module CSS

This milestone does not implement a full LLM design generator. The generator is local and prompt-inspired so it is reliable offline and does not store the user's generation prompt in agent memory or in the preset file. The generated preset stores only name, mode, description, and whitelisted visual tokens.

## Data Model

Theme data lives beside the active Nexus database in `nexus_window_themes.json`.

```json
{
  "version": 1,
  "modules": {
    "finance": "emerald-ledger"
  },
  "presets": {
    "custom-id": {
      "id": "custom-id",
      "name": "Custom Name",
      "mode": "dark",
      "description": "Short visible description",
      "tokens": {
        "--accent": "#10b981"
      }
    }
  }
}
```

Built-in presets live in code and are merged with the file at read time. Only generated custom presets and module assignments are written to disk.

## Behavior

`theme_list` returns modules, preset summaries, and current assignments. `theme_apply` validates the module and preset, persists the assignment, broadcasts Nexus state, and opens the target module with a small theme receipt. `theme_generate` creates a safe preset from a natural prompt, saves it, applies it to the requested module, and returns the same summary shape.

When `DesktopApp.open_nexus_module()` opens a module, it asks the Nexus service for the module's theme boot payload, merges it with any command receipt payload, and passes that to `_compose_nexus_module_html()`. The compositor writes:

- `data-theme="dark|light"`
- `data-theme-preset="<preset id>"`
- inline CSS variables from the whitelisted tokens
- `window.__NEXUS_BOOT__` including `theme_preset`, `theme_name`, `theme_tokens`, and `module`

## Panel UI

The Configuracoes page gets a compact "Temas por janela" tool under the Nexus Life OS section:

- module selector
- preset selector
- apply button
- prompt box for generating a new preset
- "Gerar e aplicar" button
- small status/preview area

Existing open-module buttons remain unchanged.

## Error Handling

Invalid modules fall back to overview for window opening, but theme commands return a clear error for invalid module names. Unknown presets return a clear error. Corrupt JSON theme files are ignored and replaced by the default in-memory view until the next successful save.

## Testing

Use TDD with focused tests before implementation:

- service tests for list/apply/generate and no prompt persistence
- compositor test for custom token injection
- static panel test for controls and API method names
- tool schema/prompt test for the new `theme_*` actions

Run the existing Nexus suite after the focused tests. For UI, verify the local panel in Browser/IAB when available.
