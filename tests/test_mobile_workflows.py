from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_apk_workflow_sets_up_android_sdk_before_build():
    workflow = (ROOT / ".github" / "workflows" / "build-apk.yml").read_text(encoding="utf-8")

    assert "android-actions/setup-android" in workflow
    assert "sdkmanager" in workflow
    assert "platforms;android-34" in workflow
    assert "build-tools;34.0.0" in workflow
    assert "assembleDebug" in workflow


def test_mobile_pages_workflow_deploys_mobile_directory():
    workflow_path = ROOT / ".github" / "workflows" / "deploy-mobile.yml"

    assert workflow_path.exists()
    workflow = workflow_path.read_text(encoding="utf-8")
    assert "actions/configure-pages" in workflow
    assert "actions/upload-pages-artifact" in workflow
    assert "path: mobile" in workflow
    assert "actions/deploy-pages" in workflow


def test_android_apk_embeds_mobile_bundle_and_native_update_bridge():
    build_gradle = (ROOT / "mobile-apk" / "app" / "build.gradle").read_text(encoding="utf-8")
    main_activity = (
        ROOT
        / "mobile-apk"
        / "app"
        / "src"
        / "main"
        / "java"
        / "com"
        / "nexus"
        / "mobile"
        / "MainActivity.java"
    ).read_text(encoding="utf-8")
    mobile_index = (ROOT / "mobile" / "index.html").read_text(encoding="utf-8")

    assert "assets.srcDirs" in build_gradle
    assert "../mobile" in build_gradle
    assert "file:///android_asset/index.html" in main_activity
    assert "addJavascriptInterface" in main_activity
    assert "NexusAndroid" in main_activity
    assert "installWebUpdate" in main_activity
    assert "requestPermissions" in main_activity
    assert "NexusAndroid.installWebUpdate" in mobile_index


def test_android_apk_exposes_native_apk_update_installer_flow():
    manifest = (
        ROOT
        / "mobile-apk"
        / "app"
        / "src"
        / "main"
        / "AndroidManifest.xml"
    ).read_text(encoding="utf-8")
    main_activity = (
        ROOT
        / "mobile-apk"
        / "app"
        / "src"
        / "main"
        / "java"
        / "com"
        / "nexus"
        / "mobile"
        / "MainActivity.java"
    ).read_text(encoding="utf-8")
    mobile_index = (ROOT / "mobile" / "index.html").read_text(encoding="utf-8")
    file_paths = ROOT / "mobile-apk" / "app" / "src" / "main" / "res" / "xml" / "file_paths.xml"

    assert "android.permission.REQUEST_INSTALL_PACKAGES" in manifest
    assert "androidx.core.content.FileProvider" in manifest
    assert file_paths.exists()
    assert "apk-update.json" in main_activity
    assert "installNativeUpdate" in main_activity
    assert "canRequestPackageInstalls" in main_activity
    assert "ACTION_INSTALL_PACKAGE" in main_activity
    assert "application/vnd.android.package-archive" in main_activity
    assert "sha256" in main_activity
    assert "NexusAndroid.installNativeUpdate" in mobile_index


def test_apk_workflow_publishes_signed_release_manifest_for_self_updates():
    workflow = (ROOT / ".github" / "workflows" / "build-apk.yml").read_text(encoding="utf-8")
    build_gradle = (ROOT / "mobile-apk" / "app" / "build.gradle").read_text(encoding="utf-8")

    assert "ANDROID_KEYSTORE_BASE64" in workflow
    assert "assembleRelease" in workflow
    assert "sha256sum" in workflow
    assert "apk-update.json" in workflow
    assert "gh release" in workflow
    assert "nexus-mobile-latest" in workflow
    assert "signingConfigs" in build_gradle
    assert "NEXUS_ANDROID_KEYSTORE_PATH" in build_gradle
