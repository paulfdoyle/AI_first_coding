#!/usr/bin/env python3
"""Render support and project markdown files into static HTML for offline viewing."""
from __future__ import annotations

import argparse
import html
import os
import re
from pathlib import Path
from typing import Iterable, List


TABLE_SEPARATOR = re.compile(r"^\s*\|?\s*:?[-]+:?\s*(\|\s*:?[-]+:?\s*)+\|?\s*$")


def _render_inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"<a href=\"\2\">\1</a>", escaped)
    return escaped


def _split_table_row(line: str) -> List[str]:
    trimmed = line.strip().strip("|")
    return [cell.strip() for cell in trimmed.split("|")]


def _render_markdown(md: str) -> str:
    lines = md.replace("\r\n", "\n").split("\n")
    out: List[str] = []
    in_code = False
    list_type: str | None = None
    idx = 0

    def close_list() -> None:
        nonlocal list_type
        if list_type:
            out.append(f"</{list_type}>")
            list_type = None

    while idx < len(lines):
        line = lines[idx]

        if line.strip().startswith("```"):
            if in_code:
                out.append("</code></pre>")
                in_code = False
            else:
                close_list()
                out.append("<pre><code>")
                in_code = True
            idx += 1
            continue

        if in_code:
            out.append(html.escape(line))
            idx += 1
            continue

        heading = re.match(r"^(#{1,3})\s+(.*)$", line)
        if heading:
            close_list()
            level = len(heading.group(1))
            out.append(f"<h{level}>{_render_inline(heading.group(2))}</h{level}>")
            idx += 1
            continue

        if idx + 1 < len(lines) and "|" in line and TABLE_SEPARATOR.match(lines[idx + 1] or ""):
            close_list()
            header_cells = _split_table_row(line)
            out.append("<table><thead><tr>")
            for cell in header_cells:
                out.append(f"<th>{_render_inline(cell)}</th>")
            out.append("</tr></thead><tbody>")
            idx += 2
            while idx < len(lines) and "|" in lines[idx]:
                row_cells = _split_table_row(lines[idx])
                out.append("<tr>")
                for cell in row_cells:
                    out.append(f"<td>{_render_inline(cell)}</td>")
                out.append("</tr>")
                idx += 1
            out.append("</tbody></table>")
            continue

        ul_item = re.match(r"^\s*[-*]\s+(.*)$", line)
        if ul_item:
            if list_type != "ul":
                close_list()
                out.append("<ul>")
                list_type = "ul"
            out.append(f"<li>{_render_inline(ul_item.group(1))}</li>")
            idx += 1
            continue

        ol_item = re.match(r"^\s*\d+\.\s+(.*)$", line)
        if ol_item:
            if list_type != "ol":
                close_list()
                out.append("<ol>")
                list_type = "ol"
            out.append(f"<li>{_render_inline(ol_item.group(1))}</li>")
            idx += 1
            continue

        if not line.strip():
            close_list()
            idx += 1
            continue

        close_list()
        out.append(f"<p>{_render_inline(line.strip())}</p>")
        idx += 1

    close_list()
    if in_code:
        out.append("</code></pre>")

    return "\n".join(out)


def _extract_title(md: str, default: str) -> str:
    for line in md.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return default


def _build_doc(md_path: Path, out_path: Path, repo_root: Path) -> None:
    md_text = md_path.read_text(encoding="utf-8")
    title = _extract_title(md_text, md_path.stem)
    body = _render_markdown(md_text)
    css_path = repo_root / "AI_first" / "ui" / "style" / "bugmgmt.css"
    home_path = repo_root / "AI_first" / "ui" / "index.html"
    pm_path = repo_root / "AI_first" / "ui" / "PM.html"
    bug_path = repo_root / "AI_first" / "ui" / "bugmgmt_issues.html"
    process_path = repo_root / "AI_first" / "ui" / "process_guide.html"
    css_rel = os.path.relpath(css_path, start=out_path.parent)
    home_rel = os.path.relpath(home_path, start=out_path.parent)
    pm_rel = os.path.relpath(pm_path, start=out_path.parent)
    bug_rel = os.path.relpath(bug_path, start=out_path.parent)
    process_rel = os.path.relpath(process_path, start=out_path.parent)
    raw_rel = os.path.relpath(md_path, start=out_path.parent)

    html_doc = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{html.escape(title)}</title>
  <link rel=\"stylesheet\" href=\"{css_rel}\" />
</head>
<body>
  <div class=\"container\">
    <nav class=\"top-nav\">
      <a class=\"nav-link nav-home\" href=\"{home_rel}\">Home</a>
      <a class=\"nav-link nav-process\" href=\"{process_rel}\">Process Management</a>
      <a class=\"nav-link nav-project\" href=\"{pm_rel}\">Project Management</a>
      <a class=\"nav-link nav-bug\" href=\"{bug_rel}\">Bug Management</a>
    </nav>
    <header class=\"hero\">
      <div>
        <h1 class=\"h4\">{html.escape(title)}</h1>
        <p class=\"muted small\">{html.escape(str(md_path.relative_to(repo_root)))}</p>
      </div>
      <div class=\"badges\">
        <a class=\"btn\" href=\"{raw_rel}\">Open Raw</a>
      </div>
    </header>
    <section class=\"card\">
      <div class=\"md\">
        {body}
      </div>
    </section>
  </div>
</body>
</html>
"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_doc, encoding="utf-8")


def _iter_md_files(root: Path) -> Iterable[Path]:
    return root.rglob("*.md")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render support and project markdown files into static HTML")
    parser.add_argument("--support", type=Path, default=Path("AI_first/docs"), help="Support docs root")
    parser.add_argument("--projects", type=Path, default=Path("AI_first/projects"), help="Projects root")
    parser.add_argument("--out", type=Path, default=Path("AI_first/ui/docs"), help="Output HTML root")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    support_root = (repo_root / args.support).resolve()
    projects_root = (repo_root / args.projects).resolve()
    out_root = (repo_root / args.out).resolve()

    if support_root.exists():
        for md_path in _iter_md_files(support_root):
            rel = md_path.relative_to(support_root)
            out_path = out_root / rel
            out_path = out_path.with_suffix(".html")
            _build_doc(md_path, out_path, repo_root)

    if projects_root.exists():
        for md_path in _iter_md_files(projects_root):
            rel = md_path.relative_to(projects_root)
            out_path = out_root / "projects" / rel
            out_path = out_path.with_suffix(".html")
            _build_doc(md_path, out_path, repo_root)


if __name__ == "__main__":
    main()
