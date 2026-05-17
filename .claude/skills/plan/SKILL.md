---
name: plan
description: Phase 2 of SDD. Turns an approved spec.md into a technical plan.md for the PPT generator — Flask routes, python-pptx changes, LangChain prompt deltas, SQLite schema, React component changes, test strategy. Use after /specify is complete and the user has approved the spec.
version: 0.1.0
---

# /plan — Plan Phase

You are entering **Phase 2** of SDD.

## Inputs
- `specs/NNN-slug/spec.md` (must exist and the user must have approved it)
- Repo state — **read these before drafting** so the plan reflects actual code:
  - `backend/app.py` (Flask route surface, error handling patterns)
  - `backend/utils/ppt_generator.py` (rendering logic, helper functions)
  - `backend/utils/llm_service.py` (LLM contract, Ollama integration)
  - `backend/utils/document_parser.py` (input parsing)
  - `backend/database/models.py` (SQLAlchemy schema)
  - `backend/database/db_manager.py` (CRUD operations)
  - `backend/config.py` (centralized settings)
  - `frontend/src/services/api.js` (axios client)
  - `frontend/src/pages/MainPage.jsx` (main UI orchestrator)
  - `frontend/src/components/` (existing component patterns)

## Output: specs/NNN-slug/plan.md

Use these sections, in this order:

### 1. Architecture Overview
One paragraph + a simple ASCII flow diagram. Example:
```
[Frontend] → POST /api/refine → [refinement_service.py]
                                       ↓
                              [LangChain chain] → Ollama
                                       ↓
                              [ppt_generator.py] → new .pptx
                                       ↓
                              [db_manager.py] → new version row
```

### 2. Backend Changes
- **New/changed Flask routes** — method, path, request body, response shape
- **LLM prompt changes** — which file, brief sketch of the delta
- **python-pptx logic changes** — which layouts, placeholders, run properties affected
- **Database migrations** — new tables/columns; note SQLite's ALTER limitations (no DROP COLUMN, limited type changes)
- **Config additions** — new entries in `backend/config.py`

### 3. Frontend Changes
- **New/changed pages and components** with file paths
- **API methods to add** to `frontend/src/services/api.js`
- **State management impact** — what new state in `MainPage.jsx`, where it flows
- **CSS additions** — what new classes get added to `App.css`

### 4. Template Impact
- Which `.pptx` files are affected; whether a new layout is required.
- If a template change is required, invoke `/template-audit` on the affected file and reference its output here.

### 5. Test Strategy
- Which backend test gets new cases (`backend/test_*.py`)
- Smoke test via `/pptx-test` with an example input
- Frontend manual test steps (CRA — `npm start`, then click-through)

### 6. Risks & Open Questions
List anything ambiguous, anything that might break existing behavior, anything you'd want a second opinion on.

### 7. Out-of-Scope (recap from spec)
Mirror the out-of-scope section from `spec.md` so it stays top-of-mind during `/tasks` and `/implement`.

## Rules
- **Reference real file paths from this repo.** Do not invent files. If a file doesn't exist yet and needs to be created, mark it with `(new)`.
- **Match existing code style.** This project uses: functional Python with helper functions (not classes for routes), detailed logging, consistent `create_error_response()` for errors, dict-returning DB methods.
- If a section is genuinely N/A, write **"N/A — reason."** Don't delete the section.
- **End by asking the user to approve before `/tasks`.** Explicitly say: *"Review and approve, then run `/tasks` next."*
- Do not start `/tasks` automatically.