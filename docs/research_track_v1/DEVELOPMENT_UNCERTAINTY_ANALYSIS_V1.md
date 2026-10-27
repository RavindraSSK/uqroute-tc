# Development uncertainty analysis v1

Baseline: `e3c7b611b7835575ba23426030823b875006746b`.
Scope: retrospective descriptive ranking diagnostics for the approved corrected
Qwen 1.5B 69-case primary-development coverage run. This implementation does
not finish Task 3, freeze the main protocol or enable held-out evaluation.

## Evidence boundary

The owner completed coverage generation, local CPU replay, official reference
scoring and the separate reference-review diagnostics. The approved saved
scores contain 21 compliant and 42 noncompliant reference-panel cases, plus
five relevant and one irrelevant ToolEyes case. The latter six are a separate
panel and are never pooled into a headline reference-compliance metric.

The 69 selected cases cover constructed benchmark/source strata and 55 groups;
only one selected perturbed case has its clean anchor selected. This is not
population sampling, an independent-case design or a paired perturbation
comparison. Reference ambiguity, missing reference credential literals and
objective-detector limitations remain documented separately. No flags exclude
rows or correct official outcomes in this analysis.

This policy was written after observing these development outcomes and
reference-review findings. It is not a preregistration. The original parser,
scorer, uncertainty definitions, detector outputs, references and labels are
unchanged. The adapter consumes only the previously reviewed scores/provenance
and prepared manifest/requests. Exact byte fingerprints, baseline ancestry,
case IDs, panels, development scope and evidence status are checked before
analysis. No reference sidecar, raw benchmark, split, new examples or model
weights are opened. No network/model requests occur. Existing output folders
are refused; every run must publish into a fresh local artifact directory.

## Measures and outcome direction

Use four saved measures without recalculation or calibration:

1. Whole-output sequence NLL.
2. Whole-output mean token NLL.
3. Whole-output maximum token surprisal.
4. Meaningful-token mean NLL, only where the frozen method supplied it.

The binary positive outcome is official noncompliance (`not correct`) in the
reference panel and official name irrelevance in ToolEyes. Higher uncertainty
predicts the positive outcome. Use the scorer's boolean `correct`, not a
partial RoTBench score threshold. Noncompliance is a scorer-defined proxy, not
proof of execution failure or a completed semantic adjudication.

## AUROC and average precision

AUROC compares every positive/negative score pair: positive scores above
negative scores earn one, exact ties earn one half, and lower positive scores
earn zero. Implementation uses an equivalent ascending score-block rank sweep.
It is undefined when no eligible cases or only one outcome class is present.

Average precision (AP) visits distinct scores in descending order. Include all
cases tied at a threshold, compute cumulative precision and recall after each
block, then sum `change_in_recall * precision_after_block`. This is
noninterpolated score-block AP, not trapezoidal precision-recall area. AP is
undefined with no positive observations, including an empty cohort; it equals
one if all nonempty observations are positive. Error prevalence is reported
for context. It is not asserted to be the exact finite-sample expected AP of
a random permutation. Undefined values are JSON null with explicit reasons,
never fabricated zeros.

Equal-score ties mean exact numeric equality. No rounding, random jitter or
case-ID tie-breaking changes the ranking or splits a tie block.

## Risk-coverage

Accept cases in ascending uncertainty order, adding entire equal-score blocks.
At an observed cutoff, acceptance is `uncertainty <= cutoff` and risk is the
fraction of accepted cases whose official boolean outcome is noncompliant or
irrelevant. Partial official scores do not define this risk. The zero-acceptance
point has undefined risk, represented as null rather than zero.

Each point reports two denominators:

- Eligible coverage: accepted rows / measure-eligible rows.
- Original-panel coverage: accepted rows / all original rows in that panel or
  per-benchmark cohort, retaining rows with unavailable evidence.

Missing evidence is not imputed, ranked as certain, declared an error or
silently removed from official accuracy. Maximum original-panel coverage and
the number of original rows outside the eligible cohort remain explicit.

The scalar `tie_block_right_step_area_on_eligible_coverage` is defined exactly
as `sum(block_size / eligible_rows * cumulative_error_risk_after_block)`.
It is a discrete right-step area over the eligible cohort, not an interpolated
curve area, a full-original-panel area or an operational routing result. Empty
cohorts have null area. The observed curve cutoffs are diagnostic points; no
routing threshold is selected.

## Missingness and comparisons

Available-case outputs retain eligibility and unavailable case IDs/reasons for
each measure. Whole-output measures have 63 eligible reference-panel cases;
meaningful-token mean NLL has 33. The other 30 cases remain in official accuracy.
ToolEyes has six eligible cases for each measure. ToolAlpaca retains its scoped
meaningful-token exclusion, so its meaningful-token analysis is undefined.

Repeat all four measure analyses on their common eligible case set: 33
reference-panel cases and six ToolEyes cases in this approved run. The common
cohort makes case identities comparable across measures but does not repair
nonrandom missingness or establish representative performance. Its original-
panel coverage remains bounded by the original panel denominator.

Reports are separate by panel and benchmark. Pooled reference-panel rankings
can be confounded by benchmark-specific uncertainty scales and error rates;
inspect within-benchmark results. Small strata and one-class cohorts remain
visible. No best measure, threshold or acceptance target is chosen from these
results. There is no claimed clean-versus-perturbed effect from unpaired cases.

## Explicitly disabled and unresolved

Calibration is not fitted or evaluated. Exponentiating mean NLL or rescaling
scores is not treated as calibrated correctness probability. Confidence mapping,
grouped development fitting/validation, binning, missing-evidence policy and
calibration metrics need a separate explicit protocol decision before use.

Routing threshold selection, fallback policy evaluation, hypothesis tests,
group-bootstrap intervals and final held-out evaluation remain disabled.
Before inferential main-result claims, resolve population weighting, validated
Observation/Action/Reward taxonomy, group-aware resampling and pairing, small-
stratum rules and final shared protocol freeze. Repeated-sample comparison,
other model roles and the larger static experiments remain outstanding.

## Outputs and preservation

`tools/development_audits/uncertainty_analysis_v1/analyze.py` writes three fresh
files under local development artifacts:

- `analysis.json`: cohort counts, ranking metrics, tied risk-coverage points,
  missingness, common-case analyses, explicit undefined reasons and limitations.
- `case_measures.json`: original official score dictionaries and flags with the
  four saved scalar uncertainty measures; unavailable values remain null.
- `provenance.json`: exact input hashes, policy hash and LF-normalized
  implementation hashes for the adapter and pure metric module.

Paths are normalized before publication; symlink inputs and overlap are
rejected. Input bytes are rechecked before writing. A bounded final-directory
rename retry handles transient permission errors: six attempts, at most 3.1
seconds delay, with no replacement of an existing destination. This is not
an inference retry. Old results/provenance are never rewritten.

## Verification

Package-author CPU verification: 37 synthetic tests pass. Hand-calculated
perfect/reversed/tied rankings, one-class/empty outcomes, exhaustive small
pairwise-AUROC and threshold-AP oracles, tie-block risk curves, exact area
examples, missingness, same-case comparisons, partial-score handling, input
immutability, tampered hashes and relative-path publication are covered.
The synthetic 69-case integration isolates Git ancestry and input pins;
production performs those checks. No dataset/model is required by the tests.

An additional author-only independent check compared AUROC/AP against
scikit-learn on 986 generated two-class, tie-heavy inputs; all agreed within
1e-12. Scikit-learn is not a project/runtime/test dependency. A separate scratch
replay used the uploaded hash-approved inputs with only Git ancestry isolated;
its panel counts matched the saved scoring evidence. Owner Windows tests and
local analysis execution remain pending. GPU execution is unnecessary.

The implementation generates JSON curve points for subsequent reproducible
figures; it does not yet produce paper plots, a final failure catalogue,
calibration evidence, group confidence intervals or Task 3 completion.
