# Task 3 development readiness v3

Status recorded 2026-11-05, following the owner-published preparation commit
`0bf4fe6a8069397525f42af3bf5579b977fdd05f` and the subsequent saved-output analyses.
This supersedes the current-status portions of readiness v2; historical
artifacts retain their original scope. Task 3 is **not complete**. No final
protocol freeze or new held-out evaluation is asserted.

## Completed development evidence

| Workstream | Completed evidence | Boundary |
|---|---|---|
| Primary static generation and scoring | Three small models, 1,728 responses each; 5,184 total. Original inventory: 1,754 rows / 140 groups, including 26 retained construction blocks | Construction blocks are not imputed scores; reference matching is not executable success |
| Matched uncertainty and pairs | AUROC, noninterpolated AP, risk–coverage, shared eligible cohorts, 1,588 clean/perturbed pairs per model | Original denominators, missing evidence and benchmark strata retained |
| Statistical reporting | 35 bootstrap analyses / SVGs, 2,000 group-bootstrap draws; 21 calibration scopes; released category summaries; paired-change intervals | Development diagnostics; final analysis decisions remain open |
| Failure reporting | 489 catalogue entries / 460 unique model-cases; two documented cross-model illustrative reviews | Overlapping retrospective bands; no exhaustive semantic adjudication |
| Corrected repeated sampling | Three models × 30 cases × 10 sample slots = 900 slots; 15 groups and 15 clean/perturbed pairs per model | A corrected selected development subset, not a replication of the historical Task 2 sample selection |
| Sensitivity extension | Three models × 35 BFCL same-name rows = 105 responses; 34 additional development groups; all complete | Separate population, no clean anchors, no paired change estimate |

The primary response-status totals remain Qwen 1.5B: 1,715 complete, ten invalid
evidence and three truncated; Llama 3B: 1,717 complete and 11 truncated;
Qwen 7B: 1,727 complete and one truncated. Official outcomes remain independent
of token-evidence eligibility. Existing incomplete outcomes are preserved.

## Primary development results

| Model | Reference compliance, 1,512 rows | ToolEyes relevance, 216 rows | Reference whole-output eligible | Reference meaningful-token eligible |
|---|---:|---:|---:|---:|
| Qwen 1.5B | 572 / 1,512 | 174 / 216 | 1,501 | 699 |
| Llama 3B | 621 / 1,512 | 181 / 216 | 1,502 | 292 |
| Qwen 7B | 790 / 1,512 | 204 / 216 | 1,511 | 420 |

The three-model shared whole-output reference cohort has 1,490 rows; the
all-model/all-measure intersection has 243. Larger available-case values for
meaningful-token measures cannot establish superiority over whole-output
measures on different cohorts. See [full-development reporting](FULL_DEVELOPMENT_REPORTING_V1.md)
and [readiness v2](TASK3_DEVELOPMENT_READINESS_V2.md) for the diagnostic
calibration, confidence intervals and weighting rules.

## Corrected repeated-sample findings

Ten samples use temperature 0.7, top-p 1.0 and seeds 1729–1738. They rank errors
in each model's separately generated matched single response; individual
sample slots are not independent case observations. Canonical and exact-string
clusters are distinct measures. All 24 reference cases have shared whole-output
single-response eligibility across models.

| Model | Matched single reference matches | Repeated slot reference matches | Single mean-NLL AUROC | Canonical entropy AUROC | Canonical disagreement AUROC |
|---|---:|---:|---:|---:|---:|
| Qwen 1.5B | 6 / 24 | 60 / 240 | 0.7963 | 0.7685 | 0.7685 |
| Llama 3B | 8 / 24 | 53 / 240 | 0.6484 | 0.5898 | 0.6172 |
| Qwen 7B | 9 / 24 | 99 / 240 | 0.7481 | 0.9185 | 0.9074 |

Repeated evidence is complete for Qwen 1.5B and Qwen 7B (300 slots each).
Llama has 298 complete slots, one invalid-evidence slot and one truncation;
all 300 slots remain in the recorded status-aware analysis. Qwen 1.5B and
Llama each have one canonically unanimous reference case where all ten samples
mismatch the reference. Agreement therefore does not guarantee compliance.

ToolEyes remains a separate six-case panel. Llama's matched single outcomes
are all mismatches and Qwen 7B's all matches; their AUROC is undefined.
Qwen 1.5B has one match and canonical-entropy/mean-NLL AUROC 1.0 on this tiny
panel. These observations do not establish reliability guarantees.

Whole-output mean NLL remains a practical development candidate because it
requires one response and has broad coverage. Qwen 7B canonical entropy is
a candidate for further comparison, conditional on its ten-call cost and
small selected cohort. This is a development recommendation, **not a frozen
method selection**, routing threshold or statistical superiority claim.

## Sensitivity findings

The extension contains only BFCL same-name A–E cases: 11, 2, 8, 7 and 7 rows,
respectively. There are no clean anchors. Qwen 1.5B and Qwen 7B each match
10/35 references; Llama matches 7/35. All 35 rows retain the structural flag
`reference_name_has_multiple_schema_occurrences`. Flags do not adjudicate errors
or change official labels. Whole-output eligibility is 35 for every model;
meaningful-token eligibility is 23, 25 and 25, with a 23-case shared intersection.
The [sensitivity report](SENSITIVITY_DEVELOPMENT_RESULTS_V1.md) records the
separate matched metrics and generation-only timing. No calibration was
refitted and no routing threshold selected from these cases.

## Reproduction and evidence

The new CPU entry points and five Colab notebooks are documented in
[reproduction instructions](DEVELOPMENT_RESULTS_REPRODUCTION_V1.md).
[The evidence index](DEVELOPMENT_RESULTS_EVIDENCE_V1.json) records archive,
source and selected result fingerprints. Hashes attest local byte consistency,
not authenticated provenance. Large archives, references, prompts, responses
and credentials remain outside Git.

Full-primary generation/scoring/reporting and repeated analyses above were
verified from owner-supplied execution records and the preserved analysis
sources. Sensitivity archives, all three local replays and scoring were
additionally verified in the working checkout. This update does not claim a
fresh rerun of the historical 5,184 primary generations or 900 repeated slots.

## Remaining before Task 3 closure

1. Review final population and reference/objective dispositions, success proxies,
   retained blocks and missing-evidence denominators. Preserve the disclosure
   of clean results observed before splitting. Reward metadata is not measured
   preference success, and reference compliance is not tool execution.
2. Record final development-only method choices and any fitted mappings in an
   immutable decision artifact. Freeze calibration, weighting, interval,
   repeated-sampling applicability, failure-band and final figure rules. The
   2,000-draw diagnostic policies do not silently replace draft final settings.
3. Resolve shared Task 4 interface requirements: fallback, gate objectives,
   recovery and complete policy cost accounting. These are separate work;
   fallback feasibility does not establish routing benefit.
4. Approve the final shared evaluation protocol before enabling new held-out
   access. Then perform the authorized final static evaluation, preserve its
   frozen results, reproduce final plots/catalogue and review Task 3 against
   `docs/PROJECT_TASKS.md` before closing it.

Task 1 and Task 2 remain complete within their recorded scope. Task 4 routing
and recovery and Task 5 final packaging remain outstanding. No quantitative
overall completion percentage is inferred from counts of scripts or runs.
