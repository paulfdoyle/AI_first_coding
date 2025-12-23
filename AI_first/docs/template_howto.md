# Template Adoption Guide

Use this guide to spin up a new project from the Vibe Template.

## Setup
Automation steps are optional; use them only when you need to regenerate UI outputs.

1) Copy the `AI_first/` directory into your target repo root.
   - Keep `AI_first/` as the drop-in bundle; do your product work outside it.
2) Open `AI_first/ui/index.html` via file:// to get oriented.
3) Optionally create a virtual environment: `python3 -m venv .venv && source .venv/bin/activate`.
   - Keep `.venv/` out of version control (the template includes a `.gitignore`).
4) Start the doc watcher if you want automatic updates while editing docs (from the repo root): `python3 AI_first/scripts/watch_docs.py`.
5) Regenerate BugMgmt exports (if using BugMgmt):
   ```bash
   python3 AI_first/scripts/issues.py list --format json --output AI_first/bugmgmt/exports/json/bugmgmt_issues.json
   python3 AI_first/scripts/issues.py list --format html --output AI_first/ui/bugmgmt_issues.html
   ```
6) Open `AI_first/ui/bugmgmt_issues.html` via file:// to confirm UI assets load locally.

## Process and personas
- Read `AI_first/docs/process.md` for the standard flow and persona defaults.
- See `AI_first/docs/project_wide_docs/personas.md` for persona prompts.
- Use templates under `AI_first/docs/templates/` when adding projects/phases/stages under `AI_first/projects/`.

## Starting a new project
Option A (automated):
1) Run `python3 AI_first/scripts/init_project.py --project <project> --prefix <PREFIX> --owner "Name"`.
2) Review `AI_first/ui/PM.html` and the new `AI_first/ui/project_<project>.html` detail page.
3) Run `python3 AI_first/scripts/render_docs.py` to refresh formatted docs.

Option B (manual):
1) Add a project entry to `AI_first/docs/projectplan.md` with summary and phase roots.
2) Create `AI_first/projects/<project>/project_summary_<project>.md`.
3) For each phase, add `phase_definition.md` and `action_plan_phase<NN>.md` under `phases/phase<NN>/`.
4) For each stage, add a stage action file under `phases/phase<NN>/actions/` using the naming convention.
5) Run personas and record outputs in the stage action files.

## Workspace layout
- Keep template tooling under `AI_first/` and planning docs under `AI_first/projects/`.
- Add product workspace directories in your downstream repo as needed (outside `AI_first/`).

## BugMgmt module (optional)
- Data store: `AI_first/bugmgmt/issues/issues.jsonl` (PII-free). Use `AI_first/scripts/issues.py list --help` for flags.
- Exports: `AI_first/bugmgmt/exports/json/bugmgmt_issues.json` and `AI_first/ui/bugmgmt_issues.html`.
- UI: bundled assets under `AI_first/ui/assets/` and `AI_first/ui/style/`; works via file://.
- Toggle off: skip running the CLI and remove/ignore `AI_first/bugmgmt/`, `AI_first/ui/bugmgmt_issues.html`, `AI_first/scripts/issues.py`.

## UI report template
- Base template at `AI_first/ui/templates/report_base.html`; reuse bundled CSS in `AI_first/ui/style/`.
- Duplicate and extend for new reports; keep assets local for offline usage.

## PII and determinism
- Sample data is PII-free. Keep your own data PII-free unless required.
- Maintain deterministic outputs (ordering, hashes) for repeatable runs.

## Troubleshooting
- If exports fail, verify paths or pass explicit `--data/--output` flags.
- If file:// fetch is blocked, the fallback data in `AI_first/ui/bugmgmt_issues.html` will render; ensure assets are local.
