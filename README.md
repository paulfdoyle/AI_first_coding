# Vibe Template

AI_first is a standalone drop-in pack that adds process management, project management, and bug management to any repo. Copy the `AI_first/` directory into a target repo, keep it intact, and use the docs and UI with your AI partner to run planning, execution, and QA in one place.

## What you get
- `AI_first/`: process docs, templates, Bug Management (BugMgmt) tooling, UI reports/styles, and project planning docs (`AI_first/projects/`).

## AI-first workflow (drop-in)
Copy the `AI_first/` directory into your target repo root and follow this flow. Manual commands are optional and only needed for regeneration.

1) Activate the process.
   - Open `AI_first/ui/index.html` or `AI_first/ui/PM.html` via `file://` to get oriented.
   - Start each session with the Context Launch prompt in `AI_first/ui/process_guide.html` or `AI_first/docs/process.md` before selecting a persona.
   - Read the primary docs: `AI_first/docs/process.md`, `AI_first/docs/projectplan.md`, and `AI_first/docs/project_wide_docs/personas.md`.
   - Keep the stage action file open while you work; it is the scratchpad for decisions and validation.
2) Run the workflow.
   - Pick the active project/phase and use the stage action file to track decisions and validations.
   - Use personas to drive actions: Project Management defines work, Developer executes, QA reports bugs and proposes fixes.
   - Keep PM.html, project docs, and Bug Management entries updated as you go.
3) Initiate a new project (when needed).
   - Automated: `python3 AI_first/scripts/init_project.py --project <project> --prefix <PREFIX> --owner "Name"`
   - Manual: copy `AI_first/projects/_template/` to `AI_first/projects/<project>/` and edit placeholders.

## Optional automation (manual regeneration)
Run scripts from the repo root. Use `python3` for the commands below; if your system maps `python` to Python 3, you can use `python` instead.

- Render docs: `python3 AI_first/scripts/render_docs.py`
- Watch docs: `python3 AI_first/scripts/watch_docs.py`
- Regenerate Bug Management exports:
  ```bash
  python3 AI_first/scripts/issues.py list --format json --output AI_first/bugmgmt/exports/json/bugmgmt_issues.json
  python3 AI_first/scripts/issues.py list --format html --output AI_first/ui/bugmgmt_issues.html
  ```

Open `AI_first/ui/bugmgmt_issues.html` and `AI_first/ui/PM.html` via `file://` to review.

## Optional modules
- Bug Management (BugMgmt): keep if you want local issue tracking; remove or ignore `AI_first/bugmgmt/`, `AI_first/ui/bugmgmt_issues.html`, and `AI_first/scripts/issues.py` if not needed, and remove the Bug Management link from navigation if desired.
- UI template: extend `AI_first/ui/templates/report_base.html` for lightweight static reports.
- LaTeX user docs: start from `AI_first/docs/user_docs/user_doc_template.tex` if you want PDF user guides.

## Notes
- Sample data is PII-free and deterministic.
- All assets are local; no external network calls are required.
- Update paths via CLI flags or env vars (see `python3 AI_first/scripts/issues.py --help`).
