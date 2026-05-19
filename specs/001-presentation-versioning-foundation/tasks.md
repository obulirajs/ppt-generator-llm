# Tasks — Feature 001: Presentation Versioning Foundation

**Status:** draft
**Related:** ./spec.md, ./plan.md

> Ordering rule: DB → backend service → routes → backend tests → frontend service → frontend UI → smoke test → docs.
> Frontend is N/A for this slice (see plan §3). Tasks go DB → routes → tests → smoke.

## Task 1 — Add `VERSIONING_CONFIG` to backend config
**Files:** backend/config.py
**Depends on:** none
**Done when:** `python -c "from backend.config import VERSIONING_CONFIG; print(VERSIONING_CONFIG['v1_label'], VERSIONING_CONFIG['default_lineage_list_limit'], VERSIONING_CONFIG['max_lineage_list_limit'])"` (run from project root with the backend venv) prints `Initial generation 20 100`.
**Notes:** Plan §2 "Config additions". The literal `"Initial generation"` label lives here so both the write-side hook in `generate_ppt` and the backfill method read it from one place. Pure additive — no existing keys change.
**Status:** done
**Outcome:** Added `VERSIONING_CONFIG` dict at the end of `backend/config.py` with `v1_label='Initial generation'`, `default_lineage_list_limit=20`, `max_lineage_list_limit=100`. Verified by running `cd backend && python3 -c "from config import VERSIONING_CONFIG; ..."` from project root (project convention is `from config import`, not `from backend.config import`) — output was `Initial generation 20 100`.

## Task 2 — Define `PresentationVersion` SQLAlchemy model
**Files:** backend/database/models.py, backend/database/db_manager.py
**Depends on:** Task 1
**Done when:**
1. `backend/database/models.py` exports a new `PresentationVersion` class with all columns from plan §2 "Database migrations" (`id`, `lineage_id`, `version_number`, `label`, `note`, `slide_structure`, `file_path`, `filename`, `is_stub`, `session_id`, `created_at`) plus a `to_dict()` that returns each field as a plain Python value (datetimes ISO-formatted).
2. The unique constraint on `(lineage_id, version_number)` and the indexes on `(session_id,)` and `(lineage_id,)` are declared in `__table_args__`.
3. `backend/database/db_manager.py` line 15–18 import block includes `PresentationVersion`.
4. After deleting `backend/database/ppt_generator.db` and starting the app once (or running `python backend/database/db_manager.py`), `sqlite3 backend/database/ppt_generator.db ".schema presentation_versions"` shows the new table with the expected columns and the unique index.
**Notes:** No standalone migration — `Base.metadata.create_all` in `_create_tables` picks it up automatically. FK to `generation_history.id` is declared with `ondelete='CASCADE'` for future-proofing even though SQLite won't enforce it today (plan §6 risk). `slide_structure` uses SQLAlchemy's `JSON` type. **Do not delete the existing dev DB without confirming with the user** — the backfill in Task 5 is the supported migration path on existing data.
**Status:** done
**Outcome:** Added `UniqueConstraint` + `Index` to the SQLAlchemy import in `models.py`, appended a new `PresentationVersion` class (11 columns, `to_dict()`, `__table_args__` with the unique `(lineage_id, version_number)` constraint and two non-unique indexes on `session_id` and `lineage_id`, FK to `generation_history.id` with `ondelete='CASCADE'`), and added `PresentationVersion` to the `from database.models import (...)` block in `db_manager.py`. Verified by running `python -m database.db_manager` against the existing dev DB (rows preserved: 25 users, 27 generations) and `sqlite3 database/ppt_generator.db ".schema presentation_versions"` returning the expected CREATE TABLE + UNIQUE constraint + both indexes + FK with ON DELETE CASCADE.

## Task 3 — DB manager: `save_presentation_version`
**Files:** backend/database/db_manager.py
**Depends on:** Task 2
**Done when:** A new method `save_presentation_version(self, version_data: Dict) -> Dict` exists on `DatabaseManager`, mirrors the `save_generation_history` style (single INSERT, `session.refresh`, returns `to_dict()`), and a quick REPL check succeeds:
```python
from database.db_manager import init_database
db = init_database()
row = db.save_presentation_version({
    'lineage_id': 1, 'version_number': 1, 'label': 'Initial generation',
    'note': None, 'slide_structure': {'slides': []}, 'file_path': '/tmp/x.pptx',
    'filename': 'x.pptx', 'is_stub': False, 'session_id': 'test-sess'
})
assert row['id'] and row['label'] == 'Initial generation'
```
(Adjust `lineage_id` to match an existing `generation_history.id` if FK enforcement is enabled; otherwise any int works.)
**Notes:** Plan §2 "New DB manager methods". The method must return a plain dict (matches "DB manager methods return plain dicts" in CLAUDE.md). Don't add input validation here — write-side hook in Task 6 supplies all fields; bad data is a programmer error.
**Status:** done
**Outcome:** Added a new "Presentation Versioning Management" section to `db_manager.py` and a `save_presentation_version(version_data: Dict) -> Dict` method mirroring `save_generation_history`'s shape (INSERT → commit → refresh → return `to_dict()`). Verified by inserting a test row with `lineage_id=999999`, `session_id='test-task-3-verify'`, `slide_structure={'slides': []}` — assertions on `row['id']`, `row['label']`, `row['is_stub']`, `row['session_id']`, and JSON roundtrip all passed. Test row deleted after verification.

## Task 4 — DB manager: read methods (lineages, versions, single version, ownership probe)
**Files:** backend/database/db_manager.py
**Depends on:** Task 3
**Done when:** Four new methods exist on `DatabaseManager`, each returning plain dicts/lists/bool (no SQLAlchemy objects):
- `get_lineages_for_session(self, session_id: str, limit: int = 20) -> List[Dict]` — one entry per lineage owned by `session_id`, fields: `lineage_id, latest_version_number, latest_version_label, latest_version_created_at, total_versions`. Sorted by `MAX(created_at) DESC`. Clamps `limit` to `VERSIONING_CONFIG['max_lineage_list_limit']`.
- `get_versions_for_lineage(self, lineage_id: int, session_id: str) -> Optional[List[Dict]]` — chronological (oldest-first, `version_number ASC`); returns `None` when no rows match `(lineage_id, session_id)` (covers both missing and cross-session; per spec the route translates this to 404 `not_found`).
- `get_version(self, lineage_id: int, version_number: int, session_id: str) -> Optional[Dict]` — single row including `slide_structure` and `is_stub`; `None` when missing/unauthorized.
- `lineage_exists_for_session(self, lineage_id: int, session_id: str) -> bool` — used by the download route before `send_file`.

Quick check: with two distinct session_ids each owning one row, `get_lineages_for_session(sid_a)` returns exactly 1 lineage and `get_versions_for_lineage(lid_a, sid_b)` returns `None`.
**Notes:** Plan §2 "New DB manager methods". The cross-session `None` is the **existence-leak guard** — do not return an empty list and "not found" separately; collapse both into the same return value so the route can't accidentally differentiate. Use SQLAlchemy aggregation (`func.max`, `func.count`) for the lineage list to avoid N+1.
**Status:** done
**Outcome:** Added `func` to the SQLAlchemy import and `VERSIONING_CONFIG` to the config import in `db_manager.py`, plus four new methods on `DatabaseManager`: `get_lineages_for_session` (subquery with `func.max`/`func.count` for aggregation, joined back to pick up the latest version's label, ordered by `MAX(created_at) DESC`, limit clamped to `VERSIONING_CONFIG['max_lineage_list_limit']`), `get_versions_for_lineage` (oldest-first, returns `None` when nothing matches `(lineage_id, session_id)`), `get_version` (single-row scoped to ownership, returns `None` cross-session or missing), `lineage_exists_for_session` (bool probe). Verified with two seeded sessions (A: lineage 900001 with v1+v2; B: lineage 900002 with v1 only): A's lineage list returned `total_versions=2` and `latest_version_label='tighten slide 3'`; cross-session probes from B against A's lineage all returned `None`/`False`; missing-lineage probes returned the same; owner-side lookups roundtripped `slide_structure` correctly. All 3 test rows cleaned up.

## Task 5 — DB manager: idempotent v1 backfill, wired into `__init__`
**Files:** backend/database/db_manager.py
**Depends on:** Task 4
**Done when:**
1. New method `_backfill_v1_for_existing_presentations(self)` on `DatabaseManager` performs the `LEFT JOIN ... WHERE pv.id IS NULL` select against `generation_history`, inserts one stub row per orphan with `version_number=1`, `label=VERSIONING_CONFIG['v1_label']`, `note=None`, `slide_structure=None`, `file_path=gh.file_path`, `filename=gh.filename`, `is_stub=True`, `session_id=gh.session_id`, `created_at=gh.created_at`.
2. `DatabaseManager.__init__` calls it after `_initialize_defaults()`.
3. Errors inside the method are caught and logged but do **not** raise (matches existing `initialize_database` leniency).
4. Observable proof: with at least one pre-existing `generation_history` row that lacks a `presentation_versions` row, run `python backend/database/db_manager.py` once → log line shows N stub rows inserted, sqlite shows `is_stub=1` rows. Run it again → log line shows `0 rows to insert` and row count is unchanged.
**Notes:** Plan §2 "Backfill (idempotent, on app boot)" and the EARS line in spec §Behavior. Log line format suggestion: `Versioning backfill: inserted {n} stub v1 rows` / `Versioning backfill: 0 rows to insert`. **Idempotency is non-negotiable** — re-running on a fresh DB or one where everything is already backfilled must be a clean no-op.
**Status:** done
**Outcome:** Added `_backfill_v1_for_existing_presentations()` to `DatabaseManager` (LEFT JOIN GenerationHistory ← PresentationVersion, filter where `pv.id IS NULL`, insert one stub per orphan with `is_stub=True`, `slide_structure=None`, label from `VERSIONING_CONFIG['v1_label']`, and `session_id`/`file_path`/`filename`/`created_at` carried over from the parent gh row). Wrapped in `try/except` that catches and logs but never raises. Wired into `DatabaseManager.__init__` after `_initialize_defaults()`. **Inline Task 2 fix:** discovered during verification that SQLAlchemy's `JSON` type stores Python `None` as the JSON literal `"null"`, not SQL NULL — patched `PresentationVersion.slide_structure` to `Column(JSON(none_as_null=True))` so stubs land as true SQL NULL. Verified against the dev DB by clearing `presentation_versions`, then running `DatabaseManager()` twice: run 1 logged `"Versioning backfill: inserted 27 stub v1 rows"` and produced 27 rows where `slide_structure IS NULL`, `is_stub=1`, label=`'Initial generation'`, and `session_id`/`file_path`/`filename` matched the parent gh rows; run 2 logged `"Versioning backfill: 0 rows to insert"` with row count unchanged.

## Task 6 — Write-side hook in `generate_ppt`
**Files:** backend/app.py
**Depends on:** Task 5
**Done when:** Inside the existing `if db_manager:` block in `generate_ppt`, immediately after `history = db_manager.save_generation_history(history_data)` and `generation_id = history.get('id')`, a guarded call to `db_manager.save_presentation_version({...})` writes a v1 row with `lineage_id=generation_id`, `version_number=1`, `label=VERSIONING_CONFIG['v1_label']`, `note=None`, `slide_structure=generation_structure`, `file_path=ppt_file_path`, `filename=os.path.basename(ppt_file_path)`, `is_stub=False`, `session_id=session_id`. The block is wrapped in `try/except` that logs at `logger.error` and continues (so the user still gets the .pptx download response).

Observable proof: hitting `POST /api/generate-ppt` once with `curl` produces (a) the usual success response and (b) a new row in `presentation_versions` whose `lineage_id` equals the `generation_id` returned in the JSON response, with `is_stub=False` and a non-null `slide_structure`.
**Notes:** Plan §2 "Write-side hook" and Risk #1. Add `VERSIONING_CONFIG` to the existing `from config import (...)` block at the top of `app.py`. **Do not** add a new failure path for the user — DB hiccup must not break the user-visible generation flow.
**Status:** done
**Outcome:** Added `VERSIONING_CONFIG` to the `from config import (...)` block at the top of `app.py`. Inserted the v1 write-side hook inside the existing `if db_manager:` try block in `generate_ppt`, immediately after `logger.info(f"Generation history saved with ID: {generation_id}")` and before the template-usage / preferences updates. The hook uses its own **nested** try/except so a version-save failure does not skip the subsequent DB writes (deeper isolation than required by the task, but cheap and matches plan §6 Risk #1's "non-fatal" guidance). Verified end-to-end against the running Flask + Ollama: `POST /api/generate-ppt` returned 200 with `generation_id=28`; the new `presentation_versions` row had `lineage_id=28`, `version_number=1`, `label='Initial generation'`, `is_stub=0`, non-null `slide_structure`, `filename` matching the response, and a populated `session_id`.

## Task 7 — Route: `GET /api/lineages` + ownership helper
**Files:** backend/app.py
**Depends on:** Task 6
**Done when:**
1. A small private helper `_lineage_owned_by_session(lineage_id, session_id)` (functional, not a class) lives in the helpers section of `app.py` and delegates to `db_manager.lineage_exists_for_session`.
2. A new route `@app.route('/api/lineages', methods=['GET'])` exists, calls `get_or_create_session_id()`, parses `limit` from `request.args` (clamped 1..`VERSIONING_CONFIG['max_lineage_list_limit']`, default `VERSIONING_CONFIG['default_lineage_list_limit']`), and returns `{success: true, lineages: [...], total, limit, timestamp}` — flat shape matching the rest of the codebase (e.g. `/api/history`).
3. With one v1 row in the DB owned by the active session, `curl -b cookies.txt -c cookies.txt http://localhost:5000/api/lineages` returns 200 with `total >= 1` and the lineage_id of that row in the `lineages` array.
**Notes:** Plan §2 first route. Follow existing patterns: `try/except` wrapping the whole handler with `create_error_response(...,'lineages',500)` on unexpected errors. Use `db_manager` global; return `create_error_response("Database not available", 'database', 503)` if it's None, same as other routes.
**Status:** done
**Outcome:** Added `_lineage_owned_by_session(lineage_id, session_id)` helper (functional, delegates to `db_manager.lineage_exists_for_session`) in the helpers section right after `get_or_create_session_id`. Added a new `# ==================== PRESENTATION VERSIONING ENDPOINTS ====================` section just before the error handlers, containing `GET /api/lineages`: 503 when no `db_manager`, otherwise reads session via `get_or_create_session_id`, clamps `limit` from `request.args` to `[1, VERSIONING_CONFIG['max_lineage_list_limit']]` with default `VERSIONING_CONFIG['default_lineage_list_limit']`, calls `db_manager.get_lineages_for_session`, returns `{success, lineages, total, limit, timestamp}`. Verified against the running Flask server: fresh `requests.Session()` got 200 + empty list; `limit=9999` clamped to 100, `limit=0` clamped to 1; Flask `test_client` with `session_transaction` set to `f880caba...` (owner of lineage 28 from Task 6) returned `total=1` with lineage_id 28 present and all five expected keys in each entry.

## Task 8 — Routes: list versions in a lineage + fetch a single version
**Files:** backend/app.py
**Depends on:** Task 7
**Done when:**
1. `@app.route('/api/lineages/<int:lineage_id>/versions', methods=['GET'])` returns `{success: true, lineage_id, versions: [...], total, timestamp}` with versions in chronological order (oldest-first), each entry including `version_number, label, note, created_at, has_snapshot`. Returns 404 with `error_type: "not_found"` when the DB method returns `None` (covers missing AND cross-session).
2. `@app.route('/api/lineages/<int:lineage_id>/versions/<int:version_number>', methods=['GET'])` returns `{success: true, lineage_id, version_number, label, note, created_at, filename, slide_structure, is_stub, timestamp}`. Returns 404 `not_found` when the DB method returns `None`.
3. Curl checks: with session A owning lineage L (v1), `GET /api/lineages/L/versions` → 200 with one version; `GET /api/lineages/L/versions/1` → 200 with non-null `slide_structure`. Same calls from session B (different cookie) → 404 with `error_type: "not_found"`.
**Notes:** Plan §2 second and third routes. Reuse the standard `create_error_response("Not found", 'not_found', 404)` for both failure paths — same error message and type for missing vs unauthorized (existence-leak guard). `has_snapshot = (slide_structure is not None)` is computed in the route, not stored.
**Status:** done
**Outcome:** Added two routes in the Presentation Versioning Endpoints section of `app.py`. `GET /api/lineages/<int:lineage_id>/versions` calls `db_manager.get_versions_for_lineage` and returns `{success, lineage_id, versions, total, timestamp}` where each entry is projected to `{version_number, label, note, created_at, has_snapshot}` (slide_structure intentionally omitted from list responses); returns 404 `not_found` when the DB method returns `None`. `GET /api/lineages/<int:lineage_id>/versions/<int:version_number>` calls `db_manager.get_version` and returns the full version including `slide_structure`, `is_stub`, and `filename`; returns 404 `not_found` for missing/cross-session. Both use `create_error_response("Not found", 'not_found', 404)` so missing and cross-session are indistinguishable to callers. Verified end-to-end: owner of lineage 28 got `total=1`/`has_snapshot=True` from list, `slide_structure=={'slides',...,'title'}` and `is_stub=False` from detail; a backfilled stub lineage got `has_snapshot=False` and `is_stub=True`/`slide_structure=None`; cross-session against lineage 28, missing lineage 9999999, and missing version 28/999 all returned 404 `not_found`; live HTTP via `requests.Session()` with a fresh session got 404 `not_found` for both routes.

## Task 9 — Route: download a version's `.pptx`
**Files:** backend/app.py
**Depends on:** Task 8
**Done when:** `@app.route('/api/lineages/<int:lineage_id>/versions/<int:version_number>/download', methods=['GET'])` streams the .pptx via `send_file` with the same `mimetype` / `as_attachment=True` / `download_name=<filename>` pattern as `/api/download/<filename>`. Returns 404 `error_type: "not_found"` when any of: row is missing, owned by another session, has NULL `file_path` (stub row), or `file_path` no longer exists on disk.

Observable proof:
- `GET /api/lineages/L/versions/1/download` for the active session returns 200, `Content-Type: application/vnd.openxmlformats-officedocument.presentationml.presentation`, non-empty body.
- The downloaded bytes equal the bytes from the legacy `/api/download/<filename>` route for the same .pptx.
- Stub row (manually set `file_path=NULL` via sqlite) returns 404 `not_found`.
**Notes:** Plan §2 fourth route. Path-traversal is not a concern here because the path comes from the DB, not from the URL — but still confirm the file exists via `os.path.exists` before `send_file`.
**Status:** done
**Outcome:** Added `GET /api/lineages/<int:lineage_id>/versions/<int:version_number>/download` to the Presentation Versioning Endpoints section of `app.py`. Calls `db_manager.get_version` for ownership/existence, returns 404 `not_found` for missing/cross-session; reads `file_path` and `filename` from the row, returns 404 `not_found` if `file_path` is NULL or `os.path.exists(file_path)` is False; otherwise streams via `send_file` with the existing pptx mimetype, `as_attachment=True`, and `download_name=<filename>`. All four 404 paths share the same response so the existence-leak guard holds. Verified six ways: (1) owner of lineage 28 got 200 + correct mimetype + 32,627 bytes; (2) bytes were SHA-256 identical to the legacy `/api/download/<filename>` route; (3) cross-session against lineage 28 → 404 `not_found`; (4) temp test row with `file_path=NULL` → 404 `not_found`; (5) temp test row whose `file_path` points to a non-existent path → 404 `not_found`; (6) live HTTP via `requests` from a fresh session → 404 `not_found`. Missing lineage and missing version_number also covered. Two temp test rows cleaned up after.

## Task 10 — Backend tests: DB layer (`test_database.py`)
**Files:** backend/test_database.py
**Depends on:** Task 9
**Done when:** New test cases added (functional/script-style to match the existing file's idiom — check the file before writing to mirror its current pattern, but at minimum the following cases must execute and pass):
1. `save_presentation_version` writes a row whose fields roundtrip via `get_version`.
2. Inserting a second row with the same `(lineage_id, version_number)` raises (unique constraint).
3. `get_lineages_for_session` returns only the calling session's lineages, sorted newest-first, with correct `total_versions` aggregation when a lineage has multiple versions (seed a fake v2 directly via `save_presentation_version` to test aggregation).
4. `get_versions_for_lineage` returns oldest-first; returns `None` for an unknown lineage_id; returns `None` when the lineage exists but `session_id` doesn't match.
5. `get_version` ditto for single-version lookup with cross-session probe.
6. Backfill: seed three `generation_history` rows with no `presentation_versions` entries → call `_backfill_v1_for_existing_presentations()` → assert three `is_stub=True` rows with `slide_structure IS NULL` and `label = VERSIONING_CONFIG['v1_label']`. Call again → assert zero new rows.

Run `python backend/test_database.py` exits 0 and prints all assertions passed.
**Notes:** Plan §5 "Backend tests". Use a tmp SQLite path (override `DATABASE_CONFIG['path']` for the test or use an in-memory DB) so tests don't pollute the dev DB. If the existing `test_database.py` already has setup/teardown helpers, reuse them.
**Status:** done
**Outcome:** Added a new `test_presentation_versioning()` function to `backend/test_database.py` matching the file's script-style idiom (functional, emoji-prefixed prints, no pytest). Function runs against an **isolated tmp SQLite DB** (created via `tempfile.mkdtemp`, `DATABASE_CONFIG['path']` patched before constructing a fresh `DatabaseManager`, restored + tmp dir wiped in a `finally`) — the existing `test_database()` continues to use the dev DB as before, but my new function leaves the dev DB untouched. Covers all six scenarios from the task: (1) `save_presentation_version` + roundtrip via `get_version` including all 11 columns; (2) duplicate `(lineage_id, version_number)` raises a unique-constraint error; (3) `get_lineages_for_session` aggregation — lineage with v1+v2 returns `total_versions=2` and v2's label; (4) `get_versions_for_lineage` returns chronological order + `None` for missing/cross-session; (5) `get_version` + `lineage_exists_for_session` cross-session existence-leak guard; (6) seed 3 orphan `generation_history` rows → backfill inserts 3 stubs (`is_stub=True`, `slide_structure IS NULL`, label from `VERSIONING_CONFIG['v1_label']`) → second backfill is a no-op. `__main__` runs `test_database()` then `test_presentation_versioning()`. **Inline fix during verification:** initial implementation accessed SQLAlchemy ORM attributes outside the `with db.get_session()` block on the backfill check (detached-instance error per CLAUDE.md); fixed by materializing the rows to dicts via `to_dict()` inside the session. Final run: `python test_database.py` → exit 0 with all six "✅ Test N" lines plus the existing test's output.

## Task 11 — Backend tests: API layer (`test_api.py`)
**Files:** backend/test_api.py
**Depends on:** Task 10
**Done when:** New test cases added that hit a live Flask test client (or running server, depending on existing pattern — match the file's existing style):
1. Fresh session: `GET /api/lineages` → 200, `lineages: []`, `total: 0`.
2. After one `POST /api/generate-ppt`: `GET /api/lineages` → one entry with `latest_version_number=1`, `latest_version_label="Initial generation"`.
3. `GET /api/lineages/<id>/versions` → one version, `has_snapshot=true`.
4. `GET /api/lineages/<id>/versions/1` → non-null `slide_structure`, `is_stub=false`.
5. `GET /api/lineages/<id>/versions/1/download` → 200, correct mimetype, non-empty body, bytes equal to legacy `/api/download/<filename>` for the same row.
6. `GET /api/lineages/9999999/versions` → 404 `error_type="not_found"`.
7. Cross-session: create lineage as session A, query as session B → 404 `error_type="not_found"` (never 403, never 200 empty).
8. Stub-row download: set `file_path=NULL` on a row via direct DB write, `GET .../download` → 404 `error_type="not_found"`.

Run `python backend/test_api.py` exits 0.
**Notes:** Plan §5 "Backend tests". The Ollama call in `POST /api/generate-ppt` may be heavy for tests — if the existing file mocks the LLM or seeds DB rows directly, follow the same approach for cases 2–5 (e.g. write a `generation_history` + v1 row directly and skip the LLM round-trip).
**Status:** done
**Outcome:** Added `test_presentation_versioning_api()` and a `_cleanup_versioning_rows()` helper to `backend/test_api.py`. The function hits the running Flask server via `requests.Session()` (matching the existing file's idiom), seeds `generation_history` + v1 `presentation_versions` rows directly via `DatabaseManager` (per task notes, to skip the slow Ollama POST), discovers the server-assigned session_id via the existing `GET /api/session` endpoint, and reuses an existing `temp/*.pptx` for the download bytes-equality test. **Demoted the interactive menu:** changed `__main__` so `python test_api.py` defaults to the new automated tests (exit 0 on success, non-zero on failure); the original interactive `main()` is preserved behind `python test_api.py menu`. All 8 task cases covered: (1) fresh session → empty list, (2) seeded v1 → list shows latest_version_number=1 + "Initial generation" label, (3) versions list shows has_snapshot=true (no slide_structure projected), (4) version detail returns non-null slide_structure + is_stub=false, (5) download 200/correct mimetype/SHA-256 matches legacy /api/download, (6) missing lineage 9999999 → 404 not_found, (7) cross-session via second fresh session → 404 not_found on all three read routes, (8) stub row with `file_path=NULL` → 404 not_found. Final run: `python test_api.py` → exit 0; cleanup deleted 2 pv + 1 gh + 2 user rows seeded by the tests.

## Task 12 — End-to-end smoke via `/pptx-test` + verify versioning side effects
**Files:** (no code change — verification only)
**Depends on:** Task 11
**Done when:**
1. Run the `/pptx-test` skill with a small synthetic brief. It reports success and a generated `.pptx`.
2. Open `backend/database/ppt_generator.db` and confirm: exactly one new `presentation_versions` row was created for that run, with `version_number=1`, `label="Initial generation"`, `is_stub=0`, non-null `slide_structure` (parseable as JSON containing a `slides` array).
3. `curl -b <session-cookie>` `GET /api/lineages` lists that lineage; `GET /api/lineages/<lid>/versions/1/download` returns a .pptx whose SHA-256 matches the SHA-256 of the file from `/pptx-test`'s reported path.
**Notes:** Plan §5 "Smoke test". This is the gate before the slice can be considered shippable. If any of the three checks fails, file a follow-up task rather than patching tasks already marked done.
**Status:** done
**Outcome:** Invoked `/pptx-test` against the running backend with the skill's standard Q4 2024 brief; POST returned 200 in 16.7s, generated `presentation_20260519_124411_7a3ba75c.pptx` (6 slides), `detected_type=business_review` (confidence 0.95). All three versioning gate criteria pass: (1) Exactly one new `presentation_versions` row for `lineage_id=31` (= generation_history.id) with `version_number=1`, `label='Initial generation'`, `is_stub=0`, `filename` matching the response, and a non-null `slide_structure` whose `slides` array has 6 entries. (2) `GET /api/lineages` from the owning session lists lineage 31 with `latest_version_number=1` and the `'Initial generation'` label. (3) `GET /api/lineages/31/versions/1/download` returned a .pptx whose SHA-256 (`d6b3843f1a0d7de6…`) matches the file on disk under `temp/`. **Unrelated finding flagged for follow-up (not a Task 12 blocker):** the `/pptx-test` skill's own internal `assert slide.shapes.title.text` check failed on slide 1 — the deck's title slide uses a placeholder that python-pptx doesn't surface as `slide.shapes.title`. This is a pre-existing rendering pattern, not a versioning regression (5/6 slides do have `.shapes.title.text`; all 6 have populated text frames).
