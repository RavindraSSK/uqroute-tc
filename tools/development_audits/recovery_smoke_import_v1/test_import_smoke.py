"""CPU-only archive, runtime/token evidence and discovery safeguards."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import import_smoke as importer


def runtime_payloads():
    def raw(value):
        return json.dumps(value).encode()

    command, snapshot = b"synthetic launch", b"synthetic startup log"
    payloads = {
        "metadata/launch_argv.json": command,
        "metadata/server_before_generation.log": snapshot,
        "metadata/runtime.json": raw(
            {
                "launch_command_sha256": importer.sha(command),
                "server_log_sha256": importer.sha(snapshot),
            }
        ),
        "metadata/shutdown.json": raw({"server_stopped": True, "generation_stopped": True}),
        "metadata/execution_status.json": raw(
            {
                "status": "smoke_generation_and_replay_finished",
                "official_scoring": "not_performed",
                "rq3_outcomes": "not_evaluated",
                "held_out_access_enabled": False,
                "main_experiment_ready": False,
            }
        ),
        "metadata/generation_exit.json": raw({"returncode": 0}),
        "metadata/replay_command.json": raw({"returncode": 0}),
        "metadata/sampling_constructor_check.json": raw(
            {
                "requested_temperature": 0.001,
                "constructed_temperature": 0.01,
                "top_p": 0.8,
                "top_k": 20,
                "repetition_penalty": 1.1,
                "max_tokens": 1024,
                "n": 1,
                "seed": None,
            }
        ),
    }
    local, server, rows = [], [], []
    for index in range(30):
        key = "synthetic_" + str(index)
        local.append({"request_id": key, "prompt_tokens": 10, "token_ids_sha256": "a" * 64})
        server.append(dict(local[-1]))
        rows.append({"request_id": key, "request": {"max_tokens": 1024}})
        payloads["run/cases/" + key + "/http_response.bin"] = raw({"usage": {"prompt_tokens": 10}})
    payloads["metadata/tokenizer_preflight.json"] = raw(
        {"per_request": local, "overflow_requests": 0}
    )
    payloads["metadata/server_tokenizer_preflight.json"] = raw(
        {"per_request": server, "all_match": True}
    )
    payloads["prepared/requests.json"] = raw(rows)
    return payloads


class ImportTests(unittest.TestCase):
    def test_only_expected_relative_evidence_paths_allowed(self):
        for value in (
            "metadata/runtime.json",
            "run/cases/synthetic/intent.json",
            "prepared/ledger.py",
        ):
            self.assertTrue(importer.safe_member(value))
        for value in (
            "/metadata/x",
            "metadata/../../x",
            "C:/metadata/x",
            "metadata\\x",
            "metadata//x",
            "repo/file",
            "metadata/../x",
            "",
        ):
            self.assertFalse(importer.safe_member(value))

    def test_wrong_archive_hash_rejected_before_zip_read(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.zip"
            path.write_bytes(b"synthetic wrong bytes")
            with patch.object(importer.zipfile, "ZipFile") as opened:
                with self.assertRaises(ValueError):
                    importer.read_archive(path)
                opened.assert_not_called()
            self.assertEqual(path.read_bytes(), b"synthetic wrong bytes")

    def test_member_index_inventory_changes_rejected(self):
        with self.assertRaises(ValueError):
            importer.verify_members({"metadata/export_file_hashes.json": b"{}"})

    def test_symlink_archive_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            target, link = Path(folder) / "target", Path(folder) / "link.zip"
            target.write_bytes(b"synthetic")
            try:
                link.symlink_to(target)
            except OSError:
                self.skipTest("Symlink creation unavailable")
            with self.assertRaises(ValueError):
                importer.regular(link)

    def test_matching_runtime_and_all_thirty_token_counts_accepted(self):
        importer.check_runtime_evidence(runtime_payloads())

    def test_mismatching_returned_prompt_tokens_rejected(self):
        payloads = runtime_payloads()
        payloads["run/cases/synthetic_0/http_response.bin"] = b'{"usage":{"prompt_tokens":11}}'
        with self.assertRaises(ValueError):
            importer.check_runtime_evidence(payloads)

    def test_unknown_shutdown_cannot_be_called_complete(self):
        payloads = runtime_payloads()
        payloads["metadata/shutdown.json"] = b'{"server_stopped":false,"generation_stopped":true}'
        with self.assertRaises(ValueError):
            importer.check_runtime_evidence(payloads)

    def test_missing_server_context_coverage_rejected(self):
        payloads = runtime_payloads()
        server = json.loads(payloads["metadata/server_tokenizer_preflight.json"])
        server["per_request"].pop()
        payloads["metadata/server_tokenizer_preflight.json"] = json.dumps(server).encode()
        with self.assertRaises(ValueError):
            importer.check_runtime_evidence(payloads)

    def test_discovery_checks_bytes_and_accepts_renamed_download(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            (home / "Downloads").mkdir()
            invalid = home / "Downloads/uqroute_recovery_smoke_wrong.zip"
            valid = home / "Downloads/uqroute_recovery_smoke_renamed(1).zip"
            invalid.write_bytes(b"wrong")
            valid.write_bytes(b"synthetic expected bytes")
            with (
                patch.object(importer.Path, "home", return_value=home),
                patch.object(importer, "ARCHIVE_SHA", importer.sha(valid.read_bytes())),
            ):
                self.assertEqual(importer.find_archive(), valid)
            self.assertEqual(invalid.read_bytes(), b"wrong")


if __name__ == "__main__":
    unittest.main()
