# Delivery Process (Template)

Use this process to keep changes small, reviewable, and persona-driven. Copy/adapt for new projects.

## AI-first mindset
- Docs are the source of truth; the UI reflects them and keeps context visible.
- Personas provide structured prompts so the AI stays focused on scope, risks, and quality.
- The stage action file is the working log: decisions, validations, and DoD checks live there.
- PM.html is the portfolio view; Bug Management (BugMgmt) is the audit trail for problems and fixes.
- Work in small, reviewable slices so updates stay easy to validate.

## Context setting (before you start)
- Open `AI_first/ui/index.html` (bundle entry) and the support views: `AI_first/ui/PM.html` and `AI_first/ui/bugmgmt_issues.html`.
- Identify the active project, phase, and stage action file.
- Run the context launch prompt (see below) before selecting a persona.
- Open the primary docs for the active work: `AI_first/docs/process.md`, `AI_first/docs/projectplan.md`, `AI_first/docs/project_wide_docs/personas.md`, plus the phase definition/action plan.
- If the stage action file does not exist yet, create it under `AI_first/projects/<project>/phases/phase<NN>/actions/` using the naming convention.
- Record expected behaviors and acceptance criteria before implementation work.
- Log decisions and validations in the stage action file as you go.

## Fast start (per session)
- Start in `AI_first/ui/PM.html` and `AI_first/ui/bugmgmt_issues.html` to confirm the active work.
- Pick project/phase from `projectplan`; open the phase definition/action plan and linked stage actions (if any).
- Use `AI_first/docs/process.md` and `AI_first/docs/project_wide_docs/personas.md` as reference guides.
- Open a multi-context working set: project plan, phase docs, and the active stage action file in separate windows.
- Run personas (Project Creator/Owner for new projects, then Project/Process Manager → Developer → QA Lead by default); add optional personas only when scope triggers them.
- Execute, validate, update docs/DoD, and log issues/lessons.

## Multi-context working set
- Default to three windows open:
  - **Project Creator/Owner (then Project/Process Manager):** define the project when starting a new one, then manage phases and actions using `AI_first/docs/projectplan.md` plus the active phase definition/action plan.
  - **Developer:** fix bugs and execute project actions using the current stage action file and implementation context.
  - **QA:** report bugs, update docs, and find possible solutions to bugs using the Bug Management UI and the relevant docs.
- Keep support views open for context: `AI_first/ui/PM.html` (projects/actions) and `AI_first/ui/bugmgmt_issues.html` (bugs).
- Keep the persona catalog (`AI_first/docs/project_wide_docs/personas.md`) accessible; use it to decide when to add specialist reviews.
- Treat the stage action file as the working scratchpad: log decisions, validations, and DoD checks as you go.

## Initial setup (drop-in)
- Copy the `AI_first/` directory into your target repo root and treat it as the process/Project Management/Bug Management bundle.
- Open `AI_first/ui/index.html` as the landing page for the bundle.
- Start with the **Project Creator/Owner** persona:
  - Choose the project name and update `AI_first/docs/projectplan.md` and `AI_first/projects/<project>/` paths accordingly (rename the sample project if needed).
  - Capture the project purpose, scope boundaries, and initial phases in `projectplan.md` and the project summary file.
  - Decide whether to keep the sample Bug Management (BugMgmt) module/UI and the LaTeX user-doc template; remove or keep per your needs.
- After naming, continue with the remaining default personas (Project/Process Manager → Developer → QA Lead).

## Project initialization (optional)
- Run `python3 AI_first/scripts/init_project.py --project <project> --prefix <PREFIX> --owner "Name"` to scaffold `AI_first/projects/<project>/`, update `AI_first/docs/projectplan.md`, and register Bug Management prefixes.
- The script also creates `AI_first/ui/project_<project>.html` and updates `AI_first/ui/PM.html` with the new row.
- After running, regenerate formatted docs via `python3 AI_first/scripts/render_docs.py`.

## Repo layout (AI_first-only)
- `AI_first/`: template process docs, Bug Management tooling, UI reports/styles, and project planning docs.
- `AI_first/projects/`: project planning docs (summaries, phases, stage actions).

## Documentation rendering
- While editing markdown under `AI_first/docs/` or `AI_first/projects/`, run `python3 AI_first/scripts/watch_docs.py` from the repo root to auto-render `AI_first/ui/docs/`.
- If you are not running the watcher, run `python3 AI_first/scripts/render_docs.py` after doc changes.

## Support scripts (optional)
Run scripts from the repo root; use `python3` (or `python` if it maps to Python 3). Use these only when you want to regenerate UI outputs or scaffold docs.
- `AI_first/scripts/render_docs.py`: render markdown into `AI_first/ui/docs/`.
- `AI_first/scripts/render_pm.py`: refresh `AI_first/ui/PM.html` and `AI_first/ui/project_*.html` from project docs.
- `AI_first/scripts/watch_docs.py`: auto-render docs while you edit.
- `AI_first/scripts/init_project.py`: scaffold a new project, update `AI_first/docs/projectplan.md`, and add a PM.html row.
- `AI_first/scripts/issues.py`: regenerate Bug Management JSON/HTML exports.

## Codex skill (optional)
- Install the `activate-ai-first` skill for use across repos: `cp -R skills/activate-ai-first ~/.codex/skills/`.
- `~` is your home directory (not the repo root); restart Codex to load the skill.
- Activate with a request like: "activate AI_first" or "run the AI_first context launch prompt".

## Source-of-truth stack
- **Project plan:** `AI_first/docs/projectplan.md` lists active projects and links to `AI_first/projects/<project>/`.
- **Project directory:** project summary plus phases.
- **Phase definition:** per phase, with objective/scope/completion and stage list.
- **Phase action plan:** per phase, listing stages and persona actions, validation, and checklists.
- **Stage action file:** per stage, with persona sections and acceptance for that slice of work. Naming: `AI_first/projects/<project>/phases/phase<NN>/actions/<project>_phase<NN>_stage<name>_action.md`.
- **Templates:** `AI_first/docs/templates/` for project plan, phase definitions/action plans, stage actions, review checklists, and DoD.

## Personas (defaults)
- Start with: Project Creator/Owner → Project/Process Manager → Developer → QA Lead.
- Add optional personas from `AI_first/docs/project_wide_docs/personas.md` only when scope triggers them (Docs Expert, Product Manager, Repository Steward, UI/Accessibility, etc.).

## Standard flow for a phase/stage
1. Read the project plan and the current project’s phase definition/action plan.
2. Create or open the stage action file(s) under the phase `actions/` folder using the naming convention.
3. Run personas and record outputs in the stage action file (use `AI_first/docs/templates/review_checklists.md`).
4. Execute the work and run the changed scripts yourself; QA Lead/Test Engineering validate; Docs Expert updates docs when in scope.
5. Close-out: complete the DoD checklist, log lessons, and mark the phase/stage done in the phase action plan and project plan.

## Quality gates (apply to every stage action)
- Expected behaviours/counts/filters and data scope are recorded before coding; note any temporary fallbacks and expiry conditions.
- Outputs are deterministic (ordering/filenames) and JSON-safe (no NaN/Infinity) where relevant.
- Data handling documented; avoid PII unless explicitly required for your project.
- DoD completed with test commands/results captured; issues log updated with learnings.

## Bug Management (BugMgmt module)
- Bug Management (BugMgmt) is optional. If you do not need it, remove or ignore `AI_first/bugmgmt/`, `AI_first/ui/bugmgmt_issues.html`, and `AI_first/scripts/issues.py`, and remove the Bug Management link from your UI navigation if desired.
- Source of truth is `AI_first/bugmgmt/issues/issues.jsonl` (one JSON object per line). Do not edit exports directly.
- Required fields: `id`, `date`, `project`, `phase`, `stage`, `area`, `status`, `severity`, `summary`, `owner` (defaults from `BUGMGMT_REPO_OWNER` or `git config user.name`, with optional overrides in `PROJECT_OWNERS` when set to `unassigned`).
- ID format uses a project-based prefix (example: `BMG-2025-01-001`). Configure prefixes in `AI_first/scripts/issues.py` (`PROJECT_PREFIXES`, e.g., `BMG`, `PMG`).
- For new bugs, include detail fields: `root_cause`, `proposed_fix`, `qa_reproduction` (QA reproduction steps).
- Example entry (single line):
  ```json
  {"id":"BMG-2025-01-003","date":"2025-01-07","project":"bugmgmt","phase":"01","stage":"foundation","area":"docs","status":"open","severity":"minor","summary":"Short description","owner":"unassigned","root_cause":"TBD","proposed_fix":"TBD","qa_reproduction":"TBD"}
  ```
- Use status values `open`, `in_progress`, `closed` and severity values `critical`, `major`, `minor`, `nit`.
- Create a new entry when a bug is found; update the same entry when status or ownership changes.
- After any bug change (new entry or status/field update), regenerate exports; the HTML report must be recreated each time:
  - `python3 AI_first/scripts/issues.py list --format json --output AI_first/bugmgmt/exports/json/bugmgmt_issues.json`
  - `python3 AI_first/scripts/issues.py list --format html --output AI_first/ui/bugmgmt_issues.html`
- View locally via `file://` at `AI_first/ui/bugmgmt_issues.html`; filters and counts should match the JSONL store.

## Naming and directories
- **Project plan:** `AI_first/docs/projectplan.md`.
- **Project directory:** `AI_first/projects/<project>/` with project summary and phases.
- **Phase directory:** `AI_first/projects/<project>/phases/phase<NN>/` with `phase_definition.md` and `action_plan_phase<NN>.md`.
- **Stage actions:** `AI_first/projects/<project>/phases/phase<NN>/actions/<project>_phase<NN>_stage<name>_action.md`.
- **Templates:** `AI_first/docs/templates/` (project/phase/action/review/DoD).

## Context launch prompt (copy/paste)
Use this prompt at the start of every session, before selecting a persona.

```
Context Launch: Review AI_first/ui/index.html, AI_first/ui/PM.html, AI_first/ui/bugmgmt_issues.html, AI_first/docs/process.md, AI_first/docs/projectplan.md, and AI_first/docs/project_wide_docs/personas.md. Identify the active project, phase, and stage action file; list open bugs; summarize current status; and ask which persona to activate next (default order: Project Creator/Owner -> Project/Process Manager -> Developer -> QA Lead; add optional personas from AI_first/docs/project_wide_docs/personas.md only when scope triggers them). If no stage action file exists, propose the file path using the naming convention.
```

Expected output:
- Current projects and active phases; for the chosen project, list the current phase/stage and active stage action file.
- Open bugs and any blocking issues.
- Persona catalog and a clear prompt asking which persona to activate next.
