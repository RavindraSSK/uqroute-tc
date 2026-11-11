"""Check owner-pinned recovery transfers with CPU tokenizers; never dispatch requests."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import platform
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PREPARATION = Path("artifacts/local_development_audits/recovery_development_preparation_v1")
OUTPUT = Path("artifacts/local_development_audits/recovery_context_preflight_v1")
CONFIG_SHA = "a9a3a8a6309c943759b0cbb412f07ed51a0dfa0d149751f13dc20bde66deb179"
TRANSFORMERS_VERSION = "5.20.2"
# Owner-supplied preparation output, not inferred recovery outcomes.
TRANSFERS = {
    "qwen15b": (
        "4d13f91c7c886e739a4c97b3638c31284b59de7ee2161c9ca5c95f4fe6c90e8e",
        "205ca2ec18260d49e07c9309286b34dbfeffa892969dedbc4f7db7b6fe59ef54",
        750,
        0,
    ),
    "llama3b": (
        "3503910606bf878bc8c138378e6ba8ea3482b91be5a31ff005cbe9a6b7aededf",
        "b72324fa14d7ad2f0d4c081edbf9f6b32730d3e7c7f26d105c4fb49deca55974",
        828,
        1,
    ),
    "qwen7b": (
        "f06adff44aa0583d95fc07b99ad76d33b9f2c5fd920e35144d7fd30d73084a88",
        "02bfb4c993702f89a6f60cbb117cd07f05c9fd76693543a84d1cd37b082e7747",
        834,
        2,
    ),
}
MEMBERS = {"manifest.json", "episodes.json", "small_requests.json", "fallback_requests.json"}


def canonical(value):
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def regular(path):
    if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
        raise ValueError("Expected a regular non-symlink input: " + str(path))
    return path.read_bytes()


def loads(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    def invalid(value):
        raise ValueError("Nonfinite JSON: " + value)

    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)


def read_archive(path, archive_sha, manifest_sha):
    raw = regular(path)
    if sha(raw) != archive_sha:
        raise ValueError("Owner recovery archive fingerprint differs: " + path.name)
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if (
            len(infos) != len(MEMBERS)
            or set(archive.namelist()) != MEMBERS
            or sum(i.file_size for i in infos) > 256 * 1024**2
        ):
            raise ValueError("Recovery archive member inventory/size differs")
        payloads = {name: archive.read(name) for name in MEMBERS}
    if sha(payloads["manifest.json"]) != manifest_sha:
        raise ValueError("Owner recovery manifest fingerprint differs")
    manifest = loads(payloads["manifest.json"])
    expected = {n: sha(b) for n, b in payloads.items() if n != "manifest.json"}
    if manifest["payload_sha256"] != expected:
        raise ValueError("Recovery payload fingerprints differ")
    return {n: loads(b) for n, b in payloads.items()}


def validate_plan(data, key, config, eligible_count, clean_count=140):
    manifest = data["manifest.json"]
    setting = TRANSFERS[key][3]
    if (
        manifest["version"] != "uqroute-recovery-development-preparation-1.0.0"
        or manifest["small_model_key"] != key
        or manifest["dispatch_authorized"] is not False
        or manifest["held_out_access_enabled"] is not False
        or manifest["main_experiment_ready"] is not False
        or manifest["static_dispatcher_compatible"] is not False
        or manifest["server_settings"] != config["single_sample"]["server"]
        or manifest["model_settings"]
        != {"small": config["models"][setting], "fallback": config["models"][3]}
    ):
        raise ValueError("Recovery authority/model settings differ")
    episodes = data["episodes.json"]
    keys = [e["episode_key"] for e in episodes]
    if len(set(keys)) != len(keys) or len(episodes) != clean_count * 6:
        raise ValueError("Episode inventory differs")
    groups = {}
    eligible = {}
    faults = {
        "timeout",
        "rate_limit",
        "auth_error",
        "server_error",
        "malformed_response",
        "schema_drift",
    }
    for e in episodes:
        if (
            e["split"] != "development"
            or e["population"] != "primary"
            or e["source_file"] != "clean.jsonl"
            or e["fault_type"] not in faults
        ):
            raise ValueError("Non-primary-development episode")
        group = groups.setdefault(e["canonical_base_id"], [])
        group.append(e["fault_type"])
        if e["injection_eligible"] is True:
            if e["transition_injected"] is not None or e["no_injection_reason"] is not None:
                raise ValueError("Eligible preparation must remain pending injection")
            eligible[e["episode_key"]] = e
        elif (
            e["injection_eligible"] is not False
            or e["transition_injected"] is not False
            or e["no_injection_reason"] != "initial_no_official_call"
        ):
            raise ValueError("Terminal no-injection disposition differs")
    if (
        len(groups) != clean_count
        or any(len(v) != 6 or set(v) != faults for v in groups.values())
        or len(eligible) != eligible_count
    ):
        raise ValueError("Clean-group/fault/eligible coverage differs")
    roles = {}
    for role, filename, model_role in (
        ("postfault_small", "small_requests.json", "small"),
        ("postfault_fallback", "fallback_requests.json", "fallback"),
    ):
        rows = data[filename]
        indexed = {r["episode_key"]: r for r in rows}
        if (
            len(indexed) != len(rows)
            or set(indexed) != set(eligible)
            or len({r["request_id"] for r in rows}) != len(rows)
        ):
            raise ValueError("Role request coverage differs")
        for ekey, row in indexed.items():
            body = row["request"]
            messages = body["messages"]
            context_sha = sha(canonical(messages).encode())
            expected_body = {
                "model": manifest["model_settings"][model_role]["model_id"],
                "messages": messages,
                **{
                    n: config["single_sample"][n]
                    for n in ("temperature", "max_tokens", "logprobs", "top_logprobs")
                },
            }
            if (
                body != expected_body
                or row["stage"] != role
                or row["request_sha256"] != sha(canonical(body).encode())
                or row["request_id"] != sha(canonical([ekey, role]).encode())
                or row["context_messages_sha256"] != context_sha
                or eligible[ekey]["context_messages_sha256"] != context_sha
                or not isinstance(messages, list)
                or len(messages) < 3
                or [m["role"] for m in messages[-3:]] != ["user", "assistant", "user"]
                or any(
                    set(m) != {"role", "content"} or not isinstance(m["content"], str)
                    for m in messages
                )
            ):
                raise ValueError("Role request/context binding differs")
        roles[role] = indexed
    for ekey in eligible:
        a = roles["postfault_small"][ekey]["request"]["messages"]
        b = roles["postfault_fallback"][ekey]["request"]["messages"]
        if a != b:
            raise ValueError("Small/fallback fault histories differ")
    return manifest, roles


def count_contexts(rows, tokenizer, limit):
    result = []
    for row in rows.values():
        ids = tokenizer.apply_chat_template(
            row["request"]["messages"],
            tokenize=True,
            add_generation_prompt=True,
            return_dict=False,
        )
        if not isinstance(ids, list) or not ids or any(type(n) is not int for n in ids):
            raise ValueError("Unexpected pinned-tokenizer token IDs")
        allowance = row["request"]["max_tokens"]
        result.append(
            {
                "request_id": row["request_id"],
                "episode_key": row["episode_key"],
                "request_sha256": row["request_sha256"],
                "context_messages_sha256": row["context_messages_sha256"],
                "prompt_tokens": len(ids),
                "completion_allowance": allowance,
                "within_limit": len(ids) + allowance <= limit,
            }
        )
    if not result:
        raise ValueError("Empty role context inventory")
    return {
        "requests": len(result),
        "prompt_tokens_total": sum(r["prompt_tokens"] for r in result),
        "prompt_tokens_min": min(r["prompt_tokens"] for r in result),
        "prompt_tokens_max": max(r["prompt_tokens"] for r in result),
        "overflow_requests": sum(not r["within_limit"] for r in result),
        "context_limit": limit,
        "per_request": result,
    }


def run(repo, local_files_only=False):
    output = repo / OUTPUT
    if output.exists() or any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError("Fresh preflight output required; preserve existing results")
    if subprocess.run(
        ["git", "check-ignore", "-q", "--", str(OUTPUT / "summary.json")], cwd=repo
    ).returncode:
        raise ValueError("Preflight outputs must remain ignored")
    raw = regular(repo / "docs/config/task1_single_sample_v1.json").replace(b"\r\n", b"\n")
    if sha(raw) != CONFIG_SHA:
        raise ValueError("Frozen Task 1 settings fingerprint differs")
    config = loads(raw)
    plans, inputs = {}, {}
    # Validate all three transfers before downloading any tokenizer assets.
    for key, (archive_sha, manifest_sha, eligible, _) in TRANSFERS.items():
        path = repo / PREPARATION / (key + "_recovery_development_transfer_v1.zip")
        plans[key] = validate_plan(
            read_archive(path, archive_sha, manifest_sha), key, config, eligible
        )
        inputs[path] = archive_sha
    if importlib.metadata.version("transformers") != TRANSFORMERS_VERSION:
        raise ValueError(
            "Install the recorded tokenizer runtime: transformers==" + TRANSFORMERS_VERSION
        )
    from transformers import AutoTokenizer

    summary = {
        "version": "uqroute-recovery-context-preflight-1.0.0",
        "models": {},
        "generation_requests_sent": 0,
        "observed_fault_conditioned_dispatches": 0,
        "dispatch_authorized": False,
        "held_out_access_enabled": False,
        "main_experiment_ready": False,
        "rq3_outcomes": "not_evaluated",
        "prompts_truncated": False,
        "requests_dropped": 0,
        "scope": "CPU pinned-tokenizer rendering; server/runtime validation still required",
    }
    report = {
        "input_archive_sha256": {p.name: h for p, h in inputs.items()},
        "task1_settings_sha256_lf": CONFIG_SHA,
        "preflight_source_sha256_lf": sha(Path(__file__).read_bytes().replace(b"\r\n", b"\n")),
        "python": platform.python_version(),
        "packages": {
            n: importlib.metadata.version(n)
            for n in ("transformers", "tokenizers", "huggingface-hub")
        },
        "models": {},
    }
    # Cache only tokenizer instances, never substitute a related model's tokenizer.
    cache = {}
    for key, (manifest, roles) in plans.items():
        report["models"][key], summary["models"][key] = {}, {}
        for role, rows in roles.items():
            settings = manifest["model_settings"][
                "small" if role == "postfault_small" else "fallback"
            ]
            identity = (settings["model_id"], settings["tokenizer_revision"])
            if identity not in cache:
                print("Loading pinned CPU tokenizer:", identity[0], flush=True)
                cache[identity] = AutoTokenizer.from_pretrained(
                    identity[0],
                    revision=identity[1],
                    trust_remote_code=False,
                    local_files_only=local_files_only,
                )
            tokenizer = cache[identity]
            if not tokenizer.chat_template or not getattr(tokenizer, "is_fast", False):
                raise ValueError("Expected the pinned default chat template and fast tokenizer")
            result = count_contexts(rows, tokenizer, manifest["server_settings"]["max_model_len"])
            result.update(
                model_id=identity[0],
                tokenizer_revision=identity[1],
                chat_template_sha256=sha(canonical(tokenizer.chat_template).encode()),
                tokenizer_backend_sha256=sha(tokenizer.backend_tokenizer.to_str().encode()),
            )
            report["models"][key][role] = result
            summary["models"][key][role] = {n: v for n, v in result.items() if n != "per_request"}
            print(
                key,
                role,
                "checked:",
                result["requests"],
                "overflow:",
                result["overflow_requests"],
                flush=True,
            )
    for path, expected in inputs.items():
        if sha(regular(path)) != expected:
            raise ValueError("Original transfer changed during preflight")
    summary["all_contexts_fit"] = all(
        r["overflow_requests"] == 0 for model in summary["models"].values() for r in model.values()
    )
    root = output.parent
    with tempfile.TemporaryDirectory(dir=root, prefix="recovery-context-") as folder:
        stage = Path(folder)
        for name, value in (("summary.json", summary), ("report.json", report)):
            (stage / name).write_text(canonical(value) + "\n", encoding="utf-8", newline="\n")
        # Existing helper publishes without replacing an occupied output directory.
        helper = (
            repo
            / "tools/development_audits/fallback_full_development_scoring_v1/score_fallback_full.py"
        )
        spec = importlib.util.spec_from_file_location("_recovery_context_publish", helper)
        publisher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(publisher)
        publisher.publish_directory(stage, output)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--local-files-only", action="store_true", help="Use cached pinned tokenizer assets only"
    )
    args = parser.parse_args()
    if Path.cwd().resolve() != REPO:
        raise SystemExit("Run from the uqroute-tc repository root")
    try:
        subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", str(HERE), "-p", "test_*.py"],
            cwd=REPO,
            check=True,
        )
        summary = run(REPO, args.local_files_only)
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        zipfile.BadZipFile,
        importlib.metadata.PackageNotFoundError,
        subprocess.SubprocessError,
    ) as exc:
        raise SystemExit(
            "Recovery preflight stopped: "
            + str(exc)
            + ". Preserve prepared inputs. No generation performed."
        ) from None
    print(json.dumps(summary, indent=2))
    print("Saved:", OUTPUT)
    print("No inference, injection, scoring, held-out access or dispatch authorization.")
    if not summary["all_contexts_fit"]:
        raise SystemExit("Context overflow recorded; do not trim, drop or dispatch these plans.")


if __name__ == "__main__":
    main()
