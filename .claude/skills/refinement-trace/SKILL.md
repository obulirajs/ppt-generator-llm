---
name: refinement-trace
description: Dumps the full version history and refinement instruction log for a given presentation in the PPT generator. Use when debugging refinement bugs, comparing how a deck evolved across versions, or verifying that a refinement actually produced the expected structural change. Reads from the presentation_versions table and renders a side-by-side summary. Read-only — never modifies data or calls the LLM.
version: 0.1.0
---

# /refinement-trace

## When to use
- A user reports "the refinement didn't work" → pull the trace to see what the LLM actually returned.
- Verifying that an `/implement` task on the refinement feature produced the correct version chain.
- Comparing instruction → outcome across multiple refinements during development.
- Building a bug report — paste the trace output into the report.

## Steps

1. **Ask for a presentation ID** if not supplied. This is the root `generation_history.id` (the original generation), not a specific version ID.

2. **Confirm the schema exists.** Run a quick check:
   ```bash
   cd backend && source pptenv/bin/activate && python - <<'PY'
   from database.db_manager import init_database
   db = init_database()
   # Try to call the versions method; if it doesn't exist, Spec 001 isn't done yet
   if not hasattr(db, 'get_presentation_versions'):
       print("❌ presentation_versions table / method not yet implemented.")
       print("   Spec 001 (Presentation Versioning Foundation) must ship first.")
       exit(1)
   print("✅ Schema ready")
   PY
   ```
   If the check fails, **stop and tell the user** that Spec 001 must ship before this tool works.

3. **Pull the version history:**
   ```bash
   cd backend && source pptenv/bin/activate && python - <<'PY'
   from database.db_manager import init_database
   import sys, json
   
   db = init_database()
   pres_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
   versions = db.get_presentation_versions(pres_id)
   
   if not versions:
       print(f"No versions found for presentation ID {pres_id}")
       exit(0)
   
   for v in versions:
       print(f"--- v{v['version_number']} (id={v['id']}, created={v['created_at']}) ---")
       instruction = v.get('refinement_instruction') or '(initial generation)'
       print(f"Instruction: {instruction}")
       slides = v.get('slides_json') or []
       print(f"Slides: {len(slides)}")
       for i, s in enumerate(slides):
           title = s.get('title') or s.get('name') or '(untitled)'
           print(f"  {i+1}. {title}")
       tokens = f"prompt={v.get('prompt_tokens')}, completion={v.get('completion_tokens')}"
       print(f"Tokens: {tokens}")
       print()
   PY
   ```

4. **If two version numbers are specified** (e.g., "trace pres 5, diff v2 vs v3"), run a structural diff:
   - Slides added in v3 (by title, not by index)
   - Slides removed from v2
   - Slides with changed titles
   - Slides with changed bullet count
   Print as a markdown table.

## Output format

Inline markdown report with this structure:

```markdown
# Refinement Trace — Presentation <id>

## Version Summary
| Version | Created | Instruction | Slides | Tokens |
|---|---|---|---|---|
| v1 | ... | (initial) | 8 | — |
| v2 | ... | "Make slide 3 punchier" | 8 | 1240 |
| v3 | ... | "Add a slide about pricing" | 9 | 980 |

## v1 → v2 Diff (if requested)
- **Changed:** Slide 3 title from "Our Solution" → "What We Built"
- **Bullets reduced:** Slide 3 went from 5 → 3 bullets
- **Unchanged:** Slides 1, 2, 4–8
```

If invoked inside a feature folder (when working in `specs/NNN-slug/`), save the report to `specs/NNN-slug/refinement-trace-pres-<id>.md`. Otherwise print inline.

## Rules
- **Never modify the database.** Read-only.
- **Do not call the LLM.** This is a forensic tool, not a regeneration tool.
- **If the `presentation_versions` table doesn't exist yet**, say so and stop — Spec 001 must ship first.
- **If the presentation ID doesn't exist**, say so clearly. Don't guess.
- **Truncate long instructions** at ~120 chars in the summary table; show full text in a per-version section if needed.