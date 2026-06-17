#!/usr/bin/env python3
"""Bundle Nexus Mobile JavaScript modules into mobile/app.js.

The mobile app intentionally loads a single app.js for WebView/PWA stability,
but source edits should happen in mobile/js/*.js. The bundle order is declared
in mobile/js/manifest.txt.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "mobile" / "js" / "manifest.txt"
DEFAULT_OUT = ROOT / "mobile" / "app.js"


def read_manifest(path: Path) -> list[Path]:
    files: list[Path] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        files.append((ROOT / line).resolve())
    return files


def bundle(manifest: Path = DEFAULT_MANIFEST, output: Path = DEFAULT_OUT) -> None:
    parts: list[str] = []
    for module in read_manifest(manifest):
        if not module.is_file():
            raise FileNotFoundError(f"Mobile JS module not found: {module}")
        text = module.read_text(encoding="utf-8")
        parts.append(text.rstrip() + "\n")
    output.write_text("\n".join(parts), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bundle mobile/js modules into mobile/app.js")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    bundle(args.manifest, args.output)
    print(f"Bundled {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
