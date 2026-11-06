import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import evaluate_retrieval as evaluation


def test_metrics_use_all_required_sources_and_full_returned_rank():
    result = evaluation.score_case(["a", "b"], ["x", "a", "x", "y", "b"])
    assert result == {"recall_at_3": .5, "reciprocal_rank": .5,
                      "all_required_at_3": False, "missing_at_3": ["b"]}
    assert evaluation.score_case(["a"], ["x", "y", "z", "a"])["reciprocal_rank"] == .25
    assert evaluation.score_case(["a"], [])["reciprocal_rank"] == 0
    assert evaluation.score_case(["a"], [])["recall_at_3"] == 0
    with pytest.raises(ValueError, match="positive relevance"):
        evaluation.score_case([], [])


def test_repeated_run_is_reproducible_and_step1_gate_is_respected():
    report = evaluation.evaluate()
    assert report == evaluation.evaluate()
    assert report["metrics"]["scored_cases"] == 9
    excluded = {row["row_id"]: row["reasons"] for row in report["excluded"]}
    assert excluded["no-relevant"] == ["retrieval_truth_missing_or_unreferenced"]
    assert excluded["unknown-truth"] == ["scope_not_reviewed"]
    assert excluded["unreviewed"] == ["scope_not_reviewed"]
    assert report["negative_diagnostics"][0]["correct_abstention"] is True
    assert report["ai_quality_comparison"] == "not_run"
    assert report["ai_configuration"] is None
    rows = {row["id"]: row for row in report["cases"]}
    assert rows["tie"]["ranked_source_ids"] == ["TIE-A", "TIE-B"]
    assert rows["not-found-positive"]["recall_at_3"] == 0
    assert rows["room-ceiling"]["all_required_at_3"] is True


def test_no_gate_approval_means_no_positive_score_or_search(monkeypatch):
    original = evaluation.prepare_fixture
    def empty(fixture, directory):
        sheets, ids, selection = original(fixture, directory)
        return sheets, ids, type(selection)([], selection.excluded)
    monkeypatch.setattr(evaluation, "prepare_fixture", empty)
    report = evaluation.evaluate()
    assert report["cases"] == []
    assert report["metrics"]["recall_at_3"] is None
    with pytest.raises(ValueError, match="no scored cases"):
        evaluation.compare(report, report)


def test_ai_opt_in_only_passes_same_questions_without_truth(monkeypatch):
    calls = []
    def fake(question):
        calls.append(question)
        return evaluation.local_search_arguments(question), {"model": "fake-only", "usage": {}}
    monkeypatch.setattr(evaluation, "model_search_arguments", fake)
    local = evaluation.evaluate()
    assert calls == []
    ai = evaluation.evaluate(ai=True)
    assert calls == [row["question"] for row in local["cases"]] + [local["negative_diagnostics"][0]["question"]]
    assert ai["metrics"] == local["metrics"]
    assert ai["ai_quality_comparison"] == "executed"  # mocked transport; not a live-quality assertion
    assert evaluation.compare(local, ai)["regressions"] == []


def test_unreviewed_negative_does_not_get_diagnostic_or_model_call(monkeypatch):
    original = evaluation.prepare_fixture
    def unreviewed(fixture, directory):
        fixture = copy.deepcopy(fixture)
        next(case for case in fixture["cases"] if case["id"] == "no-relevant")["review_status"] = "NEEDS_REVIEW"
        return original(fixture, directory)
    monkeypatch.setattr(evaluation, "prepare_fixture", unreviewed)
    report = evaluation.evaluate()
    assert report["negative_diagnostics"] == []
    assert report["metrics"]["scored_cases"] == 9


@pytest.mark.parametrize("field", ["input_sha256", "extracted_corpus_sha256", "settings", "corpus_version", "runtime"])
def test_comparison_rejects_changed_inputs_and_settings(field):
    baseline = evaluation.evaluate()
    candidate = copy.deepcopy(baseline)
    candidate[field] = "changed"
    with pytest.raises(ValueError, match="incomparable"):
        evaluation.compare(baseline, candidate)


def test_comparison_reports_regression_and_partial_multi_failure():
    baseline = evaluation.evaluate()
    candidate = copy.deepcopy(baseline)
    row = candidate["cases"][0]
    row.update(evaluation.score_case(row["expected_source_ids"], ["TARGET-S"]))
    row["ranked_source_ids"] = ["TARGET-S"]
    assert evaluation.compare(baseline, candidate)["regressions"] == ["room-ceiling"]
    assert row["all_required_at_3"] is False


def test_checked_in_reports_match_fixed_input_and_current_search():
    baseline = json.loads((evaluation.ROOT / "docs/evaluation/retrieval-baseline-v1.json").read_text(encoding="utf-8"))
    candidate = json.loads((evaluation.ROOT / "docs/evaluation/retrieval-candidate-v1.json").read_text(encoding="utf-8"))
    current = evaluation.evaluate()
    # Runtime patch versions can differ in CI; compare actual extraction, cases,
    # metrics and source fingerprints instead of requiring one machine's runtime.
    for field in ("input_sha256", "extracted_corpus_sha256", "settings", "cases", "metrics", "excluded", "search_source_sha256"):
        assert current[field] == candidate[field]
    assert evaluation.compare(baseline, candidate) == candidate["comparison"]
    assert candidate["comparison"]["regressions"] == []
