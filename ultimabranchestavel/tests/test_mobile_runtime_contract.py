import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "mobile" / "app.js"
INDEX_HTML = ROOT / "mobile" / "index.html"
YOUTUBE_PLAYER_HTML = ROOT / "mobile" / "youtube-player.html"


def read_app_js() -> str:
    return APP_JS.read_text(encoding="utf-8")


def read_index_html() -> str:
    return INDEX_HTML.read_text(encoding="utf-8")


def read_youtube_player_html() -> str:
    return YOUTUBE_PLAYER_HTML.read_text(encoding="utf-8")


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
    assert "isWifiConnected" in app_js
    assert "requireWifiForJarvis" in app_js


def test_mobile_blocks_jarvis_without_wifi():
    app_js = read_app_js()
    assert "requireWifiForJarvis('ligação')" in app_js
    assert "AndroidNative.isWifiConnected" in app_js or "isWifiConnected()" in app_js


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
        "window.openGoalForm",
        "window.openHabitForm",
        "window.openTaskForm",
        "window.sendChatMessage",
        "window.openQuiz",
        "window.startQuiz",
        "window.startJournalDictation",
        "window.openSettingsView",
        "window.discoverIoT",
        "updateFitnessStats",
        "habit_logs",
        "window.NexusCalendar",
        "window.syncTaskReminders",
        "window.syncHabitReminders",
        "window.openWorkoutForm",
        "window.openSubjectForm",
        "window.checkPendingReminders",
    ]
    for name in required:
        assert name in app_js, f"Missing {name}"


def test_mobile_has_shared_calendar_modal():
    html = read_index_html()
    assert 'id="nexus-calendar-modal"' in html
    assert "window.NexusCalendar" in read_app_js()


def test_mobile_has_goal_and_workout_forms():
    html = read_index_html()
    assert 'id="goal-form-modal"' in html
    assert 'id="workout-form-modal"' in html
    assert "openGoalForm" in read_app_js()
    assert "openWorkoutForm" in read_app_js()


def test_mobile_task_detail_has_notify_and_complete():
    html = read_index_html()
    assert 'id="task-detail-notify-enabled"' in html
    assert "completeCurrentTask" in read_app_js()


def test_mobile_habit_form_has_days_of_week():
    html = read_index_html()
    assert 'id="habit-form-dow"' in html
    assert "saveHabitForm" in read_app_js()


def test_mobile_studies_has_subjects_grid():
    html = read_index_html()
    assert 'id="subjects-grid"' in html
    assert "loadSubjectsGrid" in read_app_js() or "subjects-grid" in read_app_js()


def test_mobile_youtube_embed_has_referrer_policy():
    app_js = read_app_js()
    assert 'referrerpolicy="strict-origin-when-cross-origin"' in app_js
    assert "yt-embed-block" in app_js
    assert "getYouTubeEmbedSrc" in app_js
    assert "getYouTubeEmbedOrigin" in app_js
    assert "youtube-nocookie.com/embed/" in app_js
    assert "origin: origin" in app_js
    assert "mariagilda402-rgb.github.io/Project-AI/mobile/youtube-player.html" in app_js
    assert "allowfullscreen" in app_js
    assert "picture-in-picture" in app_js
    html = read_index_html()
    assert 'name="referrer"' in html
    player_html = read_youtube_player_html()
    assert "youtube-nocookie.com/embed/" in player_html
    assert "setAttribute('referrerpolicy', 'strict-origin-when-cross-origin')" in player_html
    assert "origin: origin" in player_html


def test_mobile_apk_serves_webview_from_https_appassets_for_youtube_referrer():
    main = (ROOT / "mobile-apk" / "app" / "src" / "main" / "java" / "com" / "nexus" / "mobile" / "MainActivity.java").read_text(encoding="utf-8")
    gradle = (ROOT / "mobile-apk" / "app" / "build.gradle").read_text(encoding="utf-8")

    assert "WebViewAssetLoader" in main
    assert "https://appassets.androidplatform.net/assets/index.html" in main
    assert "https://appassets.androidplatform.net/bundle/index.html" in main
    assert '"youtube-player.html"' in main
    assert "appOrigin" in main
    assert "webView.loadUrl(Uri.fromFile" not in main
    assert "androidx.webkit:webkit" in gradle


def test_mobile_save_quick_add_sets_task_name_and_title():
    app_js = read_app_js()
    block = re.search(r"window\.saveQuickAdd\s*=\s*function", app_js)
    assert block
    snippet = app_js[block.start():block.start() + 1200]
    assert "name: title" in snippet or "name:title" in snippet.replace(" ", "")
    assert "title: title" in snippet or "title:title" in snippet.replace(" ", "")


def test_mobile_apk_has_reminder_receiver():
    manifest = (ROOT / "mobile-apk" / "app" / "src" / "main" / "AndroidManifest.xml").read_text(encoding="utf-8")
    assert "ReminderReceiver" in manifest
    main = (ROOT / "mobile-apk" / "app" / "src" / "main" / "java" / "com" / "nexus" / "mobile" / "MainActivity.java").read_text(encoding="utf-8")
    assert "scheduleReminder" in main
    assert "cancelReminder" in main


def test_supabase_migration_phase14_exists():
    migration = ROOT / "supabase_migration_phase14.sql"
    assert migration.exists()
    text = migration.read_text(encoding="utf-8")
    assert "days_of_week" in text
    assert "cover_image" in text
    assert "notify_at" in text


def test_mobile_chart_destroy_uses_chartjs_registry():
    app_js = read_app_js()
    assert "Chart.getChart" in app_js
    assert "window._chartInstances" in app_js
    assert "delete window._chartInstances[id]" in app_js


def test_mobile_closes_transient_modals_when_switching_tabs():
    app_js = read_app_js()
    assert "closeTransientMobileSurfaces" in app_js
    assert "goal-form-modal" in app_js
    assert "workout-form-modal" in app_js
    nav_block = app_js[app_js.find("document.querySelectorAll('.nav-item')"):app_js.find("// ----------------------------------------------------", app_js.find("document.querySelectorAll('.nav-item')") + 1)]
    assert "closeTransientMobileSurfaces" in nav_block


def test_mobile_goal_and_workout_forms_are_centered_overlays():
    html = read_index_html()
    assert 'id="goal-form-modal" class="mobile-form-sheet"' in html
    assert 'id="workout-form-modal" class="mobile-form-sheet"' in html
    css = (ROOT / "mobile" / "style.css").read_text(encoding="utf-8")
    assert ".mobile-form-sheet" in css
    assert "align-items: center" in css
    assert "justify-content: center" in css


def test_mobile_hidden_note_textarea_cannot_render_white_box():
    html = read_index_html()
    assert 'id="note-content" class="legacy-hidden-textarea"' in html
    css = (ROOT / "mobile" / "style.css").read_text(encoding="utf-8")
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


def test_mobile_view_routines_inside_main():
    html = read_index_html()
    main_start = html.index("<main")
    main_end = html.index("</main>")
    main_content = html[main_start:main_end]
    assert 'id="view-routines"' in main_content


def test_mobile_no_literal_backslash_n_in_html():
    html = read_index_html()
    assert "\\n        <div" not in html


def test_mobile_exposes_oauth_handlers():
    app_js = read_app_js()
    assert "window.handleOAuthCallback" in app_js
    assert "getOAuthRedirectUrl" in app_js
    assert "exchangeCodeForSession" in app_js
    assert "window.triggerOcrCamera" in app_js


def test_mobile_apk_has_oauth_deep_link():
    manifest = (ROOT / "mobile-apk" / "app" / "src" / "main" / "AndroidManifest.xml").read_text(encoding="utf-8")
    assert 'android:scheme="com.nexus.mobile"' in manifest
    assert "singleTask" in manifest


def test_mobile_sync_tables_include_habit_logs():
    app_js = read_app_js()
    assert "'habit_logs'" in app_js
    assert "'flashcards'" in app_js
    assert "'journal_entries'" in app_js
    assert "'quiz_attempts'" in app_js


def test_mobile_quiz_enem_exposed():
    app_js = read_app_js()
    html = read_index_html()
    assert "window.openQuiz" in app_js
    assert "ENEM_QUIZ_QUESTIONS" in app_js
    assert 'id="quiz-view"' in html


def test_mobile_loaders_guard_missing_containers():
    app_js = read_app_js()
    for loader in ["loadVideos", "loadShop", "loadGoals", "loadFitness", "loadCleaner"]:
        block = re.search(rf"(?:function|window\.)({loader})\s*=\s*function|function {loader}\(\)\s*\{{", app_js)
        assert block, f"function {loader} not found"
        start = block.start()
        snippet = app_js[start:start + 500]
        if loader == "loadCleaner":
            assert "scanPhoneStorage" in snippet
            continue
        assert re.search(r"if\s*\(\s*!container\s*\)\s*return", snippet), f"{loader} missing container guard"


def test_mobile_has_cleaner_view():
    html = read_index_html()
    assert 'id="view-cleaner"' in html
    assert 'id="cleaner-scan-results"' in html
    assert 'runQuickClean' in html
    assert 'runDeepClean' in html


def test_mobile_exposes_cleaner_handlers():
    app_js = read_app_js()
    required = [
        "window.scanPhoneStorage",
        "window.runQuickClean",
        "window.runDeepClean",
        "window.loadCleaner",
        "window.openCleanerView",
        "window.getCleanerSuggestions",
        "window.requestCleanerAiAdvice",
    ]
    for name in required:
        assert name in app_js, f"Missing {name}"


def test_mobile_cleaner_module_toggle():
    html = read_index_html()
    assert 'id="toggle-cleaner"' in html
    assert "toggleModule('cleaner')" in html
    assert 'data-target="view-cleaner"' in html


def test_mobile_apk_has_storage_clean_bridge():
    main = (ROOT / "mobile-apk" / "app" / "src" / "main" / "java" / "com" / "nexus" / "mobile" / "MainActivity.java").read_text(encoding="utf-8")
    assert "getStorageStats" in main
    assert "getDeviceDiagnostics" in main
    assert "clearAppCache" in main
    assert "runNativeClean" in main
