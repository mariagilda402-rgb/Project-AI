"""ADB smoke test: validates YouTube embed runtime on a connected Android device."""

from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ADB = ROOT / "platform-tools" / "adb.exe"
MOBILE_DIR = ROOT / "mobile"
PACKAGE = "com.nexus.mobile"
BUNDLE_FILES = [
    "index.html",
    "app.js",
    "style.css",
    "youtube-player.html",
    "manifest.json",
    "sw.js",
    "version.json",
]
SAMPLE_VIDEO_ID = "dQw4w9WgXcQ"


def _adb(*args: str, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(ADB), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def _device_connected() -> bool:
    if not ADB.exists():
        return False
    result = _adb("devices")
    lines = [line for line in result.stdout.splitlines() if "\tdevice" in line]
    return len(lines) > 0


def _push_bundle_to_device() -> None:
    _adb("shell", "run-as", PACKAGE, "mkdir", "files")
    _adb("shell", "run-as", PACKAGE, "mkdir", "files/mobile_bundle")
    for file_name in BUNDLE_FILES:
        local_path = MOBILE_DIR / file_name
        assert local_path.exists(), f"Missing bundle file: {file_name}"
        tmp_path = f"/data/local/tmp/{file_name}"
        push = _adb("push", str(local_path), tmp_path)
        assert push.returncode == 0, push.stderr or push.stdout
        copy = _adb(
            "shell",
            "run-as",
            PACKAGE,
            "cp",
            tmp_path,
            f"files/mobile_bundle/{file_name}",
        )
        assert copy.returncode == 0, copy.stderr or copy.stdout


def _read_bundle_file(file_name: str) -> str:
    result = _adb("shell", "run-as", PACKAGE, "cat", f"files/mobile_bundle/{file_name}")
    assert result.returncode == 0, result.stderr or result.stdout
    return result.stdout


def _restart_app() -> None:
    _adb("logcat", "-c")
    _adb("shell", "am", "force-stop", PACKAGE)
    start = _adb(
        "shell",
        "am",
        "start",
        "-n",
        f"{PACKAGE}/.MainActivity",
    )
    assert start.returncode == 0, start.stderr or start.stdout
    time.sleep(5)


def _simulate_embed_src_for_origin(origin: str | None) -> str:
    if origin and origin.startswith("https://"):
        return (
            f"https://www.youtube-nocookie.com/embed/{SAMPLE_VIDEO_ID}"
            f"?rel=0&playsinline=1&origin={origin}"
        )
    return (
        "https://mariagilda402-rgb.github.io/Project-AI/mobile/youtube-player.html"
        f"?video={SAMPLE_VIDEO_ID}"
    )


@pytest.mark.skipif(not _device_connected(), reason="No Android device connected via ADB")
def test_adb_bundle_has_direct_youtube_embed_logic_not_local_wrapper_only():
    _push_bundle_to_device()
    app_js = _read_bundle_file("app.js")

    assert "function getYouTubeEmbedSrc" in app_js
    assert "function getYouTubeEmbedOrigin" in app_js
    assert "youtube-nocookie.com/embed/" in app_js
    assert "origin: origin" in app_js
    assert "mariagilda402-rgb.github.io/Project-AI/mobile/youtube-player.html" in app_js


@pytest.mark.skipif(not _device_connected(), reason="No Android device connected via ADB")
def test_adb_bundle_index_has_floating_toolbar_without_spacer_row():
    _push_bundle_to_device()
    html = _read_bundle_file("index.html")

    assert 'class="note-editor-toolbar-float"' in html
    assert "rich-toolbar-collapsible" not in html
    assert 'class="note-editor-writing-area"' in html


@pytest.mark.skipif(not _device_connected(), reason="No Android device connected via ADB")
def test_adb_runtime_embed_src_avoids_local_wrapper_404():
    _push_bundle_to_device()
    _restart_app()

    app_js = _read_bundle_file("app.js")
    uses_appassets = "appassets.androidplatform.net" in app_js
    origin = "https://appassets.androidplatform.net" if uses_appassets else None
    src = _simulate_embed_src_for_origin(origin)

    assert "youtube-nocookie.com/embed/" in src or "youtube-player.html" in src
    assert "file://" not in src
    assert f"/mobile_bundle/youtube-player.html" not in src

    logcat = _adb("logcat", "-d", "-t", "250")
    combined = (logcat.stdout or "") + (logcat.stderr or "")
    assert not re.search(r"(?i)(file not found|error\\s*404|embedder\\.identity)", combined), (
        "Logcat shows YouTube/embed errors after app restart:\n" + combined[-2500:]
    )
