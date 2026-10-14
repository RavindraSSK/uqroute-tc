"""Timing selection, attempt accounting and resume without model/GPU calls."""

import json
from types import SimpleNamespace

import pytest

from uqroute_tc.data.split import BENCHMARK_REVISION
from uqroute_tc.inference.throughput import (
    _path,
    run_timing,
    select_timing_cases,
    summarize,
)


def _write(path, rows):
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def _dataset(tmp_path):
    rows = [{"id": f"bfcl_v3__case_{i}", "benchmark": "bfcl_v3", "category": "single"}
            for i in range(4)]
    _write(tmp_path / "clean.jsonl", rows)
    _write(tmp_path / "query_paraphrase.jsonl", list(reversed(rows)))
    split = {"benchmark_revision": BENCHMARK_REVISION, "assignments": {
        row["id"]: {"benchmark": "bfcl_v3", "population": "primary",
                    "split": "test" if i == 3 else "development"}
        for i, row in enumerate(rows)}}
    return rows, split


def test_selection_deterministic_development_and_file_qualified(tmp_path):
    rows, split = _dataset(tmp_path)
    selected, coverage = select_timing_cases(tmp_path, split, 3)
    assert len(selected) == 6
    assert len({row["case_key"] for row in selected}) == 6
    assert len({row["id"] for row in selected}) == 3
    assert all(row["base_id"] != rows[3]["id"] for row in selected)
    assert all(row["eligible_rows"] == 3 for row in coverage)
    _write(tmp_path / "clean.jsonl", list(reversed(rows)))
    assert (selected, coverage) == select_timing_cases(tmp_path, split, 3)


def test_selector_excludes_sensitivity_and_multi_turn(tmp_path):
    rows, split = _dataset(tmp_path)
    extra = {"id": "bfcl_v3__BFCL_v3_multiple_type_A__same_name_multiple_type_A_9",
             "benchmark": "bfcl_v3", "category": "single"}
    split["assignments"]["bfcl_v3__BFCL_v3_multiple__multiple_9"] = {
        "benchmark": "bfcl_v3", "population": "sensitivity_only", "split": "development"}
    _write(tmp_path / "query_paraphrase.jsonl", [extra, {**rows[0], "category": "multi_turn"}])
    selected, _ = select_timing_cases(tmp_path, split)
    assert all(row["source_file"] == "clean.jsonl" for row in selected)


@pytest.mark.parametrize("bad", [0, -1])
def test_selector_invalid_limit(tmp_path, bad):
    _, split = _dataset(tmp_path)
    with pytest.raises(ValueError, match="positive"):
        select_timing_cases(tmp_path, split, bad)


def test_selector_revision_and_duplicates(tmp_path):
    rows, split = _dataset(tmp_path)
    with pytest.raises(ValueError, match="revision"):
        select_timing_cases(tmp_path, {**split, "benchmark_revision": "wrong"})
    _write(tmp_path / "query_paraphrase.jsonl", [rows[0], rows[0]])
    with pytest.raises(ValueError, match="Duplicate ID"):
        select_timing_cases(tmp_path, split)


def test_selector_rejects_missing_assignment(tmp_path):
    rows, split = _dataset(tmp_path)
    del split["assignments"][rows[0]["id"]]
    with pytest.raises(ValueError, match="assignment"):
        select_timing_cases(tmp_path, split)


class FakeClient:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(kwargs)
        outcome = next(self.outcomes)
        if isinstance(outcome, BaseException):
            raise outcome
        raw = "f(x=1)"
        response = {"choices": [{"message": {"content": raw}, "finish_reason": outcome,
                                 "logprobs": {"content": [{"token": raw,
                                    "bytes": list(raw.encode()), "logprob": -0.2}]}}],
                    "usage": {"prompt_tokens": 12, "completion_tokens": 3, "total_tokens": 15}}
        return SimpleNamespace(model_dump=lambda **_: response)


def _cases():
    return [{"case_key": f"{source}:same_id", "source_file": source,
             "base_id": "same_id", "id": "same_id", "benchmark": "bfcl_v3",
             "sample": {"benchmark": "bfcl_v3"}}
            for source in ("clean.jsonl", "query_paraphrase.jsonl")]


def _config(cases):
    return {"model_id": "fake", "temperature": 0.001, "max_tokens": 1024,
            "top_logprobs": 5, "case_keys": [c["case_key"] for c in cases]}


def _run(tmp_path, client, cases=None, retry=False):
    cases = _cases() if cases is None else cases
    return run_timing(cases, client, lambda _: [], lambda *_: [], tmp_path,
                      _config(cases), retry_errors=retry)


def test_separate_source_files_resume_and_tokens(tmp_path):
    client = FakeClient(["stop", "stop"])
    first = _run(tmp_path, client)
    second = _run(tmp_path, client)
    assert first["session"]["processed"] == 2
    assert second["session"]["resumed"] == 2
    assert len(client.calls) == 2
    assert second["summary"]["known_token_totals"]["total_tokens"] == 30
    assert second["summary"]["attempt_count"] == 2
    assert client.calls[0]["temperature"] == 0.001
    assert "seed" not in client.calls[0]


def test_retry_keeps_failed_history_and_usage_unknown(tmp_path):
    cases = _cases()[:1]
    client = FakeClient([TimeoutError("test timeout"), "stop"])
    _run(tmp_path, client, cases)
    _run(tmp_path, client, cases)
    assert len(client.calls) == 1
    last = _run(tmp_path, client, cases, retry=True)
    assert last["summary"]["status_counts"] == {"request_error": 1, "complete": 1}
    assert last["summary"]["missing_usage_attempts"]["completion_tokens"] == 1
    assert last["summary"]["completion_tokens_per_batch_second"] is None
    assert len(list(tmp_path.glob("cases/*/attempts/*.json"))) == 2


def test_truncation_kept_not_retried(tmp_path):
    client = FakeClient(["length"])
    cases = _cases()[:1]
    _run(tmp_path, client, cases)
    last = _run(tmp_path, client, cases, retry=True)
    assert last["summary"]["status_counts"] == {"truncated": 1}
    assert len(client.calls) == 1


def test_interruption_intent_survives_and_requires_explicit_retry(tmp_path):
    cases = _cases()[:1]
    client = FakeClient([KeyboardInterrupt(), "stop"])
    with pytest.raises(KeyboardInterrupt):
        _run(tmp_path, client, cases)
    attempts = list(tmp_path.glob("cases/*/attempts/*.json"))
    assert json.loads(attempts[0].read_text())["status"] == "started"
    skipped = _run(tmp_path, client, cases)
    assert skipped["summary"]["status_counts"] == {"interrupted": 1}
    assert skipped["summary"]["unfinished_sessions"] == 1
    _run(tmp_path, client, cases, retry=True)
    assert summarize(tmp_path)["attempt_count"] == 2


def test_manifest_mismatch_rejected(tmp_path):
    _run(tmp_path, FakeClient(["stop", "stop"]))
    cases = _cases()
    with pytest.raises(ValueError, match="manifest differs"):
        run_timing(cases, None, None, None, tmp_path,
                   {**_config(cases), "temperature": 0.5})


def test_output_without_manifest_rejected(tmp_path):
    (tmp_path / "unrelated.txt").write_text("keep me")
    with pytest.raises(ValueError, match="no manifest"):
        _run(tmp_path, FakeClient([]))


def test_selection_manifest_mismatch_before_write(tmp_path):
    cases = _cases()
    with pytest.raises(ValueError, match="match manifest"):
        run_timing(cases, None, None, None, tmp_path, {**_config(cases), "case_keys": []})
    assert not (tmp_path / "manifest.json").exists()


def test_attempt_path_independent_of_platform(tmp_path):
    assert _path(tmp_path, "clean.jsonl:id") != _path(tmp_path, "typos.jsonl:id")
    assert _path(tmp_path, "clean.jsonl:id").parent == tmp_path / "cases"


def test_invalid_evidence_saved_and_not_retried(tmp_path):
    client = FakeClient(["stop"])
    create = client.create

    def invalid(**kwargs):
        response = create(**kwargs).model_dump()
        response["choices"][0]["logprobs"] = None
        return SimpleNamespace(model_dump=lambda **_: response)

    client.chat.completions.create = invalid
    cases = _cases()[:1]
    _run(tmp_path, client, cases)
    _run(tmp_path, client, cases, retry=True)
    assert summarize(tmp_path)["status_counts"] == {"invalid_evidence": 1}
    assert len(client.calls) == 1
