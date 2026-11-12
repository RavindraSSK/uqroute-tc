"""Explain matched smoke structure while preserving every reference score and pair."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROOT = Path("artifacts/local_development_audits")
OUTPUT = ROOT / "recovery_matched_smoke_behaviour_review_v1"
POLICY_SHA = "76099c62e725a695e845ab631a12a196ffc5753c82ee4c07136986ad734f91fb"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def regular(path):
    if not path.is_file() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Regular review input required")
    return path.read_bytes()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def transition(small, fallback):
    """Describe parser structure; correctness labels never determine the bucket."""
    if small.status != "calls" and fallback.status != "calls":
        return "neither_parsed"
    if small.status != "calls":
        return "small_no_call_to_fallback_call"
    if fallback.status != "calls":
        return "small_call_to_fallback_no_call"
    if small.key == fallback.key:
        return "identical_calls"
    if [c["name"] for c in small.calls] == [c["name"] for c in fallback.calls]:
        return "same_names_changed_arguments"
    return "changed_names"


def outcome(row):
    a, b = row["small_reference_match"], row["fallback_reference_match"]
    if type(a) is not bool or type(b) is not bool:
        raise ValueError("Known paired reference labels required; no imputation")
    return (
        ("both_match" if b else "reference_match_lost")
        if a
        else ("reference_match_gained" if b else "both_mismatch")
    )


def describe(row, initial, small, fallback, behaviour):
    if (
        row["small_parser_status"] != small.status
        or row["fallback_parser_status"] != fallback.status
    ):
        raise ValueError("Frozen parser status differs from the scored pair")
    return {
        "transition": transition(small, fallback),
        "reference_pair": outcome(row),
        "initial_to_small": behaviour(initial, small, row["benchmark"]),
        "initial_to_fallback": behaviour(initial, fallback, row["benchmark"]),
        "small_to_fallback": behaviour(small, fallback, row["benchmark"]),
    }


def summarize(rows):
    if len({r["episode_key"] for r in rows}) != len(rows):
        raise ValueError("Duplicate paired episode")

    def counts(items):
        return {
            "rows": len(items),
            "groups": len({(r["benchmark"], r["canonical_base_id"]) for r in items}),
            "transitions": dict(Counter(r["structure"]["transition"] for r in items)),
            "reference_pairs": dict(Counter(outcome(r) for r in items)),
            "initial_control_name_rows": sum(
                r["structure"]["initial_to_fallback"]["initial_first_control_name_literal"]
                is not None
                for r in items
            ),
            "fallback_removed_initial_argument_keys_rows": sum(
                (r["structure"]["initial_to_fallback"]["removed_top_level_argument_keys"] or 0) > 0
                for r in items
            ),
            "fallback_replaced_initial_empty_strings_rows": sum(
                (r["structure"]["initial_to_fallback"]["empty_string_argument_replacements"] or 0)
                > 0
                for r in items
            ),
        }

    result = counts(rows)
    result["panels"] = {}
    allowed = ("official_reference_compliance", "tooleyes_relevance")
    if any(r["panel"] not in allowed for r in rows):
        raise ValueError("Unexpected reference endpoint")
    for panel in allowed:
        items = [r for r in rows if r["panel"] == panel]
        result["panels"][panel] = counts(items) | {
            "by_outcome": {
                name: counts([r for r in items if outcome(r) == name])
                for name in (
                    "reference_match_gained",
                    "reference_match_lost",
                    "both_match",
                    "both_mismatch",
                )
            }
        }
    result.update(
        generation_requests_sent=0,
        labels_changed=False,
        rows_excluded=0,
        semantic_fault_recovery="not_evaluated",
        execution_success="not_evaluated",
        held_out_access_enabled=False,
        main_experiment_ready=False,
        policy_evaluation=False,
    )
    return result


def report(summary):
    lines = [
        "# Matched smoke: reference-preserving behaviour review",
        "",
        "All thirty pairs remain; structural observations do not adjudicate semantic recovery.",
        "",
        "| Small-to-fallback structure | Episodes |",
        "|---|---:|",
    ]
    for bucket, n in sorted(summary["transitions"].items()):
        lines.append(f"| {bucket} | {n} |")
    lines += [
        "",
        "| Panel | Reference outcome | Rows | Structural transitions |",
        "|---|---|---:|---|",
    ]
    for panel, values in summary["panels"].items():
        for name, v in values["by_outcome"].items():
            detail = "; ".join(f"{k}: {n}" for k, n in sorted(v["transitions"].items())) or "none"
            lines.append(f"| {panel} | {name} | {v['rows']} | {detail} |")
    lines += [
        "",
        f"Initial literal control-name episodes retained: {summary['initial_control_name_rows']}.",
        "A parsed call is not evidence of correct arguments or tool execution.",
        "Argument changes describe structure, not schema validity or real credentials.",
        "ToolEyes stays separate; an appropriate refusal may mismatch the reference.",
        "Control actions and all no-call/matching cases stay included; no labels are rewritten.",
        "Five selected groups have dependent faults; no population or policy-effect claim.",
        "PRIVATE_REVIEW.md contains original text; keep it local. Paste only this report.",
        "No inference, external judge, manual outcome relabeling or held-out access occurred.",
    ]
    return "\n".join(lines) + "\n"


def review(repo):
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        return _review(repo.resolve())
    finally:
        sys.dont_write_bytecode = previous


def _review(repo):
    output = repo / OUTPUT
    if output.exists() or any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError("Fresh paired review required; preserve prior outputs")
    if subprocess.run(
        ["git", "check-ignore", "-q", "--", str(OUTPUT / "PRIVATE_REVIEW.md")], cwd=repo
    ).returncode:
        raise ValueError("Private review must stay ignored")
    raw = regular(HERE / "policy.json").replace(b"\r\n", b"\n")
    if sha(raw) != POLICY_SHA:
        raise ValueError("Paired review policy differs")
    policy = json.loads(raw)
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", policy["baseline_commit"], "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    for n, h in policy["source_sha256_lf"].items():
        if sha(regular(repo / n).replace(b"\r\n", b"\n")) != h:
            raise ValueError("Pinned review dependency differs: " + n)
    scoring = module(
        "_review_pair_scoring",
        repo / "tools/development_audits/recovery_fallback_smoke_scoring_v1/score_pairs.py",
    )
    structural = module(
        "_review_pair_structure",
        repo / "tools/development_audits/recovery_smoke_review_v1/review.py",
    )
    root = repo / ROOT
    source = root / "recovery_matched_smoke_paired_reference_scoring_v1"
    originals = {
        n: regular(source / n) for n in ("records.json", "summary.json", "provenance.json")
    }
    prior = json.loads(originals["summary.json"])
    for panel, expected in policy["expected_panels"].items():
        if any(prior["panels"][panel][n] != v for n, v in expected.items()):
            raise ValueError("Owner-reported paired reference totals differ")
    with tempfile.TemporaryDirectory(dir=root, prefix="paired-review-") as folder:
        stage = Path(folder)
        scoring.OUTPUT = (stage / "scores").relative_to(repo)
        scoring.score(repo)
        reproduced = {n: regular(stage / "scores" / n) for n in originals}
        if originals != reproduced:
            raise ValueError("Original paired scores must reproduce byte for byte")
        inputs = {source / n: sha(raw) for n, raw in originals.items()}
        for n, h in json.loads(reproduced["provenance.json"])["input_sha256"].items():
            inputs[repo / n] = h
        small_root = root / "recovery_smoke_qwen15b_import_dd91a73f/evidence"
        fallback_root = root / "recovery_fallback_smoke_import_f85c1c51/evidence"
        requests = json.loads(regular(fallback_root / "prepared/requests.json"))
        scored = {r["request_id"]: r for r in json.loads(originals["records.json"])}
        client = module(
            "_review_pair_client",
            repo / "tools/development_audits/recovery_gpu_fallback_smoke_v1/client.py",
        )
        with scoring.workflow_modules():
            support, _ = client.dependencies(repo)
            frozen = support.methods(repo)
        rows, private = (
            [],
            [
                "# Private matched recovery smoke review",
                "",
                "Original scores and all pairs retained. No semantic outcome labels assigned.",
                "",
            ],
        )
        if len(requests) != 30 or len(scored) != 30:
            raise ValueError("Complete thirty-pair review required")
        for number, request in enumerate(requests, 1):
            original = scored[request["request_id"]]
            small_id = request["paired_small_request_id"]
            if original["paired_small_request_id"] != small_id:
                raise ValueError("Scored parent identity differs")
            messages = request["request"]["messages"]
            initial = messages[-2]["content"]
            small = json.loads(regular(small_root / "run/cases" / small_id / "http_response.bin"))[
                "choices"
            ][0]["message"]["content"]
            fallback = json.loads(
                regular(fallback_root / "run/cases" / request["request_id"] / "http_response.bin")
            )["choices"][0]["message"]["content"]
            row = {
                n: original[n]
                for n in (
                    "episode_key",
                    "request_id",
                    "paired_small_request_id",
                    "canonical_base_id",
                    "benchmark",
                    "fault_type",
                    "panel",
                    "initial_reference_match",
                    "small_reference_match",
                    "fallback_reference_match",
                    "small_parser_status",
                    "fallback_parser_status",
                )
            }
            row["structure"] = describe(
                row,
                frozen["parse"](initial, row["benchmark"]),
                frozen["parse"](small, row["benchmark"]),
                frozen["parse"](fallback, row["benchmark"]),
                structural.behaviour,
            )
            rows.append(row)
            private += [
                f"## Example {number}: {row['benchmark']} / {row['fault_type']}",
                "",
                f"Unchanged reference pair: {outcome(row)}. "
                f"Small={row['small_reference_match']}; "
                f"fallback={row['fallback_reference_match']}.",
                f"Structural transition: {row['structure']['transition']}.",
                "",
            ]
            for title, text in (
                ("Original task turn", messages[-3]["content"]),
                ("Initial small output", initial),
                ("Fault feedback", messages[-1]["content"]),
                ("Post-fault small output", small),
                ("Matched fallback output", fallback),
            ):
                private += ["### " + title, "", structural.fence(text), ""]
        summary = summarize(rows)
        if summary["rows"] != 30 or summary["groups"] != 5:
            raise ValueError("Complete five-group paired review required")
        for name, value in (
            ("records.json", rows),
            ("summary.json", summary),
            (
                "provenance.json",
                {
                    "policy": policy,
                    "policy_sha256_lf": POLICY_SHA,
                    "paired_scoring_recomputed_exactly": True,
                    "original_paired_scoring_sha256": {n: sha(raw) for n, raw in originals.items()},
                    "input_sha256": {p.relative_to(repo).as_posix(): h for p, h in inputs.items()},
                },
            ),
        ):
            (stage / name).write_text(
                json.dumps(
                    value,
                    sort_keys=True,
                    ensure_ascii=False,
                    allow_nan=False,
                    separators=(",", ":"),
                )
                + "\n",
                encoding="utf-8",
                newline="\n",
            )
        (stage / "REPORT.md").write_text(report(summary), encoding="utf-8", newline="\n")
        (stage / "PRIVATE_REVIEW.md").write_text("\n".join(private), encoding="utf-8", newline="\n")
        for path, h in inputs.items():
            if sha(regular(path)) != h:
                raise ValueError("Original evidence/score changed during review")
        publisher = module(
            "_paired_review_publish",
            repo
            / "tools/development_audits"
            / "fallback_full_development_scoring_v1/score_fallback_full.py",
        )
        publisher.publish_directory(stage, output)
    return summary


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    if Path.cwd().resolve() != REPO:
        raise SystemExit("Run from the uqroute-tc repository root")
    try:
        subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", str(HERE), "-p", "test_*.py"],
            cwd=REPO,
            check=True,
        )
        summary = review(REPO)
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        raise SystemExit(
            "Paired smoke review stopped: " + str(exc) + ". Preserve evidence; no model calls."
        ) from None
    print(report(summary))
    print("Saved:", OUTPUT)
    print("PRIVATE_REVIEW.md stays local. No new generation, label changes or exclusions.")


if __name__ == "__main__":
    main()
