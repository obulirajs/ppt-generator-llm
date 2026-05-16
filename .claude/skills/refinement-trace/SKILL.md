---
name: refinement-trace
description: Dumps the full version history and refinement instruction log for a given presentation in the PPT generator. Use when debugging refinement bugs, comparing how a deck evolved across versions, or verifying that a refinement actually produced the expected structural change. Reads from the presentation_versions table and renders a side-by-side summary.
version: 0.1.0
---

# /refinement-trace

## When to use
- A user reports "the refinement didn't work" — pull the trace to see what the LLM actually returned.
- Verifying that an /implement task on the refinement feature produced the correct version chain.
- Comparing instruction → outcome across multiple refinements during dev.

## Steps
1. Ask the user for a presentation ID (the root generation_history.id, not a version ID) if not supplied.
2. Query the database via a short script run through Bash:
```bash
   cd backend && source pptenv/bin/activate && python - <<'PY'
   from database.db_manager import init_database
   import sys, json
   db = init_database()
   pres_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
   versions = db.get_presentation_versions(pres_id)  # method to be implemented in Spec 001
   for v in versions:
       print(f"--- v{v['version_number']} (id={v['id']}, created={v['created_at']}) ---")
       print(f"Instruction: {v.get('refinement_instruction', '(initial generation)')}")
       print(f"Slides: {len(v['slides_json'])}")
       print(f"Tokens: prompt={v.get('prompt_tokens')}, completion={v.get('completion_tokens')}")
       print()
   PY
```
3. For each version, also print a one-line summary per slide (title only) so the user can eyeball what changed.
4. If two version numbers are given, do a structural diff: list slides added, removed, or with changed titles between them.

## Output format
A markdown report with one section per version, plus an optional diff section. Save to `specs/NNN-slug/refinement-trace-pres-<id>.md` if invoked inside a feature folder; otherwise print inline.

## Rules
- Never modify the database from this skill. Read-only.
- Do not call the LLM. This is a forensic tool, not a regeneration tool.
- If the presentation_versions table doesn't exist yet (Spec 001 not done), say so and stop.