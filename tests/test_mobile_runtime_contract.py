import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "mobile" / "app.js"
INDEX_HTML = ROOT / "mobile" / "index.html"
YOUTUBE_PLAYER_HTML = ROOT / "mobile" / "youtube-player.html"
MANIFEST = ROOT / "mobile" / "js" / "manifest.txt"
BUNDLER = ROOT / "scripts" / "bundle_mobile_js.py"


def read_app_js() -> str:
    return APP_JS.read_text(encoding="utf-8")


def read_index_html() -> str:
    return INDEX_HTML.read_text(encoding="utf-8")


def read_youtube_player_html() -> str:
    return YOUTUBE_PLAYER_HTML.read_text(encoding="utf-8")


def read_mobile_source_bundle() -> str:
    parts = []
    for raw in MANIFEST.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            parts.append((ROOT / line).read_text(encoding="utf-8").rstrip() + "\n")
    return "\n".join(parts)


def test_mobile_sources_are_modular_and_bundle_is_deterministic():
    assert MANIFEST.is_file()
    modules = [line.strip() for line in MANIFEST.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(modules) >= 8
    for module in modules:
        assert (ROOT / module).is_file(), f"Missing mobile source module: {module}"
    assert read_mobile_source_bundle() == read_app_js()


def test_mobile_bundler_recreates_app_js_without_changes():
    result = subprocess.run(
        [sys.executable, str(BUNDLER)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert read_mobile_source_bundle() == read_app_js()


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
    assert "requireWifiForJarvis" in app_js


def test_mobile_blocks_jarvis_without_wifi():
    app_js = read_app_js()
    assert "requireWifiForJarvis" in app_js
    assert "isWifiConnected()" in app_js


def test_mobile_guards_web_notification_api_for_android_webview():
    app_js = read_app_js()

    assert 'if ("Notification" in window && Notification.permission === \'default\')' in app_js
    assert 'if ("Notification" in window && Notification.permission === \'granted\')' in app_js


def test_mobile_settings_has_single_journal_toggle():
    html = read_index_html()

    assert html.count('id="toggle-journal"') == 1
    assert html.count("toggleModule('journal')") == 1


def test_mobile_nav_targets_have_matching_views():
    html = read_index_html()
    targets = re.findall(r'data-target="(view-[^"]+)"', html)
    assert targets
    for target in set(targets):
        assert f'id="{target}"' in html, f"Missing view for nav target {target}"


def test_mobile_click_handlers_are_defined_in_js_or_known_browser_apis():
    html = read_index_html()
    app_js = read_app_js()
    handlers = set(re.findall(r'on(?:click|change|input|submit)="\s*([A-Za-z_$][\w$]*)\s*\(', html))
    known = {"alert", "confirm", "prompt", "setTimeout", "clearTimeout", "if"}
    missing = sorted(fn for fn in handlers if fn not in known and f"function {fn}" not in app_js and f"window.{fn}" not in app_js)
    assert not missing, "Missing JS handlers referenced by HTML: " + ", ".join(missing)


def test_mobile_refresh_view_content_covers_core_nav_modules():
    app_js = read_app_js()
    assert "window.refreshViewContent" in app_js
    for case in [
        "case 'view-home':",
        "case 'view-habits':",
        "case 'view-tasks':",
        "case 'view-finance':",
        "case 'view-studies':",
        "case 'view-goals':",
        "case 'view-fitness':",
        "case 'view-journal':",
        "case 'view-routines':",
        "case 'view-iot':",
    ]:
        assert case in app_js


def test_mobile_critical_handlers_for_working_baseline_exist():
    app_js = read_app_js()
    required = [
        "window.syncData",
        "window.toggleJarvisCall",
        "window.sendChatMessage",
        "window.openNoteEditor",
        "window.saveNote",
        "window.openYouTubeModal",
        "window.insertYouTubeEmbed",
        "window.openSlashMenu",
        "window.openJarvisPanel",
        "window.openQuiz",
        "window.startQuiz",
        "window.startJournalDictation",
        "window.openWorkoutForm",
        "window.NexusCalendar",
    ]
    for name in required:
        assert name in app_js, f"Missing {name}"


def test_mobile_visible_labels_are_utf8_not_mojibake():
    text = read_index_html() + read_app_js()

    assert "Início" in text
    assert "Hábitos" in text
    assert "Vídeos" in text
    assert "Módulos do App" in text
    for mojibake in ["Ă", "Â", "Ã¡", "Ã©", "Ã­", "Ã³", "Ãº", "Ã§", "ðŸ", "â€", "â\x9d"]:
        assert mojibake not in text


def test_mobile_youtube_embed_has_referrer_policy():
    app_js = read_app_js()
    html = read_index_html()
    player_html = read_youtube_player_html()

    assert 'referrerpolicy="strict-origin-when-cross-origin"' in app_js
    assert "yt-embed-block" in app_js
    assert "getYouTubeEmbedSrc" in app_js
    assert "getYouTubeEmbedOrigin" in app_js
    assert "youtube-nocookie.com/embed/" in app_js
    assert "origin: origin" in app_js
    assert "mariagilda402-rgb.github.io/Project-AI/mobile/youtube-player.html" in app_js
    assert "allowfullscreen" in app_js
    assert "picture-in-picture" in app_js
    assert 'name="referrer"' in html
    assert 'id="yt-modal"' in html
    assert "youtube-nocookie.com/embed/" in player_html
    assert "setAttribute('referrerpolicy', 'strict-origin-when-cross-origin')" in player_html
    assert "origin: origin" in player_html


def test_mobile_hidden_note_textarea_cannot_render_white_box():
    html = read_index_html()
    css = (ROOT / "mobile" / "style.css").read_text(encoding="utf-8")
    assert 'id="note-content" class="legacy-hidden-textarea"' in html
    assert ".legacy-hidden-textarea" in css
    assert "display: none !important" in css
    assert ".rich-editor" in css and "background: transparent" in css


def test_mobile_note_editor_scrolls_and_uses_compact_toolbar():
    html = read_index_html()
    css = (ROOT / "mobile" / "style.css").read_text(encoding="utf-8")

    assert 'class="note-editor-writing-area"' in html
    assert 'class="note-editor-toolbar-float"' in html
    assert ".note-editor-writing-area" in css
    assert "overflow-y: auto" in css
    assert "flex: 1" in css
    assert ".note-editor-toolbar-float" in css
    assert "height: 0" in css
    assert "rich-toolbar-collapsible" not in html
    overflow_start = html.index('id="rt-overflow-menu"')
    overflow_html = html[overflow_start:html.index("</div>", overflow_start) + 6]
    for action in ["richCmd('bold')", "openYouTubeModal()", "openJarvisPanel()", "openSlashMenu()"]:
        assert action in overflow_html


def test_mobile_youtube_player_is_compact_inside_notes():
    css = (ROOT / "mobile" / "style.css").read_text(encoding="utf-8")

    assert ".yt-embed-block" in css
    assert "max-width: 300px" in css
    assert "aspect-ratio: 16 / 9" in css
    assert "margin: 10px auto" in css


def test_mobile_sync_tables_include_core_life_os_tables():
    app_js = read_app_js()
    for table in ["'habit_logs'", "'flashcards'", "'journal_entries'", "'quiz_attempts'"]:
        assert table in app_js


def test_mobile_jarvis_cloud_and_tts_paths_are_real():
    app_js = read_app_js()
    assert "window.callJarvisChat" in app_js
    assert "jarvis-chat" in app_js
    assert "jarvis-note-action" in app_js
    assert "jarvis-tts" in app_js
    assert "window.speakJarvisText" in app_js
    assert "speechSynthesis" in app_js
    assert "SpeechSynthesisUtterance" in app_js
    edge = (ROOT / "supabase" / "functions" / "jarvis-chat" / "index.ts").read_text(encoding="utf-8")
    note_edge = (ROOT / "supabase" / "functions" / "jarvis-note-action" / "index.ts").read_text(encoding="utf-8")
    assert "generativelanguage.googleapis.com" in edge
    assert "GEMINI_API_KEY" in edge
    assert "generativelanguage.googleapis.com" in note_edge
    assert "GEMINI_API_KEY" in note_edge


def test_mobile_no_literal_backslash_n_in_html():
    html = read_index_html()
    assert "\\n        <div" not in html
