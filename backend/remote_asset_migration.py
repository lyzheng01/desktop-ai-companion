import argparse
import hashlib
import json
import shutil
from pathlib import Path

from backend.business_store import _iter_remote_asset_products

DEFAULT_AVATAR_FILENAMES = {"HatsuneMikuNT.vrm"}
DEFAULT_DANCE_FILENAMES = {
    "MMD-Ageage Again.unity3d",
    "MMD-World is Mine.unity3d",
}


def compute_sha256(path: Path) -> str:
    sha256 = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()


def copy_unique_assets(
    source_dir: Path,
    target_dir: Path,
    extensions: tuple[str, ...],
    excluded_filenames: set[str] | None = None,
) -> dict:
    source_dir = Path(source_dir)
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    normalized_exts = {ext.lower() for ext in extensions}
    excluded = {name.lower() for name in (excluded_filenames or set())}
    seen_hashes: dict[str, str] = {}
    copied: list[str] = []
    duplicates: list[dict] = []
    skipped_defaults: list[str] = []

    for path in sorted(source_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in normalized_exts:
            continue
        if path.name.lower() in excluded:
            skipped_defaults.append(str(path))
            continue

        sha256_hex = compute_sha256(path)
        if sha256_hex in seen_hashes:
            duplicates.append(
                {
                    "path": str(path),
                    "duplicate_of": seen_hashes[sha256_hex],
                    "sha256": sha256_hex,
                }
            )
            continue

        destination = target_dir / path.name
        if destination.exists():
            destination = target_dir / f"{path.stem}-{sha256_hex[:12]}{path.suffix}"

        shutil.copy2(path, destination)
        seen_hashes[sha256_hex] = str(destination)
        copied.append(str(destination))

    return {
        "source_dir": str(source_dir),
        "target_dir": str(target_dir),
        "copied_count": len(copied),
        "duplicate_count": len(duplicates),
        "skipped_default_count": len(skipped_defaults),
        "copied_files": copied,
        "duplicates": duplicates,
        "skipped_defaults": skipped_defaults,
    }


def run_migration(
    *,
    avatar_source_dir: Path,
    dance_source_dir: Path,
    backend_static_assets_dir: Path,
    report_path: Path,
) -> dict:
    backend_static_assets_dir = Path(backend_static_assets_dir)
    remote_root = backend_static_assets_dir / "remote-assets"
    avatar_target_dir = remote_root / "avatars"
    dance_target_dir = remote_root / "dances"
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    avatars_report = copy_unique_assets(
        Path(avatar_source_dir),
        avatar_target_dir,
        (".vrm",),
        excluded_filenames=DEFAULT_AVATAR_FILENAMES,
    )
    dances_report = copy_unique_assets(
        Path(dance_source_dir),
        dance_target_dir,
        (".unity3d",),
        excluded_filenames=DEFAULT_DANCE_FILENAMES,
    )

    report = {
        "avatars": avatars_report,
        "dances": dances_report,
    }
    _iter_remote_asset_products()
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Copy remote assets into backend storage and deduplicate by SHA256.")
    parser.add_argument("--avatar-source", required=True, dest="avatar_source")
    parser.add_argument("--dance-source", required=True, dest="dance_source")
    parser.add_argument("--backend-static-assets", required=True, dest="backend_static_assets")
    parser.add_argument("--report-path", required=True, dest="report_path")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    run_migration(
        avatar_source_dir=Path(args.avatar_source),
        dance_source_dir=Path(args.dance_source),
        backend_static_assets_dir=Path(args.backend_static_assets),
        report_path=Path(args.report_path),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
