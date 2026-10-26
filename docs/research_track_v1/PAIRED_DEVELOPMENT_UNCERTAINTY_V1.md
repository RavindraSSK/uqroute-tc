# Qwen and Llama development uncertainty comparison v1

## Scope

This CPU-only analysis uses the corrected 69-case development coverage runs.
It preserves all existing scores, labels, evidence, policy files and the
original Qwen analysis. No held-out input, raw benchmark or split record is
opened. No model request, network call, calibration fit, threshold selection,
bootstrap, routing simulation or tool execution occurs.
The baseline is the committed Llama scoring implementation at 6a09541.

The Qwen scores, original scoring provenance and prepared requests/manifest
are pinned to the previously reviewed SHA256 identities. The Llama scoring
implementation and policy are pinned separately. Before analysis, the full
Llama evidence-bound scorer is rerun into a new temporary output directory,
validating all approved archive and development sidecar/source fingerprints.
The recomputed scores and summary must match the existing local Llama scores
and summary structurally. The fresh scoring provenance is retained as a new
artifact; the old provenance is not rewritten. The approved development
reference sidecar is read by scoring, not by the ranking computations.
Hashes establish consistency, not authenticated provenance or proof that
partition filtering is cryptographically correct.

## Measures and cohorts

Measures are sequence NLL, mean-token NLL, maximum token surprisal and frozen
meaningful-token mean NLL. Higher values predict official noncompliance or,
in the separate ToolEyes panel, deterministic name-only irrelevance.
The numerical metric implementation is copied unchanged from the existing
versioned development analysis and is protected by a source hash.
Official correct booleans, not fractional partial-credit scores, define labels.

Both models retain all 69 rows for correctness. The Llama truncation stays in
that denominator and receives its saved raw-output score; no automatic zero,
repair, retry or substitution is applied. Probability evidence remains
unavailable on truncation. Missing measures are never imputed.

Reports include per-model available-case metrics, within-model all-measure
common cohorts, and two kinds of cross-model comparison:

1. For each measure, the intersection of eligible case identities in both models.
2. The intersection eligible for every measure in both models, reused across
   all measures for a same-case measure comparison.

Original and eligible denominators and exact case lists remain explicit.
Correctness transitions report correct-to-correct, correct-to-incorrect,
incorrect-to-correct and incorrect-to-incorrect on shared identities without
excluding unavailable cases. These are model-to-model outcome comparisons,
not clean/perturbed causal pairs. Per-benchmark outputs are provided alongside
reference and separate ToolEyes panels. Raw uncertainty values are never pooled
across models or treated as calibrated probabilities.

The same 69 request identities, order, messages and non-model request fields
must match. Identical request bodies do not imply identical tokenizer rendering,
model weights, inherited top-p, stop-token settings or runtime behavior. Those
runtime differences remain documented in the original run metadata. They limit
causal claims about model differences or speed.

## Metric definitions

AUROC gives half credit for exactly tied error/compliant pairs. It is undefined
for empty or one-class outcomes. AP is noninterpolated descending score-block
average precision, not trapezoidal PR area. With no positive errors AP is
undefined; with all outcomes positive AP is one but AUROC remains undefined.
Llama ToolEyes has no error positives, so no perfect failure-detection claim
can be made from its 6/6 relevance result.

Risk-coverage accepts ascending uncertainty by entire exact-score blocks with
no jitter, rounding or tie splitting. Zero-acceptance risk is undefined.
The area is the explicitly named tie-block right-step area over eligible
coverage. Coverage relative to the original panel is also recorded; missingness
cannot silently yield full original-panel coverage. No operating threshold is
selected. Error prevalence is descriptive, not an asserted finite-sample random
AP expectation.

## Outputs and verification

A fresh ignored output directory contains summary.json, REPORT.md,
qwen_analysis.json, llama_analysis.json, matched_comparison.json, provenance.json
and the newly recomputed Llama scoring artifacts. Existing output directories
are refused. The new workflow never commits, pushes, changes branches or
modifies existing project files. The installer checks ancestry, imports only
new source/documentation files, runs synthetic CPU tests and runs this analysis
only after those tests pass. A failure stops the workflow; do not overwrite
existing evidence or bypass fingerprints.

Synthetic tests cover tied ranking, independent exhaustive small-data oracles,
empty and one-class behavior, unavailable/truncated evidence, matching case
intersections, model-specific outcome transitions, identity/flag conflicts,
request equality, output preservation, input hash rejection and a complete
synthetic 69-case pipeline. They do not certify real model results.

This retrospective selected sample is not a population estimate. Nonrandom
eligibility, benchmark score scales and outcome rates, shared canonical groups
and small strata limit interpretation. No significance or model-superiority
claim follows from these comparisons. Calibration, group-aware uncertainty,
broader model runs, final failure-catalogue decisions and final protocol freeze
remain outstanding. Task 3 is not complete, and held-out access remains disabled.

## Whitespace maintenance

Trailing blank lines were removed before publication, and the source
and policy fingerprints were updated. Metric logic is unchanged.
Previously generated analysis outputs retain their original provenance
and were not rewritten by this maintenance change.
