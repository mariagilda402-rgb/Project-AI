from pathlib import Path


def test_orb_advanced_js_supports_backend_state_mappings():
    root = Path(__file__).resolve().parents[1]
    js_path = root / "src" / "services" / "visualizer_web" / "orb_advanced.js"
    js = js_path.read_text(encoding="utf-8")

    assert "executing: 'thinking'" in js
    assert "processing: 'thinking'" in js
    assert "loading: 'thinking'" in js
    assert "searching: 'thinking'" in js
    assert "browsing: 'thinking'" in js
    assert "warning: 'alert'" in js
    assert "error: 'alert'" in js
    assert "sleeping: 'idle'" in js
