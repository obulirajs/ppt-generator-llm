# PPT Generator — Project Context

## Stack
- **Backend:** Flask 3.0, python-pptx 0.6.23, LangChain (partial), SQLAlchemy 2 (SQLite), Python 3.11
  - Entry: `backend/app.py`
  - LLM wrapper: `backend/utils/llm_service.py` (direct Ollama calls; partial LangChain for structured output)
  - PPT engine: `backend/utils/ppt_generator.py`
  - Document ingestion: `backend/utils/document_parser.py`
  - DB layer: `backend/database/db_manager.py` + `backend/database/models.py`
  - Config: `backend/config.py` (centralized — presentation types, keywords, paths)
  - System templates: `backend/templates/system/`
  - User-uploaded templates: `backend/user_templates/`
- **Frontend:** React 19, CRA (react-scripts 5), axios
  - Entry: `frontend/src/index.js` → `App.js`
  - Pages: `frontend/src/pages/MainPage.jsx`
  - Components: `frontend/src/components/`
  - API client: `frontend/src/services/api.js`
  - Styling: single `frontend/src/App.css` with CSS variables

## LLM
- Local **Ollama** at `http://localhost:11434`
- Default model: `llama3.2`. Also supported: `deepseek-r1`.
- LangChain used **partially** — only for structured output parsing and prompt templates. No complex agents.

## Database
- SQLite at `backend/database/ppt_generator.db`
- Session-based multi-user (UUID in Flask session). Designed for clean PostgreSQL migration when auth is added.
- 8 tables: users, templates, structure_configs, section_templates, generation_history, user_preferences, content_analysis, prompt_templates.

## Workflow — Spec-Driven Development (SDD)
All non-trivial changes follow the four-phase flow:
1. `/specify` — capture intent in `specs/NNN-slug/spec.md`
2. `/plan` — design in `specs/NNN-slug/plan.md`
3. `/tasks` — break down in `specs/NNN-slug/tasks.md`
4. `/implement` — execute one task at a time

Trivial fixes (typo, single-line bug, dependency bump) can skip the spec phase but should still produce a clear commit message describing intent.

## Conventions
- **Never edit** `*_backup.py`, `*-backup.*`, or `*_backup.zip` files — those are historical snapshots.
- **Templates (`.pptx`)** are binary; describe changes in `plan.md`, do not diff them.
- **New PPT-generation features** must be exercisable via `/pptx-test` before merge.
- **Python dependencies** in `backend/requirements.txt` stay pinned.
- **Frontend components** are functional components with hooks. No class components.
- **API responses** follow a consistent shape: `{ success, data | error, errorType, timestamp }`.
- **DB manager methods** return plain dicts (not SQLAlchemy objects) to avoid detached-instance errors.
- **Logging** in backend uses the `logger` instance (logging module), not `print`.
- **Emoji icons** are used in UI and CLI output for visual clarity (✅ ❌ 🚀 📊 etc.) — keep this style.

## Testing
- Backend smoke test: `/pptx-test` (end-to-end generation)
- Backend manual: `python backend/test_database.py`, `python backend/test_api.py`
- Frontend manual: `cd frontend && npm start`, click-through

## Out-of-scope reminders
- No authentication system yet — session-based only. Auth is a future epic.
- No PostgreSQL yet — SQLite is the current target. Migration is planned, not active.
- No thumbnail generation yet — templates show category icons.