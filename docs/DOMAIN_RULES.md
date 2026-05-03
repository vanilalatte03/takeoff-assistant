# DOMAIN_RULES.md

## Drawing workflow assumptions

Typical workflow:

```text
finish schedule -> floor plan / reflected ceiling plan -> partition plan/details -> quantity table
```

Known examples:

```text
Ceiling area: finish schedule + reflected ceiling plan or floor plan
Floor area: finish schedule + floor plan
Wall finish: finish schedule + floor plan or partition plan
Partition: partition plan + partition detail
Door/window count: numbering plan + schedule
```

Do not hard-code a specific sheet number for a role. Examples:

- Finish schedule may be AE401, AE402, AE601, or another sheet.
- Floor plan may be AE101 or another sheet.
- Partition plan/details may be AE102, AE103, AE405, AE406, AE407, etc.

## Sheet role classification

Suggested role detection by title keywords:

```text
FINISH_SCHEDULE:
  contains FINISH SCHEDULE, INTR / EXT FINISH SCHEDULE, INTERIOR FINISH SCHEDULE, EXTERIOR & INTERIOR FINISH SCHEDULE

FLOOR_PLAN:
  contains FLOOR PLAN and not REMOVAL, not DEMOLITION, not ENLARGED, not PARTITION

ENLARGED_FLOOR_PLAN:
  contains ENLARGED FLOOR PLAN

CEILING_PLAN:
  contains REFLECTED CEILING PLAN or CEILING PLAN

PARTITION_PLAN:
  contains PARTITION and PLAN

PARTITION_DETAIL:
  contains PARTITION and DETAIL

DOOR_SCHEDULE:
  contains DOOR SCHEDULE

WINDOW_SCHEDULE:
  contains WINDOW SCHEDULE or LOUVER SCHEDULE

DOOR_WINDOW_NUMBERING_PLAN:
  contains DOOR/WINDOW and NUMBERING PLAN
```

## Measurement categories

```text
FLOOR_AREA
CEILING_AREA
PERIMETER_LENGTH
WALL_AREA
PARTITION_AREA
COUNT
```

## Calculation formulas

### FLOOR_AREA

Inputs:

- width and depth, or polygon area
- deductions optional

Formula:

```text
quantity = base_area - sum(deductions)
unit = m2
```

### CEILING_AREA

Inputs:

- width and depth, or polygon area
- deductions optional

Formula:

```text
quantity = base_area - sum(deductions)
unit = m2
```

### PERIMETER_LENGTH

Inputs:

- width and depth, or selected polyline length
- deductions optional

Formula:

```text
quantity = base_perimeter - sum(deductions)
unit = m
```

### WALL_AREA

Inputs:

- wall_length
- wall_height
- deductions optional

Formula:

```text
quantity = wall_length * wall_height - sum(deductions)
unit = m2
```

### PARTITION_AREA

Inputs:

- wall_length
- wall_height
- side_multiplier
- deductions optional

Formula:

```text
quantity = wall_length * wall_height * side_multiplier - sum(deductions)
unit = m2
```

Known convention:

- GWB often uses both sides: side_multiplier = 2.
- Other items often use one side: side_multiplier = 1.
- This must be editable.

### COUNT

Inputs:

- count

Formula:

```text
quantity = count
unit = EA
```

## Rounding

Round quantities to two decimal places.

## Review status

Use these statuses:

```text
DRAFT
NEEDS_REVIEW
CONFIRMED
REJECTED
```

Default extraction results should be DRAFT or NEEDS_REVIEW, not CONFIRMED.

## Source traceability

Every measurement must store source sheets, for example:

```text
AE401, AE101
AE601, AE103
AE405, AE406
```

## Data extraction confidence

Any extracted field should be editable and may include confidence metadata.

Suggested confidence fields:

- sheet_detection_confidence
- room_finish_confidence
- measurement_confidence

## Units

Use metric output:

- m2 for area
- m for length
- EA for count

Display square meters as `m²` in UI and Excel if possible, but store normalized unit as `m2`.

