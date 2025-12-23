#!/usr/bin/env python3
"""Lightweight local issue tracker helper (template version).

Reads a JSONL issue store and produces JSON or HTML exports with deterministic ordering.
All paths are configurable via flags; defaults assume running from the template root.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any

SEVERITY_ORDER = ["critical", "major", "minor", "nit"]
STATUS_ORDER = ["open", "in_progress", "closed"]
PROJECT_PREFIXES = {
    "bugmgmt": "BMG",
    "project_management": "PMG",
}
PROJECT_OWNERS = {}
ID_PATTERN = re.compile(r"^(?P<prefix>[A-Z0-9]+)-(?P<year>\d{4})-(?P<month>\d{2})-(?P<seq>\d{3})$")
OWNER_PLACEHOLDERS = {"", "unassigned", "<assign>", "tbd"}


def _repo_owner() -> str:
    env_owner = os.environ.get("BUGMGMT_REPO_OWNER", "").strip()
    if env_owner:
        return env_owner
    try:
        result = subprocess.run(
            ["git", "config", "user.name"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


DEFAULT_OWNER = _repo_owner()


def _load_issues(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _severity_weight(severity: str) -> int:
    try:
        return SEVERITY_ORDER.index(severity.lower())
    except ValueError:
        return len(SEVERITY_ORDER)


def _status_weight(status: str) -> int:
    try:
        return STATUS_ORDER.index(status.lower())
    except ValueError:
        return len(STATUS_ORDER)


def _norm(val: Any) -> str:
    return "" if val is None else str(val).strip()


def _apply_owner_defaults(rows: List[Dict[str, Any]]) -> None:
    for issue in rows:
        project = _norm(issue.get("project"))
        if not project:
            continue
        owner = _norm(issue.get("owner")).lower()
        if owner in OWNER_PLACEHOLDERS:
            default_owner = PROJECT_OWNERS.get(project.lower()) or DEFAULT_OWNER
            if default_owner:
                issue["owner"] = default_owner


def _validate_issue_ids(rows: List[Dict[str, Any]]) -> None:
    errors = []
    for idx, issue in enumerate(rows, start=1):
        project = _norm(issue.get("project"))
        issue_id = _norm(issue.get("id"))
        if not project or not issue_id:
            errors.append(f"#{idx} missing project or id (project='{project}', id='{issue_id}')")
            continue
        expected_prefix = PROJECT_PREFIXES.get(project.lower())
        match = ID_PATTERN.match(issue_id)
        if not match:
            errors.append(f"#{idx} id '{issue_id}' does not match <PREFIX>-YYYY-MM-NNN")
            continue
        actual_prefix = match.group("prefix")
        if not expected_prefix:
            errors.append(f"#{idx} project '{project}' has no configured prefix (set PROJECT_PREFIXES)")
        elif actual_prefix != expected_prefix:
            errors.append(
                f"#{idx} id '{issue_id}' prefix '{actual_prefix}' does not match project '{project}' prefix '{expected_prefix}'"
            )
    if errors:
        raise SystemExit("Issue ID validation failed:\n" + "\n".join(errors))


def _sorted(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        rows,
        key=lambda r: (
            _status_weight(_norm(r.get("status", ""))),
            _norm(r.get("project", "")).lower(),
            _severity_weight(_norm(r.get("severity", ""))),
            _norm(r.get("id", "")),
        ),
    )


def _to_json(rows: List[Dict[str, Any]]) -> str:
    return json.dumps(rows, ensure_ascii=True, separators=(",", ":"))


def _to_html(rows: List[Dict[str, Any]], json_rel_path: Path) -> str:
    data_json = json.dumps(rows, ensure_ascii=True)
    json_path_str = json_rel_path.as_posix()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Bug Management Issues</title>
  <link rel="stylesheet" href="style/bugmgmt.css" />
</head>
<body>
  <div class="container">
    <nav class="top-nav">
      <a class="nav-link nav-home" href="index.html">Home</a>
      <a class="nav-link nav-process" href="process_guide.html">Process Management</a>
      <a class="nav-link nav-project" href="PM.html">Project Management</a>
      <a class="nav-link nav-bug" href="bugmgmt_issues.html">Bug Management</a>
    </nav>
    <header class="hero">
      <div>
        <h1 class="h4">Bug Management Issues</h1>
        <p class="muted small">Local, PII-free issues · Deterministic sort (status → project → severity → ID)</p>
      </div>
      <div class="badges">
        <span class="chip" id="totalCount"></span>
      </div>
    </header>

    <div class="card">
      <div class="filter-grid">
        <label>Project<select id="project"></select></label>
        <label>Status<select id="status"></select></label>
        <label>Severity<select id="severity"></select></label>
        <label>Phase<select id="phase"></select></label>
        <label>Stage<select id="stage"></select></label>
        <label>Search<input id="search" placeholder="Search text..." /></label>
        <button id="resetFilters" class="btn">Reset filters</button>
      </div>
      <div class="filter-hint">Source: AI_first/bugmgmt/issues/issues.jsonl · Regenerate exports only when you want the UI refreshed.</div>
      <div class="summary" id="summaryRow"></div>
    </div>

    <div class="card details">
      <div class="details-header">
        <div>
          <h2 class="h4" id="detailTitle">Issue Details</h2>
          <p class="muted small" id="detailMeta">Select a bug to view details.</p>
        </div>
        <div class="badges" id="detailBadges"></div>
      </div>
      <div class="details-grid" id="detailBody">
        <div class="muted small">No issue selected.</div>
      </div>
    </div>

    <div class="card">
      <div class="table-wrap">
        <table class="issues">
          <thead>
            <tr>
              <th>ID</th><th>Status</th><th>Severity</th><th>Project</th><th>Phase</th><th>Stage</th><th>Area</th><th>Details</th>
            </tr>
          </thead>
          <tbody id="issues-body"></tbody>
        </table>
      </div>
    </div>
    
  </div>
  <script>
    window.BUGMGMT_CONFIG = {{ jsonPath: "{json_path_str}" }};
    window.BUGMGMT_FALLBACK = {data_json};
  </script>
  <script src="assets/bugmgmt.js"></script>
</body>
</html>
"""


@dataclass
class Paths:
    data: Path
    json_out: Path
    html_out: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local issue tracker helper (template)")
    parser.add_argument("command", choices=["list"], help="Command to run")
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("AI_first/bugmgmt/issues/issues.jsonl"),
        help="Path to JSONL store",
    )
    parser.add_argument("--format", choices=["json", "html"], default="json", help="Output format")
    parser.add_argument("--output", type=Path, default=None, help="Output file path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = _load_issues(args.data)
    _validate_issue_ids(rows)
    _apply_owner_defaults(rows)
    rows = _sorted(rows)
    if args.format == "json":
        content = _to_json(rows)
        default_out = Path("AI_first/bugmgmt/exports/json/bugmgmt_issues.json")
    else:
        # derive relative JSON path for the UI to fetch (defaults assume AI_first/ui alongside AI_first/bugmgmt/exports)
        default_out = Path("AI_first/ui/bugmgmt_issues.html")
        json_path = Path("AI_first/bugmgmt/exports/json/bugmgmt_issues.json")
        html_out = Path(args.output) if args.output else default_out
        # compute relative path from HTML dir to JSON file
        rel_json = Path(os.path.relpath(json_path, start=html_out.parent))
        content = _to_html(rows, rel_json)
    out_path = args.output or default_out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
