# Llama corrected development coverage scoring v1

## Scope

This additive CPU adapter binds to the 69-request Llama coverage evidence exported
from repository commit a88688c8a2e3dcb548103303f1dd70b7ac98ebaf. It does not
modify the Qwen coverage scorer, generation methods, prior scores or labels.
Held-out access and main-experiment readiness remain disabled. No network calls,
model requests or tool execution occur during scoring.

The reviewed archive SHA256 is
43e0868797e40fdc6c5c627b34dd501d4f6a7f85f68a2b90f80e853c8b68bac4.
The prepared manifest SHA256 is
5c1bea90df16b527257e6303f44806a3ca03c2279b3cc4d39b0480e9dae6521f.
The policy locks all 292 archive members, including its 291-file hash inventory.
The model is meta-llama/Llama-3.2-3B-Instruct, pinned in the prepared manifest.
The same 69 development case identities and messages were used for Qwen;
model tokenizer rendering and inherited sampling defaults can differ.

## Outcomes and eligibility

All 69 generated outputs remain in reference/relevance scoring denominators.
There are 68 complete responses and one truncated response. The saved raw text
is reparsed with the pinned official parser, preserving Python argument types.
No response is repaired, completed, retried or relabeled. A truncated response
is scored as generated: a complete parseable matching call can pass, and an
incomplete or mismatching call can fail. Truncation alone does not assign zero.
Frozen uncertainty evaluation still excludes truncated output: whole-output
eligibility is 68 and meaningful-token eligibility is 24 across both panels.
The scorer reports missingness and status separately from correctness.

The original source evaluation configuration is retained. ToolAlpaca gpt_judge
configuration uses the pinned deterministic exact-match implementation here;
ToolEyes is deterministic name-only relevance, reported separately from the
63 reference-compliance cases. Neither measures executable task success.
Original reference flags are retained without exclusions or score changes.
Cost/latency objectives remain bounded audit diagnostics, not preference success.

## Runtime interpretation

Requested temperature remains 0.001. An installed local vLLM constructor check
on all requests observed normalization to 0.01 and inherited top-p 0.9.
This is not independent observation of each server request's internal sampler.
The runtime field effective_temperature records that constructor observation;
metadata/runtime_notes.json documents the limit. Server weights and revisions
are operator-attested; the models endpoint only verifies the model identifier.
The valid tokenizer preflight counted 89,327 prompt tokens, maximum 4,513,
with no context overflow after reserving 1,024 output tokens. An earlier invalid
container-length count was superseded and is not context-fit evidence.
Request elapsed time is not GPU active time. Setup, idle time and provider quota
remain separate. No cost or speed comparison is established by this adapter.

## Validation and preservation

The adapter validates the existing development export attestation before opening
its development-only reference sidecar. It verifies selected prompt lineage,
source reference hashes, immutable workflow/scorer sources, saved evidence and
recomputed response validations. It never opens raw benchmark or split records.
Hashes establish byte consistency, not authenticated partition provenance.

Synthetic CPU tests cover original raw Python types, separate panels, reference
flag retention, tampering, membership, source pins, path/symlink boundaries,
existing-output preservation, bounded publication retries, and truncated cases
with matching calls, incomplete calls and separate ToolEyes relevance.
Only publication PermissionError is retried, at most six attempts with 3.1 seconds
total delay. There is no inference retry or overwrite fallback.

Run tests with Python unittest discovery in
 tools/development_audits/llama_coverage_scoring_v1.
Run score_llama.py --help for the five explicit repository/evidence/export/audit/
output arguments. Output must be a new child directory under
artifacts/local_development_audits. Artifacts stay ignored by Git.
The existing uncertainty analysis is evidence-bound to Qwen and must not be
pointed at Llama outputs without a separately reviewed implementation.
No model selection, calibration, confidence interval, final freeze or Task 3
completion is claimed. This 69-case selected sample is not a population estimate.
