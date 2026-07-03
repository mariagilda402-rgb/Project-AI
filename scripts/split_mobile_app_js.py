"""Split mobile/app.js into modules under mobile/js/ (one-way split for editing).

Usage:
  python scripts/split_mobile_app_js.py          # split app.js -> js/*
  python scripts/split_mobile_app_js.py --bundle # concat js/* -> app.js
  python scripts/split_mobile_app_js.py --verify # split + test, do not save
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "mobile" / "app.js"
OUT = ROOT / "mobile" / "js"

# Each entry: (filename, start_line_1indexed, end_line_1indexed_inclusive)
# Boundaries derived from // ====... section headers in app.js
SECTIONS = [
    ("00-core.js",          1,    1077),   # LocalDB, sync, navigation, boot
    ("01-studies.js",       1078, 1492),   # Studies module
    ("02-gamification.js",  1493, 1587),   # XP & rewards
    ("03-journal.js",       1588, 1804),   # Journal / mood
    ("04-fitness.js",       1805, 1920),   # Fitness module
    ("05-init.js",          1921, 1947),   # DOMContentLoaded init
    ("06-habits.js",        1948, 2133),   # Habits module
    ("07-tasks.js",         2134, 2353),   # Tasks module
    ("08-routines.js",      2354, 2490),   # Routines module
    ("09-theme.js",         2491, 2597),   # AMOLED theme + UI prefs
    ("10-editor.js",        2598, 3418),   # Rich text editor
    ("11-study-tools.js",   3419, 3754),   # Flashcards + Pomodoro
    ("12-studies-graph.js", 3755, 4194),   # Notion covers + graph view
    ("13-analytics.js",     4195, 4467),   # Analytics & charts
    ("14-auth.js",          4468, 4861),   # Multi-user auth & settings
    ("15-sprint4.js",       4862, 5843),   # Calendar, CRUD forms, reminders
    ("16-cleaner.js",       5844, None),   # Phone cleaner module
]

BUNDLE_HEADER = (
    "/**\n"
    " * AUTO-GENERATED bundle — edit mobile/js/*.js then run:\n"
    " *   python scripts/split_mobile_app_js.py --bundle\n"
    " */\n"
)


def split_to_modules(dry_run: bool = False) -> int:
    if not APP.exists() or APP.stat().st_size < 50_000:
        print("app.js missing or too small — restore from git before splitting")
        return 1

    lines = APP.read_text(encoding="utf-8").splitlines()
    total = len(lines)
    print(f"app.js: {total} lines, splitting into {len(SECTIONS)} modules...")

    if not dry_run:
        OUT.mkdir(parents=True, exist_ok=True)

    for name, start, end in SECTIONS:
        chunk = lines[start - 1 : (end if end else total)]
        body = "\n".join(chunk).rstrip() + "\n"
        path = OUT / name

        if dry_run:
            print(f"  [{name}] lines {start}-{end or total} → {len(chunk)} lines")
        else:
            path.write_text(f"/** Nexus Mobile — {name} */\n" + body, encoding="utf-8")
            print(f"  Wrote {name} ({len(chunk)} lines, {path.stat().st_size} bytes)")

    # Verify no lines were dropped
    expected = sum(
        len(lines[s - 1 : (e if e else total)])
        for _, s, e in SECTIONS
    )
    if expected != total:
        print(f"WARNING: expected {total} lines total, got {expected}. GAP DETECTED!")
        return 1

    print(f"OK — all {total} lines accounted for.")
    return 0


def bundle_from_modules() -> int:
    parts = []
    for name, _, _ in SECTIONS:
        path = OUT / name
        if not path.exists():
            print("Missing module:", path)
            return 1
        parts.append(path.read_text(encoding="utf-8"))

    APP.write_text(BUNDLE_HEADER + "\n\n".join(parts), encoding="utf-8")
    print(f"Bundled {len(parts)} modules -> {APP} ({APP.stat().st_size} bytes)")
    return 0


def main() -> int:
    if "--bundle" in sys.argv:
        return bundle_from_modules()
    if "--verify" in sys.argv:
        return split_to_modules(dry_run=True)
    return split_to_modules(dry_run=False)


if __name__ == "__main__":
    raise SystemExit(main())
