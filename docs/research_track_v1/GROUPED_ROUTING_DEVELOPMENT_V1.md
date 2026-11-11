# Group-separated development routing validation v1

The owner completed the saved-pair replay and accounting review. The Qwen 7B
25% retrospective reference point improves matches, but increases the saved
request-time proxy per match relative to fallback-only. A final operating point
must account for reliability, usable outputs and costs instead of picking the
largest development match count.

This new CPU subtask implements exploratory group-separated validation of the
existing fixed escalation-cap rule. The owner subsequently completed execution at `5528f84` and supplied its full
terminal report; aggregate findings are recorded below.
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

## Owner OOF results — 2026-11-11

The supplied terminal output reports all 27 new, 28 paired-input and 20 kernel
checks passing, followed by four-model evidence revalidation and all 30
model/endpoint/cap OOF analyses. This is owner-executed development evidence;
complete scoring sidecars remain on the owner checkout.

| Small model | Endpoint | Training cap | OOF rows | Matches | Fallback calls | Unusable final | Cap-exceeded folds | Request seconds/match |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen 1.5B | Reference | 25% | 1,512/1,512 | 721 | 381 | 90 | 3 | 5.390 |
| Qwen 1.5B | Reference | 50% | 1,512/1,512 | 770 | 753 | 131 | 3 | 7.512 |
| Llama 3B | Reference | 10% | 1,512/1,512 | 644 | 154 | 24 | 2 | 8.970 |
| Llama 3B | Reference | 25% | 1,512/1,512 | 673 | 380 | 65 | 3 | 10.781 |
| Llama 3B | Reference | 50% | 1,512/1,512 | 739 | 761 | 130 | 3 | 12.735 |
| Qwen 7B | Reference | 10% | 1,512/1,512 | 812 | 150 | 20 | 1 | 9.512 |
| Qwen 7B | Reference | 25% | 1,512/1,512 | 829 | 382 | 53 | 3 | 10.988 |
| Qwen 7B | Reference | 50% | 1,512/1,512 | 818 | 754 | 120 | 2 | 14.068 |
| Qwen 1.5B | ToolEyes relevance | 25% | 216/216 | 194 | 61 | 0 | 2 | 2.419 |
| Llama 3B | ToolEyes relevance | 25% | 216/216 | 196 | 56 | 0 | 3 | 3.952 |
| Qwen 7B | ToolEyes relevance | 25% | 216/216 | 206 | 53 | 0 | 1 | 5.372 |

Reference zero-cap views have no OOF predictions for any model; Qwen 1.5B's
reference 10% view also has none. They are infeasible training rules, not zero
accuracy. ToolEyes zero-cap Qwen 1.5B/Llama views cover only 42/216 rows and
retain unavailable full-cohort rates. Qwen 7B's zero-cap ToolEyes rule has full
coverage but still escalates two validation cases beyond training maxima.
The other displayed nonzero-cap views have complete OOF coverage.

Qwen 7B at the 25% training cap has 829/1,512 reference matches (54.83%), versus
790 small-only and 787 fallback-only. It escalates 382 cases (25.26%), exceeding
the training cap in three folds. The saved request-time proxy per match remains
higher than fallback-only, 10.988 versus 9.534. At the 10% training cap, 812
reference matches and 9.512 seconds/match are point estimates; the small timing
difference from fallback-only is not evidence of an established efficiency gain.

The next [conditional paired interval subtask](GROUPED_ROUTING_INTERVALS_V1.md)
is implemented and tested; actual execution is pending. It keeps the original
OOF thresholds/decisions fixed while resampling canonical groups within benchmark.
It is an exploratory uncertainty diagnostic, not full learning-procedure validation,
monetary-cost evaluation, model selection or a final protocol freeze.
