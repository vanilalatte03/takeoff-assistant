# SAMPLE_DATA_GUIDE.md

## Where to put sample files

Place sample PDFs under:

```text
data/samples/
```

Do not commit confidential, client-owned, government, or proprietary drawings to a public repository.
Use a private repository or keep sample PDFs out of git.

Suggested `.gitignore` entry:

```text
data/samples/*.pdf
data/uploads/
exports/
```

## First sample goals

For the first architectural PDF sample, verify:

1. Index/schedule of drawings is detected.
2. Sheet numbers and sheet titles are detected.
3. Architectural pages can be found, especially floor plan, partition plan/detail, and finish schedule pages.
4. Finish schedule text produces editable RoomFinish rows.
5. User can create measurement rows even if extraction is imperfect.

## Example expected architectural sheets

The sample drawing set may contain sheets similar to:

```text
AE101 NEW FLOOR PLAN
AE102 PARTITION WALL DETAILS - 1
AE103 PARTITION WALL PLAN - 1
AE106 ENLARGED FLOOR PLAN - 1
AE107 ENLARGED FLOOR PLAN - 2
AE401 INTR / EXT FINISH SCHEDULE
AE402 INTR / EXT FINISH SCHEDULE
AE405 DOOR / WINDOW SCHEDULE
```

A different PDF may use:

```text
AE101 FLOOR PLAN
AE103 REFLECTED CEILING PLAN
AE405 FLOOR PARTITION TYPE KEY PLAN
AE406 PARTITION TYPE DETAILS-1
AE601 EXTERIOR & INTERIOR FINISH SCHEDULE
AE605 DOOR/WINDOW AND LOUVER NUMBERING PLAN
AE606 DOOR SCHEDULE
```

The program must detect by role/title, not fixed sheet number.

## Manual validation example

Create a measurement row:

```text
room_no: 110
category: Ceiling
finish_code: ACST or GWB
measurement_type: CEILING_AREA
source_sheets: AE401, AE101 or AE601, AE103
formula: 4.2 × 2.7
quantity: 11.34
unit: m2
status: CONFIRMED
```

