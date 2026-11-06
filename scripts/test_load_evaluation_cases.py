import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from create_example_dataset_template import build_workbook
from load_evaluation_cases import load_evaluation_cases, main
from validate_example_dataset import SOURCE_HEADERS, TAKEOFF_HEADERS, validate_workbook


@pytest.fixture
def dataset(tmp_path):
    fixture = json.loads((Path(__file__).parent / "fixtures/verified_evaluation_cases.json").read_text(encoding="utf-8"))
    workbook = build_workbook()
    for source in fixture["sources"]:
        workbook["Sources"].append([source.get(header) for header in SOURCE_HEADERS])
    reviews = {"schema_version": 1, "origin": fixture["origin"], "rows": {}}
    for case in fixture["cases"]:
        row = fixture["row_defaults"] | case["row"]
        workbook["TakeoffRows"].append([row.get(header) for header in TAKEOFF_HEADERS])
        reviews["rows"][row["row_id"]] = {
            scope: copy.deepcopy(fixture["review_defaults"] | case.get("review", {}) | case.get(f"{scope}_review", {}))
            for scope in ("retrieval", "quantity")
        }
    path = tmp_path / "synthetic.xlsx"
    workbook.save(path)
    review_path = tmp_path / "reviews.json"
    _save_reviews(path, review_path, reviews)
    return path, review_path, reviews


def _save_reviews(path, review_path, reviews):
    reviews["workbook_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    review_path.write_text(json.dumps(reviews), encoding="utf-8")


def test_scope_separation_and_failure_cases(dataset):
    path, sidecar, _ = dataset
    original = path.read_bytes()
    quantity = load_evaluation_cases(path, sidecar, scope="quantity")
    assert [case["row"]["row_id"] for case in quantity.cases] == ["SYN-OK", "SYN-MULTI"]
    reasons = {case["row_id"]: case["reasons"] for case in quantity.excluded}
    assert "quantity_missing_or_invalid" in reasons["SYN-MISSING-QUANTITY"]
    assert "quantity_type_or_unit_invalid" in reasons["SYN-UNIT-CONFLICT"]
    assert "exceptions_unresolved_or_missing" in reasons["SYN-DEDUCTION-ERROR"]
    assert "scope_not_reviewed" in reasons["SYN-UNREVIEWED"]
    retrieval = load_evaluation_cases(path, sidecar, scope="retrieval")
    assert len(retrieval.cases) == 5
    assert all(case["origin"] == "synthetic" for case in retrieval.cases)
    assert len(quantity.cases[1]["sources"]) == 2
    assert path.read_bytes() == original


@pytest.mark.parametrize(("field", "value", "reason"), [
    ("reviewer", "", "reviewer_missing"),
    ("reviewed_on", "2026-02-30", "review_date_invalid"),
    ("reviewed_on", "2999-01-01", "review_date_invalid"),
    ("reviewed_on", "20261106", "review_date_invalid"),
    ("origin", "practitioner", "review_origin_mismatch"),
    ("evidence", [], "evidence_missing"),
    ("evidence", [{"source_id": "NO-SOURCE", "locator": "x"}], "evidence_invalid"),
    ("evidence", [{"source_id": [], "locator": "x"}], "evidence_invalid"),
    ("evidence", [{"source_id": "PLAN", "locator": ""}], "evidence_invalid"),
    ("unresolved_exceptions", None, "exceptions_unresolved_or_missing"),
    ("expected_source_ids", ["SCHEDULE"], "retrieval_truth_missing_or_unreferenced"),
])
def test_incomplete_review_is_excluded(dataset, field, value, reason):
    path, sidecar, reviews = dataset
    reviews["rows"]["SYN-OK"]["retrieval"][field] = value
    _save_reviews(path, sidecar, reviews)
    selection = load_evaluation_cases(path, sidecar, scope="retrieval")
    assert reason in next(item for item in selection.excluded if item["row_id"] == "SYN-OK")["reasons"]


def test_workbook_hash_prevents_stale_review(dataset):
    path, sidecar, _ = dataset
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_evaluation_cases(path, sidecar, scope="quantity")


def test_duplicate_review_keys_are_rejected(dataset):
    path, sidecar, _ = dataset
    sidecar.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        load_evaluation_cases(path, sidecar, scope="quantity")


@pytest.mark.parametrize(("column", "value", "reason"), [
    ("A3", "SYN-OK", "row_id_duplicate"),
    ("G2", "MISSING-SHEET", "source_sheet_unknown"),
    ("Q2", "NaN", "quantity_missing_or_invalid"),
    ("U2", "{}", "quantity_evidence_invalid"),
    ("U2", None, "quantity_evidence_invalid"),
    ("O2", "invalid", "quantity_deductions_invalid"),
    ("O2", None, "quantity_deductions_invalid"),
])
def test_bad_workbook_row_is_excluded_even_with_review(dataset, column, value, reason):
    from openpyxl import load_workbook
    path, sidecar, reviews = dataset
    workbook = load_workbook(path)
    workbook["TakeoffRows"][column] = value
    workbook.save(path)
    _save_reviews(path, sidecar, reviews)
    selection = load_evaluation_cases(path, sidecar, scope="quantity")
    assert reason in next(item for item in selection.excluded if item["row_id"] == "SYN-OK")["reasons"]


def test_quantity_review_cannot_replace_retrieval_review(dataset):
    path, sidecar, reviews = dataset
    del reviews["rows"]["SYN-OK"]["retrieval"]
    _save_reviews(path, sidecar, reviews)
    selection = load_evaluation_cases(path, sidecar, scope="retrieval")
    assert "SYN-OK" not in [item["row"]["row_id"] for item in selection.cases]


@pytest.mark.parametrize(("cell", "value", "reason"), [
    ("A2", "PLAN", "source_id_duplicate"),
    ("C3", None, "source_metadata_invalid"),
    ("E3", -1, "source_metadata_invalid"),
])
def test_invalid_source_metadata_excludes_case(dataset, cell, value, reason):
    from openpyxl import load_workbook
    path, sidecar, reviews = dataset
    workbook = load_workbook(path)
    workbook["Sources"][cell] = value
    workbook.save(path)
    _save_reviews(path, sidecar, reviews)
    selection = load_evaluation_cases(path, sidecar, scope="retrieval")
    assert reason in next(item for item in selection.excluded if item["row_id"] == "SYN-OK")["reasons"]


def test_multi_sheet_quantity_requires_all_evidence(dataset):
    path, sidecar, reviews = dataset
    reviews["rows"]["SYN-MULTI"]["quantity"]["evidence"].pop()
    _save_reviews(path, sidecar, reviews)
    selection = load_evaluation_cases(path, sidecar, scope="quantity")
    assert "quantity_sources_not_covered" in next(item for item in selection.excluded if item["row_id"] == "SYN-MULTI")["reasons"]


def test_legacy_empty_template_and_unreviewed_rows_are_preserved(dataset, tmp_path):
    path = tmp_path / "empty.xlsx"
    build_workbook().save(path)
    reviews = {"schema_version": 1, "origin": "practitioner", "rows": {}}
    sidecar = tmp_path / "empty-reviews.json"
    _save_reviews(path, sidecar, reviews)
    assert validate_workbook(path, allow_empty_template=True) == []
    assert load_evaluation_cases(path, sidecar, scope="quantity").cases == []
    path, sidecar, reviews = dataset
    reviews["rows"] = {}
    _save_reviews(path, sidecar, reviews)
    assert len(load_evaluation_cases(path, sidecar, scope="retrieval").excluded) == 6


def test_cli_reports_identifiers_and_exclusion_reasons(dataset, capsys):
    path, sidecar, _ = dataset
    assert main([str(path), str(sidecar), "--scope", "quantity"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["selected_row_ids"] == ["SYN-OK", "SYN-MULTI"]
    assert len(output["excluded"]) == 4
