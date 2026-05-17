---
name: template-audit
description: Inspects a .pptx template file (system templates in backend/templates/system/ or user uploads in backend/user_templates/) and reports its slide layouts, placeholder indices, fonts, and color theme. Use when planning template-touching features, debugging rendering bugs, or auditing a newly uploaded template.
version: 0.1.0
---

# /template-audit

## Steps

1. **Identify the target file.** Ask which `.pptx` file to audit if not supplied. Common locations:
   - `backend/templates/system/*.pptx` (pre-defined system templates)
   - `backend/user_templates/*.pptx` (user uploads)
   - Project root `.pptx` files if any exist

2. **Run a layout inspection script** via Bash, using the project venv:
   ```bash
   cd backend && source pptenv/bin/activate && python - <<'PY'
   import sys
   from pptx import Presentation
   
   path = sys.argv[1] if len(sys.argv) > 1 else "templates/system/corporate_default.pptx"
   p = Presentation(path)
   
   print(f"Template: {path}")
   print(f"Slide width: {p.slide_width}, height: {p.slide_height}")
   print(f"Layout count: {len(p.slide_layouts)}\n")
   
   for i, layout in enumerate(p.slide_layouts):
       print(f"Layout {i}: {layout.name}")
       for ph in layout.placeholders:
           print(f"  ph idx={ph.placeholder_format.idx} "
                 f"type={ph.placeholder_format.type} "
                 f"name={ph.name}")
       print()
   PY
   ```

3. **Summarize findings:**
   - Total layout count
   - Layout names
   - Placeholder count per layout
   - Any layouts with picture or chart placeholders
   - Whether common layouts exist: Title Slide, Title and Content, Section Header

4. **Flag risks:**
   - Missing common layouts (title, section, content)
   - Duplicate layout names
   - Layouts with zero placeholders (likely unusable)
   - Locked masters or non-standard slide dimensions

## Output

A markdown report with:
- A table of layouts and placeholder counts
- A short "Risks & Notes" paragraph
- A recommendation: is this template safe to use as-is, or does it need fixes?

If invoked inside a feature folder (when `pwd` includes `specs/NNN-slug/`), save the output to `specs/NNN-slug/template-audit-<filename>.md`. Otherwise print inline.

## Rules
- **Read-only.** Never modify the template file.
- **Don't call the LLM.** This is a structural audit, not a content generation tool.
- **If the file doesn't exist or isn't a valid .pptx**, report the error clearly and stop.
- **Don't try to render slides.** Just inspect the layout structure.