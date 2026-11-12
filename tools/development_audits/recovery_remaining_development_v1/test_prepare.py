"""Original production roles, bounded inventories and unchanged smoke reuse."""

import json
import sys
import unittest
from copy import deepcopy
from unittest.mock import patch

import prepare as audit

FOLDER = audit.REPO / "tools/development_audits/recovery_context_preflight_v1"
with patch.object(sys, "path", [str(FOLDER), *sys.path]):
    fixtures = audit.module("_remaining_test_producers", FOLDER / "test_preflight.py")


def production_plan():
    config, data = fixtures.fixture()
    data = deepcopy(data)
    data["episodes.json"], data["small_requests.json"], data["fallback_requests.json"] = [], [], []
    errors = fixtures.preparer.released_templates(
        (audit.REPO / "tools/development_audits/full_development_v1/official_runner.py").read_text()
    )
    for i in range(7):
        messages = [{"role": "user", "content": "synthetic task"}]
        candidate = {
            "case_key": "clean.jsonl:synthetic_" + str(i),
            "canonical_base_id": "synthetic_" + str(i),
            "benchmark": "bfcl_v3",
            "messages": messages,
            "messages_sha256": fixtures.recovery.messages_sha256(messages),
            "tools": [],
        }
        initial = fixtures.workflow.make_requests(
            [candidate],
            {candidate["case_key"]: {"source_file": "clean.jsonl"}},
            config["models"][0],
            config["single_sample"],
        )[0]
        for fault in errors:
            episode, roles = fixtures.preparer.episode(
                initial,
                "api()",
                [{"name": "api"}],
                "qwen15b",
                fault,
                errors,
                config["models"][3]["model_id"],
                fixtures.recovery,
            )
            data["episodes.json"].append(episode)
            data["small_requests.json"].append(roles["postfault_small"])
            data["fallback_requests.json"].append(roles["postfault_fallback"])
    manifest, roles = fixtures.p.validate_plan(data, "qwen15b", config, 42, clean_count=7)
    return data["episodes.json"], roles, manifest["model_settings"]


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.episodes, self.roles, self.settings = production_plan()

    def test_all_pending_requests_retained_in_bounded_group_batches(self):
        before = deepcopy((self.episodes, self.roles))
        pending, batches, reused = audit.remaining_plan(self.episodes, self.roles, {})
        for role in self.roles:
            self.assertEqual(len(pending[role]), 42)
            self.assertEqual([b["maximum_new_requests"] for b in batches[role]], [30, 12])
            self.assertEqual(sum(len(b["request_ids"]) for b in batches[role]), 42)
            self.assertEqual(reused[role], 0)
        self.assertEqual(before, (self.episodes, self.roles))
        self.assertTrue(
            all(
                b["parent_small_response_required_before_dispatch"]
                for b in batches["postfault_fallback"]
            )
        )

    def test_known_completed_slots_reused_without_resubmission(self):
        completed = {
            role: {r["request_id"]: r for r in list(rows.values())[:6]}
            for role, rows in self.roles.items()
        }
        pending, batches, reused = audit.remaining_plan(self.episodes, self.roles, completed)
        self.assertEqual(set(reused.values()), {6})
        for role in self.roles:
            self.assertEqual(len(pending[role]), 36)
            self.assertFalse(set(completed[role]) & {r["request_id"] for r in pending[role]})

    def test_altered_completed_message_rejected(self):
        row = deepcopy(next(iter(self.roles["postfault_small"].values())))
        row["request"]["messages"].append({"role": "assistant", "content": "later answer"})
        with self.assertRaises(ValueError):
            audit.remaining_plan(
                self.episodes, self.roles, {"postfault_small": {row["request_id"]: row}}
            )

    def test_completed_fallback_without_known_small_parent_rejected(self):
        row = next(iter(self.roles["postfault_fallback"].values()))
        with self.assertRaises(ValueError):
            audit.remaining_plan(
                self.episodes, self.roles, {"postfault_fallback": {row["request_id"]: row}}
            )

    def test_missing_original_role_row_is_not_silently_dropped(self):
        self.roles["postfault_fallback"].pop(next(iter(self.roles["postfault_fallback"])))
        with self.assertRaises(ValueError):
            audit.remaining_plan(self.episodes, self.roles, {})

    def test_terminal_no_injection_remains_outside_dispatch_inventory(self):
        terminal = deepcopy(self.episodes[0])
        terminal.update(
            episode_key="synthetic_terminal", injection_eligible=False, transition_injected=False
        )
        self.episodes.append(terminal)
        pending, _, _ = audit.remaining_plan(self.episodes, self.roles, {})
        self.assertEqual(len(pending["postfault_small"]), 42)

    def test_reference_outcomes_do_not_select_the_cohort(self):
        before = audit.remaining_plan(self.episodes, self.roles, {})
        for i, e in enumerate(self.episodes):
            e["diagnostic_reference_match"] = bool(i % 2)
        self.assertEqual(audit.remaining_plan(self.episodes, self.roles, {}), before)

    def test_input_order_does_not_change_batch_membership(self):
        first = audit.remaining_plan(self.episodes, self.roles, {})
        self.episodes.reverse()
        roles = {role: dict(reversed(list(rows.items()))) for role, rows in self.roles.items()}
        self.assertEqual(audit.remaining_plan(self.episodes, roles, {}), first)

    def context(self):
        return {
            role: {
                "requests": 42,
                "overflow_requests": 0,
                "model_id": self.settings["small" if role == "postfault_small" else "fallback"][
                    "model_id"
                ],
                "tokenizer_revision": self.settings[
                    "small" if role == "postfault_small" else "fallback"
                ]["tokenizer_revision"],
                "context_limit": 8192,
                "per_request": [
                    {
                        n: row[n]
                        for n in (
                            "request_id",
                            "episode_key",
                            "request_sha256",
                            "context_messages_sha256",
                        )
                    }
                    | {"prompt_tokens": 7168, "completion_allowance": 1024, "within_limit": True}
                    for row in rows.values()
                ],
            }
            for role, rows in self.roles.items()
        }

    def test_exact_context_boundary_and_overflow(self):
        context = self.context()
        audit.context_check(self.roles, context, self.settings)
        context["postfault_fallback"]["per_request"][0]["prompt_tokens"] += 1
        with self.assertRaises(ValueError):
            audit.context_check(self.roles, context, self.settings)

    def test_missing_context_or_wrong_model_revision_rejected(self):
        for mode in ("coverage", "revision", "body"):
            context = self.context()
            target = context["postfault_fallback"]
            if mode == "coverage":
                target["per_request"].pop()
            elif mode == "revision":
                target["tokenizer_revision"] = "wrong"
            else:
                target["per_request"][0]["request_sha256"] = "wrong"
            with self.assertRaises(ValueError):
                audit.context_check(self.roles, context, self.settings)

    def test_policy_pin_and_expected_full_inventory(self):
        raw = (audit.HERE / "policy.json").read_bytes().replace(b"\r\n", b"\n")
        self.assertEqual(audit.sha(raw), audit.POLICY_SHA)
        policy = json.loads(raw)
        self.assertEqual(sum(sum(r.values()) for r in policy["expected_pending"].values()), 4764)
        self.assertFalse(policy["dispatch_authorized"])


class ReviewBindingTests(unittest.TestCase):
    def fixture(self):
        reviewer = audit.module(
            "_remaining_closed_review_test",
            audit.REPO
            / "tools/development_audits/recovery_matched_smoke_review_v1/review_pairs.py",
        )
        records = [
            {
                "request_id": "fallback_" + str(i),
                "episode_key": "ep_" + str(i),
                "paired_small_request_id": "small_" + str(i),
                "canonical_base_id": "group_" + str(i // 6),
                "benchmark": "bfcl_v3",
                "fault_type": "timeout",
                "panel": "official_reference_compliance",
                "initial_reference_match": True,
                "small_reference_match": True,
                "fallback_reference_match": True,
                "small_parser_status": "calls",
                "fallback_parser_status": "calls",
                "structure": {
                    "transition": "identical_calls",
                    "initial_to_fallback": {
                        "initial_first_control_name_literal": "finish" if i < 6 else None,
                        "removed_top_level_argument_keys": 0,
                        "empty_string_argument_replacements": 0,
                    },
                },
            }
            for i in range(30)
        ]
        raw = {
            "records.json": json.dumps(records).encode(),
            "summary.json": b"{}",
            "provenance.json": b"{}",
        }
        provenance = {
            "paired_scoring_recomputed_exactly": True,
            "policy_sha256_lf": reviewer.POLICY_SHA,
            "original_paired_scoring_sha256": {n: audit.sha(b) for n, b in raw.items()},
        }
        return records, reviewer.summarize(records), provenance, deepcopy(records), raw, reviewer

    def test_closed_review_and_original_pair_fingerprints_match(self):
        audit.check_closed_review(*self.fixture())

    def test_changed_review_reference_label_is_rejected(self):
        records, _, provenance, paired, raw, reviewer = self.fixture()
        records[0]["fallback_reference_match"] = False
        with self.assertRaises(ValueError):
            audit.check_closed_review(
                records, reviewer.summarize(records), provenance, paired, raw, reviewer
            )

    def test_unreproduced_or_stale_prior_scores_rejected(self):
        values = list(self.fixture())
        values[2]["paired_scoring_recomputed_exactly"] = False
        with self.assertRaises(ValueError):
            audit.check_closed_review(*values)
        values = list(self.fixture())
        values[4]["records.json"] += b" "
        with self.assertRaises(ValueError):
            audit.check_closed_review(*values)


if __name__ == "__main__":
    unittest.main()
