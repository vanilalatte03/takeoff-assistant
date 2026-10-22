# Takeoff Assistant Web

React + TypeScript frontend for the PDF drawing finish takeoff assistant.

## Current Screens

- PDF upload and processing controls
- Drawing sheet list/search and page detail viewer
- Rendered PDF page viewer with manual scale, length, rectangle area, and polygon area measurement
- Room Finish review table with manual add/edit flow
- Measurement list, calculation input panel, status confirmation, filtering, and Excel download

## Development

Use Node.js 24 LTS (the test runner also supports Node `^22.12.0 || ^24.0.0 || >=26.0.0`).

```bash
npm ci
npm test
npm run build
npm run dev
```

The Vite dev server proxies `/api` to `http://localhost:8000`. Start the API server before testing integrated workflows.

The DOM interaction tests cover calculation input/deduction restoration, page changes and stale requests, compatible measurement targets, and explicit reopening of confirmed rows. They do not replace real drawing accuracy review.

Saving new manual geometry keeps notes, source sheets, dimension-assist and merge provenance, and clears obsolete calculation inputs and deductions. Confirmed rows must be reopened with **재검토 시작** before editing; rejected rows are read-only.
