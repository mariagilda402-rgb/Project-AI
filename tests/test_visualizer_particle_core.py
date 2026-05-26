from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VISUALIZER_HTML = ROOT / "src" / "services" / "visualizer_web" / "index.html"


def test_visualizer_exposes_particle_core_states(tmp_path, monkeypatch):
    import src.services.visualizer as visualizer

    state_file = tmp_path / "visualizer_state.json"
    monkeypatch.setattr(visualizer, "STATE_FILE", state_file)
    monkeypatch.setattr(
        visualizer,
        "_state",
        {
            "status": "idle",
            "subtitle": "",
            "emotion": "neutral",
            "position": "bottom_right",
            "visible": True,
        },
    )

    visualizer.set_executing("Sincronizando Nexus")
    executing_state = json.loads(state_file.read_text(encoding="utf-8"))

    assert executing_state["status"] == "executing"
    assert executing_state["subtitle"] == "Sincronizando Nexus"

    visualizer.set_alert("Atenção")
    alert_state = json.loads(state_file.read_text(encoding="utf-8"))

    assert alert_state["status"] == "alert"
    assert alert_state["subtitle"] == "Atenção"


def test_visualizer_html_declares_particle_neural_core_contract():
    html = VISUALIZER_HTML.read_text(encoding="utf-8")

    assert "particle-neural-core" in html
    assert "neural-particle-canvas" in html
    assert "ParticleNeuralCore" in html
    assert "data-core-state" in html
    assert "setState(name)" in html
    for state in ("idle", "listening", "thinking", "speaking", "executing", "alert"):
        assert state in html
    assert "'executing': 'executing'" in html
    assert "'alert': 'alert'" in html
    assert "particleCore.setState(name)" in html


def test_particle_core_uses_ordered_sphere_motion_contract():
    html = VISUALIZER_HTML.read_text(encoding="utf-8")

    assert "Ordered Neural Sphere" in html
    assert "GOLDEN_ANGLE" in html
    assert "baseY = 1 - 2 * p.seed" in html
    assert "baseR = Math.sqrt(Math.max(0, 1 - baseY * baseY))" in html
    assert "latLine" in html
    assert "meridianLine" in html
    assert "scanBand" in html
    assert "drawSphereShell" in html
    assert "projectPoint" in html
    assert ".map((p) => this.particlePoint" not in html


def test_particle_core_canvas_is_primary_visual_layer():
    html = VISUALIZER_HTML.read_text(encoding="utf-8")

    assert "#neural-particle-canvas" in html
    assert "z-index: 5;" in html
    assert "filter: drop-shadow" in html
    assert "#orb-container {\n      opacity: .16;" in html
    assert "display: none;" in html
    assert ".status-ring {\n      z-index: 6;" in html
    assert ".status-ring {\n      z-index: 6;\n      display: none;" in html
    assert "mix-blend-mode: normal;" in html


def test_particle_core_pulses_non_idle_states_and_syncs_with_tts():
    html = VISUALIZER_HTML.read_text(encoding="utf-8")

    assert "setVolume(v)" in html
    assert "this.volume" in html
    assert "particleCore.setVolume(amplitude)" in html
    assert "particleCore.setVolume(0)" in html
    assert "statePulse" in html
    assert "name === 'idle' ? 0.16 : 0.9" in html
    assert "volumeBoost" in html
    for state in ("listening", "thinking", "speaking", "executing", "alert"):
        assert f"{state}:" in html
        assert "pulse:" in html
        assert "brightness:" in html


def test_particle_core_points_are_visible_above_status_ring():
    html = VISUALIZER_HTML.read_text(encoding="utf-8")

    assert "const particleAlpha = Math.min(1, 0.44 + alpha" in html
    assert "ctx.globalCompositeOperation = 'source-over';" in html
    assert "ctx.globalAlpha = particleAlpha;" in html
    assert "ctx.shadowBlur = 6 + glow * 10 + statePulse * 4;" in html
    assert "p.size * (2.2 + depth" in html
    assert "const linkAlpha = Math.min(0.55" in html
    assert "const neuralAnchorCount = 72;" in html


def test_particle_core_accepts_transient_emotion_tint_from_state_payloads():
    html = VISUALIZER_HTML.read_text(encoding="utf-8")

    assert "setEmotion(emotion)" in html
    assert "emotionConfig" in html
    assert "particleCore.setEmotion(data.emotion || 'neutral')" in html


def test_subtitle_updates_are_safe_when_subtitle_element_is_absent():
    html = VISUALIZER_HTML.read_text(encoding="utf-8")

    assert "const el = document.getElementById('subtitle');" in html
    assert "if (!el) return;" in html


def test_visualizer_inline_scripts_are_syntax_valid():
    html = VISUALIZER_HTML.read_text(encoding="utf-8")
    scripts = re.findall(r"<script>([\s\S]*?)</script>", html, flags=re.IGNORECASE)
    assert scripts

    script = (
        "const fetch = () => Promise.resolve({ json: () => Promise.resolve({}) });\n"
        "const WebSocket = function(){};\n"
        "WebSocket.OPEN = 1;\n"
        "const document = { getElementById: () => ({ style:{}, classList:{ add(){}, remove(){}, toggle(){} }, "
        "addEventListener(){}, setAttribute(){}, textContent:'', dataset:{}, appendChild(){}, clientWidth:140, clientHeight:140 }), "
        "addEventListener(){}, querySelector: () => null };\n"
        "const window = { addEventListener(){}, requestAnimationFrame(){}, devicePixelRatio:1, "
        "AudioContext: function(){}, webkitAudioContext: function(){} };\n"
        "const requestAnimationFrame = () => 0;\n"
        "const console = { log(){}, warn(){}, error(){} };\n"
        + "\n".join(scripts)
    )
    result = subprocess.run(
        ["node", "-"],
        cwd=ROOT,
        input=f"new Function({json.dumps(script)});\n",
        text=True,
        capture_output=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr
