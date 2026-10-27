# Three-model corrected development uncertainty analysis v1

## Scope

This separate CPU-only implementation extends descriptive analysis to corrected
Qwen 1.5B, Llama 3B and Qwen 7B outcomes on the same 69 selected development
case identities. It preserves the existing two-model analysis, all source
policies, scores, reference labels, evidence and generated reports.
The baseline is ad0790b9dceb1b68ab40837747bbd1ac95309a49.
No model requests, network calls, calibration fit, threshold selection, group
bootstrap, routing simulation, tool execution or held-out access occur.
The selected coverage sample is not a population estimate or final protocol freeze.

The immutable Qwen 1.5B scores, original scoring provenance and prepared request
files remain pinned to their reviewed SHA256 identities. Llama and Qwen 7B
scoring sources and their evidence-bound policies are independently pinned.
Both scorers rerun into new temporary output directories, validating the full
approved evidence archives, frozen generation methods, raw parser/scorer and
approved development sidecar lineage. The recomputed scores and summaries must
match the existing local outputs structurally before uncertainty analysis.
New recomputation provenance is retained; the original provenance is never
rewritten. The development reference sidecar is opened by the scorer only;
raw benchmark and split records are not opened. Hashes establish consistency,
not authenticated provenance or cryptographic proof of development filtering.

## Outcomes and probability availability

Every model retains 69 cases in correctness/relevance denominators, including
the saved Llama truncation. There are 63 reference-compliance rows and six
separate ToolEyes name-only relevance rows. Neither is executable task success
or semantic adjudication. Original source gpt_judge configuration does not
mean an LLM judge was run by these deterministic scoring implementations.
All reference flags remain retained and never exclude or relabel outcomes.
Cost/latency preference success is not assessed.

Whole-output evidence eligibility is Qwen 1.5B 69, Llama 68 and Qwen 7B 69;
meaningful-token eligibility is 39, 24 and 34 respectively, across both panels.
Missingness is never imputed. A truncated output keeps its scored raw text but
has unavailable probability measures. The original correct boolean defines
error labels; fractional partial-credit scores do not become probabilistic
correctness targets. Each model has its own error labels on matching cases.

## Comparisons and denominators

The four measures are sequence NLL, mean-token NLL, maximum token surprisal and
frozen meaningful-token mean NLL. Numerical ranking and risk-coverage formulas
are preserved from the previous analysis and protected by source fingerprints.
Each model gets available-case and all-measure common-cohort analysis separately
by benchmark and by reference/relevance panel.

The package reports all three model pairs. Each pair has its own explicit
first/second model orientation, same-measure eligible intersection, all-measure
intersection and descriptive correctness-transition counts. It also reports
three-model shared cohorts: for each measure, the intersection eligible for
that measure in every model; and one fixed intersection eligible for every
measure in every model. Comparisons of measures should use the latter fixed
cohort. Exact case lists, group counts, model-specific error counts and eligible
versus original-panel coverage denominators remain available in JSON.

Three-model correctness patterns retain all cases and encode C (correct) or
I (incorrect) in an explicitly reported model order. They do not evaluate an
oracle router, imply that uncertainty can select the better answer, or establish
that a fallback will rescue failures. Pairwise and three-way cohort results are
different analyses and must not have their denominators silently interchanged.

The prepared requests must match Qwen 1.5B case order, identities, messages and
all non-model explicit request fields. Different model checkpoints can still
use different tokenizer rendering, stop-token defaults and inherited sampling
settings. The original runtime records disclose those differences. Identical
explicit requests do not create a controlled causal comparison of model size,
and timings do not establish GPU active time or complete monetary cost.

## Metric rules

Higher uncertainty predicts reference noncompliance or separate ToolEyes
irrelevance. AUROC gives half credit to exact ties and is undefined for an
empty or one-class cohort. AP is noninterpolated descending score-block average
precision, not trapezoidal PR area. No positive errors means undefined AP;
all-positive nonempty outcomes yield AP one but undefined AUROC. A model with
6/6 ToolEyes relevance therefore has no measurable error-discrimination AUROC
on those outcomes. The label balance may change after shared-case filtering.

Risk-coverage accepts ascending uncertainty by whole exact-score tie blocks,
without score jitter, rounding, arbitrary tie splitting or selected deployment
threshold. Zero-acceptance risk is undefined. The scalar area is explicitly
named tie-block right-step area over eligible coverage; original-panel coverage
is retained alongside it. No score is mapped to calibrated correctness
probability. Error prevalence is descriptive and not asserted to equal exact
finite-sample random AP expectation.

## Output, tests and limitations

A fresh ignored output folder contains REPORT.md, summary.json, three per-model
analysis JSON files, matched_comparison.json, provenance.json and both newly
recomputed scoring directories. Existing output directories are refused.
The one-command installer imports seven new source/documentation files, runs
synthetic tests, and executes the full verified CPU subtask only after tests pass.
It performs no Git staging, commits, pushes or branch changes. Repeated execution
never overwrites a result; preserve any existing folder rather than deleting it.

The CPU tests cover independent exhaustive small-data ROC/AP oracles, ties,
empty/one-class outcomes, original coverage denominators, shared intersections,
model-specific outcomes, explicit pair orientation, immutable input flags and
identities, truncation, request mismatch, hash rejection, output preservation,
failed scoring, mismatched recomputation and a complete synthetic 69-case
three-model workflow. They do not certify real model outcomes. The local run's
revalidation and reports provide that bounded evidence.

Nonrandom eligibility, benchmark scales, outcome prevalence, shared canonical
groups, small strata and retrospective development inspection limit all results.
No confidence intervals, significance tests, overall model-superiority claims,
causal perturbation comparisons or routing benefits follow from this package.
Calibration, group-aware intervals, validated Observation/Action/Reward
comparisons, broader static populations, failure-catalogue scope, final figures
and the final shared protocol freeze remain outstanding. Task 3 is not complete;
held-out evaluation remains disabled until the separately approved final freeze.
