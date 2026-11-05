# Development routing kernel and matched fallback preparation v1

This package starts Task 4 implementation while Task 3's final evaluation remains
open. It supplies a tested CPU policy kernel and a reference-free preparation
command. It does **not** freeze a threshold, authorize GPU dispatch, fit a final
calibrator or enable held-out access. No routing effectiveness result has been
measured by this package.

## What the kernel does

Implementation: `src/uqroute_tc/routing/development.py`.

The gate accepts a small-model candidate only when all three conditions hold:
the evidence status is complete, the pinned parser returned a call, and finite
whole-output mean-token NLL is at or below the supplied global threshold.
Boundary ties stay together. Missing token scores, malformed or incomplete
evidence and outputs without parsed calls escalate. An accept-none threshold is
represented by `None`, not an infinite score. A parsed `[]` is not accepted as a
call under this conservative implementation rule. This rule is a development
candidate to review before any final deployment policy is frozen.

The gate's API receives only NLL, evidence status, parser-call presence and the
threshold. Official labels, references and fallback outputs cannot influence
its decision. The evaluator uses labels afterward to measure the chosen policy.
Fallback is terminal: it never uses the reference to choose the better of the
two outputs, retries an unknown outcome, or switches back to the small model.

| Policy | Attempts charged | Output |
|---|---|---|
| Small only | One small-model attempt per case | Saved small response |
| Fallback only | One fallback attempt per case | Saved fallback response |
| Always cascade | One small and one fallback attempt per case | Saved fallback response |
| Gated | One small attempt per case, plus fallback on escalation | Small if accepted, otherwise fallback |
| Matched random | One small attempt per case, plus an exact requested number of fallback attempts | Fallback for seed-hashed selected case keys, otherwise small |

The random baseline samples across the entire input cohort, independently of
scores and outcomes; it does not force escalation of invalid small responses.
It matches the gate's fallback count, not the identities of its escalations.
Its final usability and reference outcomes remain visible. Seeds must be fixed
before reporting results; do not select the best-performing seed.

`threshold_frontier` enumerates accept-none and every distinct eligible NLL
boundary. It selects no optimum, cost budget or error target. It must be run on
development data only. A future grouped development selection procedure must
freeze its objective, feasibility rule and deterministic tie-break before
producing the one threshold used in held-out evaluation. Missing/ineligible
small evidence imposes a minimum escalation count even at the highest boundary.

## Interpreting replay output

Each input is a matched pair of saved small/fallback attempts, with a unique case
key, canonical group, benchmark, panel, population and declared development
partition. Mixed panels/populations, duplicate keys and test partitions are
rejected. The kernel performs no file or network access. The future data adapter
must independently verify the frozen split membership, source fingerprints,
prompt identity, scorer bindings and full intended cohort before constructing
these objects; a caller's string declaration is not provenance verification.
Do not drop unscorable or incomplete records from a paired cohort.

Official reference outcomes are independent of output usability. For example,
a truncated fallback response can match the released reference and still be
unusable under the conservative output rule. Both facts are reported without
relabeling. Unknown labels remain null: overall reference compliance is then
unavailable, and the report supplies lower/upper match-fraction bounds over the
full input denominator. Accepted risk is undefined at zero acceptance or when
an accepted reference outcome is unknown. Rescues and harms require both labels;
unavailable escalated pairs are counted separately.

Accounting includes the initial small attempt and every policy-required fallback
attempt, including failed attempts. Cached responses for a role a baseline does
not use incur no charge in that baseline. Counts describe policy attempt slots,
not confirmed server executions or billed requests. Unknown outcomes may have
unknown incurred usage. For each token/time field, the report gives its known
sum and missing-call count; the total remains null if any required value is
unknown. No missing value becomes zero. Saved elapsed times are sequential
replay proxies, not measured online cascade latency, GPU seconds or currency
cost. Repeated sampling, recovery, overhead and price scenarios are not yet
implemented in this single-sample static kernel.

Illustrative fixture, **not project results**: on four artificial cases the
small-only and fallback-only policies each match two references. A threshold
that escalates three cases produces three matches with seven total attempts;
always cascade produces two matches with eight attempts. The fixture also
contains a small-correct/fallback-wrong pair. A larger fallback is not assumed
to improve every call.

## Next executable subtask: prepare the matched fallback

The three small models already have corrected full-development evidence.
Earlier 14B pilot/throughput outputs do not provide a matched fallback result
on all 1,728 corrected prompts. From the owner's repository root, run:

```bash
python tools/development_audits/routing_development_v1/prepare_fallback.py
```

The command first runs routing/preparation and frozen generation CPU checks.
It then invokes the **unchanged** corrected-generation preparer with the pinned
original primary audit, candidates and denominator sidecar, selecting
`qwen14b_awq` / `full-development`. It verifies the resulting 1,728 case keys,
order, lineage, messages and request settings against the preserved Qwen 1.5B
full-development plan; only the request model field may differ.

Fallback model/tokenizer revision remains
`539535859b135b0244c91f3e59816150c8056698`, float16, AWQ 4-bit, under the frozen
Task 1 server/request settings. No references or labels are packaged.

Fresh ignored output directory:
`artifacts/local_development_audits/fallback_primary_development_preparation_v1/`

- `prepared/manifest.json` and `prepared/requests.json`
- `qwen14b_awq_full_development_transfer_v1.zip`
- `summary.json`, including the actual manifest/ZIP hashes and pending checks

The command requires the owner's existing `full_primary_audit_v1`,
`population_plan_v1` and Qwen 1.5B imported prepared plan. It preserves them and
refuses an existing destination. These local audit inputs are not in Git.
Preparation has **not** been run on those owner-only inputs in this update;
orchestration and request comparisons were tested with synthetic inputs.

Model-specific tokenizer/context validation, current GPU/quota checks and runtime
attestation must precede a separately authorized development dispatch. Preserve
new raw evidence, run CPU replay and use a separately evidence-bound fallback
scorer before constructing routing pairs. Existing small-model scorer pins must
not be repointed to the new fallback. The fallback run is a prerequisite for
measured rescues, harms and threshold selection; this preparation supplies no
fallback-quality or routing-benefit result.

## Verification and remaining freeze decisions

```bash
PYTHONPATH=src python -m unittest discover -s tests/unit -p test_routing_development.py
python -m unittest discover -s tools/development_audits/routing_development_v1 -p 'test_*.py'
```

Tests cover label-independent decisions, exact ties, malformed/nonfinite inputs,
rescue/harm accounting, terminal unusable fallback, missing labels/usage, baseline
call differences, deterministic random matching, full request matching, fresh
packaging and overwrite refusal. They use synthetic records and no GPU.

Final population/objective dispositions, development-only method selection,
calibration/refit policy, grouped threshold validation, final statistical rules,
recovery and complete policy cost accounting remain open. An immutable shared
protocol artifact must resolve these before new held-out access. Task 3 and
Task 4 completion are not asserted.
