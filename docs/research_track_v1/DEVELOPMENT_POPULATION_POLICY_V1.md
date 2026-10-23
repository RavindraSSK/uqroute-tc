# Development construction eligibility and denominator proposal

Policy: `uqroute-development-population-policy-1.0.0`.
Status: development analysis proposal; not a final evaluation freeze.
Baseline: `d8f70b64f0c2cc3e4757fe0c4ffd2387f8200bd8`.

## Source coverage and construction

Every exported primary-development row remains in the source inventory. The
coverage denominator is 1,754 rows across 140 groups. Construction candidates
number 1,728; 26 blocks remain visible, without a generated correctness label.
The candidate fraction describes construction only. It is not accuracy,
scorer approval, successful tool execution, or authorization for inference.

The sidecar reads the preserved original audit's summary.json and inventory.json
only, approved by explicit SHA256 arguments. Inventory may already contain
reference diagnostics; the planner uses identities, construction/audit status,
review flags and objective booleans. It copies no prompts, argument values,
reference calls or model responses into its outputs. It does not open raw
benchmark files, the split, original samples/references, or candidate prompts.
Git operations verify only baseline ancestry and source-document blob IDs.

Summary/input reconciliation is structural, not independent reconstruction of
the original export. Hashes prove byte consistency with approved local inputs,
not cryptographically authenticated partition membership. Membership trust
continues to rest on the reviewed development-only export/audit boundary. A
mislabeled fabricated audit cannot be authenticated by local hashing.

## Separate panels and overlapping objectives

| Panel | Source rows | Candidates | Blocks |
|---|---:|---:|---:|
| Released-reference compliance: APIBank/BFCL/RoTBench/ToolAlpaca | 1,538 | 1,512 | 26 |
| ToolEyes tool-name relevance | 216 | 216 | 0 |
| Reward preference overlap | 498 | 486 | 12 |

Reward rows remain in the reference panel and also receive separate objective
reporting. They must not be added to the other panel totals or presented as
measured deployment cost savings. Reference-compliance matches, relevance
matches and preference interpretation answer different questions.

Flags never alter official labels, select a new schema, or automatically
exclude a case. An audit without flags is not semantic clearance. A completed
bounded audit provides detected/not-detected cost and latency booleans; a
construction block or unresolved audit gives unassessed (null), not false.
The original reward audit assessed 486 rows: 61 cost detections, 61 latency
detections and 364 without a detected explicit objective. The 12 construction
blocks remain unassessed. Non-detection is not proof of absent intent.

## Pairing

A primary group needs exactly one clean anchor. All 1,614 perturbed rows retain
that join, including blocked members. The 1,588 pairs with both prompts
constructed are construction pairs only. Future paired model comparisons need
explicit generation/correctness joins and their own per-model denominators.
The sidecar does not discard blocks or require model correctness to create a
pair. Related variants share a canonical group and are dependent observations.

## Future performance denominators

Model-run attempts, returned outputs, scored outputs, complete valid token
evidence, whole-output uncertainty eligibility and meaningful-token eligibility
must be counted separately after inference. AUROC, AP, calibration and
risk–coverage denominators are not inferred from 1,728 candidates. Task 2
format exclusions remain frozen; ToolAlpaca meaningful-token scores remain
unavailable. Construction blocks have no model outcome and are not assigned
artificial official failures. Any later end-to-end coverage metric must be
explicitly named and distinguished from released-reference accuracy.

No missing-outcome imputation, invalid-output acceptance rule, threshold,
confidence mapping, tie handling, weighting or bootstrap choice is frozen by
this proposal. Those are subsequent analysis decisions. Sensitivity-only
development data remain separate and are not read by this primary-only tool.
Held-out source coverage/counts are not inspected or projected from this audit.

## Outputs and change control

The tool creates a fresh locally ignored output directory containing:

- denominators.json: aggregate reconciled construction panels, flags, reward
  assessment and pair counts, readiness false and provenance hashes.
- case_index.json: development identities and bounded status/boolean metadata;
  local evidence only, with no raw reference values or prompts.
- construction_pairs.json: development clean/perturbed identifiers and
  construction status; local evidence only.

Existing export/audit directories and their hashes are unchanged. The sidecar
does not import the changed repair module or rerun the fingerprinted auditor.
No attestation hash replacement is required. The policy content is pinned by
the planner, so amendments require versioned code/configuration review.
The source manifest verifies the documented baseline rather than reading data.

Local owner execution is still required to verify the preserved real audit.
Supplied tests use synthetic records, including a full-count filesystem run
with mocked Git identities; they establish engineering behavior, not a new
real full-population audit or model-performance result.
