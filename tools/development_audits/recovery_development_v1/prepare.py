"""Prepare reference-free fault-conditioned development plans; no inference or scoring."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROOT = Path("artifacts/local_development_audits")
OUTPUT = ROOT / "recovery_development_preparation_v1"
POLICY_SHA = "3cfaac0da95819f99a26816a32cd54935f9d87b940eff8f4b1c9614d05ad06da"


def canonical(value):
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def released_templates(raw):
    tree = ast.parse(raw)
    nodes = [
        n
        for n in tree.body
        if isinstance(n, ast.AnnAssign)
        and isinstance(n.target, ast.Name)
        and n.target.id == "TRANSITION_ERROR_MESSAGES"
    ]
    if len(nodes) != 1:
        raise ValueError("Released transition template definition differs")
    errors = ast.literal_eval(nodes[0].value)
    expected = {
        "timeout",
        "rate_limit",
        "auth_error",
        "server_error",
        "malformed_response",
        "schema_drift",
    }
    if set(errors) != expected or any(not isinstance(v, str) or not v for v in errors.values()):
        raise ValueError("Released fault taxonomy differs")
    return errors


def episode(request, initial_raw, calls, model_key, fault, errors, fallback_id, kernel):
    if request["source_file"] != "clean.jsonl":
        raise ValueError("Recovery initial source must be a clean anchor")
    if kernel.messages_sha256(request["request"]["messages"]) != request["messages_sha256"]:
        raise ValueError("Initial prompt fingerprint differs")
    context = kernel.fault_context(
        request["request"]["messages"], initial_raw, calls, fault, errors
    )
    key = sha(canonical([model_key, request["case_key"], fault]).encode())
    record = {
        "episode_key": key,
        "initial_case_key": request["case_key"],
        "canonical_base_id": request["canonical_base_id"],
        "benchmark": request["benchmark"],
        "population": "primary",
        "split": "development",
        "source_file": "clean.jsonl",
        "fault_type": fault,
        "initial_has_official_call": bool(calls),
        "injection_eligible": context["injection_eligible"],
        "transition_injected": context["transition_injected"],
        "no_injection_reason": context["reason"],
        "context_messages_sha256": context["messages_sha256"],
        "initial_messages_sha256": request["messages_sha256"],
    }
    roles = {}
    if context["injection_eligible"]:
        for role, model in (
            ("postfault_small", request["request"]["model"]),
            ("postfault_fallback", fallback_id),
        ):
            body = deepcopy(request["request"])
            body["model"] = model
            body["messages"] = deepcopy(context["messages"])
            roles[role] = {
                "request_id": sha(canonical([key, role]).encode()),
                "episode_key": key,
                "stage": role,
                "context_messages_sha256": context["messages_sha256"],
                "request_sha256": sha(canonical(body).encode()),
                "request": body,
            }
    return record, roles


def prepare(repo):
    repo = repo.resolve()
    root, output = repo / ROOT, repo / OUTPUT
    if output.exists() or any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError("Fresh preparation required; preserve existing recovery plans")
    raw = (HERE / "policy.json").read_bytes().replace(b"\r\n", b"\n")
    if sha(raw) != POLICY_SHA:
        raise ValueError("Recovery preparation policy fingerprint differs")
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
        raise ValueError("Preparation outputs must remain ignored")
    for name, wanted in policy["source_sha256_lf"].items():
        path = repo / name
        if (
            any(p.is_symlink() for p in (path, *path.parents))
            or sha(path.read_bytes().replace(b"\r\n", b"\n")) != wanted
        ):
            raise ValueError("Pinned source differs: " + name)
    sys.path.insert(0, str(repo / "src"))
    from uqroute_tc.routing import recovery as kernel

    if Path(kernel.__file__).resolve() != (repo / "src/uqroute_tc/routing/recovery.py").resolve():
        raise ValueError("Conflicting recovery kernel import")
    bound = load_module(
        "_recovery_bound", repo / "tools/development_audits/paired_routing_v1/inputs.py"
    )
    bound.check_sources(repo, policy)
    source = bound.regular(repo / "tools/development_audits/full_development_v1/official_runner.py")
    errors = released_templates(source.decode())
    if set(errors) != set(policy["fault_types"]):
        raise ValueError("Fault list differs from source")
    inventory_path = root / "full_primary_audit_v1/inventory.json"
    inventory_raw = bound.regular(inventory_path)
    if sha(inventory_raw) != policy["inventory_sha256"]:
        raise ValueError("Development inventory fingerprint differs")
    inventory = {r["case_key"]: r for r in json.loads(inventory_raw)}
    config = json.loads(bound.regular(repo / "docs/config/task1_single_sample_v1.json"))
    fallbacks = [m for m in config["models"] if m["role"] == "fallback"]
    if len(fallbacks) != 1:
        raise ValueError("Expected one frozen fallback role")
    fallback = fallbacks[0]
    ledger, reports, transfers = {inventory_path: sha(inventory_raw)}, {}, {}
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root, prefix="recovery-prepare-") as tmp:
        stage = Path(tmp)
        same_cases = None
        for model_key in policy["model_order"]:
            print(
                "Revalidating saved initial model, without reference scoring:",
                model_key,
                flush=True,
            )
            settings = policy["models"][model_key]
            scorer = bound.module("_recovery_initial_" + model_key, repo / settings["scorer"])
            rules = scorer.policy()
            evidence = root / settings["evidence"]
            files = set()
            for path in evidence.rglob("*"):
                if path.is_symlink():
                    raise ValueError("Symlink initial evidence")
                if path.is_file():
                    files.add(path.relative_to(evidence).as_posix())
            if files != set(rules["evidence_file_sha256"]):
                raise ValueError("Initial evidence inventory differs: " + model_key)
            for name, wanted in rules["evidence_file_sha256"].items():
                path = evidence / name
                data = bound.regular(path)
                if sha(data) != wanted:
                    raise ValueError("Initial evidence fingerprint differs: " + name)
                ledger[path] = wanted
            workflow, _, official_parser, _ = scorer.load_dependencies(repo, rules)
            manifest, requests = workflow.load_plan(
                repo, evidence / "prepared", rules["prepared_manifest_sha256"]
            )
            if (
                manifest["model_settings"]["role"] != "small"
                or manifest["model_settings"]["model_id"] != rules["model_id"]
            ):
                raise ValueError("Initial model role differs")
            replay = stage / (model_key + "_initial_replay")
            workflow.replay(
                repo,
                evidence / "prepared",
                rules["prepared_manifest_sha256"],
                evidence / "run",
                replay,
            )
            for name in ("summary.json", "records.json"):
                if json.loads(bound.regular(replay / name)) != json.loads(
                    bound.regular(evidence / "replay" / name)
                ):
                    raise ValueError("Initial full replay differs: " + model_key)
            records = scorer.unique_index(json.loads(bound.regular(replay / "records.json")))
            clean = sorted(
                [r for r in requests if r["source_file"] == "clean.jsonl"],
                key=lambda r: r["case_key"],
            )
            if len(clean) != policy["initial_clean_rows_per_model"] or len(
                {r["canonical_base_id"] for r in clean}
            ) != len(clean):
                raise ValueError("Expected one preserved clean case per development group")
            identities = [
                (r["case_key"], r["canonical_base_id"], r["benchmark"], r["messages_sha256"])
                for r in clean
            ]
            if same_cases is not None and identities != same_cases:
                raise ValueError("Initial model clean cohorts/prompts differ")
            same_cases = identities
            episodes, small_requests, fallback_requests = [], [], []
            for request in clean:
                member = inventory[request["case_key"]]
                if (
                    member["split"] != "development"
                    or member["population"] != "primary"
                    or member["source_file"] != "clean.jsonl"
                    or member["construction_status"] != "candidate"
                    or member["canonical_base_id"] != request["canonical_base_id"]
                    or member["benchmark"] != request["benchmark"]
                    or member["corrected_messages_sha256"] != request["messages_sha256"]
                ):
                    raise ValueError("Initial clean development membership differs")
                folder = evidence / "run/cases" / sha(request["case_key"].encode())
                metadata = json.loads(bound.regular(folder / "response_metadata.json"))
                response = json.loads(bound.regular(folder / "http_response.bin"))
                if metadata["http_status"] != 200:
                    raise ValueError(
                        "Initial request has no known successful HTTP response; preserve for review"
                    )
                initial_raw = response["choices"][0]["message"]["content"]
                calls = official_parser(initial_raw, request["benchmark"])
                for fault in policy["fault_types"]:
                    record, roles = episode(
                        request,
                        initial_raw,
                        calls,
                        model_key,
                        fault,
                        errors,
                        fallback["model_id"],
                        kernel,
                    )
                    record["initial_response_sha256"] = ledger[folder / "http_response.bin"]
                    initial_record = records[request["case_key"]]
                    record["initial_evidence_status"] = initial_record["status"]
                    record["initial_finish_reason"] = initial_record["finish_reason"]
                    record["initial_usage"] = initial_record["usage"]
                    record["initial_request_elapsed_seconds"] = metadata.get("elapsed_seconds")
                    episodes.append(record)
                    if roles:
                        small_requests.append(roles["postfault_small"])
                        fallback_requests.append(roles["postfault_fallback"])
            payloads = {
                "episodes.json": episodes,
                "small_requests.json": small_requests,
                "fallback_requests.json": fallback_requests,
            }
            data = {name: (canonical(value) + "\n").encode() for name, value in payloads.items()}
            plan = {
                "version": policy["version"],
                "policy_sha256_lf": POLICY_SHA,
                "small_model_key": model_key,
                "model_settings": {"small": manifest["model_settings"], "fallback": fallback},
                "initial_manifest_sha256": rules["prepared_manifest_sha256"],
                "generation_settings_authority": "docs/config/task1_single_sample_v1.json",
                "server_settings": config["single_sample"]["server"],
                "inventory_sha256": policy["inventory_sha256"],
                "payload_sha256": {n: sha(b) for n, b in data.items()},
                "dispatch_authorized": False,
                "held_out_access_enabled": False,
                "main_experiment_ready": False,
                "tokenizer_context_preflight": "pending for every new role/context",
                "transition_injection": "planned only; not observed for eligible contexts",
                "static_dispatcher_compatible": False,
                "recovery_execution_adapter": "pending",
            }
            data["manifest.json"] = (canonical(plan) + "\n").encode()
            destination = stage / model_key
            destination.mkdir()
            for name, raw_payload in data.items():
                (destination / name).write_bytes(raw_payload)
            archive = stage / (model_key + "_recovery_development_transfer_v1.zip")
            with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED) as zipped:
                for name, raw_payload in data.items():
                    zipped.writestr(name, raw_payload)
            with zipfile.ZipFile(archive) as zipped:
                if (
                    zipped.testzip() is not None
                    or set(zipped.namelist()) != set(data)
                    or len(zipped.namelist()) != len(data)
                ):
                    raise ValueError("Recovery archive integrity differs")
                if any(zipped.read(name) != payload for name, payload in data.items()):
                    raise ValueError("Recovery archive bytes differ")
            transfers[model_key] = {
                "file": archive.name,
                "sha256": sha(archive.read_bytes()),
                "manifest_sha256": sha(data["manifest.json"]),
            }
            terminal = sum(not e["injection_eligible"] for e in episodes)
            reports[model_key] = {
                "initial_clean_rows": len(clean),
                "canonical_groups": len(clean),
                "planned_episode_slots": len(episodes),
                "terminal_no_injection_plans": terminal,
                "pending_injection_eligible_plans": len(episodes) - terminal,
                "postfault_small_requests": len(small_requests),
                "potential_postfault_fallback_requests": len(fallback_requests),
                "maximum_new_calls_if_all_roles_dispatched": len(small_requests)
                + len(fallback_requests),
                "no_injection_reasons": dict(
                    Counter(
                        e["no_injection_reason"] for e in episodes if not e["injection_eligible"]
                    )
                ),
            }
        for path, wanted in ledger.items():
            if sha(bound.regular(path)) != wanted:
                raise ValueError("Original initial evidence changed")
        bound.check_sources(repo, policy)
        summary = {
            "version": policy["version"],
            "models": reports,
            "transfers": transfers,
            "generation_requests_sent": 0,
            "observed_fault_conditioned_dispatches": 0,
            "official_scoring": "not_performed",
            "rq3_outcomes": "not_evaluated",
            "held_out_access_enabled": False,
            "main_experiment_ready": False,
            "dispatch_authorized": False,
            "prior_files_modified": False,
            "pending": policy["pending"],
        }
        provenance = {
            "policy": policy,
            "policy_sha256_lf": POLICY_SHA,
            "input_sha256": {p.relative_to(repo).as_posix(): h for p, h in ledger.items()},
            "new_source_sha256_lf": {
                "prepare.py": sha(Path(__file__).read_bytes().replace(b"\r\n", b"\n")),
                "recovery.py": sha(
                    (repo / "src/uqroute_tc/routing/recovery.py")
                    .read_bytes()
                    .replace(b"\r\n", b"\n")
                ),
            },
        }
        for name, value in {"summary.json": summary, "provenance.json": provenance}.items():
            (stage / name).write_text(canonical(value) + "\n", encoding="utf-8", newline="\n")
        publisher = bound.module(
            "_recovery_publish",
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
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO / "src")
    try:
        for folder, pattern in (
            ("tests/unit", "test_recovery_development.py"),
            (str(HERE), "test_*.py"),
            ("tests/unit", "test_routing_development.py"),
        ):
            subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", folder, "-p", pattern],
                cwd=REPO,
                env=env,
                check=True,
            )
        summary = prepare(REPO)
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        raise SystemExit(
            "Recovery preparation stopped: " + str(exc) + ". Preserve evidence; no model retries."
        ) from None
    print(json.dumps(summary, indent=2))
    print("Prepared:", OUTPUT)
    print(
        "No inference, reference scoring, held-out access or Git writes. "
        "Context preflight and recovery executor remain pending."
    )


if __name__ == "__main__":
    main()
