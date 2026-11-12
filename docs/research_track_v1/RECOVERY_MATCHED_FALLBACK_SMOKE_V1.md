# Matched post-fault fallback smoke preparation

The owner completed the behaviour review at `4f7b584`; all 14 checks passed and
the reference scores reproduced exactly. The supplied review attributes the
fourteen reference-panel match-to-mismatch changes to eleven no-call outputs,
two changed-name sequences and one same-name argument change. The three ToolEyes
relevance losses have changed name sequences. All labels and cases remain intact.

| Structural group | Reference rows / post-fault matches / lost initial matches | ToolEyes rows / post-fault matches / lost initial matches |
|---|---:|---:|
| Changed name sequence | 5 / 0 / 2 | 3 / 0 / 3 |
| Identical canonical calls | 2 / 2 / 0 | 2 / 2 / 0 |
| No parsed post-fault call | 11 / 0 / 11 | 0 / 0 / 0 |
| Same name sequence, changed arguments | 6 / 2 / 1 | 1 / 1 / 0 |

These selected five-group diagnostics do not determine semantic fault
appropriateness, execution success or population recovery rates. Control-action
and no-call cases remain included. The next bounded comparison asks whether the
frozen 14B AWQ fallback behaves differently under the **same 30 fault histories**.
It does not assume that a larger model will repair a fault or improve the score.

## Prepare on CPU

```bash
python tools/development_audits/recovery_fallback_smoke_v1/stage.py
```

This sends no model requests, performs no downloads and requires no GPU. It
checks the existing original Qwen 1.5B recovery transfer, completed smoke import,
original reference scores, completed structural review and full saved 14B
tokenizer preflight. Original input fingerprints are checked again before
publishing a fresh ignored output.

All thirty parent small responses must be known, saved HTTP 200 outcomes. The
parent smoke ZIP/export index, preparation, source/runtime/context bindings and
request ledger are revalidated. Original scores must match the completed review's
input fingerprints, identities and unchanged labels. The structural observations
are independently reparsed from the saved text. These outcome fields are checked
for consistency; **none selects the fallback cohort**.

Each chosen fallback row must already occur in the immutable original 750-row
Qwen-history fallback plan. The complete original plan is checked against its
owner-reported transfer and manifest fingerprints with the existing preflight
validator. Selected messages and generation settings must equal those of the
matching small request, differing only in model. The new role/request identity is
`postfault_fallback` with an explicit paired-small request link. The later
post-fault small answer is not appended; the context remains the original clean
prompt, original initial small answer and released fault-feedback turn.

All five groups and thirty episodes are retained, including all eleven no-call
parents, six episodes with an initial literal control name, already-matching
outputs and all six fault types. No correctness/uncertainty filtering, threshold,
oracle case selection or cohort redesign occurs. Existing static 14B outputs
lack these fault histories and cannot replace the new fallback-role evidence.

## Transfer and runtime boundary

Fresh ignored output:
`artifacts/local_development_audits/recovery_matched_fallback_smoke_preparation_v1/`.

- `qwen14b_matched_recovery_fallback_smoke_v1.zip`: manifest, thirty selected
  fallback requests/episodes, known-small response receipts and a tested
  fallback-only ledger implementation.
- `summary.json`: matched counts, retained cases, selected token limit checks and
  transfer/manifest fingerprints.
- `provenance.json`: preserved input, policy and implementation fingerprints.

The ZIP uses fixed member order/timestamps/attributes and uncompressed members.
Its actual owner fingerprint must still be reviewed before pinning a GPU notebook.
Private messages/identifiers remain in ignored files. The transfer contains no
reference answers or correctness labels. Existing files are never overwritten.

Model: `Qwen/Qwen2.5-14B-Instruct-AWQ`, revision/tokenizer
`539535859b135b0244c91f3e59816150c8056698`, FP16, the frozen AWQ checkpoint,
vLLM 0.30.0, default pinned template, context 8,192, output allowance 1,024,
GPU utilization 0.88 and requested temperature 0.001. Inherited sampling defaults
and effective temperature remain runtime observations. The saved original 14B
tokenizer report must cover every selected request without overflow. GPU memory,
server tokenization, current quota and effective settings must be checked again
by a separately pinned runtime-specific launcher.

The new ledger is a separate adaptation of the tested small-stage ledger; the
original implementation and hashes are unchanged. It admits only the frozen
fallback model/role, valid paired-small identities, a known parent-smoke binding,
up to 30 request slots and explicit execution. Intent/submission/response stages,
unknown slots, raw responses, hashes, HTTP failures and writer locks retain the
same no-retry safeguards. There is no runnable GPU launcher in this preparation
package. The static/small-stage dispatchers are incompatible with this transfer.
`dispatch_authorized`, held-out access and main-experiment readiness remain false.

The eventual smoke has **30 new fallback requests and zero new small requests**.
This is all-pair evidence collection, not an executed uncertainty-gated policy.
It supports later paired reference/relevance diagnostics while retaining current
endpoint limitations. Collection cost and a counterfactual serving policy's
charged calls are different quantities; no monetary or policy benefit is claimed.

Thirty tests cover the adapted no-retry ledger, explicit parent/model/role
bindings, complete production-built thirty-episode selection, no-call retention,
exact messages, forbidden appended/static contexts, frozen settings, unchanged
review labels and selected 14B token boundaries. Actual saved thirty-episode
histories and receipts also pass construction checks locally. The original full
750-row transfer and completed owner review files are unavailable in this
implementation checkout, so actual owner staging and archive pins remain pending.

Run preparation and review its final summary before preparing/executing the
bounded fallback GPU notebook. Do not rerun the completed small smoke, generate
the remaining 720 small requests, change labels or enable held-out evaluation.
