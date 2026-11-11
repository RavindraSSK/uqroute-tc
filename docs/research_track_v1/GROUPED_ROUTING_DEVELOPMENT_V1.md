# Group-separated development routing validation v1

The owner completed the saved-pair replay and accounting review. The Qwen 7B
25% retrospective reference point improves matches, but increases the saved
request-time proxy per match relative to fallback-only. A final operating point
must account for reliability, usable outputs and costs instead of picking the
largest development match count.

This new CPU subtask implements exploratory group-separated validation of the
existing fixed escalation-cap rule. Actual owner execution remains pending.
It fits no monetary model, uses no new inference and does not freeze a final
routing objective or deployment threshold.

Run once from the updated owner repository root:

```bash
python tools/development_audits/grouped_routing_v1/run_validation.py
```

## Evidence binding

The versioned policy pins the existing paired-input loader, routing kernel,
all four frozen scorer adapters and their policies. The command recomputes the
four original official scorings and full replays using the preserved owner
reference/audit sidecars. Their prior scores/summaries and exported replay
records/summaries must match. Original prompt bodies, case lineage and primary
development membership are rejoined; the resulting 1,728 pairs per small model
must exactly reproduce the previous normalized paired inputs.

No held-out dataset or split records are opened. The 26 construction blocks
remain outside the model-outcome denominators, with no imputation. Non-complete
outputs and missing uncertainty retain their previous meanings and labels.
Every original input fingerprint is checked again before fresh publication.
Previous scores, references, labels, evidence and retrospective outputs remain
unchanged. Outputs stay ignored by Git; individual case records are not published.

## Fold and threshold rules

Canonical groups are ranked by SHA-256 within benchmark using seed 1729 and
assigned round-robin to five folds. All clean/perturbed variants of a group stay
together. The assignment is shared across the three small models. Reference
compliance and ToolEyes relevance are evaluated separately. Each endpoint uses
a pooled threshold across its benchmarks; there is no per-benchmark threshold
refit. Endpoint metrics are case-weighted, so larger benchmarks contribute more.

For each fold and each existing diagnostic cap (0%, 10%, 25%, 50%, 100%), all
threshold construction uses training-group candidate scores. Let N be the
training case count and K = floor(cap * N). After checking forced escalation,
select the smallest eligible score boundary accepting at least N-K training
cases. Complete parsed candidates with finite mean NLL at or below that boundary
are accepted. Entire exact-score ties are retained. A 100% cap uses accept-none.
Neither reference labels nor fallback outputs/usage enter threshold fitting.

Apply that fitted threshold unchanged to the validation groups. Do not recompute
a validation quantile or retune the threshold using validation outcomes.
Realized validation escalation can exceed the training cap, including the
nominal zero-cap view when a validation score exceeds the training maximum.
The report displays actual fallback calls and counts cap-exceeded folds;
per-fold training/validation counts and thresholds remain in the saved results.

If forced fallback already exceeds a training cap, that fold has no fitted
policy or invented validation prediction. Empty training/validation folds are
also explicit. Full-cohort match rates remain unavailable when any cases lack
OOF predictions. Evaluated-row metrics, original/evaluated denominators, missing
rows and full-cohort match-fraction bounds are reported separately. Comparisons
use baselines on exactly the same evaluated rows; do not compare incomplete
OOF results with an unrelated full-cohort denominator.

Each feasible fold evaluates small-only, fallback-only and always-cascade, plus
ten seeded random comparators (1729–1738). Random escalation exactly matches the
gated fallback count within each validation fold; it does not force escalation
for unavailable small evidence. Final fallback is terminal and no label-based
return-to-small override is allowed. Random means are not confidence intervals.

## Accounting, outputs and limits

All selected attempts contribute their saved token usage and elapsed time,
including unsuccessful attempts. Unknown usage remains unavailable. Zero or
unknown match denominators have no fabricated efficiency ratio. Final-output
usability is distinct from reference compliance: it requires complete evidence
and a canonical parsed call, not demonstrated tool execution.

Fresh output: `artifacts/local_development_audits/grouped_routing_development_v1/`.

- `REPORT.md` and `summary.json`: 30 model/endpoint/cap views, actual escalation, same-row baselines, usability and accounting.
- `oof_results.json`: fold fits, OOF predictions, same-row baselines and ten random aggregates.
- `fold_assignment.json`: one benchmark-qualified fold assignment per canonical group.
- `provenance.json` and `revalidation/`: policies, source/input fingerprints and reproduced scorer/replay artifacts.

An existing output is rejected and preserved. The command first runs 27 new
synthetic checks, 28 paired-loader/replay checks and 20 routing-kernel checks.
Ruff and a mocked-runner publication/serialization smoke check also pass.
The complete original owner sidecars are unavailable in the working implementation
checkout, so synthetic verification is not an actual model-result claim.

This policy was recorded after inspecting full-development reports. Group-separated
folds prevent direct group overlap during threshold fitting; they do not undo
that prior exposure or supply untouched confirmatory evidence. No best model/cap
is selected, no final all-development threshold is refitted, and no statistical
superiority, executable-success, monetary saving or online-latency claim follows.
Saved request-time sums remain separate-run proxies. Group-aware intervals,
a fixed final objective, full policy costs, live escalation, recovery and the
shared protocol freeze remain outstanding before separate held-out evaluation.
