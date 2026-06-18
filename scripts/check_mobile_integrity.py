#!/usr/bin/env python3
"""Guardrail checks for Nexus mobile WebView/PWA files.

The mobile runtime is authored as ordered modules in mobile/js/*.js and bundled
into mobile/app.js. This script catches common agent regressions before commit.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "mobile" / "js" / "manifest.txt"
APP_JS = ROOT / "mobile" / "app.js"
INDEX_HTML = ROOT / "mobile" / "index.html"
VERSION_JSON = ROOT / "mobile" / "version.json"
FORBIDDEN_FILES = [ROOT / "mobile" / "app.js.new"]
KNOWN_INLINE_GLOBALS = {"alert", "confirm", "prompt", "setTimeout", "clearTimeout", "if"}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def manifest_modules() -> list[Path]:
    if not MANIFEST.is_file():
        fail(f"missing manifest: {MANIFEST.relative_to(ROOT)}")
    modules: list[Path] = []
    for line_no, raw in enumerate(MANIFEST.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        path = ROOT / line
        if not path.is_file():
            fail(f"manifest entry on line {line_no} does not exist: {line}")
        if path.suffix != ".js":
            fail(f"manifest entry on line {line_no} is not JavaScript: {line}")
        modules.append(path)
    if not modules:
        fail("mobile manifest has no modules")
    return modules


def expected_bundle(modules: list[Path]) -> str:
    return "\n".join(path.read_text(encoding="utf-8").rstrip() + "\n" for path in modules)


def check_bundle_current(modules: list[Path]) -> None:
    if not APP_JS.is_file():
        fail("mobile/app.js is missing")
    if APP_JS.read_text(encoding="utf-8") != expected_bundle(modules):
        fail("mobile/app.js is stale; run python scripts/bundle_mobile_js.py")


def check_node_syntax(files: list[Path]) -> None:
    for path in files:
        result = subprocess.run(["node", "--check", str(path)], cwd=ROOT, text=True, capture_output=True)
        if result.returncode != 0:
            fail(f"JavaScript syntax check failed for {path.relative_to(ROOT)}:\n{result.stderr or result.stdout}")


def check_html_contracts(app_js: str) -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")
    ids = re.findall(r'\bid=["\']([^"\']+)["\']', html)
    duplicates = sorted(item for item, count in Counter(ids).items() if count > 1)
    if duplicates:
        fail("duplicate HTML ids: " + ", ".join(duplicates))

    targets = set(re.findall(r'data-target=["\'](view-[^"\']+)["\']', html))
    missing_views = sorted(target for target in targets if f'id="{target}"' not in html and f"id='{target}'" not in html)
    if missing_views:
        fail("navigation targets without matching views: " + ", ".join(missing_views))

    handlers = set(re.findall(r'on(?:click|change|input|submit)=["\']\s*([A-Za-z_$][\w$]*)\s*\(', html))
    missing_handlers = sorted(
        handler
        for handler in handlers
        if handler not in KNOWN_INLINE_GLOBALS
        and f"function {handler}" not in app_js
        and f"window.{handler}" not in app_js
    )
    if missing_handlers:
        fail("inline HTML handlers missing from JS: " + ", ".join(missing_handlers))


def check_version_json() -> None:
    try:
        payload = json.loads(VERSION_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"mobile/version.json is invalid JSON: {exc}")
    if not isinstance(payload, dict):
        fail("mobile/version.json must contain a JSON object")


def check_runtime_contracts(app_js: str) -> None:
    required = [
        "window.syncData",
        "window.toggleJarvisCall",
        "window.sendChatMessage",
        "window.refreshViewContent",
        "window.NexusCalendar",
        "installWebUpdate",
    ]
    missing = [token for token in required if token not in app_js]
    if missing:
        fail("required mobile runtime contracts missing: " + ", ".join(missing))


def main() -> int:
    for path in FORBIDDEN_FILES:
        if path.exists():
            fail(f"obsolete file must be removed: {path.relative_to(ROOT)}")

    modules = manifest_modules()
    check_bundle_current(modules)
    app_js = APP_JS.read_text(encoding="utf-8")
    check_node_syntax([APP_JS, *modules])
    check_html_contracts(app_js)
    check_version_json()
    check_runtime_contracts(app_js + "\n" + INDEX_HTML.read_text(encoding="utf-8"))
    print("Mobile integrity checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
