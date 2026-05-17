# Plan — Feature NNN: <Title>

**Status:** draft | approved
**Related spec:** ./spec.md

## 1. Architecture Overview
<One paragraph. Then an ASCII diagram:>

```
[user input] → [document_parser] → [llm_service] → [ppt_generator] → [.pptx download]
```

## 2. Backend Changes
### New/changed Flask routes
- `<METHOD> /path` — request: `{...}` → response: `{...}`

### LLM prompt changes
- File: backend/utils/llm_service.py
- Delta: <describe>

### python-pptx logic changes
- File: backend/utils/ppt_generator.py
- Layouts/placeholders touched: <list>

### Database migrations
- New tables/columns: <list>
- SQLite limitation notes: <list>

## 3. Frontend Changes
### Pages/components
- <list>

### axios calls
- File: frontend/src/services/<file>.js
- New calls: <list>

### State management
- <describe>

## 4. Template Impact
- Files affected: <list>
- New layout required? <yes/no>
- Audit reference: ./template-audit-<filename>.md (if applicable)

## 5. Test Strategy
- Backend tests added in: backend/test_<file>.py
- Smoke test: `/pptx-test` with payload <describe>
- Frontend manual steps:
  1. `cd frontend && npm start`
  2. <click-through steps>

## 6. Risks & Open Questions
- <list>

## 7. Out-of-Scope (recap from spec)
- <list>
