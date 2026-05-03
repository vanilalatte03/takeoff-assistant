# MVP_SPEC.md

## MVP name

PDF Drawing Finish Takeoff Assistant

## User

A single personal user who manually performs architectural finish takeoff from PDF drawing sets and spreadsheets.

## Problem

The current workflow requires repeatedly moving across PDF pages, checking drawing numbers, finding room numbers, reading finish schedules, locating dimensions on floor plans, calculating quantities, and entering results into Excel.

The program should reduce:

- page navigation time
- manual spreadsheet entry
- repeated arithmetic
- missed or duplicated takeoff lines
- loss of drawing-source traceability

## MVP outcome

Given a PDF drawing set, the user should be able to:

1. Upload the PDF.
2. See an indexed list of sheets with sheet number, title, and role.
3. Search sheets by number or keyword.
4. Find finish schedule sheets.
5. Extract or manually edit room finish rows.
6. Generate draft takeoff rows by room and finish category.
7. Enter dimensions or measure dimensions on the drawing image.
8. Apply deductions and side multipliers when needed.
9. Save each computed quantity with formula and source sheets.
10. Export an Excel workbook with Summary and Details sheets.

## User flow

### 1. Upload PDF

User uploads a PDF drawing set.

Backend stores:

- original file
- page count
- page text
- rendered page images
- extracted sheet metadata

### 2. Sheet index

System displays sheets such as:

```text
AE101 NEW FLOOR PLAN
AE102 PARTITION WALL DETAILS - 1
AE103 PARTITION WALL PLAN - 1
AE401 INTR / EXT FINISH SCHEDULE
AE402 INTR / EXT FINISH SCHEDULE
AE405 DOOR / WINDOW SCHEDULE
```

Sheet roles are classified by title keywords, not fixed sheet numbers.

### 3. Finish schedule extraction

For pages classified as FINISH_SCHEDULE, extract editable rows with fields:

- room_no
- room_name
- floor_material
- floor_finish
- base_material
- base_finish
- wall_material
- wall_finish
- ceiling_material
- ceiling_finish
- height
- remarks
- source_sheet_no
- confidence

If extraction is incomplete, mark rows NEEDS_REVIEW.

### 4. Takeoff candidate generation

From each room finish row, generate candidate measurement rows:

- Floor finish -> FLOOR_AREA
- Ceiling finish -> CEILING_AREA
- Base finish -> PERIMETER_LENGTH
- Wall finish -> WALL_AREA
- Partition code -> PARTITION_AREA

The user can delete, merge, or edit candidates.

### 5. Measurement

The user can supply dimensions by:

- direct numeric input
- rectangular measurement on page image
- polyline length measurement
- polygon area measurement
- clicked count

The system stores measurement geometry in JSON.

### 6. Calculation

Calculation engine produces:

- formula string
- quantity
- unit
- status

Round quantities to two decimal places.

### 7. Excel export

Export two sheets:

- Summary: grouped by category, finish_code, unit.
- Details: all takeoff rows with formulas, source sheets, and review status.

## MVP exclusions

Do not implement in the MVP:

- automatic room boundary recognition
- automatic dimension-line reading
- automatic deduction detection
- full OCR pipeline for scanned PDFs
- XCost import/export
- multi-user permissions
- cloud deployment

## Success criteria

The MVP is successful when:

1. A sample drawing PDF can be uploaded.
2. Sheet list is extracted and searchable.
3. Finish schedule pages are detected.
4. Room finish candidates are displayed and editable.
5. User can create/confirm measurement rows with formula and quantity.
6. User can export Summary and Details Excel workbook.
7. Every computed quantity keeps source sheet numbers.

