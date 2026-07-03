package com.nexus.mobile;

/**
 * Web bundle paths copied to assets and OTA updates.
 */
public final class WebBundleConfig {

    public static final String BUNDLE_DIR_NAME = "mobile_bundle";
    public static final String REMOTE_BUNDLE_BASE = "https://mariagilda402-rgb.github.io/Project-AI/mobile/";

    public static final String[] WEB_BUNDLE_FILES = {
        "version.json",
        "index.html",
        "style.css",
        "app.js",
        "nexus-audio.js",
        "nexus-phase15.js",
        "youtube-player.html",
        "manifest.json",
        "sw.js",
        "js/nexus-core.js",
        "js/nexus-studies.js",
        "js/nexus-gamification.js",
        "js/nexus-journal.js",
        "js/nexus-fitness.js",
        "js/nexus-habits.js",
        "js/nexus-tasks.js",
        "js/nexus-routines.js",
        "js/nexus-theme.js",
        "js/nexus-editor.js",
        "js/nexus-study-tools.js",
        "js/nexus-studies-graph.js",
        "js/nexus-analytics.js",
        "js/nexus-auth.js",
        "js/nexus-forms.js",
        "js/nexus-cleaner.js",
    };

    private WebBundleConfig() {}
}
