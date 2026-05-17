---
name: tasks
description: Phase 3 of SDD. Decomposes an approved plan.md into an ordered, testable task list in tasks.md for the PPT generator. Use after /plan is approved by the user.
version: 0.1.0
---

# /tasks — Tasks Phase

You are entering **Phase 3** of SDD.

## Inputs
- `specs/NNN-slug/spec.md`
- `specs/NNN-slug/plan.md` (must be approved)

## Output: specs/NNN-slug/tasks.md

A numbered, ordered task list. Every task must be:

- **Atomic** — completable in one `/implement` run (≈ under 30 minutes of work).
- **Verifiable** — has an explicit *"Done when:"* check that can be observed (a passing test name, a curl command output, a visible UI state).
- **Ordered** — dependencies flow top-to-bottom. No forward references.

### Required task ordering for this project
1. **Database migration / model changes first** — `backend/database/models.py` + `db_manager.py` methods
2. **Backend service layer** — `backend/utils/*.py` (new modules or new functions in existing ones)
3. **Backend routes** — new endpoints in `backend/app.py`
4. **Backend tests** — `backend/test_*.py` updates
5. **Frontend service** — methods added to `frontend/src/services/api.js`
6. **Frontend components/pages** — new files in `components/`, updates to `MainPage.jsx`
7. **Frontend styling** — additions to `App.css`
8. **End-to-end smoke** — invoke `/pptx-test` with a representative input
9. **Docs / README touch-ups** if any

### Task format
Use this exact format for every task:

```markdown
## Task N — <short title>
**Status:** pending
**Files:** path/to/file1.py, path/to/file2.js
**Depends on:** Task N-1 (or "none")
**Done when:** <explicit, observable check>
**Notes:** <gotchas, links to spec/plan sections, edge cases>
```

When `/implement` completes a task, it will update the entry to:
- `**Status:** done`
- Append an `**Outcome:**` line describing what changed.

## Rules
- **No task may span more than 3 files** unless that's intrinsic to the change (a route + service + test trio is fine).
- **If a task feels >30 minutes**, split it. Better five 15-minute tasks than two 45-minute ones.
- **Re-read `plan.md` before writing each task** — don't invent scope.
- **Backend before frontend**, always. Frontend should never block waiting on backend in the same task list.
- **Tests before the frontend that consumes them** — if a backend endpoint is added in Task 3, its test should be Task 4, not Task 9. The frontend that calls it comes after.
- **Smoke test (`/pptx-test`) belongs near the end**, after both backend and frontend are wired.
- **End by asking the user to approve before `/implement`.** Say: *"Review the tasks. When ready, run `/implement task 1`."*