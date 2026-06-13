import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "mobile" / "app.js"
INDEX_HTML = ROOT / "mobile" / "index.html"


def read_app_js() -> str:
    return APP_JS.read_text(encoding="utf-8")


def read_index_html() -> str:
    return INDEX_HTML.read_text(encoding="utf-8")


def test_mobile_app_does_not_redeclare_supabase_sdk_global():
    app_js = read_app_js()

    assert not re.search(r"^\s*(?:let|const)\s+supabase\b", app_js, re.MULTILINE)
    assert "window.nexusSupabase" in app_js


def test_mobile_localdb_exposes_legacy_offline_aliases():
    app_js = read_app_js()

    assert "static getAll(table)" in app_js
    assert "static saveAll(table, data)" in app_js


def test_mobile_exposes_jarvis_call_toggle_for_fab():
    app_js = read_app_js()

    assert "window.toggleJarvisCall" in app_js
    assert "AndroidNative.startJarvisCall" in app_js
    assert "AndroidNative.stopJarvisCall" in app_js


def test_mobile_guards_web_notification_api_for_android_webview():
    app_js = read_app_js()

    assert 'if ("Notification" in window && Notification.permission === \'default\')' in app_js
    assert 'if ("Notification" in window && Notification.permission === \'granted\')' in app_js


def test_mobile_settings_has_single_journal_toggle():
    html = read_index_html()

    assert html.count('id="toggle-journal"') == 1
    assert html.count("toggleModule('journal')") == 1


def test_mobile_nav_targets_have_views_for_videos_and_shop():
    html = read_index_html()

    assert 'data-target="view-videos"' in html
    assert 'id="view-videos"' in html
    assert 'id="videos-list"' in html
    assert 'data-target="view-shop"' in html
    assert 'id="view-shop"' in html
    assert 'id="shop-list"' in html


def test_mobile_visible_labels_are_utf8_not_mojibake():
    text = read_index_html() + read_app_js()

    assert "Início" in text
    assert "Hábitos" in text
    assert "Vídeos" in text
    assert "Módulos do App" in text
    for mojibake in ["Ă", "Â", "Ã¡", "Ã©", "Ã­", "Ã³", "Ãº", "Ã§", "ðŸ", "â€", "â"]:
        assert mojibake not in text


def test_mobile_nav_targets_all_have_matching_views():
    html = read_index_html()
    targets = re.findall(r'data-target="(view-[^"]+)"', html)
    for target in set(targets):
        assert f'id="{target}"' in html, f"Missing view for nav target {target}"


def test_mobile_exposes_critical_window_handlers():
    app_js = read_app_js()
    required = [
        "window.syncData",
        "window.toggleIoT",
        "window.promptAddGoal",
        "window.startJournalDictation",
        "window.openSettingsView",
        "window.discoverIoT",
    ]
    for name in required:
        assert name in app_js, f"Missing {name}"


def test_mobile_view_routines_inside_main():
    html = read_index_html()
    main_start = html.index("<main")
    main_end = html.index("</main>")
    main_content = html[main_start:main_end]
    assert 'id="view-routines"' in main_content


def test_mobile_no_literal_backslash_n_in_html():
    html = read_index_html()
    assert "\\n        <div" not in html


def test_mobile_loaders_guard_missing_containers():
    app_js = read_app_js()
    for loader in ["loadVideos", "loadShop", "loadGoals", "loadFitness"]:
        block = re.search(rf"function {loader}\(\)\s*\{{", app_js)
        assert block, f"function {loader} not found"
        start = block.start()
        snippet = app_js[start:start + 400]
        assert re.search(r"if\s*\(\s*!container\s*\)\s*return", snippet), f"{loader} missing container guard"
