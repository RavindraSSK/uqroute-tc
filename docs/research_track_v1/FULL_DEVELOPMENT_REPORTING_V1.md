# Full-development statistical reporting v1

Baseline: d0fe407. This package combines exploratory development intervals,
calibration, released-category summaries and bounded failure reporting for the
three completed 1728-response runs. It preserves all prior evidence, outcomes,
reference labels, policies and analysis outputs. Held-out access stays disabled.

## Verification boundary

Recompute the three-model full-development analysis into a new directory. Its
existing evidence-bound scorers verify the saved responses and approved
reference sidecar. Compare prior summary, matched-comparison and paired-summary
JSON structurally before downstream reporting. Source fingerprints are locked
for the inherited metrics, cluster bootstrap, calibration, taxonomy and scorer
implementations. Recheck prior analysis hashes before publishing.

Taxonomy comes from the already approved development-only samples sidecar,
whose SHA256 is
23ac76ad69bf42e04ab6c2a0f9c274e6885c6c1c388aee8aa126f99341b2d533.
Validate selected primary-development identities and lineage, and the released
mdp_category/type fields, using the earlier category parser. The 26 blocks
remain in the revalidated scoring coverage summary without model outcomes.
No raw benchmark file or split record is read. Hashes establish consistency,
not authenticated provenance; the reviewed exporter remains trusted.

## Bootstrap and figures

Reuse the previously implemented 2000-draw benchmark-stratified canonical-group
bootstrap with deterministic cohort seeds. All selected eligible rows of each
sampled group are retained, including repeated draws. The case-weighted metric
estimand is distinct from equal-group weighting. The same cohort draws serve
all models and, within the all-measure cohort, every uncertainty measure.

Report 95% percentile intervals with linear interpolation for AUROC, tied-score
AP and the frozen tie-block right-step area on eligible coverage. Paired model
differences use shared resamples. Withhold intervals below 10 observed groups
or 90% valid replicates; undefined metrics stay undefined. Report replicate
counts and unavailable reasons. Sampling within a one-group stratum cannot
estimate its within-stratum variation. These guards do not prove interval
coverage. No multiple-comparison adjustment or significance claim is supplied.

Seven scopes (two separate panels and five benchmarks) each have a shared
whole-output mean-NLL comparison and four shared all-measure comparisons.
This produces 35 interval entries and 35 standalone SVG figures. ToolEyes panel
and benchmark scopes describe the same underlying cases; they are duplicate
reporting views, not independent evidence. Risk figures show attainable tie-block
points using original-panel coverage, without origin risk, interpolation or
bootstrap bands. Numerical risk curves are retained in bootstrap.json.

## Calibration and categories

Reuse the fixed five-fold canonical-group-separated calibration diagnostic.
Mean-token NLL receives log1p transformation and training-only standardization.
A ridge logistic error mapping uses unpenalized intercept and slope penalty 1
on summed log loss. Negative slopes remain permitted and recorded. This is
an exploratory mapping, not the final monotonic confidence mapping proposed
in the draft protocol. No model weights are trained or fine-tuned.

Each model/scope is fitted independently, with the same outcome-independent
group-fold assignment across models. Require at least 10 training groups and
both classes. Report out-of-fold Brier, clipped log loss and ten-bin equal-width
ECE against the smoothed training-fold constant baseline on identical rows.
Retain unavailable predictions, evidence exclusions, train/validation keys and
parameters. No final full-data calibrator or hyperparameter tuning is supplied.

Report clean, Observation, Action and Reward summaries for each model with
separate reference-compliance and ToolEyes panels and per-benchmark results.
Retain available-case and common-measure cohorts and reference flags. Class
composition differs across benchmarks and groups; no causal drop is asserted.
Reward metadata is not explicit intent, measured tool cost/latency or preference
success. No objective regex, reference flag or official outcome is modified.

## Retrospective failure catalogue

Two fixed reporting bands are added after earlier development results were
inspected. They are descriptive and not a preregistered final rule:

- Within each model/benchmark, target the lowest 20% mean-token NLL among
  eligible outputs. Keep the entire exact-score boundary tie; actual acceptance
  can exceed 20%. This is low uncertainty, not calibrated confidence.
- Separately report OOF estimated compliance probability at least 0.9 within
  each fitted model/scope. This is a model estimate, not a confidence guarantee
  or an operational routing threshold. Unavailable predictions cannot enter.

Catalogue entries retain case identity, scope, band, category, official outcome,
reference flags and evidence status. They do not reproduce responses, credential
literals or hidden reasoning. Flags are not semantic adjudications. Entries
can overlap across bands and scopes; report both entry count and unique
model/case count. No case is excluded or relabeled. Manual semantic review and
a final high-confidence-failure definition remain separate decisions.

## Execution and outputs

Run unittest discovery in tools/development_audits/full_development_reporting_v1,
then run_reporting.py --repo-root . The one-command installer performs both.
The default fresh directory is artifacts/local_development_audits/
full_development_reporting_v1. It contains REPORT.md, summary.json,
bootstrap.json, calibration.json, category_results.json, failure_bands.json,
failure_catalogue.json, taxonomy.json, provenance.json, 35 SVG files and a
three_model_revalidation subdirectory. Calibration JSON is indexed by model/scope.

The 2000-draw CPU stage may take several minutes; progress prints per analysis
and every 500 metric evaluations. No model inference or GPU is required. Existing
output directories are refused. The installer never stages, commits or pushes.

This package does not close Task 3. Paired-change confidence intervals,
calibration intervals, simultaneous bands, final semantic failure review,
final figures selection, protocol freeze and authorized held-out evaluation
remain separate. Existing Task 4 routing/recovery requirements are unchanged.
