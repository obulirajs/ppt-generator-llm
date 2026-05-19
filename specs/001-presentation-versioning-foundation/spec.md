# Feature 001: Presentation Versioning Foundation

**Status:** approved
**Owner:** Raj
**Created:** 2026-05-17

## Problem / Motivation
Today, each generated presentation is a one-shot artifact. There's no way to track that a deck has been iterated on, no way to look back at what was generated before, and no way for future features (slide refinement, regeneration, rollback) to express "this deck is a descendant of that earlier deck."

This feature lays the **data foundation** for a presentation lineage: every generated presentation becomes version 1 of its own lineage, the schema can support arbitrary future versions (v2, v3, …), and a small set of read endpoints exposes the lineage and version history to callers. No refinement, no UI, no LLM work is in scope — those will land on top of this foundation in follow-up features.

## User Story
As a user of the PPT generator (and as the developer of the upcoming slide-refinement feature), I want every generated presentation to be recorded as version 1 of a lineage that I can read back later, so that future iterations of the same deck have a stable place to live and so that I can review what was previously generated for a given lineage.

## Behavior (EARS)

**Write-side (implicit, single trigger):**
- When the system successfully generates a presentation, the system shall create a corresponding v1 record in that presentation's lineage. The lineage is identified by the original presentation's ID.
- When the system fails to generate a presentation, the system shall not create a version record.

**Backfill (idempotent, runs on app startup):**
- When the application starts, the system shall ensure that every pre-existing presentation owned by any session has a corresponding stub v1 row, populated with `version_number = 1` and creation timestamp, but without a fully populated content snapshot.
- When the application starts and all pre-existing presentations already have a v1 row, the system shall exit the backfill step as a no-op. (The backfill is idempotent — there is no separate one-shot script.)

**Read-side:**
- When a caller requests the lineages for their session, the system shall return the list of lineages they own, each annotated with at minimum: lineage ID, latest version number, and the latest version's creation timestamp.
- When a caller requests the version list for a lineage they own, the system shall return all versions in chronological order (oldest first, v1 → vN), each including: version number, creation timestamp, label, and optional user-supplied note.
- When a caller requests the content of a specific version they own, the system shall return the stored slide structure for that version along with its metadata.
- When a caller requests the .pptx file for a specific version they own, the system shall return the file as a downloadable binary.
- When a caller requests a lineage or version that does not exist **or** that exists but does not belong to their session, the system shall return a failure response in the project's standard shape with `success=false` and `errorType: "not_found"`. The two cases are intentionally indistinguishable to the caller, to prevent existence leaks across sessions.

## Inputs

**Write-side (no new direct user inputs):**
- Versioning is triggered as a side effect of the existing presentation-generation flow. The user provides the same brief, template, etc. as today.

**Read-side:**
- Lineage identifier — equal to the original (v1) presentation's ID.
- Version number — integer ≥ 1, scoped within a lineage.
- Session context — used to enforce ownership (already provided by the existing session mechanism; no new auth in this slice).

## Outputs

**Per version (what is stored):**
- **Output-only snapshot:** the slide structure/content used to render the deck, and a reference to the generated .pptx file. The original input brief is **not** retained on the version record.
- **Metadata:** version number, creation timestamp, label, optional user-supplied note, lineage reference.

**Label semantics:**
- For v1, the label is the literal system-set string `"Initial generation"`. It is written at insert time by the generation flow; callers do not need to provide it.
- For v2+ (future refinement feature), the label column stores the **verbatim refinement instruction text** the user typed (e.g., `"make slide 3 punchier"`). There is no separate "instruction" column — the same `label` column carries the instruction text directly.
- The user-supplied **note** is a distinct, optional free-text field. When present, callers may treat it as an override or supplement to the label. It is never auto-populated.

**Read endpoint responses:**
- All read endpoints return JSON in the project's standard shape: `{ success, data | error, errorType, timestamp }`.
- The download endpoint returns the .pptx file as a binary attachment, or the standard JSON error shape on failure.

## Success Criteria
- [ ] Every newly generated presentation produces exactly one new v1 record in the versions table, scoped to a lineage whose ID equals the new presentation's ID.
- [ ] After the backfill runs, every pre-existing presentation in the database has at least one corresponding stub v1 row.
- [ ] A caller can list all lineages owned by their session and see each lineage's latest version number and timestamp.
- [ ] A caller can list all versions within a lineage they own, in chronological order, with version number, timestamp, label, and (when present) note.
- [ ] A caller can fetch the stored slide structure of a specific version they own.
- [ ] A caller can download the .pptx file of a specific version they own.
- [ ] A caller requesting a lineage or version they do not own, or that does not exist, receives a failure response in the project's standard error shape with an `errorType` that conveys the failure reason.
- [ ] The schema for versions is shaped such that a future refinement endpoint can insert a v2, v3, … row using the same table(s), without further schema migration.

## Out of Scope
- Refinement logic — no endpoint, no LLM call, no flow that creates v2, v3, etc. The schema must support it; nothing in this slice writes beyond v1.
- Any frontend / UI changes. The React app is unchanged in this slice.
- LLM prompt changes or generation-logic changes.
- Authentication or multi-user identity beyond the existing session model.
- Per-version thumbnail or preview generation.
- A diff or compare view between versions.
- Version rollback / restore / "make v2 the active version" actions.
- Retention or purge policy for old versions (every version is kept indefinitely in this slice).
- Storing or retaining the original input brief on the version record (explicitly excluded by the "output only" snapshot decision).
- **Lineage ownership across session resets.** If a session is recreated (cookie cleared, browser reset) lineages from the prior session become orphaned. This matches today's per-presentation behavior and is out of scope to fix in this slice.

## Resolved Decisions
The following were raised as open questions during spec review and resolved before approval. Captured here for traceability into /plan.

- **Error disambiguation:** Missing and unauthorized both return `errorType: "not_found"` — single value, no distinction surfaced to the caller. Prevents lineage existence leaks across sessions.
- **v1 label wording:** Literal string `"Initial generation"`, written by the system at insert time.
- **Backfill execution model:** Idempotent step that runs on app startup; exits as a no-op once every pre-existing presentation has a v1 row. No separate one-shot migration script.
- **Lineage ownership across session resets:** Out of scope — orphaning on session reset matches today's per-presentation behavior and is documented in Out of Scope above.
- **v2+ label storage:** The `label` column stores the verbatim refinement instruction text for v2+. No separate `instruction` column is introduced — the same column carries `"Initial generation"` for v1 and the user-typed instruction for v2+.
