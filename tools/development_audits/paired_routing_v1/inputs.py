"""Bind routing pairs to re-scored, replayed, prompt-matched development records."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

from uqroute_tc.routing.development import PairedCase, SavedOutcome, Usage

ROOT = Path("artifacts/local_development_audits")
SMALL_IDS = {
    "Qwen/Qwen2.5-1.5B-Instruct",
    "meta-llama/Llama-3.2-3B-Instruct",
    "Qwen/Qwen2.5-7B-Instruct",
}
FALLBACK_ID = "Qwen/Qwen2.5-14B-Instruct-AWQ"
LINEAGE = (
    "case_key",
    "benchmark",
    "canonical_base_id",
    "source_file",
    "messages_sha256",
    "tools_sha256",
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def regular(path):
    if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
        raise ValueError("Required regular input missing or has a symlink: " + str(path))
    return path.read_bytes()


def check_sources(repo, policy):
    for name, expected in policy["source_sha256_lf"].items():
        if sha(regular(repo / name).replace(b"\r\n", b"\n")) != expected:
            raise ValueError("Reviewed code/policy fingerprint differs: " + name)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def verified_model(repo, settings, stage, model_key, ledger):
    """Execute the existing bound scorer and frozen replay, checking prior output."""
    scorer = module("_paired_routing_scorer_" + model_key, repo / settings["scorer"])
    rules = scorer.policy()
    evidence = repo / ROOT / settings["evidence"]
    previous = repo / ROOT / settings["scored"]
    fresh = stage / (model_key + "_scoring")
    scorer.score(
        repo,
        evidence,
        repo / ROOT / "full_primary_export_v1",
        repo / ROOT / "full_primary_audit_v1",
        fresh,
    )
    for name in ("scores.json", "summary.json"):
        raw = regular(previous / name)
        ledger[previous / name] = sha(raw)
        if scorer.loads(raw) != scorer.loads(regular(fresh / name)):
            raise ValueError("Recomputed saved scoring differs: " + model_key + "/" + name)
    provenance = scorer.loads(regular(fresh / "provenance.json"))
    for name, fingerprint in provenance["input_sha256"].items():
        path = repo / name
        if path in ledger and ledger[path] != fingerprint:
            raise ValueError("Contradictory original-input fingerprints: " + name)
        ledger[path] = fingerprint
    workflow, _, _, _ = scorer.load_dependencies(repo, rules)
    manifest, requests = workflow.load_plan(
        repo, evidence / "prepared", rules["prepared_manifest_sha256"]
    )
    replay = stage / (model_key + "_replay")
    workflow.replay(
        repo, evidence / "prepared", rules["prepared_manifest_sha256"], evidence / "run", replay
    )
    for name in ("summary.json", "records.json"):
        raw = regular(evidence / "replay" / name)
        if scorer.loads(raw) != scorer.loads(regular(replay / name)):
            raise ValueError("Recomputed full replay differs: " + model_key + "/" + name)
    # The scorer has already verified the immutable reference/audit sidecars.
    inventory_path = repo / ROOT / "full_primary_audit_v1/inventory.json"
    inventory_raw = regular(inventory_path)
    if sha(inventory_raw) != rules["inventory_sha256"]:
        raise ValueError("Inventory changed after scoring")
    ledger[inventory_path] = sha(inventory_raw)
    inventory = scorer.unique_index(scorer.loads(inventory_raw))
    scores = scorer.unique_index(scorer.loads(regular(fresh / "scores.json")))
    records = scorer.unique_index(scorer.loads(regular(replay / "records.json")))
    if (
        len(requests) != 1728
        or set(scores) != set(records)
        or set(scores) != {r["case_key"] for r in requests}
    ):
        raise ValueError("Expected every constructed case, without evidence-based filtering")
    normalized = {}
    for request in requests:
        key = request["case_key"]
        score, record = scores[key], records[key]
        member = inventory[key]
        if (
            member["population"] != "primary"
            or member["split"] != "development"
            or member["construction_status"] != "candidate"
            or score["canonical_base_id"] != member["canonical_base_id"]
            or request["canonical_base_id"] != member["canonical_base_id"]
            or request["benchmark"] != member["benchmark"]
            or score["evidence_status"] != record["status"]
            or score["whole_output_scores"] != record["whole_output_scores"]
        ):
            raise ValueError("Scored/replayed development membership differs")
        calls = record["parsed_calls_json_view"]
        if not isinstance(calls, list):
            raise ValueError("Unexpected canonical parser view")
        metadata_name = "run/cases/" + sha(key.encode()) + "/response_metadata.json"
        metadata_raw = regular(evidence / metadata_name)
        if sha(metadata_raw) != rules["evidence_file_sha256"][metadata_name]:
            raise ValueError("Response timing metadata changed")
        metadata = scorer.loads(metadata_raw)
        usage = record["usage"]
        normalized[key] = {
            "request": request,
            "member": member,
            "panel": score["panel"],
            "flags": score["reference_review_flags"],
            "nll": (
                score["whole_output_scores"]["mean_token_nll"]
                if score["whole_output_scores"] is not None
                else None
            ),
            "outcome": SavedOutcome(
                reference_correct=score["official_score"]["correct"],
                evidence_status=record["status"],
                has_parsed_call=record["parser_status"] == "calls" and bool(calls),
                usage=Usage(
                    usage.get("prompt_tokens"),
                    usage.get("completion_tokens"),
                    metadata.get("elapsed_seconds"),
                ),
            ),
        }
    return normalized, scorer.loads(regular(fresh / "summary.json")), manifest


def join(small, fallback):
    """Compare actual request bodies and lineage; fallback NLL is never required."""
    if not small or set(small) != set(fallback):
        raise ValueError("Small/fallback case keys differ")
    result = []
    for key in sorted(small):
        a, b = small[key], fallback[key]
        x, y = a["request"], b["request"]
        if (
            x["case_key"] != key
            or any(x[k] != y[k] for k in LINEAGE)
            or a["panel"] != b["panel"]
            or a["flags"] != b["flags"]
            or x["request"]["model"] not in SMALL_IDS
            or y["request"]["model"] != FALLBACK_ID
        ):
            raise ValueError("Paired case, model, panel or reference-audit lineage differs")
        if {k: v for k, v in x["request"].items() if k != "model"} != {
            k: v for k, v in y["request"].items() if k != "model"
        }:
            raise ValueError("Actual prompts or generation settings differ")
        expected_panel = (
            "tooleyes_relevance"
            if x["benchmark"] == "tooleyes"
            else "official_reference_compliance"
        )
        if a["panel"] != expected_panel:
            raise ValueError("Panel does not match benchmark endpoint")
        for item in (a, b):
            member = item["member"]
            if (
                member["split"] != "development"
                or member["population"] != "primary"
                or member["construction_status"] != "candidate"
                or member["case_key"] != key
                or member["canonical_base_id"] != x["canonical_base_id"]
                or member["benchmark"] != x["benchmark"]
            ):
                raise ValueError("Non-development or mismatched pair membership")
        result.append(
            PairedCase(
                case_key=key,
                canonical_group=x["canonical_base_id"],
                benchmark=x["benchmark"],
                panel=a["panel"],
                population="primary",
                split="development",
                small_mean_nll=a["nll"],
                small=a["outcome"],
                fallback=b["outcome"],
            )
        )
    return result
