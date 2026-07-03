"""Contract tests for the Nexus Mobile web bundle.

These tests verify that critical window handlers, HTML elements,
and structural invariants are preserved across refactors and modularization.
"""
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "mobile" / "app.js"
INDEX_HTML = ROOT / "mobile" / "index.html"
YOUTUBE_PLAYER_HTML = ROOT / "mobile" / "youtube-player.html"


def read_app_js() -> str:
    """Read app.js, preferring split modules if they exist."""
    js_dir = ROOT / "mobile" / "js"
    if js_dir.is_dir():
        parts = [p.read_text(encoding="utf-8") for p in sorted(js_dir.glob("*.js"))]
        if parts:
            return "\n".join(parts)
    return APP_JS.read_text(encoding="utf-8")


def read_index_html() -> str:
    return INDEX_HTML.read_text(encoding="utf-8")


# ── 1. Critical window handlers ─────────────────────────────────

def test_mobile_exposes_critical_window_handlers():
    app_js = read_app_js()
    required = [
        "window.syncData",
        "window.toggleIoT",
        "window.openSettingsView",
        "window.openQuiz",
        "window.startQuiz",
        "window.startJournalDictation",
        "window.toggleJarvisCall",
        "window.loadHabits",
        "window.loadTasks",
        "window.loadStudies",
        "window.loadRoutines",
        "window.loadUserStats",
        "window.loadCleaner",
        "window.openCleanerView",
        "window.promptAddHabit",
        "window.promptAddTask",
        "window.promptAddGoal",
        "window.navigateTo",
        "window.handleOAuthCallback",
        "window.triggerOcrCamera",
    ]
    for name in required:
        assert name in app_js, f"Missing {name}"


def test_mobile_exposes_module_loaders():
    app_js = read_app_js()
    loaders = [
        "window.loadGoals",
        "window.loadFitness",
        "window.loadFinance",
        "window.loadShop",
        "window.loadVideos",
        "window.loadJournal",
    ]
    for name in loaders:
        assert name in app_js, f"Missing loader: {name}"


# ── 2. Supabase & sync ──────────────────────────────────────────

def test_mobile_app_does_not_redeclare_supabase_sdk_global():
    app_js = read_app_js()
    assert not re.search(r"^\s*(?:let|const)\s+supabase\b", app_js, re.MULTILINE)
    assert "window.nexusSupabase" in app_js


def test_mobile_sync_tables_include_habit_logs():
    app_js = read_app_js()
    for table in ["'habit_logs'", "'flashcards'", "'journal_entries'"]:
        assert table in app_js, f"Missing sync table {table}"


# ── 3. LocalDB ──────────────────────────────────────────────────

def test_mobile_localdb_exposes_legacy_offline_aliases():
    app_js = read_app_js()
    assert "static getAll(table)" in app_js
    assert "static saveAll(table, data)" in app_js


# ── 4. HTML structure ────────────────────────────────────────────

def test_mobile_nav_targets_all_have_matching_views():
    html = read_index_html()
    targets = re.findall(r'data-target="(view-[^"]+)"', html)
    for target in set(targets):
        assert f'id="{target}"' in html, f"Missing view for nav target {target}"


def test_mobile_nav_targets_have_views_for_videos_and_shop():
    html = read_index_html()
    assert 'data-target="view-videos"' in html
    assert 'id="view-videos"' in html
    assert 'data-target="view-shop"' in html
    assert 'id="view-shop"' in html


def test_mobile_settings_has_single_journal_toggle():
    html = read_index_html()
    assert html.count('id="toggle-journal"') == 1
    assert html.count("toggleModule('journal')") == 1


def test_mobile_has_cleaner_view():
    html = read_index_html()
    assert 'id="view-cleaner"' in html
    assert 'id="cleaner-scan-results"' in html


# ── 5. UTF-8 integrity ──────────────────────────────────────────

def test_mobile_visible_labels_are_utf8_not_mojibake():
    text = read_index_html() + read_app_js()
    # These are multi-byte mojibake patterns that indicate double-encoded UTF-8
    for mojibake in ["Ă", "Ã¡", "Ã©", "Ã­", "Ã³", "Ãº", "Ã§", "ðŸ", "â€™", "â€œ", "â€"]:
        assert mojibake not in text, f"Mojibake detected: {mojibake}"


def test_mobile_no_literal_backslash_n_in_html():
    html = read_index_html()
    assert "\\n        <div" not in html


# ── 6. YouTube embed safety ─────────────────────────────────────

def test_mobile_youtube_embed_has_referrer_policy():
    app_js = read_app_js()
    assert 'referrerpolicy="strict-origin-when-cross-origin"' in app_js
    assert "youtube-nocookie.com/embed/" in app_js
    assert "getYouTubeEmbedSrc" in app_js
    assert "allowfullscreen" in app_js


# ── 7. OAuth ─────────────────────────────────────────────────────

def test_mobile_exposes_oauth_handlers():
    app_js = read_app_js()
    assert "window.handleOAuthCallback" in app_js
    assert "getOAuthRedirectUrl" in app_js
    assert "window.triggerOcrCamera" in app_js


def test_mobile_apk_has_oauth_deep_link():
    manifest = (ROOT / "mobile-apk" / "app" / "src" / "main" / "AndroidManifest.xml").read_text(encoding="utf-8")
    assert 'android:scheme="com.nexus.mobile"' in manifest
    assert "singleTask" in manifest


# ── 8. APK structure ─────────────────────────────────────────────

def test_mobile_apk_serves_webview_from_https_appassets():
    main = (ROOT / "mobile-apk" / "app" / "src" / "main" / "java" / "com" / "nexus" / "mobile" / "MainActivity.java").read_text(encoding="utf-8")
    gradle = (ROOT / "mobile-apk" / "app" / "build.gradle").read_text(encoding="utf-8")
    assert "WebViewAssetLoader" in main
    assert "https://appassets.androidplatform.net/assets/index.html" in main
    assert "https://appassets.androidplatform.net/bundle/index.html" in main
    assert "appOrigin" in main
    assert "androidx.webkit:webkit" in gradle


def test_mobile_apk_has_reminder_receiver():
    manifest = (ROOT / "mobile-apk" / "app" / "src" / "main" / "AndroidManifest.xml").read_text(encoding="utf-8")
    assert "ReminderReceiver" in manifest
    main = (ROOT / "mobile-apk" / "app" / "src" / "main" / "java" / "com" / "nexus" / "mobile" / "MainActivity.java").read_text(encoding="utf-8")
    assert "scheduleReminder" in main
    assert "cancelReminder" in main


# ── 9. Functional module guards ──────────────────────────────────

def test_mobile_loaders_guard_missing_containers():
    app_js = read_app_js()
    for loader in ["loadVideos", "loadShop", "loadGoals", "loadFitness", "loadCleaner"]:
        block = re.search(
            rf"(?:function|window\.)({loader})\s*=\s*function|function {loader}\(\)\s*\{{",
            app_js,
        )
        assert block, f"function {loader} not found"
        start = block.start()
        snippet = app_js[start : start + 500]
        if loader == "loadCleaner":
            assert "scanPhoneStorage" in snippet
            continue
        assert re.search(r"if\s*\(\s*!container\s*\)\s*return", snippet), f"{loader} missing container guard"


# ── 10. Chart cleanup ────────────────────────────────────────────

def test_mobile_chart_destroy_uses_chartjs_registry():
    app_js = read_app_js()
    assert "Chart.getChart" in app_js
    assert "window._chartInstances" in app_js


# ── 11. Cleaner module ──────────────────────────────────────────

def test_mobile_exposes_cleaner_handlers():
    app_js = read_app_js()
    required = [
        "window.loadCleaner",
        "window.openCleanerView",
        "window.getCleanerSuggestions",
    ]
    for name in required:
        assert name in app_js, f"Missing {name}"


def test_mobile_cleaner_module_toggle():
    html = read_index_html()
    assert 'id="toggle-cleaner"' in html
    assert "toggleModule('cleaner')" in html
    assert 'data-target="view-cleaner"' in html


# ── 12. Transient surface cleanup ─────────────────────────────────

def test_mobile_closes_transient_modals_when_switching_tabs():
    app_js = read_app_js()
    assert "closeTransientMobileSurfaces" in app_js
