# Task 3 requirements and evidence review

Baseline: `d8f70b64f0c2cc3e4757fe0c4ffd2387f8200bd8`.
Authority: `docs/PROJECT_TASKS.md`, Task 3, with the operational checklist in
`docs/PROGRESS.md` and interpretation boundaries in `docs/PROTOCOL.md`.
This review reads source documentation only, not benchmark or split records.

## Requirement-to-evidence map

| Requirement | Evidence at baseline | Remaining work | Disposition |
|---|---|---|---|
| Selected small models on clean/static perturbed cases | Four-model 69-case throughput diagnostics and earlier small pilots; corrected research adapter/audit exist | Corrected generation/evidence feasibility and broader frozen static run records | Partial; diagnostics do not establish full results |
| Observation, Action and Reward comparisons | Development inventory covers released source files; reward objectives have bounded audit signals | Validate taxonomy from released metadata for analysis; predeclare panel-specific category comparisons | Pending model-result analysis |
| Correctness measurement | Official scoring is pinned; near reproduction and scoped diagnostics recorded | Broader corrected-run released-reference compliance; ToolEyes relevance separate; no execution-success claim | Partial |
| Single-sample uncertainty comparisons | Task 2 formulas and eligibility frozen | Join each corrected prediction to immutable correctness and evidence eligibility; quantify missingness | Pending effectiveness evidence |
| AUROC and AUPRC | Proposed in main-experiment plan | Implement/test tied scores, one-class outcomes, error-positive direction, eligible denominators and AP baseline | Pending |
| Calibration | Still a proposal | Freeze development-only confidence mapping, validation procedure, bins and unavailable handling; then implement | Pending |
| Risk–coverage | Still a proposal | Freeze acceptance direction, tied-score handling, coverage denominators and reference-error interpretation | Pending |
| High-confidence failure catalogue | Earlier descriptive truncation/token diagnostics | Predeclare confidence bands and catalogue from scored static outputs; reference flags kept separate | Pending |
| Development-only method selection | Frozen grouped split and development-only export/audit | Final selection procedure and immutable decision artifact before held-out access | Infrastructure complete; final selection pending |
| Held-out final static evaluation | No new held-out evaluation evidenced | Final protocol freeze first; authorized separate runner/evaluation later | Blocked |
| Group-aware confidence intervals | Group-bootstrap principle recorded | Freeze/test bootstrap settings, pairing, weighting and small-stratum rules | Pending |
| Frozen static-results dataset, uncertainty plots and failure catalogue | Preparation/audit artifacts exist | Immutable generation/results manifests and reproducible final figures/catalogue | Pending; Task 3 not complete |

## Preparation actually completed

The original full primary-development audit retained 1,754 rows / 140 groups:
1,728 construction candidates and 26 retained APIBank blocks. All 140 clean
rows were constructed; 1,614 perturbed rows have a unique clean anchor and
1,588 pairs have both prompts constructed. These are construction denominators,
not model correctness or uncertainty eligibility. The follow-up diagnostic
classified the same 26 blocks as 12 missing declarations and 14 conflicting
schemas, without new candidates. Original audit outputs retain original code
fingerprints and must not be rewritten after the diagnostic change.

Reference compliance inventory has 1,538 rows (1,512 candidates); ToolEyes has
216 separately reported relevance candidates. The 498-row reward inventory
overlaps the reference panel, with 486 assessed construction candidates and
12 blocks. Review signals on 802 rows are not 802 confirmed errors. Detailed
aggregate provenance remains in DEVELOPMENT_AUDIT_FINDINGS_V1.md.

The owner supplied a 67-test run with one Windows skip and the 26-case replay.
The latest rerun output for the older 12/24/17 suites was not supplied in this
review session; their rerun must not be inferred from successful Git push.

## Scope correction

The uncertainty gate, fallback escalation, routing baselines, threshold
operating objective, post-fault recovery and full policy cost accounting are
Task 4 requirements. They are not completion evidence for Task 3. Shared
population, uncertainty, statistics and evaluation-freeze choices must be
compatible across both tasks before final held-out evaluation.

The current scope still lists three small models and the fallback. No model,
repeated-sampling, sensitivity-population or recovery requirement is silently
removed. Timing pressure is not a scope amendment. Task 4 may begin with
implementation after Task 3 inputs/decisions are ready, but no Task 4 result or
completion is asserted by this package.

## Next implementation and subsequent sequence

1. Validate construction denominators and pairing from the preserved original
   development audit using the separate population-policy sidecar.
2. Review the population proposal and resolve reference/objective disposition
   and the distinction between source coverage and future metric denominators.
3. Implement the corrected generation/evidence adapter and resumable development
   run manifest; verify all selected model roles on development inputs.
4. Measure available quota and representative runtime on corrected prompts;
   schedule broader development generation from measured capacity.
5. Implement and test CPU static metrics, calibration, risk–coverage,
   group-aware intervals and failure catalogue using saved development results.
6. Review and freeze final shared analysis and evaluation decisions. Keep
   held-out access disabled until that separate artifact is approved.
7. Run final static evaluation and reproduce results/figures before closing
   Task 3. Implement and evaluate the separate Task 4 routing/recovery workflow.

The existing 13-decision main plan remains a historical proposal. This review
and sidecar do not flip readiness flags or claim a final protocol freeze.
