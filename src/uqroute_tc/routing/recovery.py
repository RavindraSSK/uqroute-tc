"""Development-only fault-context construction and bounded recovery decisions.

No dispatch, tool execution, reference labels, threshold selection or billing.
The caller must attest actual fault-feedback submission separately from planning.
"""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import dataclass

from uqroute_tc.routing.development import ABSENT_RESPONSE, should_escalate


def messages_sha256(messages):
    raw = json.dumps(
        messages, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def fault_context(
    messages, initial_text, official_calls, fault_type, error_messages, *, initial_error=False
):
    """Match the released prompt-mode two-turn append, with independent planning flags."""
    if type(initial_error) is not bool or not isinstance(initial_text, str):
        raise ValueError("Initial text and explicit request-error flag required")
    if not isinstance(official_calls, list) or not isinstance(messages, list) or not messages:
        raise ValueError("Original message list and official parsed-call list required")
    if any(
        not isinstance(m, dict)
        or set(m) != {"role", "content"}
        or m["role"] not in {"system", "user", "assistant"}
        or not isinstance(m["content"], str)
        for m in messages
    ):
        raise ValueError("Prompt-mode message shape differs")
    if fault_type not in error_messages or not isinstance(error_messages[fault_type], str):
        raise ValueError("Unknown released fault type")
    eligible = not initial_error and bool(official_calls)
    if not eligible:
        return {
            "injection_eligible": False,
            "transition_injected": False,
            "reason": "initial_request_error" if initial_error else "initial_no_official_call",
            "messages": None,
            "messages_sha256": None,
        }
    first = official_calls[0]
    name = (
        str(first.get("name") or first.get("tool") or "unknown_tool")
        if isinstance(first, dict)
        else str(first)
    )
    result = deepcopy(messages)
    result.append({"role": "assistant", "content": initial_text})
    result.append(
        {
            "role": "user",
            "content": f"Tool execution result for {name}: {error_messages[fault_type]}",
        }
    )
    return {
        "injection_eligible": True,
        "transition_injected": None,
        "reason": None,
        "messages": result,
        "messages_sha256": messages_sha256(result),
    }


@dataclass(frozen=True)
class RecoveryEvidence:
    context_sha256: str
    evidence_status: str
    has_parsed_call: bool
    mean_nll: float | None

    def __post_init__(self):
        if not isinstance(self.context_sha256, str) or not re.fullmatch(
            r"[0-9a-f]{64}", self.context_sha256
        ):
            raise ValueError("Recovery context fingerprint required")
        should_escalate(
            mean_nll=self.mean_nll,
            evidence_status=self.evidence_status,
            has_parsed_call=self.has_parsed_call,
            threshold=None,
        )
        if self.evidence_status != "complete" and self.mean_nll is not None:
            raise ValueError("Non-complete evidence has no eligible NLL")


@dataclass(frozen=True)
class RecoveryState:
    context_sha256: str | None
    transition_injected: bool | None
    small_intent: bool = False
    small_response: RecoveryEvidence | None = None
    fallback_intent: bool = False
    fallback_response: RecoveryEvidence | None = None

    def __post_init__(self):
        if self.transition_injected is not None and type(self.transition_injected) is not bool:
            raise ValueError("Injection status must be bool or unresolved None")
        if type(self.small_intent) is not bool or type(self.fallback_intent) is not bool:
            raise ValueError("Intent flags must be bool")
        if self.context_sha256 is not None and (
            not isinstance(self.context_sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", self.context_sha256)
        ):
            raise ValueError("Recovery context fingerprint required")
        for intent, response in (
            (self.small_intent, self.small_response),
            (self.fallback_intent, self.fallback_response),
        ):
            if response is not None:
                if not intent or not isinstance(response, RecoveryEvidence):
                    raise ValueError("Response without its durable stage intent")
                if response.context_sha256 != self.context_sha256:
                    raise ValueError(
                        "Context-incompatible response; static caches cannot recover a fault"
                    )
        if self.context_sha256 is None and self.transition_injected is not False:
            raise ValueError("No fault context requires explicit no-injection status")
        if self.transition_injected is False and (self.small_intent or self.fallback_intent):
            raise ValueError("No-injection state cannot contain post-fault attempts")
        if self.transition_injected is True and not self.small_intent:
            raise ValueError("Observed injection needs an attempted fault-conditioned stage")
        if self.fallback_intent and (
            self.small_response is None or self.transition_injected is not True
        ):
            raise ValueError("Fallback must follow an observed fault and returned small stage")
        if self.fallback_intent and (
            self.small_response.evidence_status in ABSENT_RESPONSE
            or self.small_response.evidence_status.startswith("interrupted")
        ):
            raise ValueError("Unresolved small stage cannot authorize fallback")

    def injection_metadata(self):
        return {
            "prediction": {"transition_injected": self.transition_injected},
            "perturbation": {
                "mdp_category": "transition",
                "metadata": {"pass1_had_tool_calls": self.transition_injected},
            },
            "rq3_partition": self.rq3_partition,
        }

    @property
    def attempt_slots(self):
        """Initial small slot plus occupied post-fault slots; not confirmed billing."""
        return 1 + int(self.small_intent) + int(self.fallback_intent)

    @property
    def rq3_partition(self):
        if self.transition_injected is True:
            return "injected"
        if self.transition_injected is False:
            return "no_fault_injected"
        return "injection_unknown" if self.small_intent else "pending_not_attempted"


def next_step(state, threshold):
    """At most one post-fault small attempt, then at most one terminal fallback.

    Calls receive only candidate evidence and a supplied threshold. No reference,
    correctness score or fallback quality can affect the decision.
    """
    if not isinstance(state, RecoveryState):
        raise ValueError("RecoveryState required")
    # Validate a supplied threshold even for terminal/no-injection states.
    should_escalate(
        mean_nll=None, evidence_status="complete", has_parsed_call=False, threshold=threshold
    )
    if state.transition_injected is False:
        return "terminal_no_fault"
    if not state.small_intent:
        return "plan_fault_conditioned_small"
    if state.transition_injected is None:
        return "stop_unknown_injection_no_resubmit"
    small = state.small_response
    if (
        small is None
        or small.evidence_status in ABSENT_RESPONSE
        or small.evidence_status.startswith("interrupted")
    ):
        return "stop_unknown_small_no_resubmit"
    escalate = should_escalate(
        mean_nll=small.mean_nll,
        evidence_status=small.evidence_status,
        has_parsed_call=small.has_parsed_call,
        threshold=threshold,
    )
    if not escalate:
        if state.fallback_intent:
            raise ValueError(
                "Recorded fallback conflicts with an accepting gate; preserve the original policy"
            )
        return "accept_fault_conditioned_small"
    if not state.fallback_intent:
        return "plan_fault_conditioned_fallback"
    if state.fallback_response is None:
        return "stop_unknown_fallback_no_resubmit"
    return "terminal_fault_conditioned_fallback"
