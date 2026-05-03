# AGENTS.md

## Project identity

This repository implements a personal-use **PDF drawing based finish quantity takeoff assistant**.
It is not intended to replace professional takeoff or estimating products. The goal is to reduce manual page navigation, repeated spreadsheet entry, and arithmetic mistakes for architectural finish takeoff work.

The product principle is:

> Generate an automatic draft from a drawing PDF, then let the user verify, correct, measure, and export.

Never assume the system can produce a fully correct takeoff without user review.

## MVP scope

Implement the MVP in this order:

1. PDF upload and local storage.
2. Render PDF pages as images for viewing.
3. Extract text from each page.
4. Detect sheet numbers and sheet titles.
5. Classify sheet roles such as FINISH_SCHEDULE, FLOOR_PLAN, ENLARGED_FLOOR_PLAN, PARTITION_PLAN, PARTITION_DETAIL, DOOR_SCHEDULE, WINDOW_SCHEDULE, UNKNOWN.
6. Detect finish schedule pages and extract editable room finish candidates.
7. Generate measurement candidates from room finish data.
8. Allow user input and manual measurement on PDF page images.
9. Calculate quantities and formulas.
10. Export Summary and Details sheets to Excel.

## Explicit non-goals for the MVP

Do not implement these in the first MVP unless explicitly requested later:

- Fully automatic takeoff from PDF upload.
- Automatic room boundary recognition.
- Automatic dimension-line reading.
- Automatic door/window deduction.
- Automatic support for all trades.
- XCost integration.
- Production-grade OCR for scanned PDFs.

## Domain rules

Known workflow from user research:

- A typical takeoff line uses about three drawings.
- Room numbers are checked from a finish schedule sheet.
- Room dimensions usually come from floor plans such as AE101.
- If room dimensions are not shown, the user may measure by scale.
- Final output should be organized by finish code, not primarily by room.
- The output must keep formulas and drawing source sheets.
- Quantity rounding: two decimal places.

Known calculation patterns:

- Floor area = width * height_or_depth, or polygon area.
- Ceiling area = width * height_or_depth, or polygon area.
- Perimeter length = selected boundary length or (width + depth) * 2.
- Wall finish area = wall length * wall height - deductions.
- Partition area = wall length * wall height * side multiplier - deductions.
- Count quantity = clicked count.

Known exception patterns:

- Ceiling area may need deductions for columns, walls, and openings.
- Floor area may need deductions for fixed furniture, equipment, or wall thickness.
- Wall finish area may need door/window deductions.
- GWB partition may be counted on both sides; other items are usually one side unless configured otherwise.
- Wall height can vary by room.
- Toilet wall tile may use a partial height, not full wall height.

## Technical direction

Preferred MVP stack:

- Backend: Python FastAPI.
- Database: SQLite for MVP.
- PDF processing: PyMuPDF.
- Table/text extraction: start with PyMuPDF text blocks; optionally use pdfplumber if needed.
- Excel export: openpyxl.
- Frontend: React + TypeScript.
- PDF page viewer: rendered page image from backend + canvas/SVG overlay for measurements.

Prefer simple, testable, local-first architecture over complex cloud infrastructure.

## Data model principles

Every computed quantity must store:

- project_id
- room_no, if applicable
- room_name, if applicable
- category
- finish_code
- measurement_type
- formula
- quantity
- unit
- source_sheets
- status: DRAFT, NEEDS_REVIEW, CONFIRMED
- memo
- coordinates_json, if measured on a drawing
- deductions_json, if deductions are applied

## Quality bar

For every feature:

- Add or update tests.
- Keep functions small and deterministic where possible.
- Do not silently discard extraction failures. Return confidence and status.
- Any AI/OCR/extraction result must be editable by the user.
- Prefer explicit statuses such as NEEDS_REVIEW over hidden assumptions.
- Do not hard-code only AE601. Finish schedules can be AE401, AE402, AE601, or other sheet numbers. Detect by sheet title/role, not by sheet number alone.

## Acceptance test philosophy

The MVP should work with sample architectural drawing PDFs where:

- An index sheet lists drawing numbers and names.
- Finish schedule sheets include columns such as RM NOS, ROOM NAMES, FLOOR, BASE, INTERIOR WALL, CEILING, HGT, REMARKS.
- Floor plan sheets include room numbers and room names.
- Enlarged floor plans include more detailed dimensions.

## Output Excel structure

Create at least two worksheets:

1. Summary
   - category
   - finish_code
   - description
   - unit
   - total_quantity
   - source_sheets

2. Details
   - no
   - room_no
   - room_name
   - category
   - finish_code
   - measurement_type
   - formula
   - quantity
   - unit
   - source_sheets
   - status
   - memo

