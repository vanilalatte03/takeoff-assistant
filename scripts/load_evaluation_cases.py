#!/usr/bin/env python3
"""Read reviewed evaluation cases without changing the source workbook.

Review records attest to human/synthetic review; this is not a truth calculator.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from validate_example_dataset import (
    REQUIRED_SHEETS, SOURCE_HEADERS, TAKEOFF_HEADERS, MEASUREMENT_TYPES,
    EXCEPTION_HEADERS, VALIDATION_HEADERS,
    _header_issues, _records,
)


@dataclass(frozen=True)
class CaseSelection:
    cases: list[dict[str, Any]]
    excluded: list[dict[str, Any]]


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _ids(value: Any) -> list[str]:
    if not isinstance(value, str):
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(_text(item) for item in value) and len(set(value)) == len(value)


def _json_container(value: Any, *, nonempty: bool = False) -> bool:
    try:
        parsed = json.loads(str(value), object_pairs_hook=_unique_object,
                            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        return isinstance(parsed, (dict, list)) and (bool(parsed) or not nonempty)
    except (ValueError, TypeError):
        return False


def _review_reasons(review: Any, origin: str, source_ids: set[str], row: dict) -> list[str]:
    if not isinstance(review, dict) or review.get("status") != "REVIEWED":
        return ["scope_not_reviewed"]
    reasons = []
    if not _text(review.get("reviewer")):
        reasons.append("reviewer_missing")
    reviewed_on = review.get("reviewed_on")
    try:
        if not isinstance(reviewed_on, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", reviewed_on):
            raise ValueError()
        if date.fromisoformat(reviewed_on) > date.today():
            raise ValueError()
    except ValueError:
        reasons.append("review_date_invalid")
    if review.get("origin") != origin:
        reasons.append("review_origin_mismatch")
    if review.get("unresolved_exceptions") != []:
        reasons.append("exceptions_unresolved_or_missing")
    if _text(row.get("exception_tags")) and not _text(review.get("exception_resolution")):
        reasons.append("exception_resolution_missing")
    evidence = review.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        reasons.append("evidence_missing")
    elif any(not isinstance(item, dict) or not _text(item.get("source_id")) or item["source_id"] not in source_ids
             or not _text(item.get("locator")) for item in evidence):
        reasons.append("evidence_invalid")
    return reasons


def load_evaluation_cases(workbook_path: Path, review_path: Path, *, scope: str) -> CaseSelection:
    """Select one independently reviewed scope: retrieval or quantity.

    Workbook/schema/hash errors are fatal. Individual incomplete cases are excluded
    with stable reason codes. No workbook, sidecar, or application state is written.
    """
    if scope not in {"retrieval", "quantity"}:
        raise ValueError("scope must be retrieval or quantity")
    raw = workbook_path.read_bytes()
    metadata = json.loads(review_path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    if not isinstance(metadata, dict) or type(metadata.get("schema_version")) is not int or metadata["schema_version"] != 1:
        raise ValueError("unsupported review schema")
    if metadata.get("workbook_sha256") != hashlib.sha256(raw).hexdigest():
        raise ValueError("workbook hash mismatch; review the changed workbook again")
    origin = metadata.get("origin")
    if origin not in ("synthetic", "practitioner") or not isinstance(metadata.get("rows"), dict):
        raise ValueError("invalid review origin or rows")
    workbook = load_workbook(io.BytesIO(raw), data_only=False)
    try:
        if any(name not in workbook.sheetnames for name in REQUIRED_SHEETS):
            raise ValueError("required workbook sheet missing")
        for sheet, headers in (("TakeoffRows", TAKEOFF_HEADERS), ("Sources", SOURCE_HEADERS),
                               ("Exceptions", EXCEPTION_HEADERS), ("Validation", VALIDATION_HEADERS)):
            if _header_issues(workbook[sheet], headers):
                raise ValueError(f"{sheet} header mismatch")
        rows = _records(workbook["TakeoffRows"], TAKEOFF_HEADERS)
        sources = [record for _, record in _records(workbook["Sources"], SOURCE_HEADERS)]
    finally:
        workbook.close()
    source_counts = Counter(str(source.get("source_id", "")).strip() for source in sources)
    source_map = {source["source_id"]: source for source in sources if _text(source.get("source_id"))}
    row_counts = Counter(str(row.get("row_id", "")).strip() for _, row in rows)
    selected, excluded = [], []
    for row_number, row in rows:
        row_id = row.get("row_id")
        reasons = []
        if not _text(row_id):
            reasons.append("row_id_missing")
        elif row_counts[row_id.strip()] != 1:
            reasons.append("row_id_duplicate")
        source_sheet_nos = _ids(row.get("source_sheets"))
        if not source_sheet_nos:
            reasons.append("source_sheets_missing")
        known_sheets = {source.get("sheet_no") for source in sources}
        if any(sheet not in known_sheets for sheet in source_sheet_nos):
            reasons.append("source_sheet_unknown")
        row_review = metadata["rows"].get(row_id) if isinstance(row_id, str) else None
        review = row_review.get(scope) if isinstance(row_review, dict) else None
        reasons.extend(_review_reasons(review, origin, set(source_map), row))
        if isinstance(review, dict) and not reasons:
            evidence_ids = {item["source_id"] for item in review["evidence"]}
            if any(source_counts[source_id] != 1 for source_id in evidence_ids):
                reasons.append("source_id_duplicate")
            if any(not _text(source_map[source_id].get("sheet_title"))
                   or not _text(source_map[source_id].get("sheet_no"))
                   or type(source_map[source_id].get("page_index")) is not int
                   or source_map[source_id]["page_index"] < 0 for source_id in evidence_ids):
                reasons.append("source_metadata_invalid")
            if scope == "retrieval":
                expected = review.get("expected_source_ids")
                if not _string_list(expected) or not expected or not set(expected).issubset(evidence_ids):
                    reasons.append("retrieval_truth_missing_or_unreferenced")
            else:
                evidence_sheets = {source_map[source_id]["sheet_no"] for source_id in evidence_ids}
                if not set(source_sheet_nos).issubset(evidence_sheets):
                    reasons.append("quantity_sources_not_covered")
        if scope == "quantity":
            if row.get("status") != "CONFIRMED":
                reasons.append("quantity_not_confirmed")
            measurement_type = row.get("measurement_type")
            expected_unit = "EA" if measurement_type == "COUNT" else "m" if measurement_type == "PERIMETER_LENGTH" else "m2"
            if measurement_type not in MEASUREMENT_TYPES or row.get("unit") != expected_unit:
                reasons.append("quantity_type_or_unit_invalid")
            try:
                value = Decimal(str(row.get("quantity")))
                if not value.is_finite() or value < 0 or isinstance(row.get("quantity"), bool):
                    raise ValueError()
            except (InvalidOperation, ValueError):
                reasons.append("quantity_missing_or_invalid")
            if not all(_text(row.get(field)) for field in ("formula", "category", "finish_code")):
                reasons.append("quantity_fields_missing")
            if not _json_container(row.get("evidence_json"), nonempty=True):
                reasons.append("quantity_evidence_invalid")
            if not _json_container(row.get("deductions_json")):
                reasons.append("quantity_deductions_invalid")
        if reasons:
            excluded.append({"row_id": row_id, "row_number": row_number, "scope": scope, "reasons": reasons})
        else:
            selected.append({"row": row, "review": review, "origin": origin,
                             "sources": [source_map[item["source_id"]] for item in review["evidence"]]})
    return CaseSelection(selected, excluded)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("reviews", type=Path)
    parser.add_argument("--scope", choices=("retrieval", "quantity"), required=True)
    args = parser.parse_args(argv)
    try:
        selection = load_evaluation_cases(args.workbook, args.reviews, scope=args.scope)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    # Only identifiers/reasons are printed. Full local rows are available to importers.
    print(json.dumps({"scope": args.scope, "selected_row_ids": [item["row"]["row_id"] for item in selection.cases],
                      "excluded": selection.excluded}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
