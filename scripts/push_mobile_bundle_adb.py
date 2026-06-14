"""Push mobile web bundle to connected Android device via ADB."""
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
    "nexus-audio.js",
    "nexus-phase15.js",
    "youtube-player.html",
    "manifest.json",
    "sw.js",
]


def adb(*args: str) -> subprocess.CompletedProcess[str]:
    cmd = [str(ADB), *args]
    print(">", " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def main() -> int:
    if not ADB.exists():
        print("adb not found:", ADB)
        return 1
    devices = adb("devices")
    if "\tdevice" not in devices.stdout:
        print("No device connected")
        print(devices.stdout)
        return 1

    adb("shell", "run-as", PACKAGE, "mkdir", "-p", "files/mobile_bundle")
    for name in FILES:
        local = MOBILE / name
        if not local.exists():
            print("Missing:", local)
            return 1
        tmp = f"/data/local/tmp/nexus_{name}"
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
            f"files/mobile_bundle/{name}",
        )
        if copy.returncode != 0:
            print("cp failed for", name, copy.stderr or copy.stdout)
            return copy.returncode
        adb("shell", "rm", "-f", tmp)
        print("OK", name, local.stat().st_size, "bytes")

    adb("shell", "am", "force-stop", PACKAGE)
    start = adb("shell", "am", "start", "-n", f"{PACKAGE}/.MainActivity")
    if start.returncode != 0:
        print(start.stderr or start.stdout)
        return start.returncode
    print("Bundle deployed and app restarted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
