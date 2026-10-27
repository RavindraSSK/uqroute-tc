# Qwen 7B full-development CPU scoring v1

Baseline: `eeed986a37d9029c0f46642220d9da2fe493a086`.
This adapter evaluates the saved corrected Qwen 7B full-development run.
It does not change or pool the earlier five-case and 69-case experiments.

## Bound inputs

The reviewed archive SHA256 is
`4de2c2170af330f60e03d407fff6b05f305a0be83b031e795797f09f301e2a2e`.
Its prepared manifest SHA256 is
`4547ebed5cef4224b5966e393febb590281d875533297d47f4c7e8742b1a389c`.
The scoring policy pins all 6,940 imported files, including the export inventory
of 6,939 evidence hashes. The existing generation adapter validates the plan,
source fingerprints, model revision and generation settings. Each original
HTTP response is reevaluated and compared with its saved validation result.

The approved development attestation is checked before opening its reference
sidecar. Membership, inventory hashes, canonical groups and each reference
identity are validated. Local hashes establish consistency, not authenticated
partition provenance; the reviewed exporter remains part of the trust boundary.
No raw benchmark, split records or development samples sidecar is opened.

## Coverage and scoring rules

The inventory contains 1,754 rows across 140 primary development groups.
All 1,728 construction candidates are required exactly once. The 26 blocked
cases stay blocked, receive no generated response, and are not assigned a zero
score. Coverage reporting retains their identities and original reasons.

The candidate set has 140 clean rows and 1,588 perturbed rows with unique
constructed clean anchors. This verifies construction pairing, not a paired
robustness analysis. Correctness denominators are 1,512 reference-compliance
cases and 216 separately reported ToolEyes relevance cases. Inventory coverage
is reported separately: the reference inventory has 1,538 rows, including
26 blocks; ToolEyes has 216 constructed rows.

All 1,728 saved responses remain in official scoring. The run has 1,727 complete
and one truncated response. Token-evidence invalidity
and truncation do not automatically set correctness false. The pinned parser
reparses original raw output and preserves Python value types, including tuples.
The released deterministic scorer receives those parsed calls and unchanged
reference labels. Saved JSON views of parsed calls are never scoring inputs.
No truncated output, placeholder, spelling or format is repaired.

Whole-output uncertainty remains available for 1,727 cases and meaningful-token
uncertainty for 636 under the frozen eligibility rules. Invalid-evidence and
truncated responses have unavailable probability scores. The new diagnostic
category `invalid_token_evidence` only explains this status; it does not alter
the frozen validator, official outcome or earlier output artifacts.

Reference-review flags are retained without exclusions. Their presence is not
a confirmed reference error and their absence is not semantic clearance.
Reward/objective diagnostics overlap the reference panel. Regex nondetection
is not proof of absent intent; compliance is not measured preference success.
ToolEyes is deterministic name-only relevance, not executable argument accuracy.
Originally recorded gpt_judge methods retain the released deterministic dispatch;
no LLM judge or network call is introduced.

## Outputs and local verification

Run unittest discovery in tools/development_audits/qwen7b_full_development_scoring_v1.
Then run score_qwen7b_full.py with --repo-root, --evidence-dir, --bundle, --audit-dir
and a fresh --output under artifacts/local_development_audits. The one-command
installer runs the tests and supplies the reviewed local paths automatically.
It does not stage, commit, push, generate responses or retry model requests.

Outputs are scores.json, summary.json, provenance.json and
alignment_diagnostics.json. Summary construction_coverage retains all source
and blocked denominators. Per-benchmark, source-file, reference-flag, objective
and eligibility summaries remain separate. Existing outputs are refused.
Completed files are published together; only temporary publication permission
errors receive a bounded retry, never inference or scoring-semantic retries.

This subtask supplies scoring only. Full-development uncertainty effectiveness,
category comparisons, paired statistics, calibration, failure catalogue and
remaining model experiments are subsequent work. Official reference compliance
is not semantic correctness or tool execution success. No held-out access,
routing threshold or final protocol freeze is enabled.

The existing Qwen 1.5B and Llama adapters, policies and outputs remain unchanged.
This separate Qwen 7B policy binds its own model and archive. Three-model
uncertainty analysis and comparisons are subsequent work.
