"""Revalidate saved evidence and evaluate training-derived gates on separate groups."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROOT = Path("artifacts/local_development_audits")
POLICY_SHA = "049c6e9170eed3a7ea9f5bb70d3a956f6d59d0af7176d129b79223b1912713f9"
OUTPUT = ROOT / "grouped_routing_development_v1"
PANELS = ("official_reference_compliance", "tooleyes_relevance")


def canonical(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def report(summary):
    lines = [
        "# Group-separated development routing validation",
        "",
        "Exploratory development analysis after prior inspection of full-development results.",
        "Training-only score quantiles; five canonical-group folds stratified by benchmark.",
        (
            "A training escalation cap is not a validation cap guarantee. No final "
            "threshold is selected."
        ),
        "",
        (
            "| Model | Endpoint | Training cap | OOF rows | Gate matches | Small "
            "matches | Fallback matches | Match rate | Fallback calls | Total calls "
            "| Unusable final | Cap-exceeded folds | Request seconds/match | Random mean matches |"
        ),
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary["views"]:
        rate = row["reference_compliance_full_cohort"]
        rate = f"{rate:.2%}" if rate is not None else "incomplete/unavailable"
        seconds = row["request_seconds_per_match_evaluated"]
        seconds = f"{seconds:.3f}" if seconds is not None else "unavailable"
        random = row["random_mean_matches_evaluated"]
        random = f"{random:.2f}" if random is not None else "unavailable"
        lines.append(
            f"| {row['model']} | {row['panel']} | {row['cap']:.0%} | "
            f"{row['evaluated_rows']}/{row['original_rows']} | "
            f"{row['known_matches_evaluated']} | {row['small_matches_same_rows']} | "
            f"{row['fallback_matches_same_rows']} | {rate} | {row['fallback_rows']} | "
            f"{row['accounting']['model_calls']} | "
            f"{row['unusable_final_outputs']} | {row['validation_cap_exceeded_folds']} | "
            f"{seconds} | {random} |"
        )
    lines += [
        "",
        "Unfittable folds have no fabricated predictions; their rows remain unevaluated.",
        (
            "Full-cohort rates are unavailable unless every row has an OOF "
            "prediction and known outcome."
        ),
        "Random controls match the actual fallback count within each validation fold.",
        (
            "Inspect validation_cap_exceeded in fold diagnostics; budgets are "
            "fitted only on training rows."
        ),
        (
            "Token evidence, parsed-call usability, reference compliance and "
            "ToolEyes relevance stay distinct."
        ),
        "Request seconds are saved sequential-time proxies, not online latency or GPU billing.",
        "Ten random seeds are not confidence intervals. No model/cap is selected as an optimum.",
        (
            "Group-separated folds do not undo previous full-development exposure; "
            "held-out groups remain untouched."
        ),
        "No money-saving, executable-success or statistical superiority claim is supplied.",
        "No full-development deployment threshold is refitted or frozen by this subtask.",
    ]
    return "\n".join(lines) + "\n"


def run(repo):
    repo = repo.resolve()
    root, output = repo / ROOT, repo / OUTPUT
    if output.exists() or any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError("Fresh output required; preserve existing grouped validation")
    raw = (HERE / "policy.json").read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(raw).hexdigest() != POLICY_SHA:
        raise ValueError("Grouped validation policy fingerprint differs")
    policy = json.loads(raw)
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", policy["baseline_commit"], "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    if subprocess.run(
        ["git", "check-ignore", "-q", "--", str(OUTPUT / "summary.json")], cwd=repo
    ).returncode:
        raise ValueError("Validation output must stay ignored")
    sys.path.insert(0, str(repo / "src"))
    bound = load_module(
        "_grouped_routing_inputs", repo / "tools/development_audits/paired_routing_v1/inputs.py"
    )
    bound.check_sources(repo, policy)
    validator = load_module("_grouped_routing_validation", HERE / "validation.py")
    prior_path = root / "paired_routing_development_v1/paired_inputs.json"
    prior_raw = bound.regular(prior_path)
    prior = json.loads(prior_raw)
    ledger = {prior_path: bound.sha(prior_raw)}
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root, prefix="grouped-routing-") as tmp:
        stage = Path(tmp)
        verification = stage / "revalidation"
        verification.mkdir()
        models = {}
        for model, settings in policy["models"].items():
            print("Revalidating saved model evidence:", model, flush=True)
            models[model], _, _ = bound.verified_model(repo, settings, verification, model, ledger)
        pairs = {}
        for model in policy["model_order"]:
            pairs[model] = bound.join(models[model], models[policy["fallback"]])
            if len(pairs[model]) != policy["rows_per_model"]:
                raise ValueError("Constructed primary denominator differs")
            if [asdict(r) for r in pairs[model]] != prior[model]:
                raise ValueError("Prior paired inputs differ from fresh evidence: " + model)
        first = pairs[policy["model_order"][0]]
        assignment = validator.assign_folds(first, policy["folds"], policy["fold_seed"])
        results, views = {}, []
        for model in policy["model_order"]:
            if (
                validator.assign_folds(pairs[model], policy["folds"], policy["fold_seed"])
                != assignment
            ):
                raise ValueError("Shared model group assignments differ")
            results[model] = {}
            for panel in PANELS:
                rows = [r for r in pairs[model] if r.panel == panel]
                results[model][panel] = []
                for cap in policy["caps"]:
                    print("Group-separated validation:", model, panel, "cap:", cap, flush=True)
                    result = validator.validate_cap(
                        rows, assignment, cap, policy["folds"], policy["random_seeds"]
                    )
                    results[model][panel].append(result)
                    gate = result["gated"]
                    views.append(
                        {
                            "model": model,
                            "panel": panel,
                            "cap": cap,
                            "validation_cap_exceeded_folds": sum(
                                bool(f.get("validation_cap_exceeded", False))
                                for f in result["folds"]
                            ),
                            **validator.compact(gate),
                            "random_mean_matches_evaluated": result[
                                "random_mean_matches_evaluated"
                            ],
                            "small_matches_same_rows": result["baselines_on_same_evaluated_rows"][
                                "small_only"
                            ]["known_matches_evaluated"],
                            "fallback_matches_same_rows": result[
                                "baselines_on_same_evaluated_rows"
                            ]["fallback_only"]["known_matches_evaluated"],
                        }
                    )
        summary = {
            "version": policy["version"],
            "folds": policy["folds"],
            "canonical_groups": len(assignment),
            "rows_per_model": policy["rows_per_model"],
            "views": views,
            "held_out_access_enabled": False,
            "main_experiment_ready": False,
            "deployment_threshold_selected": False,
            "inference_requests": 0,
            "prior_files_modified": False,
            "currency_cost_measured": False,
            "validation_context": policy["method_context"],
        }
        for path, wanted in ledger.items():
            if bound.sha(bound.regular(path)) != wanted:
                raise ValueError("Original input changed during validation: " + str(path))
        bound.check_sources(repo, policy)
        provenance = {
            "policy": policy,
            "policy_sha256_lf": POLICY_SHA,
            "head": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True
            ).strip(),
            "input_sha256": {p.relative_to(repo).as_posix(): h for p, h in ledger.items()},
            "new_source_sha256_lf": {
                name: bound.sha((HERE / name).read_bytes().replace(b"\r\n", b"\n"))
                for name in ("validation.py", "run_validation.py")
            },
        }
        outputs = {
            "summary.json": summary,
            "oof_results.json": results,
            "fold_assignment.json": [
                {"benchmark": b, "canonical_group": g, "fold": f}
                for (b, g), f in sorted(assignment.items())
            ],
            "provenance.json": provenance,
        }
        for name, value in outputs.items():
            (stage / name).write_text(canonical(value) + "\n", encoding="utf-8", newline="\n")
        (stage / "REPORT.md").write_text(report(summary), encoding="utf-8", newline="\n")
        publisher = bound.module(
            "_grouped_publisher", repo / policy["models"][policy["fallback"]]["scorer"]
        )
        publisher.publish_directory(stage, output)
    return summary


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    if Path.cwd().resolve() != REPO:
        raise SystemExit("Run from the uqroute-tc repository root")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO / "src")
    try:
        for folder, pattern in (
            (str(HERE), "test_*.py"),
            ("tools/development_audits/paired_routing_v1", "test_*.py"),
            ("tests/unit", "test_routing_development.py"),
        ):
            subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", folder, "-p", pattern],
                cwd=REPO,
                env=env,
                check=True,
            )
        summary = run(REPO)
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        raise SystemExit(
            "Grouped development validation stopped: "
            + str(exc)
            + ". Preserve saved evidence; no model retries."
        ) from None
    print(report(summary))
    print("Saved:", OUTPUT / "REPORT.md")
    print("No inference, held-out access, Git writes or final threshold selection performed.")


if __name__ == "__main__":
    main()
