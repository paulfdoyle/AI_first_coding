#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


IGNORED_DIRS = {".git", ".venv", "node_modules", "__pycache__"}
IGNORED_FILES = {".DS_Store"}


@dataclass(frozen=True)
class ReintegrationPaths:
    source_root: Path
    source_ai_first: Path
    scratch_root: Path
    scratch_copy: Path


def _now_stamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _date_stamp() -> str:
    return time.strftime("%Y-%m-%d")


def _timestamp_slug() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.is_dir():
            if path.name in IGNORED_DIRS:
                continue
        if path.is_file():
            if path.name in IGNORED_FILES:
                continue
            yield path


def _build_manifest(root: Path) -> Dict[str, str]:
    manifest: Dict[str, str] = {}
    for file_path in _iter_files(root):
        rel = file_path.relative_to(root).as_posix()
        manifest[rel] = _hash_file(file_path)
    return manifest


def _diff_manifests(
    current: Dict[str, str], incoming: Dict[str, str]
) -> Tuple[List[str], List[str], List[str], List[str]]:
    current_keys = set(current.keys())
    incoming_keys = set(incoming.keys())
    added = sorted(incoming_keys - current_keys)
    removed = sorted(current_keys - incoming_keys)
    common = current_keys & incoming_keys
    changed = sorted([k for k in common if current[k] != incoming[k]])
    same = sorted([k for k in common if current[k] == incoming[k]])
    return added, removed, changed, same


def _find_ai_first_dir(source_path: Path) -> Tuple[Path, Path]:
    if source_path.is_dir() and source_path.name == "AI_first":
        return source_path.parent, source_path
    candidate = source_path / "AI_first"
    if candidate.is_dir():
        return source_path, candidate
    raise FileNotFoundError("No AI_first directory found in source path")


def _git_tracked_files(root: Path, rel_dir: Path) -> Optional[List[Path]]:
    if not (root / ".git").exists():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--", str(rel_dir)],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    if not result.stdout:
        return []
    paths = [Path(p) for p in result.stdout.split("\0") if p]
    return paths


def _copy_ai_first(src: Path, dest: Path, *, tracked: Optional[List[Path]] = None) -> str:
    if tracked is not None:
        dest.mkdir(parents=True, exist_ok=True)
        for rel_path in tracked:
            if rel_path.name in IGNORED_FILES:
                continue
            if any(part in IGNORED_DIRS for part in rel_path.parts):
                continue
            src_path = src.parent / rel_path
            if not src_path.exists():
                continue
            target = dest / rel_path.relative_to(src.relative_to(src.parent))
            target.parent.mkdir(parents=True, exist_ok=True)
            if src_path.is_file():
                shutil.copy2(src_path, target)
        return "tracked"

    def _ignore(path: str, names: List[str]) -> List[str]:
        ignored: List[str] = []
        for name in names:
            if name in IGNORED_DIRS or name in IGNORED_FILES:
                ignored.append(name)
        return ignored

    shutil.copytree(src, dest, ignore=_ignore)
    return "full"


def run_reintegration(
    *,
    source_path: str,
    current_ai_first: Path,
    scratch_root: Path,
    report_path: Optional[Path] = None,
    markdown_path: Optional[Path] = None,
) -> Dict[str, object]:
    source_root, source_ai_first = _find_ai_first_dir(Path(source_path).expanduser())
    scratch_root.mkdir(parents=True, exist_ok=True)
    scratch_copy = scratch_root / f"ai_first_{_timestamp_slug()}"
    rel_ai_first = source_ai_first.relative_to(source_root)
    tracked = _git_tracked_files(source_root, rel_ai_first)
    copy_mode = _copy_ai_first(source_ai_first, scratch_copy, tracked=tracked)

    incoming_manifest = _build_manifest(scratch_copy)
    current_manifest = _build_manifest(current_ai_first)
    added, removed, changed, same = _diff_manifests(current_manifest, incoming_manifest)

    warnings: List[str] = []
    if tracked is None:
        warnings.append("Source repo is not a git repository; .gitignore rules not applied.")

    summary = {
        "timestamp": _now_stamp(),
        "date": _date_stamp(),
        "source_root": str(source_root),
        "source_ai_first": str(source_ai_first),
        "scratch_copy": str(scratch_copy),
        "copy_mode": copy_mode,
        "tracked_count": len(tracked) if tracked is not None else None,
        "warnings": warnings,
        "counts": {
            "added": len(added),
            "removed": len(removed),
            "changed": len(changed),
            "same": len(same),
            "total_current": len(current_manifest),
            "total_incoming": len(incoming_manifest),
        },
        "added": added,
        "removed": removed,
        "changed": changed,
    }

    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    if markdown_path:
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(_render_markdown(summary), encoding="utf-8")

    return summary


def _render_markdown(summary: Dict[str, object]) -> str:
    counts = summary.get("counts", {})
    lines = [
        "# Reintegration Summary",
        "",
        f"- Timestamp: {summary.get('timestamp', '')}",
        f"- Source: {summary.get('source_ai_first', '')}",
        f"- Scratch copy: {summary.get('scratch_copy', '')}",
        "",
        "## Counts",
        f"- Added: {counts.get('added', 0)}",
        f"- Removed: {counts.get('removed', 0)}",
        f"- Changed: {counts.get('changed', 0)}",
        f"- Same: {counts.get('same', 0)}",
        "",
        "## Changed Files (top 50)",
    ]
    changed = summary.get("changed", [])
    for path in list(changed)[:50]:
        lines.append(f"- {path}")
    if len(changed) > 50:
        lines.append(f"- ... {len(changed) - 50} more")
    lines.append("")
    return "\n".join(lines)
