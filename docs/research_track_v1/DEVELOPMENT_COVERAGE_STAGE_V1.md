# Development coverage stage v1

Baseline: `6dfed208793f0061b79dba76359b91d6ea484fcf`.
Task authority: `docs/PROJECT_TASKS.md`, Task 3, inspected at that commit
(Git blob `78de67ec410195c516438aa0d38c88cd3e8f0e23`).

## Evidence and remaining requirements

The owner verified the corrected Qwen 1.5B five-clean-case generation and CPU
replay, then locally scored two of four reference-compliance rows as correct
(APIBank and BFCL). RoTBench and ToolAlpaca did not meet reference compliance;
ToolEyes separately scored zero of one for name relevance. No bounded reference
flags were detected. This does not establish that unflagged references are
semantically correct. The path fixes and 31 adapter tests passed locally, with
one Windows symlink skip. These results are diagnostic, not population accuracy.

Task 3 still needs broader corrected static runs for the selected small models,
validated Observation/Action/Reward grouping, evidence-to-score joins and
missingness reports, development-only uncertainty discrimination/calibration/
risk-coverage analysis, group-aware intervals and a failure catalogue. Final
held-out evaluation remains blocked until the shared protocol is frozen.
Task 4 routing, fallback policies, transition recovery and full policy cost
accounting remain separate. No model role or required analysis is removed.

## Next bounded experiment

Run Qwen2.5-1.5B-Instruct on one construction candidate per available
`(benchmark, source_file)` stratum. This is the existing frozen `coverage`
selection in `corrected_generation_v1/workflow.py`: hash-minimum selection with
seed 1729. It is independent of model outcomes, correctness, uncertainty and
reference flags. The package does not open prior model outcomes to select rows.
The exact row count is measured locally; 85 is an upper bound (five benchmarks,
17 released static source files). Missing constructed strata are explicit.

The prior five clean feasibility cases are deliberately included again in a
separate run. This planned replication is not a retry of failed/unknown slots.
Old evidence is never overwritten and the two runs must not be pooled as
independent tasks. Coverage rows are not a representative population estimate.
Clean cases are selected independently of perturbed rows, so this is not a
paired robustness experiment. The report measures how many selected perturbed
rows happen to have a selected clean anchor; it does not manufacture pairs.
Source-file coverage is not validated O/A/R taxonomy.

## Preparation implementation

`tools/development_audits/coverage_stage_v1/stage.py` verifies the baseline
ancestor and unchanged generation implementation. It delegates preparation to
the existing workflow, using the previously reviewed candidate/denominator
fingerprints and its original summary/inventory locks. The existing workflow
checks the population sidecar, development membership, corrected prompt/tool
hashes, model settings and source fingerprints. The 1,754-row inventory and
26 construction blocks remain unchanged. No new construction repairs are made.

Preparation reads only preserved local development audit/population artifacts
and pinned project code/configuration. It does not read the raw benchmark,
full split, reference sidecar, held-out records or prior generation outcomes.
It does not launch a server or send network requests. Hashes establish
consistency with the reviewed trusted export/audit, not an authenticated
partition proof.

Paths are normalized to absolute paths after rejecting symlink paths. Output
must be a fresh directory beneath local development artifacts and must not
overlap inputs. Preparation uses a temporary directory and publishes only
after all validation and final input rehash checks pass.

The output contains:

- `prepared/manifest.json` and `prepared/requests.json`, preserving the frozen
  model, prompt, server, sampling and evidence settings;
- `coverage_report.json`, containing measured strata, group counts, retained
  blocks, intentional repeated cases, pairing limits, request count and
  maximum completion-token count;
- `MANIFEST_SHA256.txt`, binding the exact prepared manifest;
- `corrected_qwen15b_coverage_transfer_v1.zip`, containing only the two prepared
  JSON files, with no reference sidecar or gold answers.

Report byte lengths are not token counts, runtime estimates or billing. GPU
quota and context feasibility remain pending after CPU preparation.

## GPU notebook and evidence boundary

`notebooks/development/UQRoute_TC_Qwen15B_Coverage_v1.ipynb` is a complete
Colab L4 workflow. It requires the locally reviewed manifest hash and row
count, accepts only a two-file transfer and checks the pinned prepared plan.
It uses an isolated vLLM 0.30.0 environment with the Ninja PATH fix. Its private
checkout remains pinned to this package's baseline, whose generation code is
unchanged. Committing this package does not require editing the notebook SHA.

Before server startup, the notebook loads the pinned tokenizer and renders all
selected prompts with its chat template. Every prompt must fit alongside the
frozen 1,024-token completion allowance within 8,192 tokens. Any overflow stops
all dispatch; no prompt truncation, row exclusion or context amendment occurs.
The pure context diagnostic is CPU-tested; actual tokenizer counts require
execution in Colab. Tokenizer rendering is a preflight approximation and server
validation remains authoritative.

A separate output namespace preserves feasibility evidence. The existing
runner dispatches sequentially with durable intents and zero automatic retries;
previous intents within the coverage run are never resent, including unknown
outcomes. Resuming on the same preserved run is allowed; silently starting a
new run after unknown outcomes is not. Startup/request/replay logs and actual
usage remain distinct. Requested temperature stays 0.001; constructor-observed
normalization is recorded separately, as in the prior run.

Review available GPU quota before running. Five clean calls are insufficient
to predict coverage runtime or remaining allocation. An interrupted run is
reported with attempted/unattempted/unknown outcomes, not disguised as complete.
The notebook does not automatically inspect provider quota. Download the new
evidence archive before disconnecting; stop only a server owned by this notebook.

This notebook does not perform official scoring. The existing five-case scorer
is intentionally locked to the earlier archive and must not be repointed or
have its hashes edited. A separately reviewed coverage-evidence-bound CPU
scoring adapter is the next step after generation/evidence review. Reference
compliance, ToolEyes relevance and cost/latency preference must stay separate.
No readiness flag is advanced.

## Verification and limitations

Run the local commands in the package's `LOCAL_INTEGRATION.md`.
The new suite has 25 synthetic CPU tests. It exercises the real frozen selector,
request construction and source hashes; the wrapper integration test isolates
Git ancestry/frozen preparation with synthetic fixtures. Notebook checks compile
all ten code cells, test two-file extraction/reuse and execute the embedded
context function. They do not install GPU dependencies, download model weights,
start vLLM or certify a full Colab run. The existing 34 generation regression
tests also passed during package preparation. Real development preparation,
rendered token counts, GPU execution and coverage scores remain pending local
execution; no values are invented for them.
