"""Development-only recovery contexts, bounded stages and injection denominators."""

import inspect
import unittest
from copy import deepcopy

from uqroute_tc.routing.recovery import (
    RecoveryEvidence,
    RecoveryState,
    fault_context,
    messages_sha256,
    next_step,
)

ERRORS = {"timeout": "synthetic timeout", "rate_limit": "synthetic rate limit"}
MESSAGES = [
    {"role": "system", "content": "synthetic tools"},
    {"role": "user", "content": "synthetic request"},
]
CONTEXT = messages_sha256(MESSAGES + [{"role": "assistant", "content": "synthetic call"}])


def evidence(score=0.1, status="complete", parsed=True, context=CONTEXT):
    return RecoveryEvidence(context, status, parsed, score)


class ContextTests(unittest.TestCase):
    def test_appends_exact_released_message_convention_without_mutation(self):
        original = deepcopy(MESSAGES)
        result = fault_context(MESSAGES, "synthetic()", [{"name": "synthetic"}], "timeout", ERRORS)
        self.assertEqual(
            result["messages"],
            original
            + [
                {"role": "assistant", "content": "synthetic()"},
                {
                    "role": "user",
                    "content": "Tool execution result for synthetic: synthetic timeout",
                },
            ],
        )
        self.assertEqual(MESSAGES, original)
        self.assertTrue(result["injection_eligible"])
        self.assertIsNone(result["transition_injected"])

    def test_initial_no_call_is_separate_from_pending_fault_submission(self):
        result = fault_context(MESSAGES, "[]", [], "timeout", ERRORS)
        self.assertFalse(result["transition_injected"])
        self.assertFalse(result["injection_eligible"])
        self.assertIsNone(result["messages"])

    def test_initial_error_prevents_fault_even_with_returned_calls(self):
        result = fault_context(
            MESSAGES, "partial", [{"name": "tool"}], "timeout", ERRORS, initial_error=True
        )
        self.assertEqual(result["reason"], "initial_request_error")
        self.assertFalse(result["injection_eligible"])

    def test_first_tool_name_and_alias_match_released_behavior(self):
        for calls, name in (
            ([{"name": "a"}, {"name": "b"}], "a"),
            ([{"tool": "alias"}], "alias"),
            ([{}], "unknown_tool"),
            (["text"], "text"),
        ):
            result = fault_context(MESSAGES, "x", calls, "timeout", ERRORS)
            self.assertEqual(
                result["messages"][-1]["content"],
                f"Tool execution result for {name}: synthetic timeout",
            )

    def test_fault_types_produce_different_context_hashes(self):
        a = fault_context(MESSAGES, "x", [{"name": "tool"}], "timeout", ERRORS)
        b = fault_context(MESSAGES, "x", [{"name": "tool"}], "rate_limit", ERRORS)
        self.assertNotEqual(a["messages_sha256"], b["messages_sha256"])
        self.assertNotEqual(a["messages_sha256"], messages_sha256(MESSAGES))

    def test_unrecognized_fault_and_non_prompt_messages_rejected(self):
        with self.assertRaises(ValueError):
            fault_context(MESSAGES, "x", [], "other", ERRORS)
        with self.assertRaises(ValueError):
            fault_context([{"role": "tool", "content": "x"}], "x", [], "timeout", ERRORS)
        with self.assertRaises(ValueError):
            fault_context(MESSAGES, "x", [], "timeout", ERRORS, initial_error=1)


class StateTests(unittest.TestCase):
    def test_initial_plan_does_not_claim_injection(self):
        state = RecoveryState(CONTEXT, None)
        self.assertEqual(next_step(state, 0.2), "plan_fault_conditioned_small")
        self.assertEqual(state.rq3_partition, "pending_not_attempted")
        self.assertEqual(state.attempt_slots, 1)

    def test_no_fault_terminal_and_excluded_from_rq3(self):
        state = RecoveryState(None, False)
        self.assertEqual(next_step(state, 0.2), "terminal_no_fault")
        self.assertEqual(state.rq3_partition, "no_fault_injected")

    def test_intent_does_not_prove_feedback_was_submitted(self):
        state = RecoveryState(CONTEXT, None, True)
        self.assertEqual(state.rq3_partition, "injection_unknown")
        self.assertEqual(next_step(state, 0.2), "stop_unknown_injection_no_resubmit")

    def test_submitted_unknown_outcome_stays_in_injected_partition(self):
        state = RecoveryState(CONTEXT, True, True)
        self.assertEqual(state.rq3_partition, "injected")
        self.assertEqual(next_step(state, 0.2), "stop_unknown_small_no_resubmit")

    def test_inclusive_threshold_accepts_returned_small(self):
        state = RecoveryState(CONTEXT, True, True, evidence(0.2))
        self.assertEqual(next_step(state, 0.2), "accept_fault_conditioned_small")
        self.assertEqual(state.attempt_slots, 2)

    def test_accept_none_threshold_is_explicit_not_an_automatic_selection(self):
        state = RecoveryState(CONTEXT, True, True, evidence(0))
        self.assertEqual(next_step(state, None), "plan_fault_conditioned_fallback")

    def test_unavailable_truncated_or_no_call_escalates(self):
        for outcome in (
            evidence(None),
            evidence(None, "truncated"),
            evidence(0.1, parsed=False),
            evidence(0.3),
        ):
            state = RecoveryState(CONTEXT, True, True, outcome)
            self.assertEqual(next_step(state, 0.2), "plan_fault_conditioned_fallback")

    def test_occupied_fallback_slot_is_never_resubmitted(self):
        state = RecoveryState(CONTEXT, True, True, evidence(0.3), True)
        self.assertEqual(next_step(state, 0.2), "stop_unknown_fallback_no_resubmit")
        self.assertEqual(state.attempt_slots, 3)

    def test_returned_fallback_is_terminal_even_if_unusable(self):
        state = RecoveryState(
            CONTEXT, True, True, evidence(0.3), True, evidence(None, "invalid_evidence", False)
        )
        self.assertEqual(next_step(state, 0.2), "terminal_fault_conditioned_fallback")
        self.assertEqual(next_step(state, 0.2), "terminal_fault_conditioned_fallback")
        self.assertEqual(state.attempt_slots, 3)

    def test_context_incompatible_static_response_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Context-incompatible"):
            RecoveryState(CONTEXT, True, True, evidence(context=messages_sha256(MESSAGES)))

    def test_response_without_intent_or_injection_is_rejected(self):
        with self.assertRaises(ValueError):
            RecoveryState(CONTEXT, None, False, evidence())
        with self.assertRaises(ValueError):
            RecoveryState(CONTEXT, True)
        with self.assertRaises(ValueError):
            RecoveryState(CONTEXT, False, True)
        with self.assertRaises(ValueError):
            RecoveryState(None, None)

    def test_fallback_cannot_precede_small_or_bypass_unknown_stage(self):
        with self.assertRaises(ValueError):
            RecoveryState(CONTEXT, True, True, None, True)
        with self.assertRaises(ValueError):
            RecoveryState(CONTEXT, True, True, evidence(None, "unknown_outcome", False), True)

    def test_gate_change_cannot_ignore_already_occupied_fallback(self):
        state = RecoveryState(CONTEXT, True, True, evidence(0.1), True, evidence())
        with self.assertRaises(ValueError):
            next_step(state, 0.2)

    def test_unknown_small_response_does_not_automatically_escalate(self):
        for status in (
            "unknown_outcome",
            "transport_error_outcome_unknown",
            "interrupted_response_metadata_missing",
        ):
            state = RecoveryState(CONTEXT, True, True, evidence(None, status, False))
            self.assertEqual(next_step(state, 0.2), "stop_unknown_small_no_resubmit")

    def test_metadata_alias_mirrors_observed_injection_only(self):
        for flag, intent in ((None, False), (None, True), (True, True), (False, False)):
            state = RecoveryState(CONTEXT, flag, intent)
            record = state.injection_metadata()
            self.assertIs(record["prediction"]["transition_injected"], flag)
            self.assertIs(record["perturbation"]["metadata"]["pass1_had_tool_calls"], flag)

    def test_no_correctness_labels_enter_decision_api(self):
        self.assertEqual(set(inspect.signature(next_step).parameters), {"state", "threshold"})
        self.assertFalse(any("correct" in name for name in RecoveryEvidence.__dataclass_fields__))

    def test_invalid_threshold_and_evidence_are_rejected(self):
        for score in (-1, True, float("inf"), float("nan")):
            with self.assertRaises(ValueError):
                evidence(score)
        with self.assertRaises(ValueError):
            evidence(0.1, "truncated")
        with self.assertRaises(ValueError):
            next_step(RecoveryState(None, False), float("inf"))
        with self.assertRaises(ValueError):
            RecoveryState(CONTEXT, 1)


if __name__ == "__main__":
    unittest.main()
