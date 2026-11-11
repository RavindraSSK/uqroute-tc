# Development recovery context preparation and bounded controller v1

This begins the separate Task 4 recovery implementation after review of the
static OOF/conditional-bootstrap tradeoffs. It supplies reference-free request
preparation and a pure CPU decision controller. Owner preparation is complete:
750/828/834 pending eligible episodes and 90/12/6 terminal no-injection plans for Qwen 1.5B/Llama 3B/Qwen 7B, with all
52 checks passing. Model context/resource checks, durable dispatch, fault-conditioned
generation, recovery scoring and effectiveness evaluation remain pending.
No readiness flag changes.

Preparation command (already completed by the owner; preserve the occupied output):

```bash
python tools/development_audits/recovery_development_v1/prepare.py
```

The command runs 23 controller, nine preparation and 20 existing routing checks.
It performs no inference, network request, tool execution or reference scoring.
It does not read answer sidecars, saved official scoring outputs, raw benchmark files
or held-out split records. Original evidence and previous results are preserved.
An existing preparation output is rejected rather than overwritten.

## Initial source population and fault construction

The command verifies the pinned file inventories and complete generation replays
of the three saved small-model primary-development runs. Initial candidates are
the 140 clean anchors per model, checked against the immutable primary-development
audit inventory and original prepared manifests. All models retain the same clean
case identities and corrected prompt messages. The other 59 primary test groups
and sensitivity-only groups are not preparation inputs.

This is reuse of saved initial clean outputs, not 420 new initial generations
or a fresh reproduction of the entire benchmark transition runner. Future
comparisons charge one initial small-model attempt per policy episode. Initial
responses reused across six fault scenarios remain dependent by canonical group;
scenario cost totals are not new physical-generation or GPU-billing totals.

The six error templates are extracted directly from the pinned released runner:
`timeout`, `rate_limit`, `auth_error`, `server_error`, `malformed_response`, and
`schema_drift`. The initial-call trigger uses the released official parser, which
is distinct from the frozen canonical parser used for uncertainty eligibility.
It does not consult reference correctness. A known returned initial text with no
official parsed call produces a terminal no-injection plan. Invalid/truncated
initial token evidence is retained; it does not itself prevent injection planning
when the released official parser found a call. The current source cohorts require
a known successful HTTP initial response; differing initial HTTP evidence stops
preparation for review. The pure context constructor also supports an explicit
initial-request-error flag for future executors. Original statuses, finish reasons,
usage, elapsed metadata and raw-response hashes are retained separately.

Eligible contexts append the preserved initial raw output as an assistant turn
and the released feedback as a user turn, using the first official call name:
`Tool execution result for <name>: <released error message>`.
The base prompt is the corrected prompt from the saved static plan. Tests compare
the append convention with the pinned source formatter; there is no paraphrase,
response repair, changed tool schema or new perturbation taxonomy.

These are benchmark error-feedback simulations. Preparation does not execute an
external tool, observe an actual tool timeout, re-authenticate, change an API schema
or demonstrate execution success. Final recovery correctness/scoring dispositions
remain a separate protocol decision.

## Planned feedback versus observed injection

Every model/case/fault episode is retained. Eligibility and observed injection
are separate:

- Eligible prepared context: `transition_injected = null`, pending an actual fault-feedback submission/attempt record.
- Terminal initial no-call/error plan: `transition_injected = false`; no post-fault request body is created.
- Observed fault-conditioned attempt, once recorded by a future executor: `transition_injected = true`, even if its response is unavailable.
- An occupied intent without established injection remains unresolved, not an automatic `false` or a fresh request.

The CPU controller separates `pending_not_attempted`, `no_fault_injected`,
`injection_unknown` and `injected`. No-fault predictions are excluded from RQ3
and counted separately under the existing protocol. Pending plans are not
predictions or recovery denominators. Unresolved injection requires explicit
review; it is not silently scored as failure/success or pooled with no-fault cases.
The compatibility metadata alias `perturbation.metadata.pass1_had_tool_calls`
mirrors observed injection status, despite its name. Actual initial parser-call
presence is recorded independently as `initial_has_official_call`.

## Bounded candidate controller

`src/uqroute_tc/routing/recovery.py` implements a development candidate:

1. Plan at most one small-model response conditioned on the observed fault context.
2. Accept it only when complete, canonically parsed and finite mean NLL is at or below the caller-supplied threshold, retaining inclusive ties.
3. Otherwise plan at most one fallback response on the same fault-conditioned messages; that fallback is terminal, including when unusable.

There is no selected or default deployment threshold, and no static OOF threshold
is assumed to transfer to fault-conditioned outputs. Explicit `None` means
accept-none. Unknown/unresolved stages stop without automatic resubmission.
Known returned truncated/invalid evidence can trigger the one fallback stage.
The controller receives no references or correctness labels and cannot select
the better output using an oracle. Replacing a policy after occupying a fallback
slot cannot hide that attempt under an accepting gate.

State intent flags are caller-provided evidence, not a durable ledger themselves.
A future executor must persist unique stage intents, verify model/revision/body
bindings, record actual submission/injection and raw outcomes, and preserve
unknown slots. This package supplies no live dispatch or resume implementation.
The controller counts at most three scenario attempt slots: initial small,
post-fault small and post-fault fallback. Counts are not confirmed server
executions or complete cost accounting. Recovery-only/fallback/random baselines,
post-fault scoring and all required policy usage/overhead accounting remain pending.

Every returned post-fault candidate must bind to the exact fault-context message
hash. A context-incompatible static fallback record is rejected. Small and fallback
recovery plans use identical fault-conditioned messages, differing in model ID;
the uncertain post-fault small response is not added to the fallback context.
Different initial-model histories retain separate episode identities. Prepared
fallback requests are potential requests, not occupied intents or incurred cost.

## Output and execution boundary

Fresh ignored output: `artifacts/local_development_audits/recovery_development_preparation_v1/`.

- `summary.json`: per-model initial/episode counts, terminal no-injection and pending-eligible plans, potential role counts and ZIP fingerprints.
- `provenance.json` and initial replay directories: source/input hashes and preserved replay verification.
- Per-model directories: `manifest.json`, `episodes.json`, `small_requests.json`, `fallback_requests.json`.
- Three per-model `*_recovery_development_transfer_v1.zip` archives, with the same four files and validated payload/member hashes.

No answer sidecars or correctness labels are packaged. Prompt content and initial
model outputs remain private in ignored artifacts. Each role retains the frozen
Task 1 request/model settings and records the server/configuration authority.
These plans are **not compatible with the static dispatcher** and do not authorize
dispatch. A dedicated recovery executor is still required.

Model/tokenizer context checks must cover every new small and fallback message
history, including the saved initial output and fault turn. The old static context
check is insufficient. No overflow is silently trimmed or dropped. Resource/quota
measurement, a bounded development execution manifest, injection/outcome ledger,
released-reference scoring interpretation and final threshold/objective decisions
remain pending before reporting actual recovery results.

Ruff, the 52 focused checks and a full synthetic preparation/publication smoke
check pass. The synthetic integration includes both an eligible initial output
with invalid token evidence and a no-call output; it validates both role payloads,
all six templates and ZIPs without calling reference scoring. Available saved
fallback plan metadata also confirms the shared 140 clean prompts have supported
system/user message shapes. Complete small-model owner sidecars are unavailable
in the working implementation checkout. The owner subsequently supplied successful
preparation counts and transfer fingerprints; those aggregates are recorded in
[CPU context preflight](RECOVERY_CONTEXT_PREFLIGHT_V1.md). Run that preflight next;
no actual context-fit or recovery-effectiveness result is established yet.
