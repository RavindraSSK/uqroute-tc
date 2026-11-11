"""Revalidate four saved development runs and replay three small/fallback policy pairs."""

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
REPO = Path(__file__).resolve().parents[3]
ROOT = Path("artifacts/local_development_audits")
OUTPUT = ROOT / "paired_routing_development_v1"
POLICY_SHA = "aaf434bd4900078d413056207e0a0b45a4b8890a8497d356b79bf02d711b7fe0"


def canonical(value):
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )


def report(summary, results):
    lines = [
        "# Paired development routing diagnostics",
        "",
        "Cached paired replay only. No deployment threshold is frozen or held-out data evaluated.",
        "Reference compliance and ToolEyes name relevance are different endpoints.",
        "",
        (
            "| Small model | Panel | Rows | Small matches | Fallback matches | "
            "Potential rescues | Potential harms | Minimum forced fallback |"
        ),
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for model, panels in summary["paired_panels"].items():
        for panel, entry in panels.items():
            counts = entry["all_pair_outcomes_small_then_fallback"]
            lines.append(
                f"| {model} | {panel} | {entry['rows']} | "
                f"{entry['small_matches']} | {entry['fallback_matches']} | "
                f"{counts['IC']} | {counts['CI']} | {entry['minimum_fallback_rows']} |"
            )
    lines += [
        "",
        "## Fixed development escalation-cap views",
        "",
        (
            "Caps describe diagnostic cuts, not a selected operating objective. "
            "Exact ties are never split."
        ),
        "Random baselines match each actual escalation count on the entire cohort.",
        "",
        (
            "| Model | Panel | Cap | Actual fallback | Gated matches | Rescues | "
            "Harms | Random matched-count mean matches |"
        ),
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for model, scopes in results.items():
        for panel in ("official_reference_compliance", "tooleyes_relevance"):
            entry = scopes["panel/" + panel]
            for view in entry["budget_views"]:
                if not view["feasible"]:
                    lines.append(
                        f"| {model} | {panel} | {view['budget_cap']:.0%} | "
                        "infeasible | unavailable | unavailable | unavailable | unavailable |"
                    )
                    continue
                gate = view["gated"]
                mean = sum(r["reference_matches_known"] for r in view["matched_random"]) / len(
                    view["matched_random"]
                )
                lines.append(
                    f"| {model} | {panel} | {view['budget_cap']:.0%} | "
                    f"{gate['fallback_rows']}/{entry['rows']} | "
                    f"{gate['reference_matches_known']} | {gate['rescues']} | "
                    f"{gate['harms']} | {mean:.2f} |"
                )
    lines += [
        "",
        "## Interpretation",
        "",
        (
            "Potential rescues/harms describe all saved pairs; actual gated "
            "rescues/harms depend on which cases escalate."
        ),
        (
            "Final reference labels remain unchanged even when token evidence or "
            "the returned call is unusable."
        ),
        (
            "Fallback probability availability never filters the cohort. A complete "
            "parsed small candidate and finite mean NLL are required for "
            "acceptance."
        ),
        (
            "Small-only and fallback-only charge one attempt per case; "
            "always-cascade charges both. Gated/random replay charges the small "
            "attempt plus every selected fallback attempt."
        ),
        (
            "Usage includes unsuccessful attempts. Missing usage totals remain null "
            "with known sums and missing-call counts."
        ),
        (
            "Elapsed-time sums are cached sequential request-time proxies, not "
            "online latency or billed GPU seconds. Call counts and token counts do "
            "not establish monetary savings."
        ),
        (
            "Ten fixed random seeds show baseline variability, not confidence "
            "intervals. Related clean/perturbed variants are dependent."
        ),
        (
            "Per-benchmark cutpoints are exploratory views, not a set of deployment "
            "thresholds. ToolEyes benchmark and panel duplicate the same data."
        ),
        (
            "The 26 construction blocks stay outside model-outcome denominators "
            "with no imputation. No existing scores, raw outputs or reference flags "
            "are changed."
        ),
        (
            "Group-separated threshold validation, a fixed final objective, "
            "complete policy costs, recovery, and a shared evaluation freeze remain "
            "required."
        ),
        (
            "Do not choose the best-looking development frontier point and report "
            "it as independent held-out performance."
        ),
    ]
    return "\n".join(lines) + "\n"


def run(repo, output):
    if any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError("Symlink output rejected")
    repo = repo.resolve()
    output = output.absolute()
    root = repo / ROOT
    if output.exists() or not output.resolve().is_relative_to(root) or output.resolve() == root:
        raise ValueError(
            "Fresh output beneath local development artifacts required; preserve existing results"
        )
    raw = (HERE / "policy.json").read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(raw).hexdigest() != POLICY_SHA:
        raise ValueError("Routing analysis policy fingerprint differs")
    policy = json.loads(raw)
    if (
        any(
            policy[k] is not False
            for k in (
                "held_out_access_enabled",
                "main_experiment_ready",
                "routing_threshold_selected",
            )
        )
        or policy["inference_requests"] != 0
    ):
        raise ValueError("Development-only policy boundary differs")
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", policy["baseline_commit"], "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    if subprocess.run(
        ["git", "check-ignore", "-q", "--", str(output.relative_to(repo) / "summary.json")],
        cwd=repo,
    ).returncode:
        raise ValueError("Analysis outputs must stay ignored by Git")
    sys.path.insert(0, str(repo / "src"))
    import inputs

    inputs.check_sources(repo, policy)
    required = [
        root / "full_primary_export_v1" / name
        for name in ("attestation.json", "membership.json", "references.jsonl")
    ]
    required.append(root / "full_primary_audit_v1/inventory.json")
    for settings in policy["models"].values():
        required.extend(
            root / settings["scored"] / name for name in ("scores.json", "summary.json")
        )
        required.extend(
            root / settings["evidence"] / name
            for name in (
                "prepared/manifest.json",
                "prepared/requests.json",
                "run/run_manifest.json",
                "replay/summary.json",
                "replay/records.json",
            )
        )
    missing = [str(path.relative_to(repo)) for path in required if not path.is_file()]
    if missing:
        raise ValueError("Required saved inputs missing: " + "; ".join(missing))
    import analysis

    from uqroute_tc.routing import development as kernel

    if (
        Path(kernel.__file__).resolve()
        != (repo / "src/uqroute_tc/routing/development.py").resolve()
    ):
        raise ValueError("Conflicting routing kernel import")
    root.mkdir(parents=True, exist_ok=True)
    ledger, models, summaries, results, pairs = {}, {}, {}, {}, {}
    with tempfile.TemporaryDirectory(dir=root, prefix="paired-routing-") as temp:
        stage = Path(temp)
        validation = stage / "revalidation"
        validation.mkdir()
        for model, settings in policy["models"].items():
            print("Revalidating saved scoring and full replay:", model, flush=True)
            models[model], summaries[model], _ = inputs.verified_model(
                repo, settings, validation, model, ledger
            )
            if len(models[model]) != policy["rows_per_model"]:
                raise ValueError("Full model denominator differs")
        fallback = models[policy["fallback"]]
        for model in policy["model_order"]:
            pairs[model] = inputs.join(models[model], fallback)
            results[model] = {}
            scopes = {
                **{
                    "panel/" + p: [r for r in pairs[model] if r.panel == p]
                    for p in ("official_reference_compliance", "tooleyes_relevance")
                },
                **{
                    "benchmark/" + b: [r for r in pairs[model] if r.benchmark == b]
                    for b in sorted({r.benchmark for r in pairs[model]})
                },
            }
            for scope, rows in scopes.items():
                print(
                    "Computing paired frontier and fixed-cap baselines:",
                    model,
                    scope,
                    "rows:",
                    len(rows),
                    flush=True,
                )
                results[model][scope] = analysis.analyze_scope(
                    rows, policy["diagnostic_budget_caps"], policy["random_seeds"]
                )
        summary = {
            "version": policy["version"],
            "scope": "paired-primary-development-routing-diagnostics",
            "rows_per_model": policy["rows_per_model"],
            "models": {
                model: {
                    p: summaries[model][p]
                    for p in (
                        "official_reference_compliance",
                        "tooleyes_relevance",
                        "evidence_status_counts",
                    )
                }
                for model in summaries
            },
            "paired_panels": {
                model: {
                    p: {
                        "rows": results[model]["panel/" + p]["rows"],
                        "all_pair_outcomes_small_then_fallback": results[model]["panel/" + p][
                            "all_pair_outcomes_small_then_fallback"
                        ],
                        "small_matches": results[model]["panel/" + p]["baselines"]["small_only"][
                            "reference_matches_known"
                        ],
                        "fallback_matches": results[model]["panel/" + p]["baselines"][
                            "fallback_only"
                        ]["reference_matches_known"],
                        "minimum_fallback_rows": results[model]["panel/" + p][
                            "minimum_fallback_rows"
                        ],
                    }
                    for p in ("official_reference_compliance", "tooleyes_relevance")
                }
                for model in policy["model_order"]
            },
            "held_out_access_enabled": False,
            "main_experiment_ready": False,
            "routing_threshold_selected": False,
            "prior_files_modified": False,
            "inference_requests": 0,
            "currency_cost_measured": False,
        }
        for path, wanted in ledger.items():
            if inputs.sha(inputs.regular(path)) != wanted:
                raise ValueError("An original scoring input changed during analysis")
        inputs.check_sources(repo, policy)
        values = {
            "summary.json": summary,
            "baselines.json": {
                m: {
                    s: {
                        k: r[k]
                        for k in (
                            "rows",
                            "canonical_groups",
                            "all_pair_outcomes_small_then_fallback",
                            "minimum_fallback_rows",
                            "baselines",
                        )
                    }
                    for s, r in scopes.items()
                }
                for m, scopes in results.items()
            },
            "frontiers.json": {
                m: {s: r["frontier"] for s, r in scopes.items()} for m, scopes in results.items()
            },
            "budget_views.json": {
                m: {s: r["budget_views"] for s, r in scopes.items()}
                for m, scopes in results.items()
            },
            "paired_inputs.json": {m: [asdict(row) for row in rows] for m, rows in pairs.items()},
            "provenance.json": {
                "policy": policy,
                "policy_sha256_lf": POLICY_SHA,
                "head": subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=repo, text=True
                ).strip(),
                "input_sha256": {str(p.relative_to(repo).as_posix()): h for p, h in ledger.items()},
                "new_source_sha256_lf": {
                    name: inputs.sha((HERE / name).read_bytes().replace(b"\r\n", b"\n"))
                    for name in ("run_analysis.py", "inputs.py", "analysis.py")
                },
                "held_out_access_enabled": False,
                "inference_requests": 0,
                "note": (
                    "Every frozen score and complete replay was recomputed and "
                    "compared before pairing."
                ),
            },
        }
        for name, value in values.items():
            (stage / name).write_text(canonical(value) + "\n", encoding="utf-8", newline="\n")
        (stage / "REPORT.md").write_text(report(summary, results), encoding="utf-8", newline="\n")
        # Reuse the reviewed no-overwrite, Windows permission-retry publisher.
        scorer = inputs.module(
            "_paired_routing_publisher", repo / policy["models"][policy["fallback"]]["scorer"]
        )
        scorer.publish_directory(stage, output)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if Path.cwd().resolve() != REPO or not (REPO / ".git").exists():
        raise SystemExit("Run from the uqroute-tc repository root")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO / "src")
    try:
        print("Running synthetic routing checks; these are not measured model results.", flush=True)
        for folder, pattern in (
            (str(HERE), "test_*.py"),
            ("tests/unit", "test_routing_development.py"),
        ):
            subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", folder, "-p", pattern],
                cwd=REPO,
                env=env,
                check=True,
            )
        result = run(REPO, args.output)
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        message = str(exc) if type(exc) is ValueError else "Routing input/source validation failed"
        raise SystemExit(
            message + ". Preserve prior evidence; no model retries are needed"
        ) from None
    print(json.dumps(result, indent=2))
    print("Report:", args.output / "REPORT.md")
    print("No inference, held-out access, final threshold selection or Git writes performed.")


if __name__ == "__main__":
    main()
