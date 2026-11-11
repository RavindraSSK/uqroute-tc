"""Synthetic request construction and released-source compatibility checks."""

import ast
import hashlib
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import prepare

from uqroute_tc.routing import recovery


def request():
    messages = [
        {"role": "system", "content": "synthetic tools"},
        {"role": "user", "content": "synthetic task"},
    ]
    return {
        "source_file": "clean.jsonl",
        "case_key": "clean.jsonl:synthetic",
        "canonical_base_id": "synthetic",
        "benchmark": "bfcl_v3",
        "messages_sha256": recovery.messages_sha256(messages),
        "request": {
            "model": "synthetic-small",
            "messages": messages,
            "temperature": 0.001,
            "max_tokens": 1024,
            "logprobs": True,
            "top_logprobs": 5,
        },
    }


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.source = (
            prepare.REPO / "tools/development_audits/full_development_v1/official_runner.py"
        ).read_text(encoding="utf-8")
        self.errors = prepare.released_templates(self.source)

    def test_all_six_released_faults_are_loaded_without_retyping(self):
        self.assertEqual(
            set(self.errors),
            {
                "timeout",
                "rate_limit",
                "auth_error",
                "server_error",
                "malformed_response",
                "schema_drift",
            },
        )

    def test_source_formatter_and_new_contexts_match(self):
        tree = ast.parse(self.source)
        node = next(
            n
            for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "_format_tool_call_for_injection"
        )
        stripped = ast.Module(
            body=[
                ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
                node,
            ],
            type_ignores=[],
        )
        namespace = {}
        exec(compile(ast.fix_missing_locations(stripped), "pinned_formatter", "exec"), namespace)
        base = request()
        for fault in self.errors:
            calls = [{"name": "synthetic.api", "parameters": {"x": 1}}]
            _, roles = prepare.episode(
                base,
                "synthetic.api(x=1)",
                calls,
                "small",
                fault,
                self.errors,
                "synthetic-fallback",
                recovery,
            )
            expected = (
                "Tool execution result for "
                + namespace["_format_tool_call_for_injection"](calls)
                + ": "
                + self.errors[fault]
            )
            self.assertEqual(
                roles["postfault_small"]["request"]["messages"][-1]["content"], expected
            )

    def test_both_roles_have_same_fault_context_and_frozen_request_settings(self):
        base = request()
        before = deepcopy(base)
        record, roles = prepare.episode(
            base,
            "synthetic()",
            [{"name": "synthetic"}],
            "small",
            "timeout",
            self.errors,
            "synthetic-fallback",
            recovery,
        )
        a, b = roles["postfault_small"], roles["postfault_fallback"]
        self.assertEqual(a["request"]["messages"], b["request"]["messages"])
        self.assertEqual(a["context_messages_sha256"], b["context_messages_sha256"])
        self.assertNotEqual(a["request_sha256"], b["request_sha256"])
        self.assertEqual(
            {k: v for k, v in a["request"].items() if k != "model"},
            {k: v for k, v in b["request"].items() if k != "model"},
        )
        self.assertEqual(a["request"]["temperature"], 0.001)
        self.assertEqual(a["request"]["max_tokens"], 1024)
        self.assertEqual(base, before)
        self.assertIsNone(record["transition_injected"])

    def test_modified_initial_prompt_or_nonclean_source_rejected(self):
        base = request()
        base["messages_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            prepare.episode(base, "x", [], "small", "timeout", self.errors, "fallback", recovery)
        base = request()
        base["source_file"] = "query_paraphrase.jsonl"
        with self.assertRaises(ValueError):
            prepare.episode(base, "x", [], "small", "timeout", self.errors, "fallback", recovery)

    def test_no_call_has_episode_record_but_no_recovery_request(self):
        record, roles = prepare.episode(
            request(), "[]", [], "small", "timeout", self.errors, "fallback", recovery
        )
        self.assertFalse(record["transition_injected"])
        self.assertEqual(roles, {})

    def test_ids_are_stable_and_differ_by_fault_model_and_stage(self):
        base = request()
        a, roles = prepare.episode(
            base, "x", [{"name": "x"}], "small", "timeout", self.errors, "fallback", recovery
        )
        b, _ = prepare.episode(
            base, "x", [{"name": "x"}], "small", "rate_limit", self.errors, "fallback", recovery
        )
        c, _ = prepare.episode(
            base, "x", [{"name": "x"}], "other-small", "timeout", self.errors, "fallback", recovery
        )
        self.assertEqual(len({a["episode_key"], b["episode_key"], c["episode_key"]}), 3)
        self.assertNotEqual(
            roles["postfault_small"]["request_id"], roles["postfault_fallback"]["request_id"]
        )
        self.assertEqual(
            (a, roles),
            prepare.episode(
                base, "x", [{"name": "x"}], "small", "timeout", self.errors, "fallback", recovery
            ),
        )

    def test_native_or_changed_fault_templates_rejected(self):
        with self.assertRaises(ValueError):
            prepare.released_templates("x=1")
        with self.assertRaises(ValueError):
            prepare.released_templates("TRANSITION_ERROR_MESSAGES: dict = {}")

    def test_policy_and_existing_source_pins_match(self):
        raw = (Path(__file__).parent / "policy.json").read_bytes().replace(b"\r\n", b"\n")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), prepare.POLICY_SHA)
        policy = json.loads(raw)
        self.assertIs(policy["dispatch_authorized"], False)
        self.assertIs(policy["held_out_access_enabled"], False)
        for name, wanted in policy["source_sha256_lf"].items():
            self.assertEqual(
                hashlib.sha256(
                    (prepare.REPO / name).read_bytes().replace(b"\r\n", b"\n")
                ).hexdigest(),
                wanted,
            )

    def test_existing_preparation_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / prepare.OUTPUT).mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "preserve existing"):
                prepare.prepare(root)


if __name__ == "__main__":
    unittest.main()
