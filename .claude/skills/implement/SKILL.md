---
name: implement
description: Phase 4 of SDD. Executes ONE task from tasks.md at a time for the PPT generator. Use when the user says "implement task N" or "next task". Always stops after each task for review.
version: 0.1.0
---

# /implement — Implementation Phase

You are entering **Phase 4** of SDD.

## Protocol

1. **Identify which task.** Ask which feature (`specs/NNN-slug/`) and which task number if not given. Default: the next task with `Status: pending` in the most recent spec folder.

2. **Open and re-read context** before writing any code:
   - The relevant section of `plan.md` for design intent.
   - The full task entry in `tasks.md` for the "Done when" check.
   - The actual files listed in the task's `**Files:**` field.

3. **Make the changes.** Match existing code style:
   - **Backend Python:** functional helpers, `logger.info/error/warning` (not `print`), `create_error_response()` for Flask errors, dict-returning DB methods.
   - **Frontend React:** functional components with hooks, axios via `apiService`, error states matching `ErrorDisplay` pattern, loading states matching `LoadingSpinner`.
   - **Style:** preserve existing emoji conventions, CSS variable usage, BEM-ish class names.

4. **Run the verification** specified in "Done when":
   - **Backend Python tests:** `cd backend && source pptenv/bin/activate && python -m pytest <file> -k <name>` (or the matching `python backend/test_*.py` invocation).
   - **Frontend tests:** `cd frontend && npm test -- --watchAll=false` for the touched component.
   - **End-to-end PPT smoke:** invoke `/pptx-test`.
   - **Curl/API check:** run the curl command from the "Done when" check.
   - **Manual UI check:** if the task is UI-only, instruct the user to click through and confirm.

5. **Update the task entry in `tasks.md`:**
   - Change `**Status:** pending` to `**Status:** done`.
   - Append a one-line `**Outcome:**` note describing what changed (e.g., "Added `presentation_versions` table with 6 columns; migration runs on app startup.").

6. **STOP.** Report what changed, what was verified, and ask whether to proceed to the next task. Do **not** auto-start the next task.

## Rules
- **One task per run.** If you finish early, do not start the next task. Return control to the user.
- **If a task can't be completed as written** (blocker, missing info, plan ambiguity), update its entry in `tasks.md` with a `**Blocked:**` note explaining why, and return — do not silently expand scope.
- **Never modify `spec.md` from this skill.** Spec changes go through `/specify` again (creating a v2 spec, or updating with a status note).
- **Never modify files matching** `*_backup*`, `*-backup*`, `*backup.zip`.
- **If verification fails**, do not mark the task done. Report the failure, leave `Status: pending`, ask the user how to proceed.
- **Commit suggestion:** at the end of each successful task, suggest a commit message in the format `feat(NNN): task N — <short summary>` or `fix(NNN): ...`. Do not commit automatically.