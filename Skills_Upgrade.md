# Skills Upgrade Guide — PPT Generator → Spec-Driven Development

This document walks through adding **Claude Code Agent Skills** to the `ppt-generator` project and using them to adopt a **GitHub Spec Kit-style Spec-Driven Development (SDD) workflow**:

> **specify → plan → tasks → implement**

It is tailored to this repo's actual stack:

- **Backend:** Flask 3.0 + python-pptx + LangChain + SQLAlchemy/SQLite (`backend/app.py`, `backend/utils/`, `backend/database/`)
- **Frontend:** React 19 via Create React App + axios (`frontend/src/`)
- **Domain assets:** PPTX templates at the repo root (`NMS_Corporate_01.pptx`, `Sales_Template-Blue.pptx`, `Corporate_Template_Reference.pptx`)

---

## Table of Contents

1. [What you're building](#1-what-youre-building)
2. [Prerequisites](#2-prerequisites)
3. [Directory layout you will create](#3-directory-layout-you-will-create)
4. [Step 1 — Scaffold `.claude/` and `specs/`](#step-1--scaffold-claude-and-specs)
5. [Step 2 — Write the project `CLAUDE.md`](#step-2--write-the-project-claudemd)
6. [Step 3 — Author the four SDD skills](#step-3--author-the-four-sdd-skills)
7. [Step 4 — Author project-specific helper skills](#step-4--author-project-specific-helper-skills)
8. [Step 5 — Add a Spec Template](#step-5--add-a-spec-template)
9. [Step 6 — Run your first SDD feature end-to-end](#step-6--run-your-first-sdd-feature-end-to-end)
10. [Step 7 — Iterate, version, and graduate to a team workflow](#step-7--iterate-version-and-graduate-to-a-team-workflow)
11. [Appendix A — Skill file format reference](#appendix-a--skill-file-format-reference)
12. [Appendix B — Glossary](#appendix-b--glossary)

---

## 1. What you're building

A **Claude Code Agent Skill** is a Markdown file (`SKILL.md`) with YAML frontmatter that Claude loads into its context when triggered. Each skill packages a reusable workflow — what to read, what to produce, what conventions to follow — and is invoked from the chat via `/skill-name` (or by Claude auto-selecting it when its `description` matches the user's request).

After this upgrade, your project will have:

| Skill                  | Phase        | Purpose                                                                                |
| ---------------------- | ------------ | -------------------------------------------------------------------------------------- |
| `/specify`             | Spec         | Capture **what & why** a feature does in `specs/NNN-slug/spec.md`                      |
| `/plan`                | Plan         | Decide **how** to build it: API shape, data model, template impact → `plan.md`         |
| `/tasks`               | Tasks        | Break the plan into ordered, testable work items → `tasks.md`                          |
| `/implement`           | Implement    | Execute one task at a time, with checkpoints                                           |
| `/slide-spec`          | Helper       | Translate a content brief into a structured slide-by-slide outline                     |
| `/template-audit`      | Helper       | Inspect a `.pptx` template, list its layouts/placeholders, and flag style risks        |
| `/pptx-test`           | Helper       | Generate a synthetic input + render a deck end-to-end as a smoke test                  |

Plus a `specs/` directory that holds versioned spec artifacts per feature, and a `CLAUDE.md` that sets project-wide ground rules.

---

## 2. Prerequisites

- Claude Code installed and authenticated (you confirmed you have an active subscription).
- Open a shell at the project root:
  ```bash
  cd /Users/oselvaraj/Documents/Raj/NPO/Projects/ppt-generator
  ```
- Backend virtualenv working (`backend/pptenv/`) and `backend/requirements.txt` installable.
- Frontend buildable (`cd frontend && npm install && npm start`).
- Recommended: initialize git at the **project root** (the `frontend/` subfolder already has its own `.git`, but the root does not — spec artifacts should be versioned at the root):
  ```bash
  git init
  git add Skills_Upgrade.md .gitignore
  git commit -m "chore: add skills upgrade guide"
  ```

---

## 3. Directory layout you will create

```
ppt-generator/
├── CLAUDE.md                       # Project-wide guidance (Step 2)
├── Skills_Upgrade.md               # This file
├── .claude/
│   └── skills/
│       ├── specify/SKILL.md        # Step 3
│       ├── plan/SKILL.md           # Step 3
│       ├── tasks/SKILL.md          # Step 3
│       ├── implement/SKILL.md      # Step 3
│       ├── slide-spec/SKILL.md     # Step 4
│       ├── template-audit/SKILL.md # Step 4
│       └── pptx-test/SKILL.md      # Step 4
└── specs/
    ├── _template/                  # Step 5 — copy this for every new feature
    │   ├── spec.md
    │   ├── plan.md
    │   └── tasks.md
    └── 001-example-feature/        # Created by /specify (Step 6)
```

---

## Step 1 — Scaffold `.claude/` and `specs/`

Run from the project root:

```bash
cd /Users/oselvaraj/Documents/Raj/NPO/Projects/ppt-generator

mkdir -p .claude/skills/specify
mkdir -p .claude/skills/plan
mkdir -p .claude/skills/tasks
mkdir -p .claude/skills/implement
mkdir -p .claude/skills/slide-spec
mkdir -p .claude/skills/template-audit
mkdir -p .claude/skills/pptx-test
mkdir -p specs/_template
```

Add `.claude/` to your root `.gitignore`'s **allow** list if you want to share skills with collaborators (recommended). Edit `.gitignore` and make sure these lines exist:

```
# Track Claude Code project assets
!.claude/
!.claude/**
```

> **Why share skills?** The whole point of SDD is consistency — every contributor (and every future Claude session) follows the same phased workflow. Keep skills in version control.

---

## Step 2 — Write the project `CLAUDE.md`

`CLAUDE.md` is auto-loaded by Claude Code every session in this directory. It is **not** a skill — it's always-on context. Keep it short.

Create `CLAUDE.md` at the project root with content like:

```markdown
# PPT Generator — Project Context

## Stack
- Backend: Flask 3.0, python-pptx 0.6.23, LangChain 0.1, SQLAlchemy 2 (SQLite), Python 3.x
  - Entry: backend/app.py
  - LLM wrapper: backend/utils/llm_service.py
  - PPT engine: backend/utils/ppt_generator.py
  - Document ingestion: backend/utils/document_parser.py
  - DB layer: backend/database/db_manager.py + backend/database/models.py
  - Templates: backend/pptx-templates/ and root-level *.pptx files
- Frontend: React 19, CRA (react-scripts 5), axios
  - Entry: frontend/src/index.js → App.js
  - Components: frontend/src/components/
  - Pages: frontend/src/pages/
  - API client: frontend/src/services/

## Workflow — Spec-Driven Development (SDD)
All non-trivial changes follow the four-phase flow:
1. `/specify` — capture intent in specs/NNN-slug/spec.md
2. `/plan` — design in specs/NNN-slug/plan.md
3. `/tasks` — break down in specs/NNN-slug/tasks.md
4. `/implement` — execute one task at a time

Trivial fixes (typo, single-line bug, dependency bump) can skip the spec phase but should still produce a short commit message describing intent.

## Conventions
- Never edit *_backup.py or *_backup.zip files — those are historical snapshots.
- Templates (.pptx) are binary; describe changes in plan.md, do not diff them.
- New PPT generation features must be exercisable via /pptx-test before merge.
- Keep Python dependencies in backend/requirements.txt pinned.
```

---

## Step 3 — Author the four SDD skills

Each file below is the **entire content** of the corresponding `SKILL.md`. The `name`, `description`, and `version` keys in frontmatter are required. Keep descriptions tight and specific — they're how Claude decides when to auto-trigger.

### 3.1 `/specify` — `.claude/skills/specify/SKILL.md`

```markdown
---
name: specify
description: Phase 1 of SDD. Captures the WHAT and WHY of a feature for the PPT generator into specs/NNN-slug/spec.md. Use when a user describes a new capability ("add bullet density control", "support PDF input", "let users pick a template per slide") before any implementation discussion.
version: 0.1.0
---

# /specify — Spec Phase

You are entering **Phase 1** of Spec-Driven Development. Do **not** discuss implementation yet.

## Your job
1. Determine the next feature number (`ls specs/` → find the highest `NNN-*` and add 1; start at `001`).
2. Ask the user 3–6 clarifying questions covering:
   - User-visible behavior (inputs, outputs, success criteria)
   - Out-of-scope items (what this is explicitly NOT)
   - Impact on PPTX templates (layouts touched, placeholder assumptions)
   - Impact on LLM prompts (does it change how content is summarized/structured?)
   - Failure modes the user cares about
3. Propose a kebab-case slug.
4. Create `specs/NNN-slug/spec.md` using `specs/_template/spec.md` as the starting structure.
5. Show the spec back and ask: "Is this complete and accurate? If yes, run `/plan`."

## Rules
- No file paths, no code, no library choices — those belong in `/plan`.
- If the user starts answering with "we'll use X library", politely defer: "Noted for the plan phase."
- One feature per spec. If the request spans two unrelated features, split them.
- Use **EARS**-style behavior statements where natural ("When <trigger>, the system shall <response>.").
```

### 3.2 `/plan` — `.claude/skills/plan/SKILL.md`

```markdown
---
name: plan
description: Phase 2 of SDD. Turns an approved spec.md into a technical plan.md for the PPT generator — API contract, data model changes, LLM prompt deltas, PPTX template impact, frontend component changes, test strategy. Use after /specify is complete.
version: 0.1.0
---

# /plan — Plan Phase

You are entering **Phase 2** of SDD.

## Inputs
- `specs/NNN-slug/spec.md` (must exist and be approved)
- Repo state — read these before drafting:
  - `backend/app.py` (route surface)
  - `backend/utils/ppt_generator.py` (rendering logic)
  - `backend/utils/llm_service.py` (LLM contract)
  - `backend/database/models.py` (data model)
  - `frontend/src/services/` (API client)
  - `frontend/src/pages/` and `frontend/src/components/` (UI touchpoints)

## Output: specs/NNN-slug/plan.md

Sections (in order):
1. **Architecture Overview** — one paragraph + an ASCII flow diagram (input → parse → LLM → render → download).
2. **Backend Changes**
   - New/changed Flask routes (method, path, request/response JSON shape)
   - LLM prompt changes (file + a sketch of the delta)
   - python-pptx logic changes (which layouts, placeholders, run properties)
   - Database migrations (new tables/columns; SQLite ALTER limitations)
3. **Frontend Changes**
   - New/changed pages and components
   - axios calls added to `frontend/src/services/`
   - State management impact
4. **Template Impact**
   - Which `.pptx` files are affected; whether a new layout is required
   - If a template change is required, attach an **audit** by invoking `/template-audit` on the affected file
5. **Test Strategy**
   - Which backend test file gets new cases (`backend/test_*.py`)
   - Smoke test via `/pptx-test` with an example input
   - Frontend manual test steps (CRA — `npm start`, then click-through)
6. **Risks & Open Questions**
7. **Out-of-Scope (recap from spec)**

## Rules
- Reference real file paths from this repo. Do not invent files.
- If a section is genuinely N/A, write "N/A — reason."
- End by asking the user to approve before `/tasks`.
```

### 3.3 `/tasks` — `.claude/skills/tasks/SKILL.md`

```markdown
---
name: tasks
description: Phase 3 of SDD. Decomposes an approved plan.md into an ordered, testable task list in tasks.md for the PPT generator. Use after /plan is approved.
version: 0.1.0
---

# /tasks — Tasks Phase

You are entering **Phase 3** of SDD.

## Inputs
- `specs/NNN-slug/spec.md`
- `specs/NNN-slug/plan.md`

## Output: specs/NNN-slug/tasks.md

A numbered list. Every task must be:
- **Atomic** — completable in one /implement run (≈ < 30 min of work).
- **Verifiable** — has an explicit "Done when:" check.
- **Ordered** — dependencies flow top-to-bottom; no forward references.

### Required task ordering
1. Database migration / model changes first.
2. Backend service-layer (`backend/utils/*.py`) next.
3. Backend route(s) in `backend/app.py`.
4. Backend tests (`backend/test_*.py`).
5. Frontend service (`frontend/src/services/`).
6. Frontend components/pages.
7. End-to-end smoke via `/pptx-test`.
8. Docs / README touch-ups (if any).

### Task format
```
## Task N — <short title>
**Files:** path/to/file.py, path/to/component.js
**Depends on:** Task N-1 (or "none")
**Done when:** <explicit, observable check — a passing test name, a curl command output, a UI state>
**Notes:** <gotchas, links to spec/plan sections>
```

## Rules
- No task may span more than 3 files unless that's intrinsic (e.g. a route + service + test trio).
- If a task feels >30 min, split it.
- Re-read plan.md before writing — don't invent scope.
```

### 3.4 `/implement` — `.claude/skills/implement/SKILL.md`

```markdown
---
name: implement
description: Phase 4 of SDD. Executes ONE task from tasks.md at a time for the PPT generator. Use when the user says "implement task N" or "next task". Stops after each task for review.
version: 0.1.0
---

# /implement — Implementation Phase

You are entering **Phase 4** of SDD.

## Protocol
1. Ask which feature (`specs/NNN-slug/`) and which task number, if not given.
2. Open `tasks.md` and the referenced files.
3. Re-read the relevant section of `plan.md` so you stay aligned with design intent.
4. Make the changes.
5. Run the relevant verification:
   - Backend Python: `cd backend && source pptenv/bin/activate && python -m pytest <file> -k <name>` (or the matching `python backend/test_*.py` invocation).
   - Frontend: `cd frontend && npm test -- --watchAll=false` for the touched component.
   - End-to-end PPT smoke: invoke `/pptx-test`.
6. Update the task entry in `tasks.md`:
   - Mark `Status: done` and append a one-line "Outcome:" note.
7. STOP. Report what changed, what's verified, and ask whether to proceed to the next task.

## Rules
- **One task per run.** If you finish early, do not start the next task — return control to the user.
- If a task can't be completed as written (blocker, missing info), update `tasks.md` with a "Blocked:" note and return — do not silently expand scope.
- Never modify `spec.md` from this skill. Spec changes go through `/specify` again (creating a v2 spec).
- Never modify files matching `*_backup*` or `*-backup*`.
```

---

## Step 4 — Author project-specific helper skills

These are not part of the SDD core, but they make `/plan` and `/implement` dramatically more useful for *this* project.

### 4.1 `/slide-spec` — `.claude/skills/slide-spec/SKILL.md`

```markdown
---
name: slide-spec
description: Translates a freeform content brief (text the end-user pasted) into a structured, slide-by-slide outline (title, bullets, speaker notes, layout hint) used as input to the PPT renderer. Use when designing or debugging the content→slides transformation.
version: 0.1.0
---

# /slide-spec

Given a piece of content, produce a structured outline:

```yaml
deck_title: <string>
audience: <string>
tone: <executive | technical | sales | training>
slides:
  - position: 1
    layout_hint: title          # or section_header | content | two_column | image_focus | closing
    title: <string>
    bullets: [<string>, ...]    # 0–5 bullets
    speaker_notes: <string>
    placeholder_hints:
      image: <description or null>
      chart: <type or null>
```

## Rules
- 1 idea per slide; if a slide has >5 bullets, split it.
- Keep titles ≤ 60 chars.
- Speaker notes are 1–3 sentences — not a re-statement of bullets.
- Map `layout_hint` to layouts that exist in the target template (check via `/template-audit` if unsure).
- Output the YAML only; no prose preamble. The renderer in `backend/utils/ppt_generator.py` consumes it directly.
```

### 4.2 `/template-audit` — `.claude/skills/template-audit/SKILL.md`

```markdown
---
name: template-audit
description: Inspects a .pptx template file (e.g. NMS_Corporate_01.pptx, Sales_Template-Blue.pptx) and reports its slide layouts, placeholder indices, fonts, and color theme. Use when planning template-touching features or debugging rendering bugs.
version: 0.1.0
---

# /template-audit

## Steps
1. Ask which `.pptx` file to audit if not supplied. Default to scanning these:
   - `./NMS_Corporate_01.pptx`
   - `./Sales_Template-Blue.pptx`
   - `./Corporate_Template_Reference.pptx`
   - `backend/pptx-templates/*.pptx`
2. Run a short Python script via the Bash tool (use the project venv):
   ```bash
   cd backend && source pptenv/bin/activate && python - <<'PY'
   from pptx import Presentation
   import sys, json
   p = Presentation(sys.argv[1] if len(sys.argv) > 1 else "../NMS_Corporate_01.pptx")
   for i, layout in enumerate(p.slide_layouts):
       print(f"Layout {i}: {layout.name}")
       for ph in layout.placeholders:
           print(f"  ph idx={ph.placeholder_format.idx} type={ph.placeholder_format.type} name={ph.name}")
   PY
   ```
3. Summarize: total layouts, names, placeholder count per layout, any layouts with picture/chart placeholders.
4. Flag risks: missing common layouts (title, section, content), duplicate layout names, locked masters.

## Output
A markdown table + a short risks paragraph. Save to `specs/NNN-slug/template-audit-<filename>.md` if invoked inside a feature folder.
```

### 4.3 `/pptx-test` — `.claude/skills/pptx-test/SKILL.md`

```markdown
---
name: pptx-test
description: End-to-end smoke test for the PPT generation pipeline. Generates a synthetic content brief, runs it through the backend, and verifies the resulting .pptx opens and has the expected slide count. Use after any backend change touching app.py, ppt_generator.py, llm_service.py, or document_parser.py.
version: 0.1.0
---

# /pptx-test

## Steps
1. Confirm the backend is running (`curl http://localhost:5000/health` or whichever health route exists in `backend/app.py`). If not, ask the user to start it: `cd backend && source pptenv/bin/activate && python app.py`.
2. POST a known good payload to the generation endpoint (read `backend/app.py` to find the route — do not hardcode). Save the output to `backend/temp/pptx-test-<timestamp>.pptx`.
3. Verify with python-pptx:
   - Opens without error
   - Slide count ≥ 3
   - Each slide has a title placeholder populated
4. Report: pass/fail per check, plus the path to the generated file so the user can open it.

## Rules
- Do not commit generated test files. They live under `backend/temp/` which should be `.gitignore`d.
- If a check fails, do not auto-fix — return findings and stop.
```

---

## Step 5 — Add a Spec Template

Create `specs/_template/spec.md`:

```markdown
# Feature NNN: <Title>

**Status:** draft | approved | implemented
**Owner:** <name>
**Created:** YYYY-MM-DD

## Problem / Motivation
<Why does this need to exist? What user pain or business need?>

## User Story
As a <role>, I want <capability>, so that <outcome>.

## Behavior (EARS)
- When <trigger>, the system shall <response>.
- When <trigger>, the system shall <response>.

## Inputs
<What the user provides — content text, file, template choice, etc.>

## Outputs
<What the user gets — a .pptx, a preview, a notification.>

## Success Criteria
- [ ] <Observable, testable check>
- [ ] <Observable, testable check>

## Out of Scope
- <Explicit exclusion>
- <Explicit exclusion>

## Open Questions
- <Question for stakeholder>
```

Create `specs/_template/plan.md` and `specs/_template/tasks.md` with just the section headings from the `/plan` and `/tasks` skills above — they'll be filled by Claude when those skills run.

---

## Step 6 — Run your first SDD feature end-to-end

Pick a small, real change. Suggested first feature: **"Let the user choose the template before generating."**

```
You:  /specify
Claude: [asks clarifying questions, drafts specs/001-template-picker/spec.md]
You:  approve / refine until correct

You:  /plan
Claude: [reads app.py, ppt_generator.py, frontend/src/services/, writes plan.md]
You:  approve / refine

You:  /tasks
Claude: [writes tasks.md — likely: backend route param, service-layer accept template_id, frontend dropdown, test]
You:  approve

You:  /implement task 1
Claude: [does task 1, runs the test, stops]
You:  /implement task 2
…
```

Commit each artifact:

```bash
git add specs/001-template-picker/spec.md && git commit -m "spec(001): template picker"
git add specs/001-template-picker/plan.md && git commit -m "plan(001): template picker"
git add specs/001-template-picker/tasks.md && git commit -m "tasks(001): template picker"
# then per-task implementation commits
```

---

## Step 7 — Iterate, version, and graduate to a team workflow

Once the four-phase flow feels natural:

1. **Version skills.** Bump the `version:` in each `SKILL.md` when you change its behavior. Note the change in a one-line `# Changelog` section at the bottom of the file.
2. **Share with collaborators.** Because `.claude/` is committed, anyone who clones the repo and opens it in Claude Code gets the same skills automatically.
3. **Add CI guardrails (optional).** A GitHub Action that fails a PR if it changes `backend/` or `frontend/src/` without a corresponding `specs/NNN-*/` folder forces the team to follow the workflow.
4. **Promote good helper skills upstream.** If `/slide-spec` becomes useful in other projects, move it to `~/.claude/skills/` so it's available globally.
5. **Retire old specs.** When a feature ships, set `Status: implemented` in `spec.md`. Don't delete — the spec history is part of the project's design record.

---

## Appendix A — Skill file format reference

Every `SKILL.md` has the same shape:

```markdown
---
name: <kebab-case, must match folder name>
description: <one paragraph — used by Claude to auto-trigger; be specific about WHEN to use>
version: <semver>
---

# /<name>

<Body — Markdown instructions Claude reads when the skill activates.>
```

Tips:

- **Description is the trigger.** Mention concrete nouns from this project (`python-pptx`, `Flask route`, `.pptx`, `LangChain`) so Claude matches user requests accurately.
- **Body is a runbook.** Write it in the imperative ("Open X. Then run Y. If Z, ask.").
- **Don't put secrets in skills.** They get committed.
- **Reference real paths.** Skills age well when grounded in the actual repo layout.

---

## Appendix B — Glossary

- **SDD (Spec-Driven Development):** A workflow where every non-trivial change starts as a written specification (the "what & why"), is followed by a plan (the "how"), then a task list, then implementation. Each artifact is committed and reviewable.
- **Spec Kit:** GitHub's reference toolkit popularizing the four-phase `specify → plan → tasks → implement` flow.
- **Agent Skill:** A `SKILL.md` file under `.claude/skills/<name>/` that Claude Code loads on demand. Invokable via `/<name>`.
- **CLAUDE.md:** Always-on project context, loaded automatically when Claude Code starts in this directory.
- **EARS:** Easy Approach to Requirements Syntax. Behavior statements of the form "When <trigger>, the system shall <response>."

---

## Quick Reference Card

| You want to…                         | Run                          | Output lands in                  |
| ------------------------------------ | ---------------------------- | -------------------------------- |
| Start a new feature                  | `/specify`                   | `specs/NNN-slug/spec.md`         |
| Design the technical approach        | `/plan`                      | `specs/NNN-slug/plan.md`         |
| Break it into work items             | `/tasks`                     | `specs/NNN-slug/tasks.md`        |
| Build one task                       | `/implement task N`          | Code + test results              |
| Outline slides from a content brief  | `/slide-spec`                | Inline YAML                      |
| Inspect a `.pptx` template           | `/template-audit`            | Inline report or `specs/.../`    |
| Smoke-test the generator             | `/pptx-test`                 | `backend/temp/pptx-test-*.pptx`  |
