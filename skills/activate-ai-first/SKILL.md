---
name: activate-ai-first
description: Activate the AI_first context launch prompt and execute its steps for this repository. Use when the user asks to activate AI_first, run the context launch prompt, start a session, or request a status recap that identifies the active project/phase/stage action file, lists open bugs, summarizes status, and asks which persona to activate next.
---

# Activate AI_first

## Overview

Execute the AI_first context launch flow: load the prompt text, review the specified UI/docs, identify the active project, phase, and stage action file, list open bugs, summarize status, and ask which persona to activate next.

## Workflow

1. Load the prompt text from the source of truth.
   - Read `AI_first/ui/index.html` and capture the `<code id="contextPromptText">` contents.
   - If missing, fall back to `AI_first/ui/process_guide.html`, then `AI_first/docs/process.md`.
   - Use the prompt text verbatim in your response before executing it.

2. Review the required context files (read-only).
   - `AI_first/ui/index.html`
   - `AI_first/ui/PM.html`
   - `AI_first/ui/bugmgmt_issues.html`
   - `AI_first/docs/process.md`
   - `AI_first/docs/projectplan.md`
   - `AI_first/docs/project_wide_docs/personas.md`

3. Identify the active project and phase.
   - Use `AI_first/docs/projectplan.md` to list current projects and their phase directories.
   - Cross-check the status with `AI_first/ui/PM.html`.
   - Prefer the first project/phase not marked complete/closed; if all are complete, state that and pick the most recently updated project/phase for context.

4. Locate the active stage action file.
   - Open the active phase definition and phase action plan files (paths in `AI_first/docs/projectplan.md`).
   - Look for stage action links or entries under `AI_first/projects/<project>/phases/phase<NN>/actions/`.
   - If multiple exist, choose the one most recently updated or the first stage not marked complete.
   - If none exist, propose a path using the naming convention in `AI_first/docs/process.md`:
     `AI_first/projects/<project>/phases/phase<NN>/actions/<project>_phase<NN>_stage<name>_action.md`
   - Use a short, slug-style `<name>` derived from the phase action plan stage list.

5. List open bugs from the source of truth.
   - Read `AI_first/bugmgmt/issues/issues.jsonl`.
   - List `status: open` items and call out any `status: in_progress` separately.
   - For each bug, report: id, summary, severity, status, owner.

6. Summarize current status.
   - Include active project/phase/stage action file, key next actions from the stage action file (if present), and bug counts/priority.

7. Ask which persona to activate next.
   - Default order: Project Creator/Owner -> Project/Process Manager -> Developer -> QA Lead.
   - Mention optional personas from `AI_first/docs/project_wide_docs/personas.md` only when scope requires them.

## Output checklist

- Include the prompt text verbatim (from `AI_first/ui/index.html` or fallback).
- Identify the active project, phase, and stage action file (or proposed path).
- List open bugs with id/summary/severity/status/owner.
- Provide a concise current status summary.
- Ask which persona to activate next (use default order; mention optional personas only if relevant).
