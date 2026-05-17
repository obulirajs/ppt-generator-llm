---
name: specify
description: Phase 1 of SDD. Captures the WHAT and WHY of a feature for the PPT generator into specs/NNN-slug/spec.md. Use when a user describes a new capability ("add bullet density control", "support PDF input", "let users pick a template per slide", "add presentation versioning") before any implementation discussion.
version: 0.1.0
---

# /specify — Spec Phase

You are entering **Phase 1** of Spec-Driven Development. Do **not** discuss implementation, file paths, libraries, or code yet.

## Your job
1. Determine the next feature number: run `ls specs/` and find the highest `NNN-*` folder. The new number is that + 1, zero-padded to 3 digits. If `specs/` is empty or doesn't exist, start at `001`.
2. Ask the user **3–6 clarifying questions** covering these dimensions (skip any that are already clear from the user's seed message):
   - **User-visible behavior** — what does the user see, click, receive?
   - **Inputs & outputs** — what goes in, what comes out, in what format?
   - **Out-of-scope items** — what is this explicitly NOT doing?
   - **Impact on PPTX templates** — does this touch layouts, placeholders, branding?
   - **Impact on LLM prompts** — does this change how content is summarized or structured?
   - **Failure modes the user cares about** — what should happen when things go wrong?
   - **Success criteria** — how will we know it works?
3. Propose a kebab-case slug (e.g. `presentation-versioning`, `slide-refinement-api`).
4. Create `specs/NNN-slug/spec.md` using the structure in `specs/_template/spec.md` if it exists, otherwise use the structure below.
5. Show the spec back to the user and ask: **"Is this complete and accurate? If yes, run `/plan` next."**

## Spec structure (if no template exists)
```markdown
# Feature NNN: <Title>

**Status:** draft
**Created:** <date>

## Problem / Motivation
<Why does this need to exist?>

## User Story
As a <role>, I want <capability>, so that <outcome>.

## Behavior (EARS-style)
- When <trigger>, the system shall <response>.

## Inputs
## Outputs
## Success Criteria
- [ ] <observable, testable check>

## Out of Scope
## Open Questions
```

## Rules
- **No implementation talk.** No file paths, no library choices, no code, no API shapes. Those belong in `/plan`.
- If the user starts answering with "we'll use X library" or "add it to app.py", politely defer: *"Noted — that's a great input for the plan phase. For now, let's focus on what the user will experience."*
- **One feature per spec.** If the request clearly spans two unrelated features, say so and ask the user to pick one (or run `/specify` twice).
- Use **EARS**-style behavior statements where natural: *"When the user clicks Refine, the system shall create a new version."*
- If you genuinely cannot proceed without an implementation detail (rare), flag it as an **Open Question** in the spec and continue.
- After creating the spec, do **not** start `/plan` automatically. Wait for the user.