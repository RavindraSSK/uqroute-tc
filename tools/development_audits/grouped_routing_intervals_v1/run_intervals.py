"""Reproduce saved OOF routing and quantify conditional paired group uncertainty."""

from __future__ import annotations

import argparse
import hashlib
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
OUTPUT = ROOT / "grouped_routing_intervals_v1"
POLICY_SHA = "9f0090d97f73217cd2a1a6203677d606f0fdcbec01a8d76403f4b4d2b5293416"
PANELS = ("official_reference_compliance", "tooleyes_relevance")


def canonical(value):
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )


def format_metric(result, name, scale=1):
    if result.get("unavailable_reason"):
        return result["unavailable_reason"]
    metric = result["metrics"][name]
    point = metric["point"]
    if point is None:
        return metric["point_unavailable_reason"]
    interval = metric["interval_95_percentile"]
    if interval is None:
        return f"{point * scale:.3f}; interval unavailable"
    return f"{point * scale:.3f} [{interval[0] * scale:.3f}, {interval[1] * scale:.3f}]"


def report(summary, display_caps):
    lines = [
        "# Conditional paired group-bootstrap routing intervals",
        "",
        (
            "Exploratory development results; 2,000 group draws within benchmark, "
            "shared across policies."
        ),
        "Intervals condition on fixed OOF thresholds and decisions; thresholds are not refitted.",
        (
            "No multiplicity correction or independent held-out confirmation. "
            "Differences are gate minus baseline."
        ),
        "",
        (
            "| Model | Endpoint | Training cap | OOF rows | Gate matches | Fallback "
            "calls | Match difference vs small (pp), 95% interval | Match "
            "difference vs fallback (pp), 95% interval | Request seconds/match "
            "difference vs fallback, 95% interval |"
        ),
        "|---|---|---:|---:|---:|---:|---|---|---|",
    ]
    for view in summary["views"]:
        if view["cap"] not in display_caps:
            continue
        comparisons = view["comparisons"]
        a = format_metric(comparisons["small_only"], "match_fraction_difference", 100)
        b = format_metric(comparisons["fallback_only"], "match_fraction_difference", 100)
        t = format_metric(comparisons["fallback_only"], "request_seconds_per_match_difference")
        lines.append(
            f"| {view['model']} | {view['panel']} | {view['cap']:.0%} | "
            f"{view['evaluated_rows']}/{view['original_rows']} | {view['known_matches']} | "
            f"{view['fallback_rows']} | {a} | {b} | {t} |"
        )
    lines += [
        "",
        "All original caps and three baselines are retained in intervals.json.",
        "Incomplete OOF coverage receives no full-cohort bootstrap interval or imputed outcome.",
        "Intervals require at least 10 canonical groups and 90% valid replicates.",
        (
            "Unknown reference outcomes and missing usage withhold affected "
            "metrics; ratios need nonzero matches."
        ),
        (
            "Positive match differences favor the gate; negative time-proxy "
            "differences favor the gate."
        ),
        (
            "Request seconds are cached sequential request-time sums, not online "
            "latency or billed GPU time."
        ),
        (
            "The two endpoint panels measure different outcomes; ToolEyes relevance "
            "is not argument correctness."
        ),
        (
            "Group resampling does not remove prior development exposure or "
            "estimate all threshold-learning variability."
        ),
        (
            "No best cap/model, monetary saving, execution-success guarantee or "
            "final deployment threshold is selected."
        ),
    ]
    return "\n".join(lines) + "\n"


def run(repo):
    repo = repo.resolve()
    root, output = repo / ROOT, repo / OUTPUT
    if output.exists() or any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError("Fresh output required; preserve previous routing intervals")
    raw = (HERE / "policy.json").read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(raw).hexdigest() != POLICY_SHA:
        raise ValueError("Conditional-interval policy fingerprint differs")
    policy = json.loads(raw)
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", policy["baseline_commit"], "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    if subprocess.run(
        ["git", "check-ignore", "-q", "--", str(OUTPUT / "intervals.json")], cwd=repo
    ).returncode:
        raise ValueError("Interval output must remain ignored")
    sys.path.insert(0, str(repo / "src"))
    # Import the unchanged prior helper only after checking its recorded bytes.
    for name, wanted in policy["source_sha256_lf"].items():
        path = repo / name
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise ValueError("Symlink source rejected: " + name)
        if hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() != wanted:
            raise ValueError("Pinned source differs: " + name)
    sys.path.insert(0, str(repo / "tools/development_audits/grouped_routing_v1"))
    import run_validation as old

    if (
        Path(old.__file__).resolve()
        != (repo / "tools/development_audits/grouped_routing_v1/run_validation.py").resolve()
    ):
        raise ValueError("Conflicting grouped runner import")
    context_raw = (old.HERE / "policy.json").read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(context_raw).hexdigest() != policy["grouped_policy_sha256_lf"]:
        raise ValueError("Prior grouped policy differs")
    context = json.loads(context_raw)
    bound = old.load_module(
        "_intervals_bound_inputs", repo / "tools/development_audits/paired_routing_v1/inputs.py"
    )
    bound.check_sources(repo, policy)
    validator = old.load_module("_intervals_group_validator", old.HERE / "validation.py")
    engine = old.load_module("_routing_intervals", HERE / "intervals.py")
    ledger = {}

    def saved(path):
        data = bound.regular(path)
        ledger[path] = bound.sha(data)
        return json.loads(data)

    prior_pairs = saved(root / "paired_routing_development_v1/paired_inputs.json")
    prior_results = saved(root / "grouped_routing_development_v1/oof_results.json")
    prior_folds = saved(root / "grouped_routing_development_v1/fold_assignment.json")
    prior_proof = saved(root / "grouped_routing_development_v1/provenance.json")
    if prior_proof["policy"] != context or prior_proof["policy_sha256_lf"] != old.POLICY_SHA:
        raise ValueError("Prior grouped provenance policy differs")
    with tempfile.TemporaryDirectory(dir=root, prefix="routing-intervals-") as tmp:
        stage = Path(tmp)
        verification = stage / "revalidation"
        verification.mkdir()
        models = {}
        for model, settings in context["models"].items():
            print("Revalidating source model evidence:", model, flush=True)
            models[model], _, _ = bound.verified_model(repo, settings, verification, model, ledger)
        pairs = {
            model: bound.join(models[model], models[context["fallback"]])
            for model in context["model_order"]
        }
        for model, rows in pairs.items():
            if (
                len(rows) != context["rows_per_model"]
                or [asdict(r) for r in rows] != prior_pairs[model]
            ):
                raise ValueError("Saved normalized pairs differ: " + model)
        first = pairs[context["model_order"][0]]
        assignment = validator.assign_folds(first, context["folds"], context["fold_seed"])
        expected_folds = [
            {"benchmark": b, "canonical_group": g, "fold": f}
            for (b, g), f in sorted(assignment.items())
        ]
        if expected_folds != prior_folds:
            raise ValueError("Saved fold membership differs")
        plans = {
            panel: engine.make_plan(
                [r for r in first if r.panel == panel],
                policy["replicates"],
                policy["bootstrap_seed"],
            )
            for panel in PANELS
        }
        views = []
        for model in context["model_order"]:
            if (
                validator.assign_folds(pairs[model], context["folds"], context["fold_seed"])
                != assignment
            ):
                raise ValueError("Model group folds differ")
            for panel in PANELS:
                rows = [r for r in pairs[model] if r.panel == panel]
                for index, cap in enumerate(context["caps"]):
                    print(
                        "Reproducing OOF and paired intervals:",
                        model,
                        panel,
                        "cap:",
                        cap,
                        flush=True,
                    )
                    result = validator.validate_cap(
                        rows, assignment, cap, context["folds"], context["random_seeds"]
                    )
                    if result != prior_results[model][panel][index]:
                        raise ValueError(
                            "Saved complete OOF result differs: " + model + "/" + panel
                        )
                    gate = result["gated"]
                    comparisons = {}
                    for baseline in policy["baselines"]:
                        if gate["complete_oof_coverage"]:
                            comparisons[baseline] = engine.contrast(
                                rows,
                                gate["predictions"],
                                baseline,
                                plans[panel],
                                policy["minimum_canonical_groups"],
                                policy["minimum_valid_fraction"],
                            )
                        else:
                            comparisons[baseline] = {
                                "unavailable_reason": "incomplete_oof_coverage",
                                "original_rows": len(rows),
                                "evaluated_rows": gate["evaluated_rows"],
                            }
                    views.append(
                        {
                            "model": model,
                            "panel": panel,
                            "cap": cap,
                            "original_rows": len(rows),
                            "evaluated_rows": gate["evaluated_rows"],
                            "known_matches": gate["known_matches_evaluated"],
                            "fallback_rows": gate["fallback_rows"],
                            "comparisons": comparisons,
                        }
                    )
        summary = {
            "version": policy["version"],
            "scope": "conditional-primary-development-oof-routing-intervals",
            "views": views,
            "currency_cost_measured": False,
            "held_out_access_enabled": False,
            "main_experiment_ready": False,
            "deployment_threshold_selected": False,
            "prior_files_modified": False,
            "inference_requests": 0,
            "conditioning": policy["conditioning"],
        }
        for path, wanted in ledger.items():
            if bound.sha(bound.regular(path)) != wanted:
                raise ValueError("Original input changed during bootstrap")
        bound.check_sources(repo, policy)
        provenance = {
            "policy": policy,
            "policy_sha256_lf": POLICY_SHA,
            "head": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True
            ).strip(),
            "python_version": sys.version,
            "input_sha256": {p.relative_to(repo).as_posix(): h for p, h in ledger.items()},
            "new_source_sha256_lf": {
                name: bound.sha((HERE / name).read_bytes().replace(b"\r\n", b"\n"))
                for name in ("run_intervals.py", "intervals.py")
            },
            "bootstrap_plans": {
                p: {k: v for k, v in plan.items() if k != "draws"} for p, plan in plans.items()
            },
        }
        for name, value in {"intervals.json": summary, "provenance.json": provenance}.items():
            (stage / name).write_text(canonical(value) + "\n", encoding="utf-8", newline="\n")
        (stage / "REPORT.md").write_text(
            report(summary, policy["display_caps"]), encoding="utf-8", newline="\n"
        )
        publisher = bound.module(
            "_interval_publisher", repo / context["models"][context["fallback"]]["scorer"]
        )
        publisher.publish_directory(stage, output)
    return summary, policy["display_caps"]


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    if Path.cwd().resolve() != REPO:
        raise SystemExit("Run from the uqroute-tc repository root")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO / "src")
    try:
        for folder, pattern in (
            (str(HERE), "test_*.py"),
            ("tools/development_audits/grouped_routing_v1", "test_*.py"),
            ("tests/unit", "test_routing_development.py"),
        ):
            subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", folder, "-p", pattern],
                cwd=REPO,
                env=env,
                check=True,
            )
        summary, caps = run(REPO)
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        raise SystemExit(
            "Routing interval validation stopped: "
            + str(exc)
            + ". Preserve existing outputs; no model retries."
        ) from None
    print(report(summary, caps))
    print("Saved:", OUTPUT / "REPORT.md")
    print("No inference, held-out access, Git writes or final policy selection performed.")


if __name__ == "__main__":
    main()
