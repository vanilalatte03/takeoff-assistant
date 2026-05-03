# ACCEPTANCE_CHECKLIST.md

## Product acceptance

- [ ] User can upload a PDF.
- [ ] User can see page count.
- [ ] User can view rendered page images.
- [ ] User can search sheets by sheet number.
- [ ] User can search sheets by keyword.
- [ ] System extracts sheet number and sheet title for common architectural pages.
- [ ] System classifies finish schedule pages.
- [ ] System does not depend only on AE601 for finish schedule detection.
- [ ] System extracts editable room finish candidates.
- [ ] User can manually correct room finish rows.
- [ ] System generates draft measurement candidates.
- [ ] User can enter dimensions directly.
- [ ] User can set scale and measure length/area on page image.
- [ ] Calculation engine saves formula, quantity, unit, source_sheets, and status.
- [ ] Quantities are rounded to two decimal places.
- [ ] User can apply deductions.
- [ ] User can set side multiplier for partition/wall work.
- [ ] User can export Excel.
- [ ] Excel has Summary sheet.
- [ ] Excel has Details sheet.
- [ ] Summary groups by finish code and category.
- [ ] Details keeps room, formula, quantity, status, and source sheets.

## Technical acceptance

- [ ] Backend tests pass.
- [ ] Frontend builds.
- [ ] No confidential sample PDF is committed to a public repo.
- [ ] Extraction failures produce NEEDS_REVIEW rather than silent success.
- [ ] All extracted data is editable.
- [ ] All computed quantities are traceable to source sheets.

## Sample validation cases

- [ ] Direct floor/ceiling area: 4.2 * 2.7 = 11.34 m2.
- [ ] Perimeter: (4.2 + 2.7) * 2 = 13.80 m.
- [ ] Wall/partition area: 4.2 * 4.6 = 19.32 m2.
- [ ] Deduction: 20.00 - 1.89 = 18.11 m2.
- [ ] GWB two-sided partition: 4.2 * 4.6 * 2 = 38.64 m2.

