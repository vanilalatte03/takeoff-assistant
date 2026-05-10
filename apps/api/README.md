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
- Excel export with Summary and Details worksheets

## Development

Use the Python 3.11 environment in `apps/api/.venv311`.

```bash
.venv311/Scripts/python.exe -m pytest
.venv311/Scripts/python.exe -m uvicorn app.main:app --reload
```

The API stores local runtime data under the repository `data/` and `exports/` directories. Uploaded PDFs, rendered pages, SQLite databases, logs, and generated Excel files should stay out of git.
