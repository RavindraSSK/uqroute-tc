# Matched recovery fallback smoke on Colab L4

The owner completed CPU preparation at `c3cbf9f`: thirty checks ran successfully
(one Windows symlink skip), all thirty known small-response pairs remain, and
all selected 14B contexts fit. The maximum prompt is 3,872 tokens with a 1,024-token
output allowance inside 8,192. All eleven no-call parents and six initial-control
episodes remain. This is five selected groups with dependent fault variants.

The new notebook is
[`UQRoute_TC_Qwen14B_Matched_Recovery_Fallback_Smoke_v1.ipynb`](../../notebooks/UQRoute_TC_Qwen14B_Matched_Recovery_Fallback_Smoke_v1.ipynb).
Its upload, execution and download cells are separate. Run it on a fresh Colab
**L4** runtime. Do not repeat the completed small-model notebook or preparation.

## Run once

1. Pull `feat/task3-throughput` to obtain the notebook, then open it in Colab.
2. Choose **Runtime → Change runtime type → L4 GPU**.
3. Run Upload INPUT and select
   `artifacts/local_development_audits/recovery_matched_fallback_smoke_preparation_v1/qwen14b_matched_recovery_fallback_smoke_v1.zip`.
4. Run Execute once. Enter the currently displayed quota/compute units, or type
   `not displayed` when no remaining quota is shown. The note is not measured cost.
5. Run Download OUTPUT after completion or a recorded failure. Save and attach the
   `uqroute_qwen14b_matched_recovery_fallback_smoke_*.zip` evidence archive.
6. After saving the evidence, disconnect and delete the GPU runtime.

Running the execution cell authorizes up to **30 new 14B fallback requests and
zero new small-model requests**, for this matched development smoke only. All
messages are the original prompt, initial small answer and released fault turn.
No later small response is appended. Every parent episode is retained, regardless
of parse status, reference score or uncertainty. This collects all thirty pairs;
it does not run an uncertainty threshold or measure a policy effect.

## Frozen inputs and runtime checks

| Item | Pin |
|---|---|
| Study-source checkout | `c3cbf9f44334547a747585c613afe34d381bd070` |
| INPUT archive SHA256 | `2e2bc38f6104c06d9a6084344a5d89b1dfcd2ddb7b3ec53791a7d9d65c3abc61` |
| Manifest SHA256 | `3bc0762f233ebfcad69f55bc20285235a8962b6a93417b73fab96d24094d816d` |
| Model | `Qwen/Qwen2.5-14B-Instruct-AWQ` |
| Model/tokenizer revision | `539535859b135b0244c91f3e59816150c8056698` |
| Serving | vLLM 0.30.0, Transformers 5.20.2, FP16, frozen AWQ checkpoint |
| Context / completion allowance | 8,192 / 1,024 tokens |
| GPU utilization | 0.88 |

The notebook embeds the tested client/supervisor source. It checks the archive,
manifest, every payload, packaged fallback ledger and known-parent receipts
against the pinned study-source checkout. Reference answers are absent.

An isolated environment installs the pinned serving dependencies and Ninja,
checks dependency consistency, records GPU identity/current quota, and verifies
that the checkpoint configuration describes four-bit AWQ. Backend selection is
left to pinned vLLM, matching the prior feasibility setup; the configuration and
server log are saved. No BF16 small-model launch is reused.

Before generation it renders all thirty prompts with the pinned tokenizer,
checks 8,192-token capacity including the completion allowance, and compares
**every token ID sequence** against the local server `/tokenize` endpoint. An
occupied port, model mismatch, context mismatch or configuration failure stops
execution. Tokenizer requests do not generate responses.

Requested temperature remains 0.001 with inherited model defaults and no added
seed. The installed constructor must reproduce the previously observed 0.01
clamp, n=1 and output cap=1,024; defaults and the observed constructor values are
saved. A constructor observation is not independent proof of each server sample.
Model revision/precision are evidenced by pinned arguments and logs; the served
model-name endpoint alone cannot verify weights.

## Partial outcomes and evidence

There are zero automatic model-request retries. An existing execution directory
is refused. An intent or submitted request without a saved response remains an
occupied unknown slot. Preserve and download partial evidence before reviewing
any failure; do not reset and resend this batch. The fallback ledger also checks
the known parent-smoke binding and paired-small request identities.

Startup has a 1,200-second deadline, generation a 900-second wall limit, and each
request a 300-second timeout. These are stopping limits, not runtime estimates,
quota guarantees or measurements of all GPU allocation time. Installation time
is separate. The supervisor attempts server shutdown before exporting completed
or partial evidence. Forced runtime deletion may lose unsaved evidence.

Exports contain prepared inputs, raw response/intent/submission records,
metadata/logs, a full file-hash index and frozen parser/token-evidence replay.
They exclude environment variables, credentials, model weights and dependency
caches. Raw tasks, outputs and identifiers remain private. Replay accounts for
known/unknown HTTP outcomes, usage availability, parser status and token alignment;
it performs no reference scoring, semantic adjudication or external tool execution.

## Validation and remaining work

Twenty-five CPU tests pass: production-built five-benchmark fallback plans,
known-parent receipt binding, model/role/settings validation, no outcome-based
subset mode, wrong input hashes, interrupted slots before/after submission,
usage completeness, exact server/local token matching, runtime evidence coverage,
four-bit AWQ checks, partial exports and notebook source/cell compilation.
Ruff and notebook regeneration checks pass.

The transfer was independently reconstructed from preserved parent histories and
production episode construction. Both its archive and manifest fingerprints
match the owner's reported values exactly, and the pinned GPU client loads all
thirty requests. The original full750 owner transfer is unavailable in this
checkout; its owner-side staging verification is recorded separately.

The owner subsequently completed this L4 smoke: thirty saved responses, zero
HTTP errors/unknown slots, all thirty complete token-evidence records, and exact
independent CPU replay of all saved records. All 155 export file hashes match.
There are 24 parsed calls and six unparsed/no-call outputs. See
[verified evidence and owner CPU import](RECOVERY_MATCHED_FALLBACK_SMOKE_EVIDENCE_V1.md)
for the current next step; preserve this completed notebook run. The observed
14B repetition penalty is 1.05, its pinned inherited default. Owner local import
is complete at `d5be459`; the
[paired CPU reference scorer](RECOVERY_MATCHED_SMOKE_PAIRED_REFERENCE_SCORING_V1.md)
is supplied, with actual paired outcomes still pending. No fallback benefit, execution rescue, final threshold, monetary
saving, broader study readiness or held-out result is claimed.
