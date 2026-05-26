# Nexus Particle Neural Core Design

## Goal

Evolve the Jarvis visualizer from a simple orb into a Particle Neural Core: a compact, professional assistant face that reacts to core runtime states without replacing the functional Nexus panels.

## Scope

- Keep the existing WebGL orb as the bright central energy mass.
- Add a lightweight Canvas 2D particle network layer around the orb.
- Support the primary assistant states:
  - `idle`
  - `listening`
  - `thinking`
  - `speaking`
  - `executing`
  - `alert`
- Preserve existing compatibility states such as `loading`, `success`, `warning`, `sleeping`, and `error`.
- Expose Python setters `set_executing()` and `set_alert()` through `src.services.visualizer`.
- Render state-specific colors, ring fill, particle motion, and halo intensity.

## Out Of Scope For This Slice

- Full Three.js rewrite.
- Replacing every Nexus window with the particle system.
- Audio spectrum calibration beyond the existing `speaking` volume bridge.
- Mobile assistant UI.

## Architecture

`src/services/visualizer.py` remains the Python state writer. It persists `status`, `subtitle`, and `emotion` to `data/visualizer_state.json`.

`src/services/visualizer_web/index.html` keeps the inline WebGL orb and adds `ParticleNeuralCore`, a small Canvas 2D renderer. The particle core uses the same mapped state as the orb, so WebSocket and polling updates drive both layers together.

The visual contract is:

- `#particle-neural-core` wraps the orb.
- `#neural-particle-canvas` renders particles and links.
- `data-core-state` and `data-orb-state` expose the current visual state for tests and debugging.

## State Mapping

- `idle`: calm violet/blue breathing.
- `listening`: green/teal receptive motion.
- `thinking`: purple/blue faster orbiting.
- `speaking`: cyan audio-reactive pulse.
- `executing`: amber tactical activity.
- `alert`: red/pink high-energy warning.

Compatibility mappings:

- `loading` maps visually close to `executing`.
- `warning` maps visually close to `alert`.
- `error` maps visually close to `alert`.
- `success` remains green.
- `sleeping` remains dim indigo.

## Testing

- Python service test: `set_executing()` and `set_alert()` persist the expected status/subtitle.
- Static visualizer test: HTML declares the particle core wrapper, particle canvas, `ParticleNeuralCore`, and all primary states.
- Static renderer test: inline orb states include `executing` and `alert`.
- JS syntax test: inline scripts in `visualizer_web/index.html` parse without syntax errors.
