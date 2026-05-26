# Nexus Particle Neural Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a state-driven Particle Neural Core face to the Jarvis visualizer.

**Architecture:** The Python visualizer service writes canonical assistant states to `data/visualizer_state.json`. The existing WebGL orb remains the center, while `visualizer_web/index.html` adds a Canvas 2D particle-network layer that listens to the same state updates.

**Tech Stack:** Python, pytest, static HTML/CSS/JavaScript, WebGL, Canvas 2D.

---

### Task 1: State API

**Files:**
- Modify: `src/services/visualizer.py`
- Test: `tests/test_visualizer_particle_core.py`

- [x] Write `test_visualizer_exposes_particle_core_states` to monkeypatch `STATE_FILE`, reset `_state`, call `set_executing("Sincronizando Nexus")` and `set_alert("Atenção")`, then assert the JSON file stores `executing` and `alert`.
- [x] Run the targeted test and verify it fails because `set_executing` and `set_alert` are missing.
- [x] Add `set_executing(detail: str = "")` and `set_alert(detail: str = "")`.
- [x] Run the targeted test and verify it passes.

### Task 2: Static Visual Contract

**Files:**
- Modify: `src/services/visualizer_web/index.html`
- Test: `tests/test_visualizer_particle_core.py`

- [x] Write `test_visualizer_html_declares_particle_neural_core_contract` to assert the HTML contains `particle-neural-core`, `neural-particle-canvas`, `ParticleNeuralCore`, `data-core-state`, and all primary states.
- [x] Run the test and verify it fails because the particle layer is missing.
- [x] Add the particle wrapper/canvas, CSS, state metadata for `executing` and `alert`, and a `ParticleNeuralCore` class.
- [x] Connect `setOrbState()` to `particleCore.setState(name)`.
- [x] Run the targeted test and verify it passes.

### Task 3: Compatibility And Syntax

**Files:**
- Modify: `src/services/visualizer_web/index.html`
- Test: `tests/test_visualizer_particle_core.py`

- [x] Write `test_visualizer_inline_scripts_are_syntax_valid` that extracts inline `<script>` blocks and parses each with Node `new Function`.
- [x] Run the test and verify it fails if the new JavaScript has syntax issues.
- [x] Fix syntax or escaping problems.
- [x] Run the test and verify it passes.

### Task 4: Verification

- [x] Run `python -m pytest tests/test_visualizer_particle_core.py -q`.
- [x] Run `python -m py_compile src/services/visualizer.py`.
- [x] Run the existing focused tests touched by visualizer changes if any.
- [x] Attempt Browser/IAB render verification on a local visualizer server. Screenshot capture timed out, so DOM state, canvas dimensions, and state transitions were verified instead.
