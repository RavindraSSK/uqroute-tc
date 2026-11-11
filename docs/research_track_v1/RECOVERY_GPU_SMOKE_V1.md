# Qwen 1.5B recovery resource smoke on Colab L4

The owner supplied the completed staging summary: five groups spanning APIBank,
BFCL v3, RoTBench, ToolAlpaca and ToolEyes, all six released fault-feedback types,
30 planned post-fault small-model requests, and zero planned fallback requests.
No benchmark lacked an eligible group. Generation and observed submissions remain
zero; correctness scoring, recovery effectiveness and main readiness are pending.
The earlier occupied-output guard preserved this completed preparation.

The following owner-reported fingerprints bind the new execution notebook:

| Input | SHA256 |
|---|---|
| `qwen15b_recovery_resource_smoke_v1.zip` | `ecd1e39441ddffdd4623d699cd6112dc791c322bfcec9336390f71d1cde2f453` |
| `manifest.json` | `3b747531cb19eb6e11a5fd74cdf338382f47e22ac0b5c9f596c84f08006d105c` |

These fingerprints and counts came from the supplied summary. The private archive
has not been uploaded here or independently inspected. The notebook validates its
actual bytes, payload inventory, full request bodies, episode/context bindings,
five groups and six faults before dispatch. Do not rerun staging over its occupied
output or recreate the archive to bypass a mismatch.

## Completed owner run

The owner subsequently supplied the completed OUTPUT ZIP. All 152 indexed file
hashes and 30 responses verify, and independent frozen replay matches all saved
records and summary bytes. There are 19 parsed-call outputs and 11 unparsed/no-call
outputs; correctness is unscored. See [evidence and CPU owner import](RECOVERY_SMOKE_EVIDENCE_V1.md).
Do not rerun the completed smoke. The following instructions are retained as
execution provenance.

Notebook: `notebooks/UQRoute_TC_Qwen15B_Recovery_Resource_Smoke_v1.ipynb`.

1. Open it in Colab and select an **L4 GPU**.
2. Upload the existing INPUT ZIP from
   `artifacts/local_development_audits/recovery_resource_smoke_preparation_v1/`.
3. Run the execution cell once. Enter the current provider quota/compute-unit
   note, or explicitly `not displayed` when remaining quota is not shown.
4. Run the download cell after execution, including after a recorded failure.
   Save and attach the OUTPUT `uqroute_qwen15b_recovery_smoke_*.zip` for review.
5. After saving the output, disconnect and delete the GPU runtime.

Executing that cell authorizes only this bounded 30-request development smoke.
The original preparation flags remain false and unchanged. No initial call is
regenerated, no fallback is called, and no held-out group or reference sidecar is
read. All scenarios use their preserved initial-model history and released fault
feedback. A local HTTP write is evidence of a fault-feedback submission attempt,
not proof of model execution or a real external tool fault.

## Runtime and evidence

The notebook embeds the tested client and supervisor from
`tools/development_audits/recovery_gpu_smoke_v1/`. Its immutable study-source
checkout is `fbe1e3ed1892cfa4b71fb69559af8235107ad0dc`; that revision supplies
the staged ledger and frozen parser/token-evidence methods. Newly supplied
execution sources are embedded in the notebook and copied into evidence.

The isolated environment uses vLLM 0.30.0, Transformers 5.20.2 and Ninja. The
model/tokenizer revision remains `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`,
with BF16, default pinned chat template, 8,192-token context and 1,024 output tokens.
Requested temperature remains 0.001. The local installed sampling constructor
must reproduce the prior 0.01 clamp; inherited defaults are recorded, with no seed
added. This is constructor observation, not independent proof of each server's
internal sampling. Launch settings attest revisions; the model-ID endpoint does
not authenticate loaded weight bytes.

Before generation, all 30 server `/tokenize` token sequences must match the local
pinned tokenizer exactly. These are tokenizer checks, not model generations.
The interface uses the official vLLM chat-tokenization defaults with an explicit
generation prompt and no additional special tokens; see the
[vLLM tokenize protocol](https://docs.vllm.ai/en/v0.15.0/api/vllm/entrypoints/serve/tokenize/protocol/).
The installed 0.30.0 server is still checked at runtime; mismatches stop dispatch.

Generation uses the separately tested write-once ledger, at most 30 sequential
requests, a 300-second request timeout and a 900-second generation wall deadline.
Startup has a 1,200-second deadline. These are stopping limits, not completion
estimates or a quota guarantee. Setup and model loading also consume allocated
GPU time. The quota note is operator information, not measured available GPU
minutes or billed cost.

An existing execution/run directory is refused. An intent, submission or unknown
response cannot trigger an automatic retry. The supervisor stops generation and
the server, then exports completed or partial evidence. Setup-failure salvage is
also available. Forced runtime deletion or hardware failure can still lose files;
save the export before removing the runtime. A partial/interrupted batch requires
review rather than resetting the runtime and repeating its requests.

The export contains prepared messages, raw HTTP bodies, intents/submissions,
status/timing, source/runtime fingerprints and frozen CPU replay results. Returned
HTTP errors and unusable/truncated outputs remain visible. Missing usage withholds
complete totals while preserving known sums. Every record retains null official
correctness; no output is repaired, relabeled or scored against a reference.
Environment variables, authentication tokens, dependency caches and weights are
excluded from export.

## Verification and remaining work

All 18 new CPU checks pass. They use production request construction and synthetic
transports, exercise all five benchmarks/six faults, immutable ZIP/manifest/ledger
bindings, runtime revision checks, token-sequence comparisons, frozen replay,
usage missingness, unknown injection, setup-failure/partial export and notebook
source identity/compilation. They do not claim an actual CUDA/vLLM run. The 96
existing focused checks also pass; Ruff and diff checks are clean.

The Qwen 1.5B smoke is now complete and independently verified. It establishes
only bounded serving/evidence feasibility. Full recovery collection, other model
roles, fallback generation, objective/threshold selection, post-fault scoring
dispositions, baselines, full cost accounting and held-out evaluation remain open.
