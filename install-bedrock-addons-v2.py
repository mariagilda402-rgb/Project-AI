#!/usr/bin/env python3
"""
Robust installer for Minecraft Bedrock .mcpack/.mcaddon uploads.

Installs validated resource/behavior packs from a world's uploads directory,
updates world_resource_packs.json/world_behavior_packs.json, and writes detailed
logs for debugging.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any


CRAFTY_ROOT = Path("/opt/crafty-4/servers")
LOG_PATH = Path("/var/log/bedrock-addon-installer.log")
PACK_EXTS = {".mcpack", ".mcaddon"}
INNER_ZIP_EXTS = {".mcpack", ".mcaddon", ".zip"}
UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


@dataclass(frozen=True)
class Pack:
    source: Path
    root: Path
    kind: str
    uuid: str
    version: Any
    name: str
    manifest: dict[str, Any]


class InstallError(RuntimeError):
    pass


def setup_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(LOG_PATH, encoding="utf-8"))
    except OSError:
        pass
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
    )


def sanitize_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip())
    cleaned = cleaned.strip("._-")
    return cleaned[:64] or "pack"


def resolve_localized_name(root: Path, raw_name: str) -> str:
    if not raw_name or "." not in raw_name:
        return raw_name
    texts = root / "texts"
    if not texts.is_dir():
        return raw_name

    language_files: list[Path] = []
    languages_json = texts / "languages.json"
    if languages_json.exists():
        try:
            languages = read_json(languages_json, [])
            if isinstance(languages, list):
                for lang in languages:
                    candidate = texts / f"{lang}.lang"
                    if candidate.exists():
                        language_files.append(candidate)
        except InstallError:
            logging.debug("Nao consegui ler languages.json em %s", languages_json, exc_info=True)

    language_files.extend(sorted(texts.glob("*.lang")))
    seen: set[Path] = set()
    for lang_file in language_files:
        if lang_file in seen:
            continue
        seen.add(lang_file)
        try:
            for line in lang_file.read_text(encoding="utf-8-sig", errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key.strip() == raw_name and value.strip():
                    return value.strip()
        except OSError:
            logging.debug("Nao consegui ler arquivo de idioma %s", lang_file, exc_info=True)
    return raw_name


def normalize_version(version: Any) -> Any:
    if isinstance(version, list) and len(version) == 3 and all(isinstance(x, int) for x in version):
        return version
    if isinstance(version, str):
        parts = version.strip().split(".")
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            return [int(p) for p in parts]
        return version
    raise InstallError(f"Versao invalida no manifest: {version!r}")


def safe_extract_zip(zip_path: Path, dest: Path) -> None:
    logging.debug("Extraindo %s em %s", zip_path, dest)
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            name = info.filename
            pure = PurePosixPath(name)
            if pure.is_absolute() or ".." in pure.parts:
                raise InstallError(f"Zip inseguro, caminho invalido: {name}")
            if info.file_size > 750 * 1024 * 1024:
                raise InstallError(f"Arquivo grande demais dentro do zip: {name}")
        zf.extractall(dest)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise InstallError(f"JSON invalido em {path}: {exc}") from exc


def write_json_atomic(path: Path, data: Any, dry_run: bool) -> None:
    if dry_run:
        logging.info("[dry-run] Atualizaria %s", path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def looks_like_world_dir(path: Path) -> bool:
    markers = [
        "level.dat",
        "levelname.txt",
        "world_behavior_packs.json",
        "world_resource_packs.json",
        "db",
    ]
    return any((path / marker).exists() for marker in markers)


def find_latest_world() -> Path:
    candidates: list[Path] = []
    logging.debug("Procurando pastas uploads dentro de %s", CRAFTY_ROOT)
    for uploads in CRAFTY_ROOT.rglob("uploads"):
        if not uploads.is_dir():
            continue
        world = uploads.parent
        if looks_like_world_dir(world):
            candidates.append(world)
            logging.debug("Candidato de mundo encontrado: %s", world)
        else:
            logging.debug("Ignorando uploads sem marcadores de mundo: %s", uploads)
    if not candidates:
        raise InstallError(
            "Nao encontrei nenhum mundo com pasta uploads dentro de /opt/crafty-4/servers. "
            "Use o caminho manual: install-bedrock-addons /caminho/do/mundo --dry-run --debug"
        )
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def find_server_dir(world_dir: Path, explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    current = world_dir.resolve()
    for parent in [current, *current.parents]:
        if (parent / "bedrock_server").exists():
            return parent
        if parent.name == "servers":
            break
    if world_dir.parent.name == "worlds":
        return world_dir.parent.parent
    raise InstallError("Nao consegui detectar a pasta do servidor. Use --server-dir.")


def discover_manifest_roots(extracted: Path) -> list[Path]:
    roots = [p.parent for p in extracted.rglob("manifest.json") if p.is_file()]
    return sorted(set(roots))


def detect_kind(manifest: dict[str, Any]) -> str:
    modules = manifest.get("modules")
    if not isinstance(modules, list):
        raise InstallError("Manifest sem lista modules")
    types = {str(m.get("type", "")).lower() for m in modules if isinstance(m, dict)}
    has_resources = "resources" in types
    has_behavior = bool(types & {"data", "script", "client_data"})
    if has_behavior and not has_resources:
        return "behavior"
    if has_resources and not has_behavior:
        return "resource"
    if has_behavior and has_resources:
        raise InstallError("Manifest mistura resource e behavior no mesmo pack; separe em packs distintos")
    raise InstallError(f"Nao consegui classificar pack. Tipos encontrados: {sorted(types)}")


def load_pack(source: Path, root: Path) -> Pack:
    manifest_path = root / "manifest.json"
    manifest = read_json(manifest_path, None)
    if not isinstance(manifest, dict):
        raise InstallError(f"Manifest invalido em {manifest_path}")
    header = manifest.get("header")
    if not isinstance(header, dict):
        raise InstallError(f"Manifest sem header em {manifest_path}")
    uuid = str(header.get("uuid", "")).lower()
    if not UUID_RE.match(uuid):
        raise InstallError(f"UUID invalido em {manifest_path}: {uuid!r}")
    version = normalize_version(header.get("version"))
    raw_name = str(header.get("name") or root.name)
    name = resolve_localized_name(root, raw_name)
    if name == raw_name and raw_name in {"pack.name", "pack_name"}:
        name = root.name
    kind = detect_kind(manifest)
    return Pack(source=source, root=root, kind=kind, uuid=uuid, version=version, name=name, manifest=manifest)


def unpack_upload(upload: Path, workdir: Path) -> list[Pack]:
    first = workdir / sanitize_name(upload.stem)
    first.mkdir(parents=True, exist_ok=True)
    safe_extract_zip(upload, first)

    queue = [first]
    seen_inner: set[Path] = set()
    packs: list[Pack] = []

    while queue:
        current = queue.pop(0)
        for inner in current.rglob("*"):
            if inner.is_file() and inner.suffix.lower() in INNER_ZIP_EXTS and inner not in seen_inner:
                seen_inner.add(inner)
                nested_dest = workdir / f"nested_{len(seen_inner)}_{sanitize_name(inner.stem)}"
                nested_dest.mkdir(parents=True, exist_ok=True)
                safe_extract_zip(inner, nested_dest)
                queue.append(nested_dest)

    roots = discover_manifest_roots(first)
    for nested in sorted(workdir.glob("nested_*")):
        roots.extend(discover_manifest_roots(nested))

    unique_roots = sorted(set(roots))
    if not unique_roots:
        raise InstallError(f"Nenhum manifest.json encontrado em {upload}")

    for root in unique_roots:
        packs.append(load_pack(upload, root))
    return packs


def list_uploads(uploads_dir: Path) -> list[Path]:
    if not uploads_dir.exists():
        raise InstallError(f"Pasta uploads nao existe: {uploads_dir}")
    uploads = sorted(
        p for p in uploads_dir.iterdir()
        if p.is_file() and p.suffix.lower() in PACK_EXTS
    )
    if not uploads:
        raise InstallError(f"Nenhum .mcpack/.mcaddon encontrado em {uploads_dir}")
    return uploads


def pack_dest(server_dir: Path, pack: Pack) -> Path:
    base = server_dir / ("behavior_packs" if pack.kind == "behavior" else "resource_packs")
    return base / f"{sanitize_name(pack.name)}_{pack.uuid[:8]}"


def backup_path(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return path.with_name(f"{path.name}.bak-{stamp}")


def backup_existing(path: Path, dry_run: bool) -> None:
    if not path.exists():
        return
    dst = backup_path(path)
    if dry_run:
        logging.info("[dry-run] Faria backup de %s para %s", path, dst)
        return
    logging.info("Backup: %s -> %s", path, dst)
    if path.is_dir():
        shutil.copytree(path, dst)
    else:
        shutil.copy2(path, dst)


def merge_activation(existing: list[Any], packs: list[Pack]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for item in existing:
        if isinstance(item, dict) and item.get("pack_id"):
            merged[str(item["pack_id"]).lower()] = {
                "pack_id": str(item["pack_id"]).lower(),
                "version": normalize_version(item.get("version", [1, 0, 0])),
            }
    for pack in packs:
        merged[pack.uuid] = {"pack_id": pack.uuid, "version": pack.version}
    return list(merged.values())


def warn_missing_dependencies(packs: list[Pack]) -> None:
    available = {p.uuid for p in packs}
    for pack in packs:
        deps = pack.manifest.get("dependencies", [])
        if not isinstance(deps, list):
            continue
        for dep in deps:
            if not isinstance(dep, dict) or "uuid" not in dep:
                continue
            dep_uuid = str(dep["uuid"]).lower()
            if UUID_RE.match(dep_uuid) and dep_uuid not in available:
                logging.warning(
                    "Pack %s depende de UUID %s. Se esse pack ja nao estiver instalado, o addon pode falhar.",
                    pack.name,
                    dep_uuid,
                )


def same_uuid_guard(packs: list[Pack]) -> None:
    seen: dict[tuple[str, str], Pack] = {}
    for pack in packs:
        key = (pack.kind, pack.uuid)
        if key in seen:
            raise InstallError(
                f"UUID duplicado nos uploads: {pack.uuid} ({seen[key].source.name} e {pack.source.name})"
            )
        seen[key] = pack


def chown_like_world(path: Path, world_dir: Path, dry_run: bool) -> None:
    if dry_run or os.geteuid() != 0:
        return
    stat = world_dir.stat()
    if path.is_file():
        os.chown(path, stat.st_uid, stat.st_gid)
        return
    for root, dirs, files in os.walk(path):
        os.chown(root, stat.st_uid, stat.st_gid)
        for name in dirs:
            os.chown(os.path.join(root, name), stat.st_uid, stat.st_gid)
        for name in files:
            os.chown(os.path.join(root, name), stat.st_uid, stat.st_gid)


def install(args: argparse.Namespace) -> int:
    world_dir = Path(args.world_dir).resolve() if args.world_dir else find_latest_world()
    server_dir = find_server_dir(world_dir, args.server_dir)
    uploads_dir = Path(args.uploads_dir).resolve() if args.uploads_dir else world_dir / "uploads"

    logging.info("Mundo: %s", world_dir)
    logging.info("Servidor: %s", server_dir)
    logging.info("Uploads: %s", uploads_dir)
    logging.info("Modo dry-run: %s", "sim" if args.dry_run else "nao")

    uploads = list_uploads(uploads_dir)
    logging.info("Uploads encontrados: %s", ", ".join(p.name for p in uploads))

    with tempfile.TemporaryDirectory(prefix="bedrock-addon-install-") as tmp:
        workdir = Path(tmp)
        packs: list[Pack] = []
        for upload in uploads:
            logging.info("Validando upload: %s", upload.name)
            packs.extend(unpack_upload(upload, workdir / sanitize_name(upload.name)))

        same_uuid_guard(packs)
        warn_missing_dependencies(packs)

        resources = [p for p in packs if p.kind == "resource"]
        behaviors = [p for p in packs if p.kind == "behavior"]
        logging.info("Resource packs detectados: %d", len(resources))
        logging.info("Behavior packs detectados: %d", len(behaviors))
        for pack in packs:
            logging.info("Pack: kind=%s uuid=%s version=%s name=%s", pack.kind, pack.uuid, pack.version, pack.name)

        for pack in packs:
            dest = pack_dest(server_dir, pack)
            backup_existing(dest, args.dry_run)
            if args.dry_run:
                logging.info("[dry-run] Instalaria %s em %s", pack.name, dest)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                shutil.rmtree(dest)
            logging.info("Instalando %s em %s", pack.name, dest)
            shutil.copytree(pack.root, dest)
            chown_like_world(dest, world_dir, args.dry_run)

        behavior_json = world_dir / "world_behavior_packs.json"
        resource_json = world_dir / "world_resource_packs.json"
        if behaviors:
            backup_existing(behavior_json, args.dry_run)
            current = read_json(behavior_json, [])
            write_json_atomic(behavior_json, merge_activation(current, behaviors), args.dry_run)
            chown_like_world(behavior_json, world_dir, args.dry_run)
        if resources:
            backup_existing(resource_json, args.dry_run)
            current = read_json(resource_json, [])
            write_json_atomic(resource_json, merge_activation(current, resources), args.dry_run)
            chown_like_world(resource_json, world_dir, args.dry_run)

        if not args.dry_run:
            installed_dir = uploads_dir / "installed"
            installed_dir.mkdir(exist_ok=True)
            for upload in uploads:
                target = installed_dir / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{upload.name}"
                logging.info("Movendo upload instalado: %s -> %s", upload, target)
                shutil.move(str(upload), str(target))
            chown_like_world(installed_dir, world_dir, args.dry_run)

    logging.info("Instalacao concluida. Reinicie o servidor pelo Crafty para aplicar.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Instala .mcpack/.mcaddon de uma pasta uploads no mundo Bedrock.")
    parser.add_argument("world_dir", nargs="?", help="Pasta do mundo. Se omitido, detecta o mundo mais recente com uploads.")
    parser.add_argument("--server-dir", help="Pasta do servidor Bedrock/Crafty.")
    parser.add_argument("--uploads-dir", help="Pasta de uploads. Padrao: WORLD/uploads.")
    parser.add_argument("--dry-run", action="store_true", help="Valida e mostra o que faria, sem alterar arquivos.")
    parser.add_argument("--debug", action="store_true", help="Ativa logs detalhados.")
    args = parser.parse_args()
    setup_logging(args.debug)

    try:
        return install(args)
    except Exception as exc:
        logging.exception("Falha na instalacao: %s", exc)
        print(f"\nERRO: {exc}", file=sys.stderr)
        print(f"Log: {LOG_PATH}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
