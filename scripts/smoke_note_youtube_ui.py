#!/usr/bin/env python3
"""Interactive smoke test: opens note editor and inserts YouTube via ADB + DevTools."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADB = ROOT / "platform-tools" / "adb.exe"
PACKAGE = "com.nexus.mobile"
ACTIVITY = f"{PACKAGE}/.MainActivity"
YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
VIDEO_ID = "dQw4w9WgXcQ"
SCREENSHOT = ROOT / "smoke-youtube.png"
DUMP_DIR = ROOT / "ui-dumps"
RESULT_FILE = ROOT / "smoke-result.txt"


def log(msg: str) -> None:
    line = f"[smoke] {msg}"
    print(line)
    with RESULT_FILE.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def adb(*args: str, timeout: int = 90) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(ADB), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def require_device() -> str:
    out = adb("devices").stdout
    lines = [l for l in out.splitlines() if "\tdevice" in l]
    if not lines:
        raise SystemExit("FAIL: no Android device connected")
    serial = lines[0].split()[0]
    log(f"device: {serial}")
    return serial


def restart_app() -> None:
    adb("logcat", "-c")
    adb("shell", "am", "force-stop", PACKAGE)
    adb("shell", "am", "start", "-n", ACTIVITY)
    time.sleep(5)


def screenshot(tag: str) -> Path:
    path = ROOT / f"smoke-{tag}.png"
    proc = subprocess.run(
        [str(ADB), "exec-out", "screencap", "-p"],
        capture_output=True,
        timeout=30,
        check=False,
    )
    if proc.returncode == 0 and proc.stdout:
        path.write_bytes(proc.stdout)
        log(f"screenshot: {path}")
    return path


def dump_ui(tag: str) -> list[dict]:
    DUMP_DIR.mkdir(exist_ok=True)
    remote = "/sdcard/nexus_ui_dump.xml"
    adb("shell", "uiautomator", "dump", remote)
    local = DUMP_DIR / f"{tag}.xml"
    adb("pull", remote, str(local))
    if not local.exists():
        return []
    root = ET.parse(local).getroot()
    nodes = []
    for el in root.iter("node"):
        bounds = el.attrib.get("bounds", "")
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
        if not m:
            continue
        x1, y1, x2, y2 = map(int, m.groups())
        nodes.append({
            "text": (el.attrib.get("text") or "").strip(),
            "desc": (el.attrib.get("content-desc") or "").strip(),
            "cls": el.attrib.get("class", ""),
            "clickable": el.attrib.get("clickable") == "true",
            "cx": (x1 + x2) // 2,
            "cy": (y1 + y2) // 2,
        })
    return nodes


def tap(x: int, y: int, label: str) -> None:
    log(f"tap {label} ({x},{y})")
    adb("shell", "input", "tap", str(x), str(y))
    time.sleep(1.2)


def find_tap(nodes: list[dict], *needles: str, fallback: tuple[int, int] | None = None, label: str = "") -> bool:
    for n in nodes:
        hay = f"{n['text']} {n['desc']}".lower()
        if any(n.lower() in hay for n in needles) and n["clickable"]:
            tap(n["cx"], n["cy"], label or needles[0])
            return True
    if fallback:
        tap(fallback[0], fallback[1], f"{label or needles[0]} fallback")
        return True
    return False


def devtools_eval(js: str) -> str:
    adb("forward", "tcp:9222", "localabstract:chrome_devtools_remote")
    try:
        with urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=6) as resp:
            pages = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"DevTools unavailable: {exc}") from exc

    if not pages:
        raise RuntimeError("No DevTools targets")

    page = next((p for p in pages if "Nexus" in p.get("title", "") or PACKAGE in p.get("url", "")), pages[0])
    ws_url = page.get("webSocketDebuggerUrl")
    if not ws_url:
        raise RuntimeError("Missing webSocketDebuggerUrl")

    try:
        import websocket  # type: ignore
    except ImportError as exc:
        raise RuntimeError("pip install websocket-client") from exc

    result: dict[str, str] = {}

    def on_message(_ws, message: str) -> None:
        payload = json.loads(message)
        if payload.get("id") == 1 and "result" in payload:
            value = payload["result"].get("result", {}).get("value")
            result["value"] = "" if value is None else str(value)

    ws = websocket.create_connection(ws_url, timeout=12)
    try:
        ws.send(json.dumps({
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {"expression": js, "returnByValue": True},
        }))
        deadline = time.time() + 12
        while "value" not in result and time.time() < deadline:
            on_message(ws, ws.recv())
    finally:
        ws.close()

    if "value" not in result:
        raise RuntimeError("DevTools eval timeout")
    return result["value"]


def inject_youtube_via_devtools() -> dict:
    js = f"""
    (function() {{
      try {{
        const nav = document.querySelector('.nav-item[data-target="view-studies"]');
        if (nav) nav.click();
        if (typeof openNoteEditor === 'function') openNoteEditor(null, null);
        const editor = document.getElementById('note-content-rich');
        if (!editor) return JSON.stringify({{ok:false, step:'no-editor'}});
        editor.focus();
        const videoId = '{VIDEO_ID}';
        const src = (typeof getYouTubeEmbedSrc === 'function')
          ? getYouTubeEmbedSrc(videoId)
          : 'https://www.youtube-nocookie.com/embed/' + videoId;
        const html = '<div class="yt-embed-block" contenteditable="false"><iframe src="' + src + '" title="YouTube" referrerpolicy="strict-origin-when-cross-origin" allow="accelerometer; autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe></div>';
        document.execCommand('insertHTML', false, html);
        const iframe = editor.querySelector('.yt-embed-block iframe');
        return JSON.stringify({{
          ok: true,
          origin: window.location.origin,
          src: iframe ? iframe.getAttribute('src') : null,
          hasBlock: !!editor.querySelector('.yt-embed-block'),
          editorVisible: !!document.getElementById('note-editor-view') && getComputedStyle(document.getElementById('note-editor-view')).display !== 'none'
        }});
      }} catch (e) {{
        return JSON.stringify({{ok:false, error: String(e)}});
      }}
    }})()
    """
    raw = devtools_eval(js)
    return json.loads(raw)


def ui_flow_fallback(w: int, h: int) -> None:
    log("fallback UI taps")
    tap(int(w * 0.45), int(h * 0.97), "Estudos nav")
    tap(int(w - 40), int(h - 150), "FAB nova nota")
    nodes = dump_ui("editor")
    if not find_tap(nodes, "mais", "ellipsis", fallback=(int(w * 0.92), int(h * 0.40)), label="overflow"):
        pass
    nodes = dump_ui("menu")
    find_tap(nodes, "youtube", fallback=(int(w * 0.5), int(h * 0.52)), label="YouTube")
    tap(int(w * 0.5), int(h * 0.46), "url field")
    adb("shell", "input", "text", YOUTUBE_URL.replace(" ", "%s").replace(":", "%s").replace("/", "%s").replace("?", "%s").replace("=", "%s").replace("&", "%s"))
    nodes = dump_ui("modal")
    find_tap(nodes, "inserir", fallback=(int(w * 0.75), int(h * 0.56)), label="Inserir")


def check_errors() -> list[str]:
    found = []
    nodes = dump_ui("final")
    ui_blob = " ".join(f"{n['text']} {n['desc']}" for n in nodes).lower()
    for token in ["404", "file not found", "error 153", "configuration error", "video unavailable"]:
        if token in ui_blob:
            found.append(f"ui:{token}")
    logcat = adb("logcat", "-d", "-t", "150").stdout.lower()
    for token in ["file not found", "error 153", "embedder.identity"]:
        if token in logcat:
            found.append(f"logcat:{token}")
    return found


def main() -> int:
    if RESULT_FILE.exists():
        RESULT_FILE.unlink()
    log("=== Nexus YouTube smoke (interactive) ===")

    require_device()
    restart_app()
    screenshot("01-start")

    w_h = adb("shell", "wm", "size").stdout
    m = re.search(r"(\d+)x(\d+)", w_h)
    w, h = (int(m.group(1)), int(m.group(2))) if m else (1080, 2400)
    log(f"screen {w}x{h}")

    inject_result: dict | None = None
    try:
        inject_result = inject_youtube_via_devtools()
        log(f"devtools inject: {inject_result}")
    except Exception as exc:
        log(f"devtools failed ({exc}), using UI taps")
        ui_flow_fallback(w, h)

    time.sleep(4)
    screenshot("02-after-embed")
    errors = check_errors()

    passed = True
    if inject_result:
        passed = inject_result.get("ok") and inject_result.get("hasBlock")
        if inject_result.get("src") and "file://" in str(inject_result.get("src")):
            passed = False
            errors.append("iframe uses file://")

    if errors:
        passed = False

    log(f"errors= {errors or 'none'}")
    log(f"RESULT: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
