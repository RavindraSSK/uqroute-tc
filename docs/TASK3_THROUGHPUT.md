# Task 3 throughput preparation

This addition prepares a development-only timing diagnostic. It does not mark
Task 3 complete, and it does not change the Task 1/Task 2 frozen files.

## Selection and limits

- Deterministic SHA-256 ranking (seed namespace 1729), separately within each
  benchmark × static JSONL source-file stratum. Default: one row per nonempty
  eligible stratum. Preview prints the actual count; no count is assumed.
- Only primary, clean-anchored development groups; exclude held-out,
  sensitivity-only and multi-turn rows. Runtime transition faults are not tested.
- Selection uses identity and split assignment, not model outputs or correctness.
- Keys include the source filename because clean and perturbed rows can share IDs.
- The same selection is reused across all four pinned models. A row can recur
  across files; this is expected and does not create an independent base group.
- This is a coverage-stratified diagnostic, not a population-weighted sample,
  context-length-balanced sample, accuracy study or routing-benefit estimate.
  One case per stratum can give a noisy estimate; review measured durations,
  token lengths and failures before extrapolating or enlarging the diagnostic.

## Measurement

Sequential requests, no request seed, frozen temperature 0.001, max tokens 1024,
logprobs and top-logprobs 5. Server settings/model revisions come from the frozen
configuration. No automatic request retries or unrecorded warm-up requests.
The first request is included; do not interpret this as warmed concurrent vLLM
capacity. Timeout is 300 seconds and recorded in the manifest.

Per-attempt elapsed time includes message construction and parsing; per-session
batch wall time also includes atomic Drive writes. SDK usage is saved with raw
responses. Token totals are explicitly *known* totals. Missing/error/interrupted
usage is not zero cost; incomplete usage suppresses aggregate token throughput.
Returned tokens can still be recorded if a local parser fails after inference.

Single-GPU batch wall-hours are an allocation proxy, not GPU active compute.
The notebook separately records startup and the observed GPU window from its
first device check through owned-server shutdown. This is a lower bound on the
allocated runtime, excluding prior and subsequent idle time. Record the platform
balance/quota and disconnect/delete the runtime after the run. No quota estimate
is invented by the notebook.

## Saving and resume

Separate Drive folders under `UQRoute-TC/throughput/`; existing pilots untouched.
Manifest mismatch aborts. One process per output folder: no multiwriter guarantee.
Attempt intent is saved before sending a request; each new attempt has its own
file. Successful, truncated and invalid-evidence outcomes are skipped on resume.
Request errors and interrupted intents are also skipped unless `--retry-errors`
is explicitly supplied. Prior attempts remain in accounting; an interrupted
request may have executed remotely despite its unknown local outcome.

Sessions that never finish remain marked `running`, counted as unfinished in
the summary. Their wall time is unknown and is not silently reconstructed.
Timing data is not exported as ordinary benchmark-scoring JSONL: file-qualified
identities must not be collapsed by the official scorer's ID-only interface.

## Install into the Windows repository

1. Verify the working tree is clean at `a2a095af10eaa433147d095df07d396980ca47e5`.
2. Create `feat/task3-throughput` from that checkpoint.
3. Extract the supplied overlay into the repository root. It adds four files only.
4. Run `python -m pytest -q`, `python -m ruff check src tests`, and
   `git diff --check`. Review `git status` and the four new files.
5. Commit/push only these Task 3 additions. Paste the full pushed commit SHA into
   `notebooks/UQRoute_TC_Task3_Throughput.ipynb` in Colab before running it.

Start with `MODEL_KEY = 'qwen15b'` on a fresh L4. The notebook launches a fresh
owned server and rejects an existing endpoint rather than trusting its model
name as proof of revision. Repeat in fresh runtimes for the other models after
reviewing the first result. Never expose `HF_TOKEN` or commit saved responses.

## Evidence still pending

Local mocked tests can verify selection/resume/accounting, not live serving,
release-wide stratum counts, GPU capacity or throughput. The benchmark data and
GPU are not included in the source archive. Review the notebook's selection
preview and live run results before scheduling the full development experiment.
Held-out perturbation evaluation remains untouched until analysis/routing
decisions are frozen.
