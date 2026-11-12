"""Compare saved matched small/fallback text against unchanged references on CPU."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROOT = Path("artifacts/local_development_audits")
OUTPUT = ROOT / "recovery_matched_smoke_paired_reference_scoring_v1"
POLICY_SHA = "134836189c964b322df81fc8d338e3d8524f392cca308df1a63017894a320a8a"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


@contextmanager
def workflow_modules():
    """Keep historical generic imports scoped to each checked source checkout."""
    names = ("support", "workflow")
    previous = {n: sys.modules.get(n) for n in names}
    for n in names:
        sys.modules.pop(n, None)
    try:
        yield
    finally:
        for n in names:
            sys.modules.pop(n, None)
            if previous[n] is not None:
                sys.modules[n] = previous[n]


def compare_original_scores(original, reproduced):
    if (
        set(original) != {"records.json", "summary.json", "provenance.json"}
        or original != reproduced
    ):
        raise ValueError("Original small reference scores must reproduce byte for byte")


def score_pair(
    request,
    small_request,
    episode,
    saved,
    response,
    initial_request,
    parent_score,
    reference,
    member,
    parser,
    scorer,
    workflow,
    frozen,
    legacy,
):
    """Score the new role only after binding its exact history to the rescored parent."""
    body = request["request"]
    if (
        request["stage"] != "postfault_fallback"
        or body["model"] != "Qwen/Qwen2.5-14B-Instruct-AWQ"
        or small_request["stage"] != "postfault_small"
        or request["paired_small_request_id"] != small_request["request_id"]
        or parent_score["request_id"] != small_request["request_id"]
        or request["request_id"]
        != legacy.sha(legacy.canonical([episode["episode_key"], "postfault_fallback"]).encode())
        or request["request_sha256"] != legacy.sha(legacy.canonical(body).encode())
        or request["context_messages_sha256"]
        != legacy.sha(legacy.canonical(body["messages"]).encode())
        or {n: v for n, v in body.items() if n != "model"}
        != {n: v for n, v in small_request["request"].items() if n != "model"}
        or any(
            row["episode_key"] != episode["episode_key"]
            for row in (request, small_request, saved, parent_score)
        )
        or saved["request_id"] != request["request_id"]
        or any(
            row["context_messages_sha256"] != episode["context_messages_sha256"]
            for row in (request, small_request, saved)
        )
        or saved["transition_injected"] is not True
        or saved["ledger_state"] != "injected_response_saved"
        or saved["http_status"] != 200
        or parent_score["transition_injected"] is not True
        or initial_request["case_key"] != episode["initial_case_key"]
        or initial_request["messages_sha256"] != episode["initial_messages_sha256"]
        or parent_score["initial_case_key"] != initial_request["case_key"]
        or any(
            parent_score[n] != episode[n] or initial_request[n] != episode[n]
            for n in ("benchmark", "canonical_base_id")
        )
        or parent_score["fault_type"] != episode["fault_type"]
    ):
        raise ValueError("Known fallback response and unchanged complete parent history required")
    # The original request supplies only the frozen clean label identity. Its
    # original fault context was independently reproduced by the small scorer;
    # the exact fallback message equality above carries that binding to this role.
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
    if (
        type(after["official_score"]["correct"]) is not bool
        or type(parent_score["postfault_reference_match"]) is not bool
        or type(parent_score["initial_reference_match"]) is not bool
        or parent_score["postfault_reference_match"]
        != parent_score["postfault_score"]["official_score"]["correct"]
        or parent_score["initial_reference_match"]
        != parent_score["initial_score"]["official_score"]["correct"]
        or after["panel"] != parent_score["panel"]
        or after["original_eval_config"] != parent_score["postfault_score"]["original_eval_config"]
        or after["official_labels_changed"] is not False
        or after["ambiguity_exclusion_applied"] is not False
    ):
        raise ValueError("Original reference endpoint and flags must remain unchanged")
    return {
        "episode_key": episode["episode_key"],
        "request_id": request["request_id"],
        "paired_small_request_id": small_request["request_id"],
        "initial_case_key": initial_request["case_key"],
        "canonical_base_id": episode["canonical_base_id"],
        "benchmark": episode["benchmark"],
        "fault_type": episode["fault_type"],
        "panel": after["panel"],
        "transition_injected": True,
        "initial_reference_match": parent_score["initial_reference_match"],
        "small_reference_match": parent_score["postfault_reference_match"],
        "fallback_reference_match": after["official_score"]["correct"],
        "small_parser_status": parent_score["canonical_parser_status"],
        "fallback_parser_status": saved["validation"]["parser_status"],
        "fallback_score": after,
        "semantic_fault_recovery": "not_evaluated",
        "execution_success": "not_evaluated",
    }


def aggregate(rows):
    panels = ("official_reference_compliance", "tooleyes_relevance")
    if len({r["episode_key"] for r in rows}) != len(rows) or any(
        r["panel"] not in panels for r in rows
    ):
        raise ValueError("Unique paired episodes and separate approved endpoints required")
    if any(
        type(r[n]) is not bool
        for r in rows
        for n in ("initial_reference_match", "small_reference_match", "fallback_reference_match")
    ):
        raise ValueError("Every paired reference outcome must be known; no imputation")

    def count(items):
        return {
            "rows": len(items),
            "groups": len({(r["benchmark"], r["canonical_base_id"]) for r in items}),
            "initial_matches_repeated_per_episode": sum(
                r["initial_reference_match"] for r in items
            ),
            "small_postfault_matches": sum(r["small_reference_match"] for r in items),
            "fallback_postfault_matches": sum(r["fallback_reference_match"] for r in items),
            "small_mismatch_to_fallback_match": sum(
                not r["small_reference_match"] and r["fallback_reference_match"] for r in items
            ),
            "small_match_to_fallback_mismatch": sum(
                r["small_reference_match"] and not r["fallback_reference_match"] for r in items
            ),
            "both_match": sum(
                r["small_reference_match"] and r["fallback_reference_match"] for r in items
            ),
            "both_mismatch": sum(
                not r["small_reference_match"] and not r["fallback_reference_match"] for r in items
            ),
            "small_parser_status_counts": dict(Counter(r["small_parser_status"] for r in items)),
            "fallback_parser_status_counts": dict(
                Counter(r["fallback_parser_status"] for r in items)
            ),
        }

    result = {}
    for name in panels:
        items = [r for r in rows if r["panel"] == name]
        result[name] = count(items) | {
            "by_fault": {
                fault: count([r for r in items if r["fault_type"] == fault])
                for fault in sorted({r["fault_type"] for r in items})
            }
        }
    return {
        "rows": len(rows),
        "groups": len({(r["benchmark"], r["canonical_base_id"]) for r in rows}),
        "panels": result,
        "generation_requests_sent": 0,
        "rows_excluded": 0,
        "reference_labels_changed": False,
        "held_out_access_enabled": False,
        "main_experiment_ready": False,
        "final_protocol_frozen": False,
        "policy_evaluation": False,
        "semantic_fault_recovery": "not_evaluated",
        "execution_success": "not_evaluated",
    }


def report(summary):
    lines = [
        "# Matched development smoke: unchanged-reference comparison",
        "",
        "Five selected groups, six dependent fault scenarios each. No execution-success claim.",
        "",
        "| Panel | Rows / groups | Initial (repeated) | Small post-fault | "
        "Fallback post-fault | Reference matches gained | Reference matches lost |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, p in summary["panels"].items():
        lines.append(
            f"| {name} | {p['rows']} / {p['groups']} | "
            f"{p['initial_matches_repeated_per_episode']} | {p['small_postfault_matches']} | "
            f"{p['fallback_postfault_matches']} | {p['small_mismatch_to_fallback_match']} | "
            f"{p['small_match_to_fallback_mismatch']} |"
        )
    lines += [
        "",
        "| Panel | Fault | Rows | Small matches | Fallback matches | Gained | Lost |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for name, p in summary["panels"].items():
        for fault, v in p["by_fault"].items():
            lines.append(
                f"| {name} | {fault} | {v['rows']} | {v['small_postfault_matches']} | "
                f"{v['fallback_postfault_matches']} | {v['small_mismatch_to_fallback_match']} | "
                f"{v['small_match_to_fallback_mismatch']} |"
            )
    lines += [
        "",
        "Original small scores reproduce exactly; all 30 pairs and original labels remain.",
        "Reference gains/losses compare model text, not executed recovery.",
        "ToolEyes name relevance remains separate from reference tool/argument compliance.",
        "A semantically appropriate refusal may mismatch the reference; no adjudication occurs.",
        "Auth/schema feedback supplies no new credentials or replacement schema.",
        "Initial outcomes repeat across six faults, not 30 independent initial generations.",
        "Pinned model defaults remain: repetition penalty 1.1 (small), 1.05 (fallback).",
        "Both outputs already exist per pair; no uncertainty-gated policy was executed.",
        "No threshold, interval, best policy, monetary saving or held-out result is selected.",
        "CPU only; no generation, external judge or tool execution requests.",
    ]
    return "\n".join(lines) + "\n"


def verified_payloads(repo, policy, original, ledger):
    owner = repo / ROOT / "recovery_fallback_smoke_import_f85c1c51"
    evidence = owner / "evidence"
    importer = module(
        "_paired_fallback_import",
        repo / "tools/development_audits/recovery_fallback_smoke_import_v1/import_smoke.py",
    )
    index = original.checked(
        evidence / "metadata/export_file_hashes.json",
        policy["fallback_export_manifest_sha256"],
        ledger,
    )
    expected = json.loads(index)
    files = {p.relative_to(evidence).as_posix() for p in evidence.rglob("*") if p.is_file()}
    if files != set(expected) | {"metadata/export_file_hashes.json"} or any(
        p.is_symlink() for p in evidence.rglob("*")
    ):
        raise ValueError("Exact imported fallback file inventory required")
    payloads = {n: original.checked(evidence / n, h, ledger) for n, h in expected.items()}
    payloads["metadata/export_file_hashes.json"] = index
    importer.verify_members(payloads)
    importer.check_runtime_evidence(payloads)
    importer.check_fallback_runtime(payloads)
    importer.paired_parent_check(repo, payloads)
    for n in ("records.json", "summary.json"):
        path = owner / "reproduced/replay" / n
        raw = original.regular(path)
        if raw != payloads["replay/" + n]:
            raise ValueError("Owner independent fallback replay differs")
        ledger[path] = original.sha(raw)
    client = module("_paired_verified_client", evidence / "metadata/client.py")
    plan, requests, episodes, dispatch, support, workflow = client.load_plan(
        owner / "reproduced/repo", evidence / "prepared"
    )
    state = dispatch.replay(
        requests, evidence / "run", client.binding_for(evidence, plan, requests, support, workflow)
    )
    if state["saved_responses"] != 30 or state["unknown_slots"] or state["known_http_errors"]:
        raise ValueError("All thirty known fallback outcomes required")
    return payloads, requests, episodes


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
        raise ValueError("Fresh paired scoring output required; preserve prior results")
    if subprocess.run(
        ["git", "check-ignore", "-q", "--", str(OUTPUT / "summary.json")], cwd=repo
    ).returncode:
        raise ValueError("Detailed paired scores must remain ignored")
    # No reference data is opened before policy/source and original attestation checks.
    import hashlib

    policy_path = HERE / "policy.json"
    if any(p.is_symlink() for p in (policy_path, *policy_path.parents)):
        raise ValueError("Regular paired scoring policy required")
    raw = policy_path.read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(raw).hexdigest() != POLICY_SHA:
        raise ValueError("Paired scoring policy fingerprint differs")
    policy = json.loads(raw)
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", policy["baseline_commit"], "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    for n, h in policy["source_sha256_lf"].items():
        path = repo / n
        if (
            any(p.is_symlink() for p in (path, *path.parents))
            or hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() != h
        ):
            raise ValueError("Pinned paired scoring dependency differs: " + n)
    original = module(
        "_paired_original_score",
        repo / "tools/development_audits/recovery_smoke_scoring_v1/score_smoke.py",
    )
    root = repo / ROOT
    ledger = {}
    with workflow_modules():
        payloads, requests, episodes = verified_payloads(repo, policy, original, ledger)
    small_root = root / "recovery_smoke_reference_scoring_v1"
    prior_scores = {
        n: original.regular(small_root / n)
        for n in ("records.json", "summary.json", "provenance.json")
    }
    ledger.update({small_root / n: original.sha(raw) for n, raw in prior_scores.items()})
    with tempfile.TemporaryDirectory(dir=root, prefix="paired-score-") as folder:
        stage = Path(folder)
        original.OUTPUT = stage.relative_to(repo) / "small_replay"
        with workflow_modules():
            original.score(repo)
        reproduced = {n: original.regular(stage / "small_replay" / n) for n in prior_scores}
        compare_original_scores(prior_scores, reproduced)
        # Carry the original scorer's verified input hashes through final publication.
        for n, h in json.loads(reproduced["provenance.json"])["input_sha256"].items():
            if repo / n in ledger and ledger[repo / n] != h:
                raise ValueError("Original input binding differs")
            ledger[repo / n] = h
        legacy = module("_paired_reference_legacy", repo / policy["scorer"])
        rules = legacy.policy()
        with workflow_modules():
            workflow, frozen, parser, scorer = legacy.load_dependencies(repo, rules)
        refs, inventory = legacy.development_inputs(
            root / "full_primary_export_v1",
            root / "full_primary_audit_v1/inventory.json",
            rules,
            ledger,
        )
        initial_root = root / policy["initial_evidence"]
        initial_plan, initials = workflow.load_plan(
            repo, initial_root / "prepared", rules["prepared_manifest_sha256"]
        )
        config = json.loads(original.regular(repo / "docs/config/task1_single_sample_v1.json"))
        if initial_plan["model_settings"] != config["models"][0]:
            raise ValueError("Original initial small configuration differs")
        initials = legacy.unique_index(initials)
        parent_scores = {r["request_id"]: r for r in json.loads(prior_scores["records.json"])}
        small_path = root / "recovery_smoke_qwen15b_import_dd91a73f/evidence/prepared/requests.json"
        smalls = {r["request_id"]: r for r in json.loads(original.regular(small_path))}
        saved = {r["request_id"]: r for r in json.loads(payloads["replay/records.json"])}
        if len(parent_scores) != 30 or set(parent_scores) != set(smalls):
            raise ValueError("Complete original scored parent cohort required")
        rows = []
        for request in requests:
            ep = episodes[request["episode_key"]]
            key = ep["initial_case_key"]
            parent = request["paired_small_request_id"]
            response = json.loads(
                payloads["run/cases/" + request["request_id"] + "/http_response.bin"]
            )
            rows.append(
                score_pair(
                    request,
                    smalls[parent],
                    ep,
                    saved[request["request_id"]],
                    response,
                    initials[key],
                    parent_scores[parent],
                    refs[key],
                    inventory[key],
                    parser,
                    scorer,
                    workflow,
                    frozen,
                    legacy,
                )
            )
        summary = aggregate(rows)
        if summary["rows"] != 30 or summary["groups"] != 5:
            raise ValueError("Complete thirty-pair, five-group smoke required")
        provenance = {
            "policy": policy,
            "policy_sha256_lf": POLICY_SHA,
            "small_scoring_recomputed_exactly": True,
            "original_small_scoring_sha256": {
                n: original.sha(raw) for n, raw in prior_scores.items()
            },
            "input_sha256": {p.relative_to(repo).as_posix(): h for p, h in ledger.items()},
        }
        for name, value in (
            ("summary.json", summary),
            ("records.json", rows),
            ("provenance.json", provenance),
        ):
            (stage / name).write_text(
                legacy.canonical(value) + "\n", encoding="utf-8", newline="\n"
            )
        (stage / "REPORT.md").write_text(report(summary), encoding="utf-8", newline="\n")
        for path, h in ledger.items():
            if original.sha(original.regular(path)) != h:
                raise ValueError("Original evidence/reference changed during scoring")
        publisher = module(
            "_paired_score_publish",
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
            "Paired smoke scoring stopped: "
            + str(exc)
            + ". Preserve all evidence; no model requests."
        ) from None
    print(report(summary))
    print("Saved:", OUTPUT)
    print(
        "CPU only; original references/cohort preserved; execution and policy effects unevaluated."
    )


if __name__ == "__main__":
    main()
