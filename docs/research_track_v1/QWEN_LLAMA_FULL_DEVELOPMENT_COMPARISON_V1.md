# Qwen and Llama full-development diagnostics v1

Baseline: 01e855a. This subtask combines Llama full-development uncertainty and
clean/perturbed analysis with two-model same-case comparisons. Qwen's existing
full-development analysis and both earlier 69-case runs remain unchanged.

Recompute both pinned scorers in fresh directories and compare scores and
summaries structurally with existing approved outputs. Check both 1728-request
plans have identical case order, prompt lineage and explicit request settings
except model ID. Source fingerprints and scorer evidence policies are locked.
Neither raw benchmark files nor split records are analysis inputs. Approved
development references are read only through the evidence-bound scorers.

Each model retains its own official labels, probability eligibility and
reference flags. Report available-case results and all-measure-common cohorts
within each model. Pairwise results include per-measure shared eligible cases
and the intersection across both models and all measures. Report per-benchmark
comparisons alongside the separate reference and ToolEyes relevance panels.
Model labels can differ on identical cases, and AP depends on error prevalence.
Raw uncertainty scales are not pooled or normalized between models.

Clean/perturbed pair records and summaries retain all 1588 constructed pairs
per model. Correctness transitions, pair-weighted mean changes and equal-group
mean changes remain descriptive; repeated use of a clean response creates
dependence. NLL differences use jointly eligible evidence only. Different
references, schemas and objectives limit causal interpretation. The 26 original
construction blocks are covered by each recomputed scoring summary but have
no model outcomes and receive no imputed pair or score.

Outputs include summary.json, REPORT.md, matched_comparison.json,
paired_summaries.json, one analysis and pair-row file per model, provenance.json
and both fresh scoring directories. Existing outputs are refused. All earlier
evidence and labels remain unchanged. No new inference, model retry, calibration
fit, bootstrap, routing threshold or held-out access occurs. Qwen 7B's broader
run and final evaluation freeze remain pending.

Run the new folder's unittest suite, then run_comparison.py --repo-root .
The default new artifact directory is qwen_llama_full_development_comparison_v1
under artifacts/local_development_audits. The installer performs these actions
without staging, committing or pushing. Metric numerical definitions are reused
from the tested versioned uncertainty engine without modification.
