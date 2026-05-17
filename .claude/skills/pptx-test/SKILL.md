---
name: pptx-test
description: End-to-end smoke test for the PPT generation pipeline. Generates a synthetic content brief, runs it through the Flask backend, and verifies the resulting .pptx opens and has the expected slide count. Use after any backend change touching app.py, ppt_generator.py, llm_service.py, document_parser.py, or db_manager.py.
version: 0.1.0
---

# /pptx-test

## Steps

1. **Confirm the backend is running.** Run:
   ```bash
   curl -s http://localhost:5000/api/health
   ```
   - If the response shows `"status": "healthy"` or `"degraded"` (with Ollama issue), proceed.
   - If it fails to connect, ask the user to start the backend:
     ```bash
     cd backend && source pptenv/bin/activate && python app.py
     ```

2. **POST a known-good payload** to the generation endpoint. Read `backend/app.py` to find the exact route (typically `/api/generate-ppt`). Use a representative text payload:
   ```bash
   curl -s -X POST http://localhost:5000/api/generate-ppt \
     -F "text=Q4 2024 Performance Review

   Executive Summary: Revenue grew 23% YoY to \$4.2M. We exceeded targets in three of four key metrics.

   Key Findings: Customer acquisition up 15%. Retention at 92%. Average deal size increased to \$28K. Operating margin improved to 18%.

   Challenges: Supply chain delays added 5 days to delivery. Support ticket resolution slowed to 48 hours.

   Recommendations: Invest \$500K in infrastructure. Hire 10 support staff. Establish secondary suppliers.

   Next Steps: Finalize Q1 2025 budget by Jan 15. Launch customer success program Feb 1." \
     -F "model=llama3.2" \
     -F "auto_detect_type=true"
   ```

3. **Capture the response.** Extract `filename` and `slide_count` from the JSON response. Note the path: generated files land in `backend/temp/`.

4. **Verify the output** with a short python-pptx check:
   ```bash
   cd backend && source pptenv/bin/activate && python - <<PY
   from pptx import Presentation
   import sys, os
   
   filename = "$FILENAME"  # substitute from step 3
   path = f"temp/{filename}"
   
   assert os.path.exists(path), f"File not found: {path}"
   
   p = Presentation(path)
   slide_count = len(p.slides)
   
   assert slide_count >= 3, f"Expected ≥3 slides, got {slide_count}"
   
   for i, slide in enumerate(p.slides):
       title = slide.shapes.title.text if slide.shapes.title else None
       assert title, f"Slide {i+1} missing title"
       print(f"  Slide {i+1}: {title}")
   
   print(f"\n✅ PASS — {slide_count} slides, all have titles")
   PY
   ```

5. **Report results:**
   - Pass/fail per check
   - Path to the generated file so the user can open it manually
   - Detected presentation type and confidence score (from the API response)
   - Total processing time

## Rules
- **Do not commit generated test files.** They live under `backend/temp/` and should be `.gitignore`d.
- **If a check fails, do not auto-fix.** Return findings and stop. The user decides what to do.
- **Don't run this against the user's real templates or content unless explicitly asked.** Use the synthetic payload above by default.
- **If the backend is unreachable after 2 retries**, give up and tell the user clearly.
- **Detected type matters.** If `detected_type` is `null` or wildly wrong for the test payload, flag it — that's a regression even if the file is valid.