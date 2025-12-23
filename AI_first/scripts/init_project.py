#!/usr/bin/env python3
"""Initialize a new project directory and register it in the template docs."""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import textwrap
from datetime import date
from pathlib import Path

PROJECT_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]*$")
PREFIX_RE = re.compile(r"^[A-Z0-9]+$")
PM_ROWS_START = "<!-- PROJECT_ROWS_START -->"
PM_ROWS_END = "<!-- PROJECT_ROWS_END -->"


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return cleaned.strip("_")


def _project_title(slug: str) -> str:
    return slug.replace("_", " ").title()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, content: str, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] write {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _update_mapping(text: str, var_name: str, key: str, value: str) -> tuple[str, bool]:
    pattern = re.compile(rf"({var_name}\s*=\s*{{)(?P<body>[^}}]*)(}})", re.S)
    match = pattern.search(text)
    if not match:
        raise SystemExit(f"Could not locate {var_name} mapping in issues.py")
    body = match.group("body")
    existing = re.search(rf"[\"']{re.escape(key)}[\"']\s*:\s*[\"'](?P<val>[^\"']+)[\"']", body)
    if existing:
        if existing.group("val") == value:
            return text, False
        raise SystemExit(
            f"{var_name} already contains '{key}' with value '{existing.group('val')}'. "
            "Use a different key or update manually."
        )
    indent = "    "
    body_trimmed = body.rstrip()
    prefix = "\n" if body_trimmed else "\n"
    new_body = f"{body_trimmed}{prefix}{indent}\"{key}\": \"{value}\",\n"
    updated = text[: match.start("body")] + new_body + text[match.end("body") :]
    return updated, True


def _count_open_bugs(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if str(payload.get("status", "")).lower() == "open":
            count += 1
    return count


def _extract_list_block(md_text: str) -> str:
    lines = md_text.splitlines()
    block: list[str] = []
    collecting = False
    for line in lines:
        if re.match(r"^\s*[-*]\s+", line):
            collecting = True
        if collecting:
            if not line.strip():
                break
            block.append(line)
    return "\n".join(block)


def _render_inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"<a href=\"\2\">\1</a>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def _render_list_summary(md_text: str) -> str:
    block = _extract_list_block(md_text)
    if not block:
        return '<ul class="muted small"></ul>'
    items: list[str] = []
    for line in block.splitlines():
        match = re.match(r"^\s*[-*]\s+(.*)$", line)
        if not match:
            continue
        content = _render_inline(match.group(1))
        items.append(f"<li>{content}</li>")
    return '<ul class="muted small">' + "".join(items) + "</ul>"


def _render_project_row(
    project: str,
    purpose: str,
    owner: str,
    phase_name: str,
    stage_slug: str,
    date_str: str,
) -> str:
    indent = "            "
    escaped_purpose = html.escape(purpose if purpose else "Project overview.")
    escaped_owner = html.escape(owner)
    return textwrap.dedent(
        f"""\
        {indent}<tr data-link="project_{project}.html" tabindex="0" role="button" aria-label="Open {project} project details">
        {indent}  <td>
        {indent}    <a class="fw" href="project_{project}.html">{project}</a>
        {indent}    <div class="muted small">{escaped_purpose}</div>
        {indent}  </td>
        {indent}  <td>Phase 01 — {phase_name}</td>
        {indent}  <td><span class="badge status-open">Planning</span></td>
        {indent}  <td><span class="badge status-closed">On Track</span></td>
        {indent}  <td>{escaped_owner}</td>
        {indent}  <td>{date_str}</td>
        {indent}  <td class="muted small">
        {indent}    <div>Define scope and success criteria.</div>
        {indent}    <div>Populate the Phase 01 stage action.</div>
        {indent}  </td>
        {indent}  <td>
        {indent}    <div class="muted small">Primary</div>
        {indent}    <div class="links">
        {indent}      <a href="docs/projects/{project}/project_summary_{project}.html">Summary</a>
        {indent}      <a href="docs/projects/{project}/phases/phase01/action_plan_phase01.html">Action Plan</a>
        {indent}      <a href="docs/projects/{project}/phases/phase01/actions/{project}_phase01_stage_{stage_slug}_action.html">Stage Action</a>
        {indent}    </div>
        {indent}    <div class="muted small">Supporting</div>
        {indent}    <div class="links">
        {indent}      <a href="docs/projects/{project}/phases/phase01/phase_definition.html">Phase Def</a>
        {indent}      <a href="bugmgmt_issues.html">Bug Management</a>
        {indent}    </div>
        {indent}  </td>
        {indent}</tr>"""
    )


def _replace_count(text: str, key: str, value: int) -> str:
    pattern = re.compile(rf'(data-count="{re.escape(key)}">)(\d+)(</div>)')
    return pattern.sub(rf"\g<1>{value}\3", text, count=1)


def _replace_last_updated(text: str, value: str) -> str:
    pattern = re.compile(r'(<span id="pm-last-updated">)([^<]*)(</span>)')
    return pattern.sub(rf"\g<1>{value}\3", text, count=1)


def _update_pm_html(
    pm_path: Path,
    project: str,
    purpose: str,
    owner: str,
    phase_name: str,
    stage_slug: str,
    date_str: str,
    issues_path: Path,
    dry_run: bool,
) -> bool:
    text = _read_text(pm_path)
    if f"project_{project}.html" in text:
        raise SystemExit(f"{pm_path} already references project_{project}.html")
    start_idx = text.find(PM_ROWS_START)
    end_idx = text.find(PM_ROWS_END)
    if start_idx == -1 or end_idx == -1 or start_idx > end_idx:
        raise SystemExit(f"{pm_path} is missing project row markers for auto-update.")
    rows_section = text[start_idx + len(PM_ROWS_START) : end_idx]
    new_row = _render_project_row(project, purpose, owner, phase_name, stage_slug, date_str)
    if rows_section.strip():
        rows_section = rows_section.rstrip() + "\n" + new_row + "\n"
    else:
        rows_section = "\n" + new_row + "\n"

    updated = text[: start_idx + len(PM_ROWS_START)] + rows_section + text[end_idx:]
    row_count = len(re.findall(r'<tr\s+[^>]*data-link="project_', rows_section))
    updated = _replace_count(updated, "projects", row_count)
    updated = _replace_count(updated, "active-phases", row_count)
    open_bugs = _count_open_bugs(issues_path)
    updated = _replace_count(updated, "open-bugs", open_bugs)
    updated = _replace_last_updated(updated, date_str)

    if dry_run:
        print(f"[dry-run] update {pm_path}")
        return False
    pm_path.write_text(updated, encoding="utf-8")
    return True


def _write_project_detail_page(
    out_path: Path,
    project: str,
    purpose: str,
    owner: str,
    goal: str,
    phase_name: str,
    stage_slug: str,
    phase_def_summary: str,
    action_plan_summary: str,
    stage_action_summary: str,
    date_str: str,
    dry_run: bool,
) -> None:
    if out_path.exists():
        raise SystemExit(f"{out_path} already exists; remove it or choose a new project slug.")
    escaped_purpose = html.escape(purpose)
    escaped_owner = html.escape(owner)
    escaped_goal = html.escape(goal)
    detail_html = textwrap.dedent(
        f"""\
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="UTF-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <title>Project Detail — {project}</title>
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
                <h1 class="h4">{project}</h1>
                <p class="muted small">{escaped_purpose}</p>
              </div>
            </header>

            <div class="summary">
              <div class="summary-card"><div class="muted small">Phases</div><div class="h6">1</div></div>
              <div class="summary-card"><div class="muted small">Active Phase</div><div class="h6">Phase 01</div></div>
              <div class="summary-card"><div class="muted small">Status</div><div class="h6">Planning</div></div>
            </div>

            <section class="card">
              <details class="block">
                <summary class="h4">Project Summary</summary>
                <ul class="muted small">
                  <li><strong>Project:</strong> {project}</li>
                  <li><strong>Purpose:</strong> {escaped_purpose}</li>
                  <li><strong>Current Goal:</strong> {escaped_goal}</li>
                  <li><strong>Environment:</strong> Local docs and static assets; offline.</li>
                  <li><strong>Constraints:</strong> Keep PII-free; deterministic outputs; local assets only.</li>
                  <li><strong>Consumers:</strong> Project stakeholders.</li>
                  <li><strong>Status:</strong> Planning</li>
                  <li><strong>Owner:</strong> {escaped_owner}</li>
                </ul>
              </details>
            </section>

            <section class="card">
              <h2 class="h4">Phase History</h2>
              <div class="table-wrap">
                <table class="issues">
                  <thead>
                    <tr>
                      <th>Phase</th>
                      <th>Status</th>
                      <th>Last Updated</th>
                      <th>Links</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr data-phase="Phase 01 — {phase_name}"
                        data-phase-def-id="phase01-def"
                        data-action-plan-id="phase01-plan"
                        data-stage-action-id="phase01-action"
                        tabindex="0" role="button" aria-label="View Phase 01 details">
                      <td>Phase 01 — {phase_name}</td>
                      <td><span class="badge status-open">Planning</span></td>
                      <td>{date_str}</td>
                      <td>
                        <div class="links">
                          <a href="docs/projects/{project}/phases/phase01/phase_definition.html">Phase Def</a>
                          <a href="docs/projects/{project}/phases/phase01/action_plan_phase01.html">Action Plan</a>
                          <a href="docs/projects/{project}/phases/phase01/actions/{project}_phase01_stage_{stage_slug}_action.html">Stage Action</a>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p class="filter-hint">Update this table as phases progress or close.</p>
            </section>

            <section class="card">
              <h2 class="h4">Phase Details</h2>
              <p class="muted small" id="phaseDetailTitle">Select a phase to review the summary.</p>
              <div class="phase-detail" id="phaseDetail">
                <div class="muted small">No phase selected.</div>
              </div>
            </section>

            <template id="phase01-def">
              {phase_def_summary}
            </template>
            <template id="phase01-plan">
              {action_plan_summary}
            </template>
            <template id="phase01-action">
              {stage_action_summary}
            </template>

          </div>
          <script>
            const detail = document.getElementById("phaseDetail");
            const detailTitle = document.getElementById("phaseDetailTitle");
            const getTemplate = (id) => {{
              if (!id) return '<div class="muted small">No summary available.</div>';
              const node = document.getElementById(id);
              return node ? node.innerHTML.trim() : '<div class="muted small">No summary available.</div>';
            }};
            const renderDetails = (row) => {{
              if (!row) return;
              const phase = row.dataset.phase || "Phase Details";
              const phaseDef = getTemplate(row.dataset.phaseDefId);
              const actionPlan = getTemplate(row.dataset.actionPlanId);
              const stageAction = getTemplate(row.dataset.stageActionId);
              if (detailTitle) detailTitle.textContent = phase;
              detail.innerHTML = `
                <div class="details-grid">
                  <div class="detail-item">
                    <div class="detail-title">Phase Definition</div>
                    ${{phaseDef}}
                  </div>
                  <div class="detail-item">
                    <div class="detail-title">Action Plan</div>
                    ${{actionPlan}}
                  </div>
                  <div class="detail-item">
                    <div class="detail-title">Stage Action</div>
                    ${{stageAction}}
                  </div>
                </div>
              `;
            }};
            document.querySelectorAll("tr[data-phase]").forEach((row) => {{
              row.addEventListener("click", (evt) => {{
                if (evt.target.closest("a")) return;
                renderDetails(row);
              }});
              row.addEventListener("keydown", (evt) => {{
                if (evt.target.closest("a")) return;
                if (evt.key !== "Enter" && evt.key !== " ") return;
                renderDetails(row);
              }});
            }});
          </script>
        </body>
        </html>
        """
    )
    _write_text(out_path, detail_html, dry_run)


def _update_projectplan(
    projectplan_path: Path,
    project: str,
    phase_name: str,
    dry_run: bool,
) -> bool:
    content = _read_text(projectplan_path)
    if f"AI_first/projects/{project}/" in content:
        raise SystemExit(f"{projectplan_path} already references AI_first/projects/{project}/")
    block = textwrap.dedent(
        f"""\
        - **{project} (planning)**
          - Summary: `AI_first/projects/{project}/project_summary_{project}.md`
          - Phases root: `AI_first/projects/{project}/phases/`
          - Issues log: use Bug Management entries with `project: "{project}"`
          - Phases overview:
            - Phase 01 — {phase_name} (planning): see `AI_first/projects/{project}/phases/phase01/`.
          - Phase directory map:
            - `AI_first/projects/{project}/phases/phase01/phase_definition.md` — definition of Phase 01.
            - `AI_first/projects/{project}/phases/phase01/action_plan_phase01.md` — action plan for Phase 01 (links to stage actions under `AI_first/projects/{project}/phases/phase01/actions/`).
        """
    )
    marker = "## Project-wide references and actions"
    if marker in content:
        before, after = content.split(marker, 1)
        if not before.endswith("\n"):
            before += "\n"
        updated = f"{before}{block}\n{marker}{after}"
    else:
        updated = content.rstrip() + "\n\n" + block
    _write_text(projectplan_path, updated, dry_run)
    return True


def _validate_project_slug(slug: str) -> None:
    if not PROJECT_SLUG_RE.match(slug):
        raise SystemExit(
            "Project slug must be lowercase snake_case (letters, numbers, underscores) "
            "and start with a letter."
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize a new project in the template")
    parser.add_argument("--project", required=True, help="Project slug (snake_case)")
    parser.add_argument("--title", default=None, help="Display title (defaults to slug in title case)")
    parser.add_argument("--owner", default="unassigned", help="Project owner name")
    parser.add_argument("--purpose", default="TBD", help="Short purpose statement")
    parser.add_argument("--goal", default=None, help="Current goal statement")
    parser.add_argument("--phase-name", default="Foundation", help="Phase 01 name")
    parser.add_argument("--stage-name", default="foundation", help="Stage name for phase 01")
    parser.add_argument("--prefix", default=None, help="Bug ID prefix to add (e.g., BMG)")
    parser.add_argument("--no-projectplan", action="store_true", help="Skip updating AI_first/docs/projectplan.md")
    parser.add_argument("--no-ui", action="store_true", help="Skip updating AI_first/ui/PM.html and project detail page")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing files")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project = args.project.strip()
    _validate_project_slug(project)

    repo_root = Path(__file__).resolve().parents[2]
    title = args.title.strip() if args.title else _project_title(project)
    phase_name = args.phase_name.strip()
    stage_name = args.stage_name.strip()
    stage_slug = _slugify(stage_name) or "stage"

    if args.prefix and not PREFIX_RE.match(args.prefix):
        raise SystemExit("Prefix must be uppercase letters/numbers only (example: BMG)")

    project_root = repo_root / "AI_first" / "projects" / project
    if project_root.exists():
        raise SystemExit(f"{project_root} already exists; choose a new project slug or remove the directory.")

    goal = args.goal.strip() if args.goal else f"Complete Phase 01 {phase_name}."

    summary_path = project_root / f"project_summary_{project}.md"
    phase_dir = project_root / "phases" / "phase01"
    phase_def_path = phase_dir / "phase_definition.md"
    action_plan_path = phase_dir / "action_plan_phase01.md"
    stage_action_path = phase_dir / "actions" / f"{project}_phase01_stage_{stage_slug}_action.md"

    summary_body = textwrap.dedent(
        f"""\
        # Project Summary ({project})

        - **Project:** {project}
        - **Purpose:** {args.purpose.strip()}
        - **Current Goal:** {goal}
        - **Environment:** Local docs and static assets; offline.
        - **Constraints:** Keep PII-free; deterministic outputs; local assets only.
        - **Consumers:** Project stakeholders.
        - **Status:** Planning
        - **Owner:** {args.owner.strip()}
        """
    )
    phase_def_body = textwrap.dedent(
        f"""\
        # Phase 01 — {phase_name}

        - **Objective:** Establish the baseline plan and workflow for {title}.
        - **Scope:** In: project docs, phase/stage definitions; Out: implementation or integrations.
        - **Definition of completion:** Phase action plan and at least one stage action exist with persona notes and DoD references.
        - **Stages:**
          - {stage_name} stage -> `AI_first/projects/{project}/phases/phase01/actions/{project}_phase01_stage_{stage_slug}_action.md`
        - **Dependencies:** None.
        - **Risks/assumptions:** Keep scope focused; remain PII-free.
        - **Links:** `AI_first/docs/projectplan.md`, `AI_first/projects/{project}/project_summary_{project}.md`
        """
    )
    action_plan_body = textwrap.dedent(
        f"""\
        # Phase 01 Action Plan — {phase_name}

        - **Phase:** see `AI_first/projects/{project}/phases/phase01/phase_definition.md`.
        - **Stage list:**
          - {stage_name} stage -> `AI_first/projects/{project}/phases/phase01/actions/{project}_phase01_stage_{stage_slug}_action.md`
        - **Objective:** Establish the baseline project workflow, scope, and documentation.
        - **Scope/files:** In: stage action doc(s); Out: implementation or external tooling.
        - **Dependencies:** None.
        - **Risks/assumptions:** Keep the initial stage actionable and small.
        - **Persona actions:** Default Reviewer/Sponsor → Project/Process Manager → Developer → QA Lead.
        - **Validation:** Stage action file exists and references review checklists.
        - **Rollback:** Revert phase documents if scope changes.
        - **Ready checklist:** Templates available.
        - **Done checklist:** Stage action populated with persona notes.
        """
    )
    stage_action_body = textwrap.dedent(
        f"""\
        # Stage Action ({project}_phase01_stage_{stage_slug}_action.md)

        - **Phase/Stage:** Phase 01 — {phase_name} ({stage_name}).
        - **Objective:** Define scope, workflow, and expectations for {title}.
        - **Scope:** In: planning docs and acceptance criteria; Out: implementation.
        - **Acceptance:** Persona notes recorded; scope documented; DoD referenced.
        - **Dependencies/data:** `AI_first/docs/process.md`, `AI_first/docs/projectplan.md`, `AI_first/projects/{project}/project_summary_{project}.md`
        - **Outputs:** Updated phase/stage docs and any related process updates.
        - **Definition of Done:** Persona notes filled, DoD checklist referenced, validation steps recorded.

        ## Personas (record outputs; use `AI_first/docs/templates/review_checklists.md`)
        - Reviewer/Sponsor:
        - Project/Process Manager:
        - Developer:
        - QA Lead:
        - Docs Expert:
        - Architect/Security/Ops/Perf/DBA/UI (if triggered):

        ## Plan
        - Confirm project scope and constraints.
        - Define initial workflow and phase expectations.
        - Record acceptance and validation steps.

        ## Execution notes
        - Pending.

        ## Validation
        - Pending.

        ## Documentation updates
        - Pending.

        ## Issues & lessons
        - Pending.
        """
    )

    phase_def_summary = _render_list_summary(phase_def_body)
    action_plan_summary = _render_list_summary(action_plan_body)
    stage_action_summary = _render_list_summary(stage_action_body)

    _write_text(summary_path, summary_body, args.dry_run)
    _write_text(phase_def_path, phase_def_body, args.dry_run)
    _write_text(action_plan_path, action_plan_body, args.dry_run)
    _write_text(stage_action_path, stage_action_body, args.dry_run)

    updated_projectplan = False
    if not args.no_projectplan:
        updated_projectplan = _update_projectplan(
            repo_root / "AI_first" / "docs" / "projectplan.md",
            project,
            phase_name,
            args.dry_run,
        )

    issues_path = repo_root / "AI_first" / "scripts" / "issues.py"
    issues_text = _read_text(issues_path)
    updated_prefix = False
    updated_owner = False
    if args.prefix:
        issues_text, updated_prefix = _update_mapping(issues_text, "PROJECT_PREFIXES", project, args.prefix)
    if args.owner and args.owner.strip().lower() != "unassigned":
        issues_text, updated_owner = _update_mapping(
            issues_text, "PROJECT_OWNERS", project, args.owner.strip()
        )
    if (updated_prefix or updated_owner) and not args.dry_run:
        issues_path.write_text(issues_text, encoding="utf-8")
    elif (updated_prefix or updated_owner) and args.dry_run:
        print(f"[dry-run] update {issues_path}")

    today = date.today().isoformat()
    updated_pm = False
    if not args.no_ui:
        detail_path = repo_root / "AI_first" / "ui" / f"project_{project}.html"
        _write_project_detail_page(
            detail_path,
            project,
            args.purpose.strip(),
            args.owner.strip(),
            goal,
            phase_name,
            stage_slug,
            phase_def_summary,
            action_plan_summary,
            stage_action_summary,
            today,
            args.dry_run,
        )
        updated_pm = _update_pm_html(
            repo_root / "AI_first" / "ui" / "PM.html",
            project,
            args.purpose.strip(),
            args.owner.strip(),
            phase_name,
            stage_slug,
            today,
            repo_root / "AI_first" / "bugmgmt" / "issues" / "issues.jsonl",
            args.dry_run,
        )

    created = [
        summary_path,
        phase_def_path,
        action_plan_path,
        stage_action_path,
    ]
    print("Project initialized:")
    for item in created:
        print(f"  - {item}")
    if updated_projectplan:
        print("Updated AI_first/docs/projectplan.md")
    if updated_prefix:
        print("Updated AI_first/scripts/issues.py PROJECT_PREFIXES")
    if updated_owner:
        print("Updated AI_first/scripts/issues.py PROJECT_OWNERS")

    print("Next steps:")
    if not args.no_ui:
        print("  - Review AI_first/ui/PM.html and the new AI_first/ui/project_<project>.html detail page.")
    print("  - Run python3 AI_first/scripts/render_docs.py to refresh AI_first/ui/docs/.")
    print("  - Regenerate Bug Management exports if you changed issues or prefixes.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
