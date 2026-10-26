# Development category analysis v1

Baseline: `38cb695`. The owner inspected released perturbation metadata in
an existing primary-development export after reviewing the model results.
The exact samples SHA256 is
`23ac76ad69bf42e04ab6c2a0f9c274e6885c6c1c388aee8aa126f99341b2d533`.
The selected 69 cases contain five clean, 20 Observation, 24 Action and 20
Reward records. These are selection counts, not population weights.

## Metadata authority and validation

Classification uses sample.perturbation.mdp_category and type from the
hash-checked development export. The reviewed source/type combinations and
counts are validated together; categories are not guessed from source names.
The clean file must have explicit null-like category/type fields. Actual JSON
null and literal "None" are distinguished in saved released metadata, while
both are accepted only for clean rows. Missing fields fail closed.

Selected cases must match the pinned prepared request identities and lineage,
and must be primary development rows. Unknown sources, category/type conflicts,
duplicate selected keys, missing cases and changed hashes stop the run. The
full development samples sidecar is read, but only the selected 69 taxonomy
records are saved. It contains no held-out samples. No raw benchmark or split
record is opened. References are used only through the existing, separately
preserved evidence-bound development scoring revalidation.

## Analysis outputs

Recompute the established three-model evidence verification in a new folder.
Join taxonomy to existing outcomes without modifying any official score,
reference flag or eligibility status. Report four category scopes plus 17
exploratory source-file scopes. Each includes separate reference-compliance
and ToolEyes relevance panels, per-benchmark results, available-case metrics
and all-measure-common metrics. Use the unchanged AUROC, score-block AP and
risk-coverage implementation. Empty and one-class metrics remain undefined.

Same-case pairwise and three-model intersections are supplied per scope in
matched_comparison.json. These preserve model-specific outcome labels and
separate availability from correctness. These matches compare models and
measures on identical cases; they do not pair clean and perturbed variants.
The clean subset has just five cases. Differences in benchmark, group and
reference composition confound category-level comparisons. No causal drop,
category-superiority test or population-weighted estimate is asserted.

Reward membership is released taxonomy, not proof of an explicit cost/latency
objective. Preference success, tool execution and measured tool cost/latency
are not assessed. Existing reference-review flags are retained without
exclusions or semantic relabeling. Construction blocks and unselected cases
are not silently added to model-result denominators.

## Execution and remaining scope

Run unittest discovery in tools/development_audits/development_categories_v1,
then run run_categories.py --repo-root . The default fresh output directory
is artifacts/local_development_audits/development_categories_v1. It contains
summary.json, taxonomy.json, category_results.json, matched_comparison.json,
provenance.json, REPORT.md and a fresh evidence_revalidation directory.
Existing outputs are refused; the installer makes no Git changes.

This is a retrospective diagnostic, not a final protocol freeze. Category
confidence intervals, broader development generation, representative clean
pairing, final failure-band rules and held-out evaluation remain separate.
Calibration is not refitted and no routing threshold or model is selected.
