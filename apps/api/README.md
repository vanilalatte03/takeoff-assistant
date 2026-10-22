# Takeoff Assistant API

FastAPI backend for the PDF drawing finish takeoff assistant.

## What It Provides

- PDF upload, local file storage, and page count extraction
- PDF page text extraction and PNG rendering
- Drawing sheet number/title detection and role classification
- Sheet search by number, title, role, and page text keyword
- Editable RoomFinish extraction and manual correction APIs
- Measurement candidate generation from RoomFinish rows
- Calculation APIs for area, perimeter, wall, partition, count, custom quantities, deductions, and side multipliers
- Excel export with Summary, Details, and Review worksheets; rejected rows remain in Details for audit but are excluded from Summary and Review

## Integrity contracts

- RoomFinish rows retain their drawing file owner even without a source sheet. Startup adds this nullable column to existing SQLite databases and backfills only project-consistent sheet-backed rows. Ambiguous legacy manual rows are retained unassigned and excluded from file-scoped APIs; no PDF owner is guessed.
- Confirmed rows are read-only until an explicit `PATCH {"status":"DRAFT"}` request containing no other fields. Rejected rows cannot be restored by editing or calculating. Invalid legacy confirmed rows can still be reopened for correction.
- Calculations validate positive dimensions, finite non-negative quantities/deductions, whole counts, measurement-specific units, storage bounds, and deductions no greater than the base quantity.
- Merge requires complete, valid rows in the same assigned drawing file and project. Original row IDs, quantities, formulas, coordinates, and deductions are recorded in `coordinates_json.merge_provenance`; subsequent recalculation/manual replacement archives that record under `coordinates_json.history`.
- Calculation API inputs are stored as JSON under `coordinates_json.calculation_inputs`, alongside existing dimension evidence. Metadata-only/no-op patches preserve them. Changed values, manual geometry, or changed dimension candidates invalidate them; new dimension candidates preserve existing deductions. PATCH accepts `deductions_json: null` for manual replacement, while non-null deduction changes must use the calculation API.

## Development

Use the Python 3.11 environment in `apps/api/.venv311`.

```bash
.venv311/Scripts/python.exe -m pytest
.venv311/Scripts/python.exe -m uvicorn app.main:app --reload
```

The API stores local runtime data under the repository `data/` and `exports/` directories. Uploaded PDFs, rendered pages, SQLite databases, logs, and generated Excel files should stay out of git.
