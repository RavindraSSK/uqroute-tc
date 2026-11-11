# Bounded recovery resource smoke preparation v1

The owner completed context preflight at `2b9527d`: all 4,824 potential request
contexts fit the frozen 8,192-token limit with the full 1,024-token completion
allowance, with zero overflows, truncations or dropped requests. All 19 context
tests passed. These figures are from the supplied owner terminal report; private
per-request files have not been independently inspected in this checkout.

| Initial small model | Small / fallback contexts | Maximum small prompt | Maximum fallback prompt |
|---|---:|---:|---:|
| Qwen 1.5B | 750 / 750 | 4,937 | 4,937 |
| Llama 3B | 828 / 828 | 5,474 | 5,603 |
| Qwen 7B | 834 / 834 | 4,954 | 4,954 |

The largest context uses 5,603 + 1,024 = 6,627 tokens, leaving 1,565 tokens of
headroom. Tokenizer fit does not establish GPU memory feasibility, serving
correctness, available quota, latency, recovery effectiveness or monetary cost.
No actual recovery submission or scoring has occurred.

## Stage on CPU

```bash
python tools/development_audits/recovery_smoke_v1/stage.py
```

This command runs 25 synthetic staging/ledger checks and reads the three original
owner-pinned preparation ZIPs plus the completed local context preflight. It
verifies all role/request coverage, context bindings and token-count aggregates.
It performs no downloads, serving, inference, injection or reference scoring.
The original preparation and context-preflight outputs must remain in place.
Do not rerun those earlier commands over their occupied outputs.

For Qwen 1.5B only, choose one eligible clean group per available benchmark by
SHA-256 ranking of `[benchmark, canonical_base_id]`. Include all six released
fault scenarios for each selected group. Selection uses no correctness label,
uncertainty score or model outcome beyond the existing initial-call eligibility.
Benchmarks without an eligible group are explicitly listed, not filled with
other cases. At most five groups and 30 small-stage requests are prepared; no
fallback requests or initial generations are included. These few dependent
scenarios are a resource/engineering smoke, not an effectiveness sample.

Fresh ignored output:
`artifacts/local_development_audits/recovery_resource_smoke_preparation_v1/`.

- `summary.json`: selected benchmark/group counts, bounded request count and ZIP pins.
- `provenance.json`: preserved input fingerprints and staging/ledger source hashes.
- `qwen15b_recovery_resource_smoke_v1.zip`: manifest, selected episodes and requests,
  and the tested small-stage ledger source.

The archive contains private prompts and initial responses. Keep it with the
other ignored evidence. An existing output is rejected; no prior evidence or
authorization flag is modified. Review the printed counts and transfer hashes
before building a pinned runtime-specific GPU notebook. The package remains
`dispatch_authorized: false`, with runtime validation pending.

## Ledger implementation boundary

`tools/development_audits/recovery_smoke_v1/ledger.py` supplies a separate
write-once small-stage dispatcher kernel. It is not a ready-to-run GPU executor
or a complete adaptive recovery implementation. It accepts at most 30 fixed
Qwen 1.5B small-stage requests, requires explicit development execution and
binds its manifest to the request inventory. The future runtime launcher must
verify the packaged manifest/source fingerprints, pinned weights/tokenizer,
server settings and effective sampling, tokenizer/server context counts, actual
GPU allocation, current quota and a runtime-bound run manifest before calling it.
The static dispatcher is not used.

Per request, the ledger saves a unique durable intent before transport. A
separate submission record follows a completed local HTTP request write. The
submission records `transition_injected: true` for the benchmark fault-feedback
attempt; it does not prove the server executed the model or a real tool failed.
An intent without submission evidence remains injection-unknown. A submitted
request without a complete saved response remains response-unknown. No unknown
slot is resubmitted, and the batch stops on transport or known HTTP failure.
The direct transport accepts only loopback HTTP and follows no proxies/redirects
or automatic retries. Raw response bytes, HTTP status, hashes and request elapsed
time are preserved without reference scoring or repairs.

Completed slots can be read/resumed without new requests under the same binding.
An occupied unknown slot or previous HTTP failure blocks automatic continuation;
an abandoned writer lock requires review. Changed run bindings, unexpected files,
hash mismatches and symlinks are rejected. The ledger does not claim that disk
writes survive every hardware/storage failure. Frozen parser/token-evidence
replay, complete usage accounting and actual runtime execution remain pending.

The 25 tests cover production-built request compatibility, fixed selection and
all six faults, no-call benchmark reporting, context-preflight coverage, complete
synthetic staging/publication, single-writer and resume rules, pre/post-submission
interruptions, HTTP failure, raw-evidence changes, context changes, stage/budget
limits, endpoint constraints and write/submission/response ordering. No actual
model responses are generated by these tests.

After owner staging, prepare a bounded GPU runtime smoke using its exact ZIP and
manifest fingerprints. Keep full recovery collection, fallback roles, the final
objective/threshold, post-fault scoring dispositions, baselines/cost accounting
and held-out evaluation separate and pending.
