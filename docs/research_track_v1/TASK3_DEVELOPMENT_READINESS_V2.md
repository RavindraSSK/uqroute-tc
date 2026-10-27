# Task 3 development readiness and remaining requirements v2

Evidence baseline: ff277c8. This current development snapshot supersedes older
pending-development statements for the milestones below. Earlier documents
remain historical records. This is not a final protocol freeze.

## Verified development milestones

- All three selected small models generated 1,728 primary-development responses
  each: 5,184 responses in total. The source inventory retains 1,754 rows,
  140 groups and 26 construction blocks without imputed model outcomes.
- Full local replay matches exported evidence for each model. Official scoring
  includes returned non-complete outcomes; uncertainty eligibility is separate.
- Reference compliance: Qwen 1.5B 572/1,512; Llama 3B 621/1,512;
  Qwen 7B 790/1,512. Separate ToolEyes name relevance: 174/216, 181/216,
  and 204/216 respectively. These are not executable task-success results.
- Three-model comparisons use matched cases and report missingness explicitly.
  Whole-output reference intersection: 1,490; all-measure intersection: 243.
- Each model has 1,588 constructed clean/perturbed pairs. Paired descriptive
  changes retain dependent clean anchors and distinguish pair/group weighting.
- Development reporting produced 35 bootstrap entries and 35 SVG plots,
  21 calibration scopes, 12 category scopes and 460 unique model/case failures
  across overlapping retrospective diagnostic bands (489 catalogue entries).
- Category construction totals: 140 clean, 560 Observation, 542 Action,
  486 Reward. Reward membership does not establish preference success.
- Two full-development cross-model examples were reviewed in ff277c8.
  They are illustrative, not an exhaustive semantic adjudication.

## This new implementation

The development_completion_v1 tool writes a fresh, separately versioned output.
It revalidates all three full-development scores and comparisons before analysis.
It does not rewrite existing diagnostics or change their hashes.

Calibration uses whole-output mean NLL, five deterministic group-separated
folds, training-only log1p scaling, and the existing ridge-logistic objective
with nonnegative error slope. Compliance probability is thus nonincreasing
with NLL. If the unconstrained optimum has negative slope, convexity places
the constrained optimum at slope zero; the intercept is reoptimized at the
training error fraction. This differs from the smoothed training-fold baseline.
Training folds still require ten groups and both classes. Missing scores and
unavailable validation folds remain explicit. No final full-development refit,
threshold selection or deployable probability guarantee is supplied.

Paired intervals use 2,000 canonical-group draws within benchmark, retaining
all variants and all model outcomes together. Pair-weighted and equal-group
correctness changes and paired model differences use the same draws.
A repeated sampled group contributes once per sampled occurrence, including
for equal-group weighting. Changes mean perturbed minus clean reference
compliance or separate ToolEyes relevance. Intervals are percentile 95%,
withheld below ten groups or 90 percent valid draws. They are exploratory,
condition on the observed group/benchmark mixture, and are not causal effects.
No multiplicity adjustment or superiority claim is supplied. ToolEyes panel
and benchmark views duplicate the same data, not independent evidence.

## Remaining requirement map

| Requirement | Current position | Remaining work |
|---|---|---|
| Primary development single-sample runs | Complete for three small models | Final manifest and evaluation artifact review |
| Reference/relevance metrics | Measured separately | Preserve proxy boundaries in final claims |
| O/A/R and perturbation types | Development diagnostics implemented | Final weighting, category/benchmark reporting decisions |
| AUROC, AP and risk coverage | Matched development diagnostics implemented | Approve final tie/coverage/integration rules |
| Calibration | Unconstrained diagnostics measured; constrained implementation supplied | Owner run/review and final method approval/refit policy |
| Paired-change intervals | Implementation supplied | Owner run/review; final statistical settings |
| Failure catalogue | Diagnostic catalogue and illustrative reviews available | Final band definition, broader review and evidence manifest |
| Repeated sampling | Frozen 30-case/900-response historical diagnostic | Corrected-prompt subset and fresh generation amendment; no response transfer |
| Sensitivity population | Separate extension remains required | Trusted separate development preparation, run and analysis plan |
| Development method selection | Evidence available | Recorded selection rule and immutable decision artifact |
| Shared Task 3/4 freeze | Pending | Gate, baselines, missing/status rules, cost/recovery/sampling decisions |
| Held-out static evaluation | Blocked | Separate approved freeze and controlled evaluation |
| Task 3 final deliverables | Partial | Frozen dataset, final reproducible figures and reviewed claims |

The historical main plan proposes 10,000 bootstrap draws; that value was never
frozen. The 2,000-draw diagnostics do not silently establish the final setting.
Original near-reproduction and pre-split clean-result exposure remain disclosed.
No sensitivity or repeated-sampling requirement is removed for time pressure.
Task 4 fallback, routing, recovery and cost results remain pending; fallback
size alone does not establish better outcomes. Task 5 packaging remains pending.
Held-out access and main-experiment readiness remain false.
