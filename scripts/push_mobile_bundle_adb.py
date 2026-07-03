"""Push the mobile web bundle to a connected Android device via ADB.

Usage:
    python scripts/push_mobile_bundle_adb.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADB = ROOT / "platform-tools" / "adb.exe"
MOBILE = ROOT / "mobile"
PACKAGE = "com.nexus.mobile"

FILES = [
    "version.json",
    "index.html",
    "style.css",
    "app.js",
    "youtube-player.html",
    "manifest.json",
    "sw.js",
]


def adb(*args: str) -> subprocess.CompletedProcess[str]:
    cmd = [str(ADB), *args]
    print(">", " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def push_file(local: Path, dest_rel: str) -> int:
    """Push a single file to the app's internal storage via adb."""
    tmp = f"/data/local/tmp/nexus_{dest_rel.replace('/', '_')}"
    push = adb("push", str(local), tmp)
    if push.returncode != 0:
        print(push.stderr or push.stdout)
        return push.returncode
    copy = adb(
        "shell",
        "run-as",
        PACKAGE,
        "cp",
        tmp,
        f"files/mobile_bundle/{dest_rel}",
    )
    if copy.returncode != 0:
        print("cp failed for", dest_rel, copy.stderr or copy.stdout)
        return copy.returncode
    adb("shell", "rm", "-f", tmp)
    print("OK", dest_rel, local.stat().st_size, "bytes")
    return 0


def main() -> int:
    if not ADB.exists():
        print("adb not found:", ADB)
        return 1

    devices = adb("devices")
    if "device" not in devices.stdout.split("\n", 1)[-1]:
        print("No device connected.\nOutput:", devices.stdout)
        return 1

    # Create bundle directory
    adb("shell", "run-as", PACKAGE, "mkdir", "-p", "files/mobile_bundle")

    # Push main bundle files
    for name in FILES:
        local = MOBILE / name
        if not local.exists():
            print("Missing:", local)
            return 1
        if push_file(local, name) != 0:
            return 1

    # Push JS modules if they exist
    js_dir = MOBILE / "js"
    if js_dir.is_dir():
        js_files = sorted(js_dir.glob("*.js"))
        if js_files:
            adb("shell", "run-as", PACKAGE, "mkdir", "-p", "files/mobile_bundle/js")
            for js_file in js_files:
                if push_file(js_file, f"js/{js_file.name}") != 0:
                    return 1

    # Restart the app
    adb("shell", "am", "force-stop", PACKAGE)
    start = adb("shell", "am", "start", "-n", f"{PACKAGE}/.MainActivity")
    if start.returncode != 0:
        print("Failed to start app:", start.stderr or start.stdout)
        return start.returncode

    print("Bundle deployed and app restarted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
