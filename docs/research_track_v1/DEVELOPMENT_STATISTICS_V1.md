# Development statistical diagnostics v1

Baseline: `37430ea`. This add-on revalidates the existing three-model
selected development evidence into a fresh output directory before analysis.
Existing scores, labels, references, policies and outputs remain unchanged.
Held-out access and main-experiment readiness remain disabled.

## Cohorts and estimands

Reference compliance and deterministic ToolEyes name relevance remain separate.
Per-benchmark results accompany pooled reference-panel diagnostics. Higher
uncertainty predicts an official error, not a verified execution failure.

The whole-output comparison uses mean-token NLL on the three-model shared
eligible cohort. The all-measure comparison uses the three-model, all-measure
intersection for all four frozen measures. Each model retains its own labels.
Unavailable cases remain in original-panel coverage denominators and are
never imputed as correct, incorrect or certain.

## Exploratory bootstrap rules

Use 2,000 draws, fixed deterministic cohort seeds and 95% percentile intervals
with linear interpolation. Benchmarks are fixed strata. Within each benchmark,
sample its observed canonical groups with replacement, retaining every selected
eligible row of each sampled group, including repeated draws. Metrics are
case weighted; replicate row counts may vary. The same draws serve every model
and measure in a shared cohort. Paired differences are first model minus second.

Report AUROC, noninterpolated score-block AP and the frozen tie-block right-step
area on eligible coverage. Lower area is better. Report valid and undefined
replicate counts. Withhold intervals when the point is undefined, fewer than
10 groups are present, or fewer than 90% of draws produce a defined metric.
These conservative reporting guards are diagnostic choices, not validated
coverage guarantees. One-class cohorts retain undefined AUROC; no-error AP
stays undefined. Sampling strata with one group cannot estimate within-stratum
variation. Intervals condition on the selected cases and fixed benchmarks.

No hypothesis test, simultaneous interval, multiplicity adjustment, population
representativeness or final method selection is asserted. AP differences also
reflect model-specific error prevalence. Intersections do not repair nonrandom
missingness. Reference flags never exclude cases or change outcomes.

## Outputs and verification

`tools/development_audits/development_statistics_v1/run_statistics.py` produces
`statistics.json`, `REPORT.md`, a fresh evidence-revalidation subdirectory and
35 standalone SVG risk-coverage figures. Figures show attainable exact-score
block points, using original-panel coverage, without interpolation, origin
risk, bootstrap bands or threshold selection. No graphics dependency is needed.
The JSON records the policy and exact cohort keys. The revalidation subdirectory
records source/input fingerprints through the existing three-model workflow.

Run synthetic tests with Python unittest discovery in this source directory.
Run the analysis from the repository root with `--repo-root .`. The default
output is `artifacts/local_development_audits/development_statistics_v1` and
must not already exist. A failed run never authorizes deleting prior evidence.
The installer does not stage, commit, push, launch inference or access a network.

This subtask supplies exploratory intervals and risk-coverage artifacts only.
Calibration, full-population experiments, perturbation taxonomy comparisons,
final protocol freeze and held-out evaluation remain separate work.
