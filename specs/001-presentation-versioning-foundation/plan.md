# Plan — Feature 001: Presentation Versioning Foundation

**Status:** draft
**Related spec:** ./spec.md

## 1. Architecture Overview

A new `presentation_versions` table is added to the existing SQLite schema. Each row is one version in a lineage; the **lineage ID is the `generation_history.id` of v1** (the first/original generation). The existing `generate-ppt` flow gets a single new side-effect after saving generation history: write a v1 row carrying the slide-structure snapshot and `.pptx` file pointer. On every app boot, an idempotent backfill scans `generation_history` for rows that lack a v1 in `presentation_versions` and inserts a stub (no `slide_structure`, file pointer carried over). Four new read endpoints expose lineages, versions, version content, and version `.pptx` download — all session-scoped, all returning the project-standard JSON shape, with "missing" and "not owned by this session" collapsed into a single `error_type: "not_found"` to avoid existence leaks.

```
                              ┌─ existing path ─┐
[POST /api/generate-ppt] → [...generation...] → [save_generation_history]
                                                       │  (returns gh.id)
                                                       ▼
                                       [save_presentation_version]   ◄── NEW
                                       lineage_id = gh.id
                                       version_number = 1
                                       label = "Initial generation"
                                       slide_structure = <generated dict>
                                       file_path = <pptx path>

[app startup]
   │
   ▼
[init_database] → [_create_tables] → [_initialize_defaults] → [_backfill_v1_for_existing_presentations]  ◄── NEW
                                                                       (idempotent: no-op if no orphan rows)

[GET /api/lineages]                                       ─┐
[GET /api/lineages/<lid>/versions]                         ├─► [db_manager versioning methods] ─► [presentation_versions]
[GET /api/lineages/<lid>/versions/<n>]                     │
[GET /api/lineages/<lid>/versions/<n>/download] → send_file ┘
```

## 2. Backend Changes

### New/changed Flask routes
All four are session-scoped via the existing `get_or_create_session_id()` helper, return the standard `{success, ..., error, error_type, timestamp}` shape used elsewhere in `backend/app.py`, and treat "row not found" and "row exists but `session_id` differs" identically (`error_type: "not_found"`, HTTP 404).

- **`GET /api/lineages`** — list lineages owned by the current session.
  - Request: no body. Optional query param `limit` (clamped 1–100; default 20), mirroring `/api/history`.
  - Response: `{ success: true, lineages: [{ lineage_id, latest_version_number, latest_version_label, latest_version_created_at, total_versions }, ...], total, limit, timestamp }`.
  - Order: newest-lineage-first by `MAX(created_at)` across the lineage's versions (matches `/api/history`).

- **`GET /api/lineages/<int:lineage_id>/versions`** — chronological version list for one lineage.
  - Response: `{ success: true, lineage_id, versions: [{ version_number, label, note, created_at, has_snapshot }, ...], total, timestamp }`.
  - Order: oldest-first (v1 → vN), per spec.
  - `has_snapshot: bool` flag tells callers whether `slide_structure` is populated (stub backfill rows are `false`).
  - Failure: caller doesn't own / lineage doesn't exist → 404 `error_type: "not_found"`.

- **`GET /api/lineages/<int:lineage_id>/versions/<int:version_number>`** — fetch a single version's content.
  - Response: `{ success: true, lineage_id, version_number, label, note, created_at, filename, slide_structure, is_stub, timestamp }`.
  - `slide_structure` is `null` for stub backfill rows; `is_stub: true` flags that case.
  - Failure: 404 `error_type: "not_found"` for missing/unauthorized.

- **`GET /api/lineages/<int:lineage_id>/versions/<int:version_number>/download`** — stream the `.pptx`.
  - On success: `send_file(...)` with `mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation'`, `as_attachment=True`, `download_name=<filename>` — same pattern as the existing `/api/download/<filename>`.
  - Failure modes (all return 404 `error_type: "not_found"` to avoid leaks):
    - lineage/version not in DB
    - lineage/version owned by a different session
    - row exists but `file_path` is `NULL` (stub backfill row)
    - row's `file_path` no longer exists on disk (cleaned up by the existing 24h sweeper)

A small private helper `_lineage_owned_by_session(lineage_id, session_id)` lives next to the routes (functional-helper style, matching the rest of `app.py`) and returns a bool the routes use before responding.

### LLM prompt changes
N/A — this is data-layer only. `backend/utils/llm_service.py` is unchanged.

### python-pptx logic changes
N/A — no rendering changes. `backend/utils/ppt_generator.py` is unchanged.

### Database migrations
**New table — `presentation_versions`** (declared in `backend/database/models.py` as a new `PresentationVersion` SQLAlchemy model; created on app boot by the existing `Base.metadata.create_all(self.engine)` call in `DatabaseManager._create_tables`).

Columns:
| Column           | Type          | Constraint                                                   | Purpose                                                                            |
|------------------|---------------|--------------------------------------------------------------|------------------------------------------------------------------------------------|
| `id`             | INTEGER       | PK, autoincrement                                            | Surrogate row ID                                                                   |
| `lineage_id`     | INTEGER       | NOT NULL, FK → `generation_history.id` ON DELETE CASCADE     | Equal to the v1's `generation_history.id`; identifies the whole lineage            |
| `version_number` | INTEGER       | NOT NULL, ≥ 1                                                | `1` for v1; future refinement work will append 2, 3, …                             |
| `label`          | TEXT          | NOT NULL                                                     | `"Initial generation"` for v1; verbatim refinement instruction text for v2+        |
| `note`           | TEXT          | NULL                                                         | Optional user-supplied free-text override (not auto-populated)                     |
| `slide_structure`| JSON          | NULL                                                         | Snapshot of the dict passed to `ppt_generator.create_presentation*` for this version; NULL for stub backfill rows |
| `file_path`      | TEXT          | NULL                                                         | Absolute path to the generated `.pptx`; NULL only if file isn't known              |
| `filename`       | TEXT          | NULL                                                         | Basename of `.pptx` (denormalized for download convenience)                        |
| `is_stub`        | BOOLEAN       | NOT NULL, default `false`                                    | True for backfilled rows; false for rows created by the live generation flow       |
| `session_id`     | VARCHAR(100)  | NOT NULL                                                     | Denormalized from `generation_history.session_id` for cheap ownership filtering    |
| `created_at`     | DATETIME      | NOT NULL, default `func.now()`                               | Version creation timestamp                                                         |

Indexes:
- **Unique** `(lineage_id, version_number)` — prevents duplicate version numbers within a lineage; this is the integrity guarantee for the future refinement endpoint.
- `(session_id)` — for `GET /api/lineages` listing.
- `(lineage_id)` — for `GET /api/lineages/<lid>/versions` listing.

**SQLite limitation notes:**
- `Base.metadata.create_all` is the project's existing migration mechanism. It only **adds** missing tables — fine here since we're adding a brand-new table, not altering an existing one. No ALTER, no DROP, no risk.
- SQLite enforces FK constraints only when `PRAGMA foreign_keys = ON`. The project doesn't currently enable this; relying on the FK for hard delete-cascade is not safe today. Behavior is still correct because the lineage-orphan path is "user clears session → presentations become orphaned" which the spec explicitly accepts as out-of-scope.
- JSON column on SQLite is stored as TEXT under the hood (SQLAlchemy's `JSON` type handles serialization). `slide_structure` will be roundtripped as JSON without issue.

**Backfill (idempotent, on app boot):**
- New method `DatabaseManager._backfill_v1_for_existing_presentations()`, called from `DatabaseManager.__init__` immediately after `_initialize_defaults()`.
- Logic: `SELECT gh.id, gh.session_id, gh.file_path, gh.filename, gh.created_at FROM generation_history gh LEFT JOIN presentation_versions pv ON pv.lineage_id = gh.id WHERE pv.id IS NULL`. For each orphan, INSERT one stub row: `lineage_id=gh.id, version_number=1, label="Initial generation", note=NULL, slide_structure=NULL, file_path=gh.file_path, filename=gh.filename, is_stub=True, session_id=gh.session_id, created_at=gh.created_at`.
- Idempotency: re-running on a clean DB finds zero orphans and exits without writing. Logged as `logger.info("Versioning backfill: 0 rows to insert")` so operators can see the no-op.
- Wraps DB errors in a try/except that logs and **does not raise**, so a backfill failure doesn't prevent the app from starting (matches the existing leniency in `initialize_database`).

**Write-side hook (inside `backend/app.py:generate_ppt`):**
- Right after `history = db_manager.save_generation_history(history_data)` and `generation_id = history.get('id')`, add a guarded call to `db_manager.save_presentation_version({...})` populating `lineage_id=generation_id`, `version_number=1`, `label="Initial generation"`, `note=None`, `slide_structure=generation_structure`, `file_path=ppt_file_path`, `filename=os.path.basename(ppt_file_path)`, `is_stub=False`, `session_id=session_id`. The block is inside the same `if db_manager:` branch and uses the same try/except-and-log pattern already used by the existing history save (no response failure if DB write fails — matches existing code's leniency; risk is flagged in §6).

**New DB manager methods** in `backend/database/db_manager.py`:
- `save_presentation_version(version_data: Dict) -> Dict` — single INSERT, returns `to_dict()` of the inserted row.
- `get_lineages_for_session(session_id: str, limit: int = 20) -> List[Dict]` — aggregated query: latest version per lineage; newest-lineage-first by `MAX(created_at)`.
- `get_versions_for_lineage(lineage_id: int, session_id: str) -> Optional[List[Dict]]` — chronological version list; returns `None` if no rows match the `(lineage_id, session_id)` pair (which the route translates into 404).
- `get_version(lineage_id: int, version_number: int, session_id: str) -> Optional[Dict]` — single version lookup with ownership filter baked in.
- `lineage_exists_for_session(lineage_id: int, session_id: str) -> bool` — used by the download route before `send_file`.

All return plain dicts (matching the rest of the file).

### Config additions
- `backend/config.py` gets a new top-level dict `VERSIONING_CONFIG`:
  ```python
  VERSIONING_CONFIG = {
      'v1_label': 'Initial generation',
      'default_lineage_list_limit': 20,
      'max_lineage_list_limit': 100,
  }
  ```
- The v1 label is centralized here (single source of truth — `_backfill_v1_for_existing_presentations`, the write-side hook in `generate_ppt`, and any future audit job all read from this constant).
- Imported by `app.py` and `db_manager.py` alongside the existing config imports.

## 3. Frontend Changes
**N/A — the spec excludes any UI/frontend work.** `frontend/src/services/api.js`, `frontend/src/pages/MainPage.jsx`, and the `frontend/src/components/` tree are untouched. Future work (slide refinement UI, version history panel) will add axios methods like `api.listLineages()`, `api.getVersions(lineageId)`, `api.getVersionContent(...)`, `api.downloadVersion(...)` — those are out of scope here.

## 4. Template Impact
**N/A — no `.pptx` template files are touched.** Template-audit is not required because the rendering pipeline is unchanged: this slice only stores a snapshot of the dict that `ppt_generator.create_presentation*` already consumes today.

## 5. Test Strategy

### Backend tests
- **`backend/test_database.py`** — new cases:
  - `save_presentation_version` writes a row whose columns match the input, returns dict (not SQLAlchemy object).
  - The unique `(lineage_id, version_number)` constraint rejects a second v1 for the same lineage.
  - `get_lineages_for_session` returns only the calling session's lineages, sorted newest-first, with correct `total_versions` and `latest_version_*` aggregations.
  - `get_versions_for_lineage` returns versions oldest-first; returns `None` when the lineage_id doesn't match anything for that session_id; returns `None` when the lineage exists but is owned by a different session (this is the existence-leak guard).
  - `get_version` ditto for single-version lookup.
  - `_backfill_v1_for_existing_presentations`: seed three `generation_history` rows with no `presentation_versions` entries, call the method, assert three stub rows exist with `is_stub=True`, `slide_structure IS NULL`, label `"Initial generation"`, `file_path`/`filename`/`session_id` carried over from the source rows. Run it a second time and assert zero new rows are inserted (idempotency).
- **`backend/test_api.py`** — new cases:
  - Fresh session: `GET /api/lineages` returns `200` with `lineages: []`, `total: 0`.
  - After one successful `POST /api/generate-ppt`: `GET /api/lineages` returns one entry with `total_versions: 1`, `latest_version_number: 1`, `latest_version_label: "Initial generation"`.
  - `GET /api/lineages/<id>/versions` returns one version with `version_number: 1`, `has_snapshot: true`.
  - `GET /api/lineages/<id>/versions/1` returns a non-null `slide_structure` and `is_stub: false`.
  - `GET /api/lineages/<id>/versions/1/download` returns 200, `Content-Type: application/vnd.openxmlformats-officedocument.presentationml.presentation`, non-empty body.
  - `GET /api/lineages/9999999/versions` returns 404 `error_type: "not_found"`.
  - Cross-session attempt (create lineage as session A, query as session B by spoofing the cookie): same 404 `error_type: "not_found"` — never 403, no information disclosure.
  - Download for a stub row (simulate by setting `file_path=NULL` on a row) returns 404 `error_type: "not_found"`.

### Smoke test
- **`/pptx-test`** with a small synthetic brief (default template, default model). After it reports success, verify:
  1. A row exists in `presentation_versions` with `version_number = 1`, `label = "Initial generation"`, `is_stub = False`, non-null `slide_structure`.
  2. `GET /api/lineages` (with the test session cookie) lists exactly that lineage.
  3. The download endpoint for that lineage's v1 returns the same `.pptx` byte stream as the legacy `/api/download/<filename>` route.

### Frontend manual test steps
**N/A** — no frontend changes to click through. (`cd frontend && npm start` and exercising the existing flow is still a sensible sanity check that the React app didn't break from any incidental import-order weirdness, but it's not required by this slice.)

## 6. Risks & Open Questions

- **Non-fatal DB save for the write-side hook.** The existing `save_generation_history` failure path logs and continues, returning a successful response with a `.pptx` link. The plan mirrors that for the v1 version save — meaning a transient DB error after a successful generation produces a deck the user can download (via the legacy `/api/download/<filename>`) but **not** see in the new lineage list. This is the same tolerance the rest of the code shows, but if the team wants stricter behavior ("if the v1 row can't be created, the request fails") it should be flipped before /implement. Worth a quick yes/no in plan review.
- **Stub rows hide content from the read endpoints.** Backfilled rows return `slide_structure: null` and `is_stub: true`. A future refinement endpoint that wants to seed a v2 from v1 will need to handle the case where v1 is a stub (e.g., refuse, or rehydrate from the existing `.pptx`). Flagged for the upcoming refinement feature's plan; not blocking this slice.
- **`error_type` field naming (spec said `errorType`).** The spec used camelCase shorthand; the actual API surface (per `backend/app.py:create_error_response`) is snake_case `error_type`. The plan uses `error_type` throughout for code consistency. Confirming this is the right read of the spec.
- **Stale `file_path` on disk.** The existing 24h cleanup (`/api/cleanup`) deletes generated `.pptx` files but doesn't touch `generation_history` rows — and now won't touch `presentation_versions` rows either. The download route handles this gracefully (404 `not_found`), but the version row will outlive its file. Acceptable for this foundation; a future "retention policy" feature is already noted as out-of-scope in the spec.
- **SQLite FK enforcement not enabled.** Cascade-on-delete on `lineage_id → generation_history.id` is declared but won't fire under current SQLite settings (`PRAGMA foreign_keys` defaults to OFF). Since the spec explicitly accepts orphan-on-session-reset, this is **not** a bug for this slice, but it's worth surfacing for any future feature that does want hard cascades.
- **Sort key for `GET /api/lineages`.** Plan defaults to newest-first by `MAX(created_at)` across the lineage's versions, matching `/api/history`. The spec doesn't pin a sort order; if a stakeholder wants a different default (e.g., alphabetical by latest label), flag during plan review.

## 7. Out-of-Scope (recap from spec)
- Refinement logic — no endpoint, no LLM call, no flow that creates v2, v3, etc. The schema must support it; nothing in this slice writes beyond v1.
- Any frontend / UI changes. The React app is unchanged in this slice.
- LLM prompt changes or generation-logic changes.
- Authentication or multi-user identity beyond the existing session model.
- Per-version thumbnail or preview generation.
- A diff or compare view between versions.
- Version rollback / restore / "make v2 the active version" actions.
- Retention or purge policy for old versions (every version is kept indefinitely in this slice).
- Storing or retaining the original input brief on the version record.
- Lineage ownership across session resets — orphan-on-reset matches today's per-presentation behavior and is accepted.
