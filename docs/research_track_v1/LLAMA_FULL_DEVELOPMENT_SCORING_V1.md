# Llama 3B full-development CPU scoring v1

Baseline: `87674b233e55b020a9208dea3ea61e7f2eb48417`.
This adapter evaluates the saved corrected Llama 3B full-development run.
It does not change or pool the earlier five-case and 69-case experiments.

## Bound inputs

The reviewed archive SHA256 is
`f111f4e3c20bad403c47876abaf93e453568a61900c6792da7196f6b37a5b7b1`.
Its prepared manifest SHA256 is
`c150b291712314af67607cd801d74ea7e6cd77ccb3b13c0f7c34d3e8764bef0a`.
The scoring policy pins all 6,941 imported files, including the export inventory
of 6,940 evidence hashes. The existing generation adapter validates the plan,
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

All 1,728 saved responses remain in official scoring. The run has 1,717 complete
and 11 truncated responses. Token-evidence invalidity
and truncation do not automatically set correctness false. The pinned parser
reparses original raw output and preserves Python value types, including tuples.
The released deterministic scorer receives those parsed calls and unchanged
reference labels. Saved JSON views of parsed calls are never scoring inputs.
No truncated output, placeholder, spelling or format is repaired.

Whole-output uncertainty remains available for 1,717 cases and meaningful-token
uncertainty for 489 under the frozen eligibility rules. Invalid-evidence and
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

Run unittest discovery in tools/development_audits/llama_full_development_scoring_v1.
Then run score_llama_full.py with --repo-root, --evidence-dir, --bundle, --audit-dir
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

The Qwen full-development adapter, policies and outputs remain unchanged.
This separate Llama policy binds its own model and archive. Cross-model
uncertainty and paired policy comparisons are not performed by this scorer.
