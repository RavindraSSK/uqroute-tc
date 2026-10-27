# Qwen 1.5B full-development analysis v1

Baseline: f76cadc. This retrospective development analysis reruns the pinned
full-development scorer into a fresh directory, compares saved outcomes and
summary structurally, and preserves old outputs. It uses existing frozen
uncertainty metrics and exact-score tie-block risk curves without changing
scores, reference flags, parsers or probability eligibility.

All 1728 constructed cases remain in outcome denominators. Probability
analyses report available cases and all-measure-common cohorts separately,
by panel and benchmark. Reference compliance and ToolEyes deterministic
name relevance remain separate. No reference-flag exclusions apply. The 26
construction blocks retain their coverage in the recomputed scoring summary;
they receive no imputed outcome and no invented clean/perturbed pair.

The 140 clean responses anchor 1588 constructed perturbed responses. Pair
records retain both case keys, benchmark, group, source file, C/I outcomes,
reference flags and mean-NLL change on jointly eligible evidence. One clean
response can anchor many variants. Pair-weighted correctness change and
an equal-weight average of within-group mean changes are reported separately.
These are descriptive compliance differences, not independent trials or
causal perturbation effects. References, objectives and schemas can differ
between variants. Per-source comparisons must not obscure benchmark mixture.
No cross-benchmark uncertainty-scale normalization is introduced.

Outputs: analysis.json, paired_rows.json, paired_summary.json, provenance.json,
REPORT.md and scoring_recomputed. Risk curves are retained numerically in the
analysis JSON. No new calibration fit, confidence interval, bootstrap, routing
threshold, model generation or held-out access occurs. Earlier 69-case outputs
are not pooled with these responses. Task 3 completion is not asserted.

Run unittest discovery in the new source folder and then run_analysis.py
--repo-root . The default fresh output is artifacts/local_development_audits/
qwen15b_full_development_analysis_v1. The installer handles both actions.
It never stages, commits or pushes. Existing output directories are refused.
The approved development references are read through the existing evidence-bound
scorer only; raw benchmark files, split records and held-out examples are not
analysis inputs. Hashes establish byte consistency, not authentication.
