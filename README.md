# Takeoff Assistant MVP

A personal-use web application for architectural finish quantity takeoff from PDF drawing sets.

The application helps a user:

1. Upload a drawing PDF.
2. Extract and search drawing sheet numbers and titles.
3. Detect finish schedule pages.
4. Extract room finish candidates.
5. Generate takeoff candidate rows.
6. Enter or manually measure dimensions on drawing images.
7. Calculate area, length, wall area, partition area, and count quantities.
8. Export an Excel workbook with Summary and Details sheets.

## Product principle

The system creates an **automatic draft**. The user verifies and corrects it before export.

Do not design the MVP as a fully automatic estimating system.

## Recommended stack

- Backend: FastAPI, SQLite, PyMuPDF, openpyxl
- Frontend: React, TypeScript, canvas/SVG overlay
- Storage: local filesystem for PDF and rendered page images

## Repository layout

```text
apps/
  api/        FastAPI backend
  web/        React frontend
docs/
  MVP_SPEC.md
  DOMAIN_RULES.md
  CODEX_TASKS.md
  ACCEPTANCE_CHECKLIST.md
  SAMPLE_DATA_GUIDE.md
data/
  samples/   Put sample PDFs here. Do not commit confidential files to a public repo.
exports/      Generated Excel files, ignored by git
```

## First sample target

Use the attached drawing PDF supplied by the user as the first validation sample. The first goal is not perfect extraction. The first goal is a usable workflow with editable extracted data.

## How to work with Codex

1. Put these files in a private GitHub repository or local repo.
2. Copy sample PDFs into `data/samples/`.
3. Open the repository in Codex.
4. Ask Codex to read `AGENTS.md`, `docs/MVP_SPEC.md`, and `docs/CODEX_TASKS.md` first.
5. Give Codex one task at a time from `docs/CODEX_TASKS.md`.
6. After every task, ask for tests and a short diff summary.

