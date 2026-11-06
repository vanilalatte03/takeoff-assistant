"""Reproducible synthetic search evaluation; never reads business data or env files."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import platform
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.models import DrawingSheet
from app.services.assist_search import local_search_arguments, search_sheets, model_search_arguments
from app.services.sheet_classifier import classify_sheet_role
from app.core.config import settings as app_settings
from create_example_dataset_template import build_workbook
from load_evaluation_cases import load_evaluation_cases
from validate_example_dataset import SOURCE_HEADERS, TAKEOFF_HEADERS

CORPUS = ROOT / "scripts/fixtures/retrieval_corpus.json"
SETTINGS = {"k": 3, "search_limit": 12, "path": "argument builder -> search_sheets", "pdf_font": "helv", "pdf_fontsize": 11}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def prepare_fixture(fixture, directory):
    """Materialize ONLY the authored synthetic fixture, then use step1 review gate."""
    if fixture.get("origin") != "synthetic":
        raise ValueError("only the bundled synthetic corpus is supported")
    pdf = fitz.open()
    for sheet in fixture["sheets"]:
        page = pdf.new_page()
        page.insert_text((40, 60), sheet["text"], fontsize=SETTINGS["pdf_fontsize"], fontname=SETTINGS["pdf_font"])
    pdf_path = directory / "synthetic.pdf"
    pdf.save(pdf_path)
    pdf.close()
    with fitz.open(pdf_path) as document:
        sheets = [DrawingSheet(id=index + 1, page_index=index, sheet_no=item["sheet_no"],
                    sheet_title=item["sheet_title"], text_content=document[index].get_text(),
                    role=classify_sheet_role(item["sheet_title"], document[index].get_text()))
                  for index, item in enumerate(fixture["sheets"])]
    ids = {sheet.id: item["source_id"] for sheet, item in zip(sheets, fixture["sheets"])}
    sources = {item["source_id"]: item | {"page_index": index} for index, item in enumerate(fixture["sheets"])}
    workbook = build_workbook()
    for source in sources.values():
        workbook["Sources"].append([source.get(header) for header in SOURCE_HEADERS])
    reviews = {"schema_version": 1, "origin": "synthetic", "rows": {}}
    for case in fixture["cases"]:
        expected = case["expected"] or []
        # The step1 loader deliberately excludes empty/unknown truth. Negative
        # adjudications remain diagnostics; they never become positive relevance.
        evidence_ids = expected or list(sources)
        row = {"row_id": case["id"], "status": "NEEDS_REVIEW",
               "source_sheets": ",".join(sources[source_id]["sheet_no"] for source_id in evidence_ids)}
        workbook["TakeoffRows"].append([row.get(header) for header in TAKEOFF_HEADERS])
        review = {"status": case.get("review_status", "REVIEWED"), "reviewer": fixture["reviewer"],
                  "reviewed_on": fixture["reviewed_on"], "origin": "synthetic", "unresolved_exceptions": [],
                  "expected_source_ids": case["expected"],
                  "evidence": [{"source_id": source_id, "locator": case["locator"]} for source_id in evidence_ids]}
        if case.get("truth_state") == "unknown":
            review["status"] = "NEEDS_REVIEW"
        reviews["rows"][case["id"]] = {"retrieval": review}
    workbook_path = directory / "synthetic.xlsx"
    workbook.save(workbook_path)
    workbook.close()
    reviews["workbook_sha256"] = hashlib.sha256(workbook_path.read_bytes()).hexdigest()
    sidecar = directory / "reviews.json"
    sidecar.write_text(json.dumps(reviews), encoding="utf-8")
    selection = load_evaluation_cases(workbook_path, sidecar, scope="retrieval")
    return sheets, ids, selection


def score_case(expected, ranked, k=3):
    if not expected:
        raise ValueError("positive relevance required; empty/unknown truth is excluded")
    # Unique sources determine ranks; duplicate hits never inflate recall.
    ranked = list(dict.fromkeys(ranked))
    expected = set(expected)
    top = ranked[:k]
    hits = expected.intersection(top)
    rank = next((index for index, item in enumerate(ranked, 1) if item in expected), None)
    return {"recall_at_3": len(hits) / len(expected), "reciprocal_rank": 1 / rank if rank else 0,
            "all_required_at_3": expected.issubset(top), "missing_at_3": sorted(expected - set(top))}


def evaluate(*, ai=False):
    fixture = json.loads(CORPUS.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="takeoff-retrieval-") as directory:
        sheets, source_ids, selection = prepare_fixture(fixture, Path(directory))
        selected = {case["row"]["row_id"]: case for case in selection.cases}
        excluded = {case["row_id"]: case["reasons"] for case in selection.excluded}
        results, diagnostics = [], []
        for case in fixture["cases"]:
            # Only the question reaches the argument builder. No truth, review,
            # corpus text or expected source ID is sent to the model.
            reviewed_negative = (case.get("truth_state") == "no_relevant" and case["expected"] == []
                                 and excluded.get(case["id"]) == ["retrieval_truth_missing_or_unreferenced"])
            if case["id"] not in selected and not reviewed_negative:
                continue
            question = case["question"]
            args, metadata = model_search_arguments(question) if ai else (local_search_arguments(question), {})
            ranked = [source_ids[item["sheet_id"]] for item in search_sheets(sheets, args, question)]
            common = {"id": case["id"], "question": question, "arguments": args.model_dump(), "ranked_source_ids": ranked}
            if ai:
                common["model_metadata"] = metadata
            if case["id"] in selected:
                expected = selected[case["id"]]["review"]["expected_source_ids"]
                results.append(common | {"expected_source_ids": expected} | score_case(expected, ranked))
            else:
                diagnostics.append(common | {"truth_state": "no_relevant", "correct_abstention": not ranked,
                                             "reviewer": fixture["reviewer"], "reviewed_on": fixture["reviewed_on"], "locator": case["locator"]})
        count = len(results)
        metrics = {"scored_cases": count, "recall_at_3": sum(row["recall_at_3"] for row in results) / count if count else None,
                   "mrr_at_12": sum(row["reciprocal_rank"] for row in results) / count if count else None,
                   "all_required_at_3_rate": sum(row["all_required_at_3"] for row in results) / count if count else None}
        return {"schema_version": 1, "corpus_version": fixture["version"], "input_sha256": digest(fixture),
                "extracted_corpus_sha256": digest([{ "source_id": source_ids[sheet.id], "text": sheet.text_content,
                                                     "role": sheet.role.value} for sheet in sheets]),
                "runtime": {"python": platform.python_version(), "pymupdf": fitz.VersionBind},
                "settings": SETTINGS, "search_source_sha256": hashlib.sha256((ROOT / "apps/api/app/services/assist_search.py").read_text(encoding="utf-8").encode()).hexdigest(),
                "mode": "ai" if ai else "local", "ai_quality_comparison": "executed" if ai else "not_run",
                "ai_configuration": {"model": app_settings.ai_model, "max_output_tokens": 500, "timeout_seconds": 25,
                                     "parallel_tool_calls": False, "store": False} if ai else None,
                "origin": "synthetic", "metrics": metrics, "cases": results,
                "excluded": selection.excluded, "negative_diagnostics": diagnostics}


def compare(baseline, candidate):
    for field in ("schema_version", "input_sha256", "extracted_corpus_sha256", "corpus_version", "settings", "origin", "runtime"):
        if baseline[field] != candidate[field]:
            raise ValueError(f"incomparable reports: {field}")
    before = {row["id"]: row for row in baseline["cases"]}
    after = {row["id"]: row for row in candidate["cases"]}
    if before.keys() != after.keys() or baseline["excluded"] != candidate["excluded"]:
        raise ValueError("incomparable reports: selected/excluded cases")
    if not before:
        raise ValueError("no scored cases to compare")
    if any(before[key][field] != after[key][field] for key in before for field in ("question", "expected_source_ids")):
        raise ValueError("incomparable reports: question/truth")
    fields = ("recall_at_3", "mrr_at_12", "all_required_at_3_rate")
    return {"delta": {field: candidate["metrics"][field] - baseline["metrics"][field] for field in fields},
            "regressions": [key for key in before if any(after[key][field] < before[key][field]
                             for field in ("recall_at_3", "reciprocal_rank", "all_required_at_3"))],
            "changed_cases": [key for key in before if before[key]["ranked_source_ids"] != after[key]["ranked_source_ids"]]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--ai-opt-in", action="store_true", help="Paid model calls for the same public synthetic questions only; uses current configured model")
    args = parser.parse_args(argv)
    report = evaluate(ai=args.ai_opt_in)
    if args.baseline:
        report["comparison"] = compare(json.loads(args.baseline.read_text(encoding="utf-8")), report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"metrics": report["metrics"], "comparison": report.get("comparison"),
                      "ai_quality_comparison": report["ai_quality_comparison"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
