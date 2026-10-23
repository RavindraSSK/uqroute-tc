# Primary-development audit findings

## Evidence and scope

The owner ran pipeline `uqroute-development-pipeline-1.0.0` locally from the
implementation based on project commit `05a95bf`. The reviewed aggregate output
records benchmark revision `d5d03180de41eb30a6c796d04a9bfbd9dad85c1d`, split
SHA256 `688c1013d8fe9d5c1b454d14d4cbe215659e48adc7bdfd63175580e83e2eb0db`,
and export attestation SHA256
`77071dc342a19b0f32995fed9f9f9e25840294e633ef5368830f07a3ccf3ccb9`.
These identify the original run, not a run of the diagnostic revision.

The summary reports all 1,754 primary-development rows retained across 140
canonical groups, zero held-out bundle rows accepted, and zero raw benchmark
files opened by the auditor. The trusted exporter read mixed source bytes to
filter membership before decoding selected nested development payloads.
Official labels, references, and ambiguity exclusions were unchanged.

## Construction and pairing

| Measure | Count |
|---|---:|
| Constructed candidates | 1,728 |
| Retained construction blocks | 26 |
| Clean rows constructed | 140 |
| Perturbed rows with a unique clean anchor | 1,614 |
| Pairs with both prompts constructed | 1,588 |
| Reference audits completed with bounded signals | 1,728 |
| Reference audits unassessed because construction was blocked | 26 |

All construction blocks are APIBank cases. Review of the owner's 26-case
input-only development extract distinguishes 12 reward cases with no matching
schema declaration from 14 cases with conflicting schemas (13 same_name_B,
one same_name_D). The reward cases contain a mismatch between structured tools
and the system's declarations. The duplicate-name cases contain differing
schemas under indistinguishable names/descriptions and empty structured
property maps. Empty property maps can also represent explicit zero-argument
schemas; they cannot universally be treated as missing.

The diagnostic revision changes only exception text for zero versus multiple
distinct candidate schemas. It does not change matching, repair, tool ordering,
prompt construction, exclusions, or scoring. All 26 reviewed cases remain
blocked; no positional schema assignment or reference-derived repair is made.

## Separate evaluation interpretations

| Panel | Inventory rows | Candidates | Blocks |
|---|---:|---:|---:|
| Official-reference compliance inventory | 1,538 | 1,512 | 26 |
| Separate ToolEyes name-relevance inventory | 216 | 216 | 0 |
| Overlapping reward inventory | 498 | 486 | 12 |

These are inventories, not compliance, relevance, or preference scores.
ToolEyes has zero detected reference-review signals under these rules; that
is not a semantic correctness certificate. Reward rows overlap the other
panels and must not be added to their denominators.

The 486 assessed reward rows include 61 with a detected cost objective, 61
with a detected latency objective, and 364 without a detected explicit
objective. The 12 blocked reward rows were not assessed. Objective detection
is bounded textual analysis, not proof of user intent or its absence.

Across the full inventory, 802 cases have one or more review signals:
402 multiple-schema-name signals, 49 year-not-literal signals, 16 explicit
time-range mismatch signals, 182 cost-preference/objective signals, 182
latency-preference/objective signals, and 364 reward-objective non-detections.
Counts overlap and are not distinct confirmed errors. No flags automatically
change labels, score eligibility, or denominators. Repeated perturbations
within a group are not independent observations.

## Remaining decisions and provenance

Main readiness remains `DEVELOPMENT_AUDIT_ONLY_MAIN_EXPERIMENT_NOT_READY`.
The development export and audit have measured output, but final protocol
freeze is pending. Decisions remain on construction-block treatment,
reference/objective interpretation, analysis populations and pairing,
generation evidence, gate measure and missing-signal acceptance, threshold
objective, baselines, statistics/calibration, compute feasibility, and repeated
recovery scope. Existing main-plan decision flags are not changed here.

Original export and audit directories remain immutable local evidence. The
original summary records the original implementation hashes. Changing
`repair.py` changes its fingerprint; the revised auditor must not accept the
old bundle by editing attestations, replacing hashes, or disabling validation.
The separate blocked-input replay verifies diagnostic classification without
rewriting the original run or reading its reference sidecar. A future complete
run with revised code requires a fresh export and audit directory and a new
attestation, with comparison to the retained original evidence.

No inference, model-performance estimate, routing result, official score
change, or held-out evaluation is established by this audit.
