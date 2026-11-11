"""Recheck smoke scores and describe parsed-call changes; no semantic relabeling."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROOT = Path("artifacts/local_development_audits")
OUTPUT = ROOT / "recovery_smoke_behaviour_review_v1"
POLICY_SHA = "a2bf1b8106b8273f53d297665cea30cc4c0ab2c993dc9aef81da2bc7ef3a7377"
CONTROL_NAMES = {"finish", "ask_to_user"}
CONTROL_BENCHMARKS = {"rotbench", "tooleyes"}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def regular(path):
    if not path.is_file() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Expected a regular review input")
    return path.read_bytes()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def behaviour(initial, after, benchmark):
    """Describe frozen parser outputs only; labels/references cannot affect buckets."""
    a = [c["name"] for c in initial.calls] if initial.status == "calls" else []
    b = [c["name"] for c in after.calls] if after.status == "calls" else []
    if after.status != "calls":
        bucket = "no_parsed_postfault_call"
    elif initial.status != "calls":
        bucket = "initial_canonical_unavailable"
    elif initial.key == after.key:
        bucket = "identical_canonical_calls"
    elif a == b:
        bucket = "same_name_sequence_changed_arguments"
    else:
        bucket = "changed_name_sequence"
    removed = replacements = None
    if a and a == b:
        removed, replacements = 0, 0
        for left, right in zip(initial.calls, after.calls, strict=True):
            x = left.get("parameters", left.get("arguments", {}))
            y = right.get("parameters", right.get("arguments", {}))
            removed += len(x.keys() - y.keys())
            replacements += sum(
                isinstance(x[k], str) and x[k] == "" and isinstance(y[k], str) and y[k] != ""
                for k in x.keys() & y.keys()
            )
    control_scope = benchmark in CONTROL_BENCHMARKS
    return {
        "bucket": bucket,
        "initial_parser_status": initial.status,
        "postfault_parser_status": after.status,
        "initial_first_control_name_literal": a[0]
        if control_scope and a and a[0] in CONTROL_NAMES
        else None,
        "postfault_has_control_name_literal": control_scope and any(n in CONTROL_NAMES for n in b),
        "removed_top_level_argument_keys": removed,
        "empty_string_argument_replacements": replacements,
    }


def summarize(rows):
    def counts(items):
        return {
            "rows": len(items),
            "groups": len({r["canonical_base_id"] for r in items}),
            "buckets": dict(Counter(r["behaviour"]["bucket"] for r in items)),
            "initial_first_control_name_rows": sum(
                r["behaviour"]["initial_first_control_name_literal"] is not None for r in items
            ),
            "postfault_control_name_rows": sum(
                r["behaviour"]["postfault_has_control_name_literal"] for r in items
            ),
            "rows_with_removed_argument_keys": sum(
                (r["behaviour"]["removed_top_level_argument_keys"] or 0) > 0 for r in items
            ),
            "rows_with_empty_string_replacement": sum(
                (r["behaviour"]["empty_string_argument_replacements"] or 0) > 0 for r in items
            ),
        }

    result = counts(rows)
    result["by_fault"] = {
        name: counts([r for r in rows if r["fault_type"] == name])
        for name in sorted({r["fault_type"] for r in rows})
    }
    result["panels"] = {}
    for panel in ("official_reference_compliance", "tooleyes_relevance"):
        items = [r for r in rows if r["panel"] == panel]
        changes = {}
        for name in sorted({r["behaviour"]["bucket"] for r in items}):
            subset = [r for r in items if r["behaviour"]["bucket"] == name]
            changes[name] = {
                "rows": len(subset),
                "postfault_reference_matches": sum(r["postfault_reference_match"] for r in subset),
                "match_to_mismatch": sum(
                    r["initial_reference_match"] and not r["postfault_reference_match"]
                    for r in subset
                ),
            }
        result["panels"][panel] = counts(items) | {
            "postfault_reference_matches": sum(r["postfault_reference_match"] for r in items),
            "match_to_mismatch": sum(
                r["initial_reference_match"] and not r["postfault_reference_match"] for r in items
            ),
            "matching_rows_with_removed_argument_keys": sum(
                r["postfault_reference_match"]
                and (r["behaviour"]["removed_top_level_argument_keys"] or 0) > 0
                for r in items
            ),
            "matching_rows_with_empty_string_replacement": sum(
                r["postfault_reference_match"]
                and (r["behaviour"]["empty_string_argument_replacements"] or 0) > 0
                for r in items
            ),
            "by_bucket": changes,
        }
    result.update(
        generation_requests_sent=0,
        labels_changed=False,
        rows_excluded=0,
        semantic_fault_recovery="not_evaluated",
        execution_success="not_evaluated",
        held_out_access_enabled=False,
        main_experiment_ready=False,
    )
    return result


def report(summary):
    lines = [
        "# Development smoke: parsed-call behaviour review",
        "",
        "Structural diagnostics only; original references, scores and cohort are unchanged.",
        "",
        "| Behaviour | Episodes |",
        "|---|---:|",
    ]
    for name, count in sorted(summary["buckets"].items()):
        lines.append(f"| {name} | {count} |")
    lines += [
        "",
        "Initial first parsed action has a literal control name: "
        f"{summary['initial_first_control_name_rows']}/{summary['rows']}.",
        "Post-fault parsed calls include a literal control name: "
        f"{summary['postfault_control_name_rows']}/{summary['rows']}.",
        "",
        "| Panel | Behaviour | Episodes | Post-fault reference matches | Match to mismatch |",
        "|---|---|---:|---:|---:|",
    ]
    for panel, values in summary["panels"].items():
        for name, counts in values["by_bucket"].items():
            lines.append(
                f"| {panel} | {name} | {counts['rows']} | "
                f"{counts['postfault_reference_matches']} | {counts['match_to_mismatch']} |"
            )
    lines += [
        "",
        "Literal control names are finish/ask_to_user in RoTBench and ToolEyes; "
        "this is not an execution-success label.",
        "Argument-key removal and empty-string replacement describe parsed structure, "
        "not schema validity or real credentials.",
        "ToolEyes name relevance and the released BFCL parameter-matching rules "
        "do not establish universal argument correctness.",
        "A no-call response may be a refusal or an unrecognized format; "
        "no semantic correctness is assigned.",
        "Do not drop control-action episodes or relabel refusals after seeing these results.",
        "Five selected groups have dependent fault variants; "
        "this is not a population estimate or a gate/fallback evaluation.",
        "Review PRIVATE_REVIEW.md locally. It contains original task/output text; "
        "paste only this aggregate report.",
        "No new inference, manual outcome relabeling, threshold selection "
        "or held-out access occurred.",
    ]
    return "\n".join(lines) + "\n"


def fence(text):
    length = max([2] + [len(m.group()) for m in re.finditer(r"`+", text)]) + 1
    marker = "`" * length
    return marker + "text\n" + text + "\n" + marker + "\n"


def review(repo):
    prior = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        return _review(repo.resolve())
    finally:
        sys.dont_write_bytecode = prior


def _review(repo):
    output = repo / OUTPUT
    if output.exists() or any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError("Fresh review output required; preserve existing files")
    if subprocess.run(
        ["git", "check-ignore", "-q", "--", str(OUTPUT / "records.json")], cwd=repo
    ).returncode:
        raise ValueError("Detailed review text must remain ignored")
    raw = regular(HERE / "policy.json").replace(b"\r\n", b"\n")
    if sha(raw) != POLICY_SHA:
        raise ValueError("Review policy fingerprint differs")
    policy = json.loads(raw)
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", policy["baseline_commit"], "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    for name, expected in policy["source_sha256_lf"].items():
        if sha(regular(repo / name).replace(b"\r\n", b"\n")) != expected:
            raise ValueError("Reviewed dependency differs: " + name)
    root = repo / ROOT
    source = root / "recovery_smoke_reference_scoring_v1"
    originals = {
        name: regular(source / name) for name in ("records.json", "summary.json", "provenance.json")
    }
    prior_summary = json.loads(originals["summary.json"])
    for panel, values in policy["expected_reference_panels"].items():
        if any(
            prior_summary["panels"][panel][name] != expected for name, expected in values.items()
        ):
            raise ValueError("Owner-reported smoke reference totals differ")
    with tempfile.TemporaryDirectory(dir=root, prefix="recovery-smoke-review-") as folder:
        stage = Path(folder)
        scoring = module(
            "_review_bound_scorer",
            repo / "tools/development_audits/recovery_smoke_scoring_v1/score_smoke.py",
        )
        scoring.OUTPUT = (stage / "recomputed_reference_scores").relative_to(repo)
        scoring.score(repo)
        for name in ("records.json", "summary.json"):
            if regular(stage / "recomputed_reference_scores" / name) != originals[name]:
                raise ValueError("Independently recomputed smoke reference scores differ")
        owner = root / "recovery_smoke_qwen15b_import_dd91a73f"
        evidence = owner / "evidence"
        client = module(
            "_review_bound_client",
            repo / "tools/development_audits/recovery_gpu_smoke_v1/client.py",
        )
        _, requests, episodes, _, support, _ = client.load_plan(
            owner / "reproduced/repo", evidence / "prepared"
        )
        frozen = support.methods(owner / "reproduced/repo")
        scored = {r["request_id"]: r for r in json.loads(originals["records.json"])}
        records, private = (
            [],
            [
                "# Private development smoke review",
                "",
                "Original scores retained. Structural observations "
                "are not semantic recovery judgments.",
                "",
            ],
        )
        for number, request in enumerate(requests, 1):
            row = scored[request["request_id"]]
            episode = episodes[request["episode_key"]]
            messages = request["request"]["messages"]
            initial_text = messages[-2]["content"]
            response = json.loads(
                regular(evidence / "run/cases" / request["request_id"] / "http_response.bin")
            )
            post_text = response["choices"][0]["message"]["content"]
            a = frozen["parse"](initial_text, episode["benchmark"])
            b = frozen["parse"](post_text, episode["benchmark"])
            if b.status != row["canonical_parser_status"]:
                raise ValueError("Frozen parser status changed during review")
            record = {
                name: row[name]
                for name in (
                    "request_id",
                    "episode_key",
                    "canonical_base_id",
                    "benchmark",
                    "fault_type",
                    "panel",
                    "initial_reference_match",
                    "postfault_reference_match",
                )
            }
            record["behaviour"] = behaviour(a, b, episode["benchmark"])
            records.append(record)
            private += [
                f"## Example {number}: {episode['benchmark']} / {episode['fault_type']}",
                "",
                f"Initial reference match: {row['initial_reference_match']}; "
                f"post-fault reference match: {row['postfault_reference_match']}.",
                f"Structural bucket: {record['behaviour']['bucket']}.",
                "",
                "### Original request",
                "",
                fence(messages[-3]["content"]),
                "### Initial output",
                "",
                fence(initial_text),
                "### Fault feedback",
                "",
                fence(messages[-1]["content"]),
                "### Post-fault output",
                "",
                fence(post_text),
                "### Original reference flags",
                "",
                fence(
                    json.dumps(row["postfault_score"]["reference_review_flags"], ensure_ascii=False)
                ),
            ]
        summary = summarize(records)
        if summary["rows"] != 30 or summary["groups"] != 5:
            raise ValueError("Complete thirty-episode/five-group smoke required")
        for name, value in (
            ("records.json", records),
            ("summary.json", summary),
            (
                "provenance.json",
                {
                    "policy": policy,
                    "policy_sha256_lf": POLICY_SHA,
                    "original_scoring_sha256": {n: sha(b) for n, b in originals.items()},
                    "reference_scoring_recomputed_exactly": True,
                },
            ),
        ):
            (stage / name).write_text(
                json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
            )
        (stage / "REPORT.md").write_text(report(summary), encoding="utf-8", newline="\n")
        (stage / "PRIVATE_REVIEW.md").write_text("\n".join(private), encoding="utf-8", newline="\n")
        for name, raw in originals.items():
            if regular(source / name) != raw:
                raise ValueError("Original scores changed during review")
        publisher = module(
            "_review_publish",
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
            "Smoke review stopped: " + str(exc) + ". Preserve original evidence; no model requests."
        ) from None
    print(report(summary))
    print("Saved:", OUTPUT)
    print(
        "PRIVATE_REVIEW.md stays local. No generation, label changes, exclusions or policy choice."
    )


if __name__ == "__main__":
    main()
