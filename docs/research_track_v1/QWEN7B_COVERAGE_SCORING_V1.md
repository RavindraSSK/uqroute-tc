# Qwen 7B corrected development coverage scoring v1

## Scope and source identity

This separate CPU scorer binds to the 69 selected primary-development responses
from Qwen/Qwen2.5-7B-Instruct, with frozen model/tokenizer revision
a09a35458c702b33eeacc393d103063234e8bc28, BF16 and no quantization.
The generation code revision is 94a7be413488b2c023e99144877e7c49ac439c6e.
The prepared manifest SHA256 is
 aea421f662be4499926c8b3432814d08754a6ac5fd71fce02fc8f7b9fa33d7ce.
The archive uqroute_qwen7b_corrected_coverage_b4ede513.zip has SHA256
 f25c749ea191631107efa3703db2dffff7f78b0835e79620ed98d91651b3b18f.
Its 302 members include the inventory of 301 evidence-file hashes; every member
is independently pinned in this scoring policy. Hashes establish consistency,
not authenticated provenance or cryptographic proof of partition filtering.

The prepared requests were checked locally to use the same 69 selected case
identities, order, prompt messages and request settings as corrected Qwen 1.5B,
except for the model ID. This is bounded benchmark/source-stratum coverage,
not representative population sampling or a clean/perturbed paired design.
No held-out evaluation or final protocol freeze is enabled.

## Generation and replay observations

All 69 response slots are complete, with zero resumed slot visits, one finished
session and no missing token-usage counters. Frozen evidence replay gives
69 whole-output and 34 meaningful-token eligible cases. Eligibility does not
establish official reference compliance or execution success.
The pinned tokenizer counted 88,220 prompt tokens, maximum 4,633. Every prompt
fits the 8,192-token context with the 1,024-token completion allowance; no
prompt truncation or case dropping was used. Completion usage is 4,198 tokens,
92,418 total. Session wall time is 261.382230219 seconds; request elapsed sum
is 260.350051818 seconds. These exclude setup/loading/idle allocation and are
not GPU active time, full cost or a controlled cross-model speed comparison.

The recorded environment is Python 3.13.16, vLLM 0.30.0, Torch 2.13.0 with CUDA
13.0 and Transformers 5.20.2 on an NVIDIA L4. Requested temperature remains
0.001. A local installed constructor check observed normalization to 0.01,
inherited top-p 0.8, top-k 20 and repetition penalty 1.05. This is not independent
per-request server observation. Identical explicit request settings do not
ensure identical inherited sampling defaults across model checkpoints.
Server shutdown is recorded as successful. The notebook's code and logs are
included in metadata; no environment dictionary or user HF token is serialized.
Revision/weight identity is operator-attested; the models endpoint checks ID.

## CPU scoring and preservation

The unchanged pinned official parser reparses the original raw response, keeping
Python argument types intact. The unchanged pinned scorer computes outcomes.
The development export attestation is checked before opening its approved
reference sidecar, and selected prompt, group, reference and audit lineage is
verified. Raw benchmark and split files are never opened by this scorer.
The original source evaluation configuration is retained alongside the actual
scoring method. ToolAlpaca gpt_judge source settings use deterministic exact
matching here; ToolEyes uses deterministic name-only relevance. Neither should
be described as an LLM-judge verdict or executable task success.

All 69 cases remain in scoring denominators, with 63 reference-compliance cases
and six ToolEyes relevance cases reported separately. Reference flags are
retained without exclusions or label changes. Preference success and measured
tool cost/latency remain unassessed. Regex nondetection does not prove absent
intent. Probability missingness and alignment diagnostics are separate from
correctness. If a future response is truncated, it is scored as generated
without repair or automatic zero; its probability measures remain unavailable.
The currently pinned archive contains no truncations.

The adapter is copied into a separate versioned directory and changes no Qwen
1.5B, Llama, generation or uncertainty source. Original evidence and outputs
are never overwritten. Only new ignored output directories are accepted.
Bounded retries apply solely to PermissionError during completed-directory
publication (six attempts, 3.1 seconds total delay), never to model requests.

## Local complete-subtask workflow

The supplied installer adds three Python/policy source files plus this document,
verifies/imports the downloaded archive, runs 46 synthetic CPU regression tests,
replays all evidence, compares the full local replay summary with its exported
counterpart, and scores into a fresh output directory. Each failed stage stops
the sequence. Existing matching imported evidence may be reused only after all
pinned hashes and the exact file set match. Existing scoring output is refused.
No Git staging, branch changes, commits or pushes occur automatically.

Tests cover raw Python types, separate relevance panels, flags, development
membership and source pins, tampering, output preservation, path/symlink
boundaries, bounded publication behavior, and truncation scoring/eligibility.
Synthetic tests do not establish real model results. Real reference outcomes
must be read from the locally verified scoring report; this document does not
invent them. The existing uncertainty/comparison packages remain bound to their
previous evidence and must not be repointed by editing hashes. Three-model
comparison requires a separately reviewed analysis implementation.

Calibration, group-aware intervals, validated O/A/R comparisons, broader static
experiments, failure catalogue scope and final shared protocol freeze remain
outstanding. This diagnostic does not complete Task 3 or establish routing benefit.
