# Three-model full-development analysis v1

Baseline: d734311. This retrospective development subtask analyzes the saved
Qwen 1.5B, Llama 3B and Qwen 7B full-development runs without changing prior
policies, scores, reference labels or outputs. No earlier 69-case response is
pooled into these 1728-response runs as a new independent case.

## Verification

Rerun each evidence-bound scorer into a fresh directory and compare its scores
and summary structurally with the existing approved outputs. The scorers pin
all raw response files, prepared manifests and saved validation records, check
the approved development export before opening references, and retain the
original 26 construction blocks separately without imputing scores. Raw
benchmark files, held-out records and split records are not analysis inputs.

Check all three request plans contain the same 1728 unique case identities,
order, canonical groups, source files, corrected messages and explicit sampling
settings, except for the requested model ID. This does not establish equal
rendered token sequences or inherited model sampling defaults. Input hashes
are rechecked before publishing results. Output directories must be new.

## Comparisons and denominators

Each model retains all constructed outcomes in correctness denominators and
its own probability eligibility. Report reference compliance and deterministic
ToolEyes name relevance separately. These are not executable task-success or
semantic-correctness labels. Existing reference flags do not exclude cases.

The unchanged metric engine reports AUROC with error-positive direction,
noninterpolated score-block AP, and exact-tie-block risk-coverage points.
Available-case results accompany within-model all-measure common cohorts.
Pairwise comparisons cover all three model pairs. The three-model joint
comparison reports shared eligibility separately for each measure and for
the all-measure intersection. Per-benchmark results accompany the pooled
reference panel. Different model outcomes and error prevalence remain visible;
raw uncertainty scales are not pooled across models.

Outcome patterns use an explicitly recorded alphabetical model order and
C/I correctness indicators over all original panel rows. They are descriptive
agreement patterns, not a tested oracle routing or fallback policy. Empty and
one-class metrics remain undefined. Nonrandom intersections do not repair
missingness or establish applicability to the excluded formats.

Each model also retains 1588 constructed clean/perturbed pairs, with both case
keys, reference flags, C/I outcomes and joint-eligible mean-NLL changes.
Pair-weighted and equal-group-weighted changes are separate. Reusing a clean
response across variants creates dependence; these are not independent trials.
Reference and schema changes limit causal interpretation of correctness changes.

## Outputs and scope

Outputs include summary.json, REPORT.md, matched_comparison.json,
paired_summaries.json, an analysis and pair-row file for each model,
provenance.json, and three scoring_recomputed directories. Numeric risk curves
remain in analysis JSON; this package adds no new plot renderer.

Run unittest discovery in tools/development_audits/three_model_full_development_v1,
then run_comparison.py --repo-root . The default fresh output is
artifacts/local_development_audits/three_model_full_development_v1. The installer
performs these actions without staging, committing or pushing.

This completes a development comparison subtask, not Task 3 as a whole.
Full-development bootstrap intervals, calibration, released-category analysis,
failure catalogue and final protocol review remain separate. No new model
requests, automatic retries, calibration fitting, routing threshold, significance
claim, held-out access or final protocol freeze is enabled.
