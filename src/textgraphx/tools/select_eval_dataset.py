"""Select original dataset documents that correspond to annotated gold files.

Example:
  python -m textgraphx.tools.select_eval_dataset \
    --annotated-dir textgraphx/datastore/annotated \
    --original-dir textgraphx/datastore/original_dataset \
    --target-dir textgraphx/datastore/dataset_eval_selected \
    --clean
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path


def _collect_annotated_stems(annotated_dir: Path) -> list[str]:
    return sorted({p.stem for p in annotated_dir.glob("*.xml") if p.is_file()})


def _resolve_original_files(stems: list[str], original_dir: Path, extension: str) -> tuple[list[Path], list[str]]:
    selected: list[Path] = []
    missing: list[str] = []
    for stem in stems:
        candidate = original_dir / f"{stem}{extension}"
        if candidate.exists() and candidate.is_file():
            selected.append(candidate)
        else:
            missing.append(stem)
    return selected, missing


def _materialize_selection(files: list[Path], target_dir: Path, mode: str) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for src in files:
        dst = target_dir / src.name
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        if mode == "copy":
            shutil.copy2(src, dst)
        elif mode == "symlink":
            dst.symlink_to(src.resolve())
        elif mode == "hardlink":
            os.link(src, dst)
        else:
            raise ValueError(f"Unsupported materialization mode: {mode}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Select originals in datastore/original_dataset that correspond to gold "
            "annotations in datastore/annotated."
        )
    )
    parser.add_argument(
        "--annotated-dir",
        default="textgraphx/datastore/annotated",
        help="Directory containing annotated XML gold files.",
    )
    parser.add_argument(
        "--original-dir",
        default="textgraphx/datastore/original_dataset",
        help="Directory containing original dataset files (for example .naf).",
    )
    parser.add_argument(
        "--target-dir",
        default="textgraphx/datastore/dataset_eval_selected",
        help="Directory where selected originals are materialized.",
    )
    parser.add_argument(
        "--original-ext",
        default=".naf",
        help="Extension for files in --original-dir that correspond to annotated stems.",
    )
    parser.add_argument(
        "--mode",
        choices=["copy", "symlink", "hardlink"],
        default="copy",
        help="How to materialize matched files in --target-dir.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove existing files in --target-dir before materializing new selection.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print selection summary, do not write files.",
    )
    parser.add_argument(
        "--fail-on-missing",
        action="store_true",
        help="Exit with non-zero status if any annotated stem has no matching original file.",
    )
    parser.add_argument(
        "--manifest",
        default=None,
        help="Optional JSON path for selection manifest. Defaults to <target-dir>/selection_manifest.json.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    annotated_dir = Path(args.annotated_dir)
    original_dir = Path(args.original_dir)
    target_dir = Path(args.target_dir)
    original_ext = str(args.original_ext)
    if not original_ext.startswith("."):
        original_ext = f".{original_ext}"

    if not annotated_dir.exists() or not annotated_dir.is_dir():
        parser.error(f"Annotated directory not found: {annotated_dir}")
    if not original_dir.exists() or not original_dir.is_dir():
        parser.error(f"Original directory not found: {original_dir}")

    stems = _collect_annotated_stems(annotated_dir)
    selected, missing = _resolve_original_files(stems, original_dir, original_ext)

    if args.clean and not args.dry_run and target_dir.exists():
        shutil.rmtree(target_dir)

    if not args.dry_run:
        _materialize_selection(selected, target_dir, args.mode)

    manifest_path = Path(args.manifest) if args.manifest else (target_dir / "selection_manifest.json")
    manifest = {
        "annotated_dir": str(annotated_dir),
        "original_dir": str(original_dir),
        "target_dir": str(target_dir),
        "original_extension": original_ext,
        "materialization_mode": args.mode,
        "annotated_docs": len(stems),
        "selected_docs": len(selected),
        "missing_docs": len(missing),
        "selected_files": [str(p) for p in selected],
        "missing_stems": missing,
    }
    if not args.dry_run:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(manifest, sort_keys=True))
    if missing and args.fail_on_missing:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
