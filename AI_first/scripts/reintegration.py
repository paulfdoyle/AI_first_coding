#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from reintegration_lib import run_reintegration


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Copy external AI_first into scratch and summarize differences.")
    p.add_argument("--source", required=True, help="Path to repo (or AI_first directory) to scan.")
    p.add_argument(
        "--scratch-root",
        default="AI_first/reintegration/scratch",
        help="Scratch root for copied AI_first (default: AI_first/reintegration/scratch).",
    )
    p.add_argument(
        "--report",
        default="AI_first/reintegration/last_reintegration.json",
        help="JSON report output path.",
    )
    p.add_argument(
        "--markdown",
        default="AI_first/reintegration/last_reintegration.md",
        help="Markdown summary output path.",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[2]
    summary = run_reintegration(
        source_path=args.source,
        current_ai_first=root / "AI_first",
        scratch_root=root / args.scratch_root,
        report_path=root / args.report,
        markdown_path=root / args.markdown,
    )
    print("Reintegration summary:")
    print(f"Source: {summary['source_ai_first']}")
    print(f"Scratch copy: {summary['scratch_copy']}")
    print(f"Added: {summary['counts']['added']}")
    print(f"Removed: {summary['counts']['removed']}")
    print(f"Changed: {summary['counts']['changed']}")
    print(f"Report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
