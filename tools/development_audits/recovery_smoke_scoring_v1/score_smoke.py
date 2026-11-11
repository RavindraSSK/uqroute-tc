"""Score saved smoke text against unchanged clean references; CPU only."""

from __future__ import annotations

import argparse
import ast
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
OUTPUT = ROOT / "recovery_smoke_reference_scoring_v1"
POLICY_SHA = "8be68c1925a863cc67e29c8ddd80b13baf18c9834ab99ec91bf042fee9e716ba"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def regular(path):
    if not path.is_file() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Expected a regular input without symlinks")
    return path.read_bytes()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def checked(path, expected, ledger):
    raw = regular(path)
    if sha(raw) != expected:
        raise ValueError("Evidence fingerprint differs: " + path.name)
    ledger[path] = expected
    return raw


def check_transition_writer(source):
    """Verify the published writer copies the original reference/config in transition mode."""
    tree = ast.parse(source)
    writers = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "out_record" for t in n.targets)
        and isinstance(n.value, ast.Dict)
    ]
    if len(writers) != 1:
        raise ValueError("Released prediction writer differs")
    values = {
        k.value: v
        for k, v in zip(writers[0].value.keys, writers[0].value.values, strict=True)
        if isinstance(k, ast.Constant)
    }
    expected = {"golden_answers": 's["golden_answers"]', "eval_config": 's.get("eval_config")'}
    for name, code in expected.items():
        if ast.dump(values[name]) != ast.dump(ast.parse(code, mode="eval").body):
            raise ValueError("Released Transition reference/config inheritance changed")


def score_episode(
    request,
    episode,
    saved,
    response,
    initial_request,
    initial_response,
    initial_saved,
    reference,
    member,
    parser,
    scorer,
    workflow,
    frozen,
    legacy,
    kernel,
    errors,
):
    if (
        saved["transition_injected"] is not True
        or saved["ledger_state"] != "injected_response_saved"
        or request["stage"] != "postfault_small"
        or episode["initial_case_key"] != initial_request["case_key"]
        or episode["initial_messages_sha256"] != initial_request["messages_sha256"]
        or episode["benchmark"] != initial_request["benchmark"]
        or episode["canonical_base_id"] != initial_request["canonical_base_id"]
        or saved["episode_key"] != episode["episode_key"]
        or saved["request_id"] != request["request_id"]
        or saved["context_messages_sha256"] != request["context_messages_sha256"]
    ):
        raise ValueError("Known injected, context-bound small-stage smoke episode required")
    initial_raw = initial_response["choices"][0]["message"]["content"]
    calls = parser(initial_raw, initial_request["benchmark"])
    context = kernel.fault_context(
        initial_request["request"]["messages"], initial_raw, calls, episode["fault_type"], errors
    )
    if (
        context["injection_eligible"] is not True
        or context["messages"] != request["request"]["messages"]
        or context["messages_sha256"] != request["context_messages_sha256"]
        or context["messages_sha256"] != episode["context_messages_sha256"]
    ):
        raise ValueError("Preserved initial output/released fault context differs")
    # The legacy request identifies the clean label source. The new context was
    # independently bound above; it is never substituted with a static response.
    before = legacy.score_case(
        initial_request,
        initial_response,
        reference,
        member,
        parser,
        scorer,
        workflow,
        frozen,
        initial_saved,
    )
    after = legacy.score_case(
        initial_request,
        response,
        reference,
        member,
        parser,
        scorer,
        workflow,
        frozen,
        saved["validation"],
    )
    for result in (before, after):
        if (
            type(result["official_score"]["correct"]) is not bool
            or result["official_labels_changed"] is not False
            or result["ambiguity_exclusion_applied"] is not False
        ):
            raise ValueError("Reference outcomes/flags must remain unchanged")
    return {
        "episode_key": episode["episode_key"],
        "request_id": request["request_id"],
        "initial_case_key": initial_request["case_key"],
        "canonical_base_id": episode["canonical_base_id"],
        "benchmark": episode["benchmark"],
        "fault_type": episode["fault_type"],
        "transition_injected": True,
        "panel": after["panel"],
        "initial_reference_match": before["official_score"]["correct"],
        "postfault_reference_match": after["official_score"]["correct"],
        "postfault_score": after,
        "initial_score": before,
        "canonical_parser_status": saved["validation"]["parser_status"],
        "whole_output_scores": saved["validation"]["whole_output_scores"],
        "semantic_fault_recovery": "not_evaluated",
        "execution_success": "not_evaluated",
    }


def aggregate(rows):
    def count(items):
        return {
            "rows": len(items),
            "groups": len({r["canonical_base_id"] for r in items}),
            "initial_matches_repeated_per_episode": sum(
                r["initial_reference_match"] for r in items
            ),
            "postfault_matches": sum(r["postfault_reference_match"] for r in items),
            "match_to_mismatch": sum(
                r["initial_reference_match"] and not r["postfault_reference_match"] for r in items
            ),
            "mismatch_to_match": sum(
                not r["initial_reference_match"] and r["postfault_reference_match"] for r in items
            ),
            "both_match": sum(
                r["initial_reference_match"] and r["postfault_reference_match"] for r in items
            ),
            "both_mismatch": sum(
                not r["initial_reference_match"] and not r["postfault_reference_match"]
                for r in items
            ),
            "parser_status_counts": dict(Counter(r["canonical_parser_status"] for r in items)),
        }

    panels = {}
    for name in ("official_reference_compliance", "tooleyes_relevance"):
        items = [r for r in rows if r["panel"] == name]
        panels[name] = count(items) | {
            "by_fault": {
                fault: count([r for r in items if r["fault_type"] == fault])
                for fault in sorted({r["fault_type"] for r in items})
            }
        }
    return {
        "rows": len(rows),
        "groups": len({r["canonical_base_id"] for r in rows}),
        "panels": panels,
        "generation_requests_sent": 0,
        "no_fault_injected_in_smoke": 0,
        "unknown_outcomes_in_smoke": 0,
        "reference_labels_changed": False,
        "held_out_access_enabled": False,
        "main_experiment_ready": False,
        "semantic_fault_recovery": "not_evaluated",
        "execution_success": "not_evaluated",
        "final_protocol_frozen": False,
    }


def report(summary):
    lines = [
        "# Development smoke: reference compliance after fault feedback",
        "",
        "Five selected groups, six dependent fault scenarios each. No execution-success claim.",
        "",
        "| Panel | Rows / groups | Initial matches (repeated per episode) | "
        "Post-fault matches | Match to mismatch | Mismatch to match |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, p in summary["panels"].items():
        lines.append(
            f"| {name} | {p['rows']} / {p['groups']} | "
            f"{p['initial_matches_repeated_per_episode']} | {p['postfault_matches']} | "
            f"{p['match_to_mismatch']} | {p['mismatch_to_match']} |"
        )
    lines += ["", "| Panel | Fault | Rows | Post-fault reference matches |", "|---|---|---:|---:|"]
    for name, p in summary["panels"].items():
        for fault, values in p["by_fault"].items():
            lines.append(f"| {name} | {fault} | {values['rows']} | {values['postfault_matches']} |")
    lines += [
        "",
        "Original clean references, eval_config and review flags remain unchanged.",
        "ToolEyes name relevance is separate from reference tool/argument compliance.",
        "A reference mismatch may include a semantically appropriate refusal; "
        "no adjudication is performed.",
        "Auth/schema feedback does not supply new credentials or a replacement schema.",
        "Initial outcomes are reused across six faults, not 30 independent initial generations.",
        "These paired changes are text/reference diagnostics, "
        "not executed recovery rescues or policy effects.",
        "No threshold, confidence interval, best policy, monetary saving "
        "or held-out result is selected.",
        "All scoring is CPU-only and deterministic; no model or external judge requests.",
    ]
    return "\n".join(lines) + "\n"


def score(repo):
    prior = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        return _score(repo.resolve())
    finally:
        sys.dont_write_bytecode = prior


def _score(repo):
    output = repo / OUTPUT
    if output.exists() or any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError("Fresh smoke scoring output required; preserve existing results")
    if subprocess.run(
        ["git", "check-ignore", "-q", "--", str(OUTPUT / "summary.json")], cwd=repo
    ).returncode:
        raise ValueError("Detailed smoke scores must remain ignored")
    raw = regular(HERE / "policy.json").replace(b"\r\n", b"\n")
    if sha(raw) != POLICY_SHA:
        raise ValueError("Scoring policy fingerprint differs")
    policy = json.loads(raw)
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", policy["baseline_commit"], "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    for name, expected in policy["source_sha256_lf"].items():
        if sha(regular(repo / name).replace(b"\r\n", b"\n")) != expected:
            raise ValueError("Pinned scoring dependency differs: " + name)
    legacy = module("_recovery_smoke_legacy_score", repo / policy["scorer"])
    rules = legacy.policy()
    workflow, frozen, parser, scorer = legacy.load_dependencies(repo, rules)
    source = regular(
        repo / "tools/development_audits/full_development_v1/official_runner.py"
    ).decode()
    check_transition_writer(source)
    preparer = module(
        "_recovery_smoke_preparer",
        repo / "tools/development_audits/recovery_development_v1/prepare.py",
    )
    errors = preparer.released_templates(source)
    sys.path.insert(0, str(repo / "src"))
    from uqroute_tc.routing import recovery as kernel

    root = repo / ROOT
    owner = root / "recovery_smoke_qwen15b_import_dd91a73f"
    evidence = owner / "evidence"
    importer = module(
        "_recovery_smoke_import",
        repo / "tools/development_audits/recovery_smoke_import_v1/import_smoke.py",
    )
    ledger = {}
    index = checked(
        evidence / "metadata/export_file_hashes.json",
        policy["smoke_export_manifest_sha256"],
        ledger,
    )
    expected = json.loads(index)
    if any(p.is_symlink() for p in evidence.rglob("*")):
        raise ValueError("Symlink smoke evidence")
    files = {p.relative_to(evidence).as_posix() for p in evidence.rglob("*") if p.is_file()}
    if files != set(expected) | {"metadata/export_file_hashes.json"}:
        raise ValueError("Imported smoke file inventory differs")
    payloads = {
        name: checked(evidence / name, fingerprint, ledger)
        for name, fingerprint in expected.items()
    }
    payloads["metadata/export_file_hashes.json"] = index
    importer.verify_members(payloads)
    importer.check_runtime_evidence(payloads)
    for name in ("records.json", "summary.json"):
        if regular(owner / "reproduced/replay" / name) != payloads["replay/" + name]:
            raise ValueError("Owner independent replay differs")
    smoke_client = module("_recovery_scoring_client", evidence / "metadata/client.py")
    plan, requests, episodes, smoke_ledger, support, smoke_workflow = smoke_client.load_plan(
        owner / "reproduced/repo", evidence / "prepared"
    )
    binding = smoke_client.binding_for(evidence, plan, requests, support, smoke_workflow)
    ledger_state = smoke_ledger.replay(requests, evidence / "run", binding)
    if (
        ledger_state["saved_responses"] != 30
        or ledger_state["unknown_slots"]
        or ledger_state["known_http_errors"]
    ):
        raise ValueError("Complete smoke outcomes required; unknowns are not reference failures")
    # The attestation gates all reference-sidecar access. No raw/test data is read.
    refs, inventory = legacy.development_inputs(
        root / "full_primary_export_v1",
        root / "full_primary_audit_v1/inventory.json",
        rules,
        ledger,
    )
    initial_root = root / policy["initial_evidence"]
    initial_manifest, initial_requests = workflow.load_plan(
        repo, initial_root / "prepared", rules["prepared_manifest_sha256"]
    )
    if initial_manifest["model_settings"] != plan["model_settings"]:
        raise ValueError("Initial/recovery small model settings differ")
    by_key = legacy.unique_index(initial_requests)
    saved = {r["request_id"]: r for r in json.loads(payloads["replay/records.json"])}
    results = []
    for request in requests:
        ep = episodes[request["episode_key"]]
        key = ep["initial_case_key"]
        initial = by_key[key]
        folder = "run/cases/" + sha(key.encode()) + "/"

        def initial_file(name, folder=folder):
            return json.loads(
                checked(
                    initial_root / (folder + name),
                    rules["evidence_file_sha256"][folder + name],
                    ledger,
                )
            )

        initial_response = initial_file("http_response.bin")
        metadata = initial_file("response_metadata.json")
        if (
            metadata["http_status"] != 200
            or ep["initial_response_sha256"]
            != rules["evidence_file_sha256"][folder + "http_response.bin"]
        ):
            raise ValueError("Known initial response/source fingerprint differs")
        initial_saved = initial_file("validation.json")
        response = json.loads(payloads["run/cases/" + request["request_id"] + "/http_response.bin"])
        results.append(
            score_episode(
                request,
                ep,
                saved[request["request_id"]],
                response,
                initial,
                initial_response,
                initial_saved,
                refs[key],
                inventory[key],
                parser,
                scorer,
                workflow,
                frozen,
                legacy,
                kernel,
                errors,
            )
        )
    summary = aggregate(results)
    if summary["rows"] != 30 or summary["groups"] != 5:
        raise ValueError("Full thirty-episode smoke cohort required")
    with tempfile.TemporaryDirectory(dir=root, prefix="recovery-smoke-score-") as folder:
        stage = Path(folder)
        values = {
            "summary.json": summary,
            "records.json": results,
            "provenance.json": {
                "policy": policy,
                "policy_sha256_lf": POLICY_SHA,
                "input_sha256": {p.relative_to(repo).as_posix(): h for p, h in ledger.items()},
            },
        }
        for name, value in values.items():
            (stage / name).write_text(
                legacy.canonical(value) + "\n", encoding="utf-8", newline="\n"
            )
        (stage / "REPORT.md").write_text(report(summary), encoding="utf-8", newline="\n")
        for path, expected in ledger.items():
            if sha(regular(path)) != expected:
                raise ValueError("Original evidence/reference changed during scoring")
        publisher = module(
            "_recovery_smoke_score_publish",
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
        summary = score(REPO)
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        raise SystemExit(
            "Smoke reference scoring stopped: "
            + str(exc)
            + ". Preserve evidence; no model requests."
        ) from None
    print(report(summary))
    print("Saved:", OUTPUT)
    print(
        "CPU only; original labels preserved; execution and semantic recovery remain unevaluated."
    )


if __name__ == "__main__":
    main()
