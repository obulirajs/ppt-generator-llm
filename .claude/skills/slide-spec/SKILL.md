---
name: slide-spec
description: Translates a freeform content brief (text the end-user pasted, document text, or a draft outline) into a structured, slide-by-slide YAML outline used as input to the PPT renderer in backend/utils/ppt_generator.py. Use when designing or debugging the content-to-slides transformation, or when authoring example inputs for tests.
version: 0.1.0
---

# /slide-spec

Given a piece of content, produce a structured outline in YAML.

## Output format
```yaml
deck_title: <string>
audience: <string>
tone: <executive | technical | sales | training>
slides:
  - position: 1
    layout_hint: title          # title | section_header | content | two_column | image_focus | closing
    title: <string>
    bullets: []                 # empty for title slides
    speaker_notes: <string>
    placeholder_hints:
      image: <description or null>
      chart: <type or null>

  - position: 2
    layout_hint: content
    title: <string>
    bullets:
      - <bullet 1>
      - <bullet 2>
    speaker_notes: <string>
    placeholder_hints:
      image: null
      chart: null
```

## Rules
- **One idea per slide.** If a slide has more than 5 bullets, split it into two slides.
- **Titles ≤ 60 characters.** If the original heading is longer, shorten while preserving meaning.
- **Speaker notes are 1–3 sentences.** Not a restatement of bullets — provide context, framing, or a transition cue.
- **`layout_hint` must map to layouts that exist in the target template.** If unsure which layouts are available, invoke `/template-audit` first on the active template.
- **Output the YAML only.** No prose preamble, no closing commentary. The renderer in `backend/utils/ppt_generator.py` consumes the YAML directly.
- **Match the tone to the presentation type.** Executive for reports/business reviews; sales for pitches/proposals; technical for pre-sales; training for case studies / client success.

## When to use
- Designing a new presentation type and need a reference structure.
- Debugging "the deck looks wrong" — produce the expected structure, then compare to what the LLM actually generated.
- Building test fixtures for `backend/test_api.py`.

## Optional inputs the user may provide
- **Target template name** — affects available `layout_hint` values.
- **Desired slide count** — cap the output. If absent, choose the natural length (typically 7–15 for a substantive brief).
- **Target presentation type** — `report | pitch | business_review | client_success | case_study | presales | proposal`. Use this to inform tone, structure, and section ordering (see `backend/config.py` PRESENTATION_TYPES).