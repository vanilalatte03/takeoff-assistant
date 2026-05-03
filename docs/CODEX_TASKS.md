# CODEX_TASKS.md

Use one task at a time. Do not ask Codex to implement the whole product in one prompt.

## Task 0: Plan and repository setup

Prompt:

```text
Read AGENTS.md, README.md, docs/MVP_SPEC.md, docs/DOMAIN_RULES.md, and docs/ACCEPTANCE_CHECKLIST.md.
Do not write application code yet.
Create a concise implementation plan for the MVP, identify risks, and propose the backend/frontend folder structure.
Then create only the minimal project skeleton files needed to start.
```

Acceptance:

- Codex summarizes scope correctly.
- It does not attempt full automation.
- It creates a clean backend/frontend skeleton.

---

## Task 1: FastAPI backend skeleton

Prompt:

```text
Implement the FastAPI backend skeleton under apps/api.
Use SQLite for persistence.
Create models or schemas for Project, DrawingFile, DrawingSheet, RoomFinish, Measurement.
Add basic health check and database initialization.
Add pytest tests for the health check and model/schema creation.
Do not implement PDF processing yet.
```

Acceptance:

- Tests pass.
- Backend starts locally.
- Data structures include formula, quantity, unit, source_sheets, status.

---

## Task 2: PDF upload and storage

Prompt:

```text
Add PDF upload support to the FastAPI backend.
Store uploaded PDFs under a local data/uploads directory.
Create DrawingFile records with original filename, stored path, page_count, created_at.
Use PyMuPDF to count pages.
Add tests using a small sample PDF fixture.
```

Acceptance:

- Upload API returns drawing_file_id and page_count.
- Invalid non-PDF upload is rejected.
- Tests pass.

---

## Task 3: Page rendering and text extraction

Prompt:

```text
For an uploaded PDF, extract text for each page and render each page to a PNG image.
Create DrawingSheet records with page_index and text_content.
Add an endpoint to fetch a page image.
Add tests that verify text extraction and image file creation.
```

Acceptance:

- Page text is stored.
- Page image endpoint works.
- Tests pass.

---

## Task 4: Sheet number and title detection

Prompt:

```text
Implement sheet detection.
Use page text to detect sheet_no and sheet_title.
First try INDEX OF DRAWINGS / SCHEDULE OF DRAWINGS pages if present.
Then fallback to title block text on each page.
Do not hard-code only AE601.
Add tests with sample text fixtures for AE101, AE401, AE402, AE601, AE405.
```

Acceptance:

- Detects sheet numbers such as AE101, AE401, AE402.
- Stores sheet_title.
- Handles unknown pages gracefully.

---

## Task 5: Sheet role classification

Prompt:

```text
Implement sheet role classification using docs/DOMAIN_RULES.md.
Add roles: FINISH_SCHEDULE, FLOOR_PLAN, ENLARGED_FLOOR_PLAN, CEILING_PLAN, PARTITION_PLAN, PARTITION_DETAIL, DOOR_SCHEDULE, WINDOW_SCHEDULE, DOOR_WINDOW_NUMBERING_PLAN, UNKNOWN.
Add unit tests for title keyword classification.
```

Acceptance:

- AE401 INTR / EXT FINISH SCHEDULE -> FINISH_SCHEDULE.
- AE101 NEW FLOOR PLAN -> FLOOR_PLAN.
- AE106 ENLARGED FLOOR PLAN -> ENLARGED_FLOOR_PLAN.
- AE103 PARTITION WALL PLAN -> PARTITION_PLAN.

---

## Task 6: Drawing sheet search API

Prompt:

```text
Add APIs to list and search drawing sheets.
Search should match sheet number, sheet title, role, and page text keyword.
Return page_index, sheet_no, sheet_title, role, and confidence/status fields.
Add tests.
```

Acceptance:

- User can search AE101, FINISH SCHEDULE, PARTITION, DOOR.
- Tests pass.

---

## Task 7: Finish schedule candidate extraction

Prompt:

```text
Implement a first-pass finish schedule extractor.
For pages classified as FINISH_SCHEDULE, parse room finish candidates with fields:
room_no, room_name, floor_code, base_code, wall_code, ceiling_code, height, source_sheet_no, confidence, status.
Start with text-block and regex based parsing. It does not need to be perfect.
Expose extracted rows through an API and allow create/update/delete.
Add tests using sample text from a finish schedule page.
```

Acceptance:

- Produces editable RoomFinish rows.
- Imperfect results are marked NEEDS_REVIEW.
- Tests pass.

---

## Task 8: Measurement candidate generation

Prompt:

```text
Generate takeoff measurement candidates from RoomFinish rows.
Floor code -> FLOOR_AREA.
Ceiling code -> CEILING_AREA.
Base code -> PERIMETER_LENGTH.
Wall code -> WALL_AREA.
Each candidate should be DRAFT, editable, and include source_sheets.
Add tests.
```

Acceptance:

- Candidates are generated but not confirmed automatically.
- Duplicate generation is avoided.

---

## Task 9: Calculation engine

Prompt:

```text
Implement a calculation engine for FLOOR_AREA, CEILING_AREA, PERIMETER_LENGTH, WALL_AREA, PARTITION_AREA, and COUNT.
Support direct numeric input, deductions, and side_multiplier.
Generate a human-readable formula string.
Round quantities to two decimal places.
Add comprehensive unit tests.
```

Acceptance:

- 4.2 * 2.7 -> 11.34 m2.
- (4.2 + 2.7) * 2 -> 13.80 m.
- 4.2 * 4.6 -> 19.32 m2.
- Deductions and side_multiplier work.

---

## Task 10: React frontend skeleton

Prompt:

```text
Create the React + TypeScript frontend under apps/web.
Implement pages for project list, PDF upload, sheet list/search, finish schedule table, and measurement list.
Use placeholder UI where backend integration is not ready.
```

Acceptance:

- Frontend builds.
- Basic navigation works.

---

## Task 11: PDF page viewer and manual measurement UI

Prompt:

```text
Implement a page image viewer with a canvas or SVG overlay.
Support scale calibration, line measurement, rectangle area measurement, polygon area measurement, and count clicks.
Store measurement geometry as JSON.
Connect measurement results to the backend calculation engine.
```

Acceptance:

- User can set scale.
- User can measure a length and area.
- Measurement is saved with coordinates_json.

---

## Task 12: Excel export

Prompt:

```text
Implement Excel export with openpyxl.
Create two worksheets: Summary and Details.
Summary groups confirmed and draft measurements by category, finish_code, and unit.
Details includes room_no, room_name, category, finish_code, measurement_type, formula, quantity, unit, source_sheets, status, memo.
Add tests that inspect the generated workbook.
```

Acceptance:

- Excel file downloads.
- Summary totals are correct.
- Details retains formulas and source sheets.

---

## Task 13: End-to-end MVP smoke test

Prompt:

```text
Add an end-to-end smoke test or documented manual test script:
1. Upload sample PDF.
2. Verify sheet list and search.
3. Verify finish schedule extraction or manual correction.
4. Generate measurement candidate.
5. Enter dimensions 4.2 and 2.7.
6. Verify formula 4.2 × 2.7 and quantity 11.34.
7. Export Excel and verify Summary and Details.
```

Acceptance:

- The test or manual script can be followed by a developer.
- MVP workflow is demonstrable.

