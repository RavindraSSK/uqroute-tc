# Exploratory development calibration v1

Baseline: `78522c9`. Revalidate the existing three-model development evidence
into a fresh directory, preserving all previous source policies, outcomes and
outputs. No benchmark clone, split records, held-out inputs or network access
is used. Existing official compliance and ToolEyes relevance remain separate.

## Fixed diagnostic design

Use whole-output mean-token NLL only. The feature is fixed for this diagnostic,
not selected as a winning measure. Transform with log1p, then standardize using
training rows only. Fit a two-parameter logistic error-probability model with
unpenalized intercept and slope penalty 1 on summed log loss. Negative slopes
are permitted and recorded; no monotonicity or probability calibration claim
is imposed. Optimization failure stops the run instead of changing settings.

Assign five folds independently of outcomes: within benchmark, sort canonical
groups by SHA256 of `1729/benchmark/group` and assign round-robin. All selected
rows of a group have the same fold across models, regardless of eligibility.
Each fitted scope uses only its own training rows: the reference panel,
ToolEyes relevance, and each benchmark are fitted separately. Validation rows
never contribute to scaling, coefficients or the baseline. No final full-data
calibrator is fitted. Training folds require at least 10 groups and both
outcome classes; otherwise validation predictions remain unavailable.

Report out-of-fold Brier score, log loss (probabilities clipped at 1e-15 only
for log-loss calculation), and ECE with 10 fixed equal-width error-probability
bins. Bin edges are left-inclusive, except 1 belongs to the final bin. Compare
the logistic mapping with the training-fold smoothed error-rate predictor
`(errors+1)/(rows+2)` on exactly the same eligible validation rows. This
baseline is a comparator, not an alternative deployment policy.

Truncated/unavailable evidence never becomes zero uncertainty or an outcome
label. Original denominators, excluded case keys, fold membership, fitted
parameters, predictions and unavailable reasons remain visible. Model-specific
eligible cohorts differ. Pooled reference results reflect benchmark mixtures;
inspect per-benchmark results. Tiny ToolEyes folds will be unavailable under
the minimum-group rule. This is an honest non-estimate, not a failure to fix.

## Interpretation and execution

These diagnostics are retrospective, conditional on the 69 selected cases.
They do not establish population calibration, significance, threshold quality,
routing benefit or semantic correctness. ECE depends on bin choice and sample
size. No tuning, calibration confidence intervals, held-out method selection
or final protocol freeze is performed. A later approved evaluation design may
require different or additional calibration methods without rewriting this run.

Run unittest discovery in `tools/development_audits/development_calibration_v1`.
Then run `run_calibration.py --repo-root .`. The default new output directory
is `artifacts/local_development_audits/development_calibration_v1`, containing
`calibration.json`, `REPORT.md`, `provenance.json` and an evidence-revalidation
subdirectory. Existing output directories are refused. No Git mutation,
model inference or new GPU run is required.
