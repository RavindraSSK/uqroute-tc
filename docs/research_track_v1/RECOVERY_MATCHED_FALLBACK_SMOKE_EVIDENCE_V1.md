# Verified matched 14B recovery fallback smoke

The owner supplied `uqroute_qwen14b_matched_recovery_fallback_smoke_f721c202.zip`.
Its SHA256 is
`f85c1c51bb4a3cc19bda831ee87e64b0235af08d8a8f3868a0334415acce14b9`.
The exact 156-member inventory, ZIP CRC and all 155 indexed file hashes pass.
Published client/supervisor/ledger bytes and the original prepared manifest match.
Independent CPU replay at the pinned study-source checkout `c3cbf9f` reproduces
the owner's `summary.json` and all thirty `records.json` entries byte for byte.

| Check | Verified result |
|---|---:|
| Fallback requests / saved responses | 30 / 30 |
| New small requests | 0 |
| Known matched parent small responses | 30 |
| Groups / benchmarks | 5 / 5 |
| Episodes per fault type | 5 |
| HTTP failures / unknown slots | 0 / 0 |
| Complete frozen token-evidence records | 30 |
| Parsed calls / unparsed or no call | 24 / 6 |
| Parsed candidates with finite mean NLL | 24 |
| Prompt / completion tokens | 56,606 / 1,754 |
| Missing usage slots | 0 |
| Sum of request elapsed seconds | 71.953 |
| Dispatch process wall seconds | 74.007 |
| Supervisor wall seconds | 370.675 |
| Server / generation stopped | Both recorded true |

All thirty contexts and parent receipts match the completed small smoke. No
later small response is appended; all no-call, control-action and matching parent
episodes remain. This is all-pair data collection without a routing threshold.
The aggregate machine-readable report is
[`qwen14b_matched_recovery_fallback_smoke_v1_summary.json`](../evidence/qwen14b_matched_recovery_fallback_smoke_v1_summary.json).
Detailed inputs, responses, identifiers, quota notes and logs remain private.

## Runtime and interpretation

The L4 served the frozen Qwen2.5-14B-Instruct-AWQ checkpoint in FP16 with
vLLM 0.30.0 and Transformers 5.20.2. Its configuration records four-bit AWQ.
Every server/local prompt token sequence and returned prompt usage reconciles.
The launch arguments, model configuration, source hashes and server snapshot
are retained; a served model-name endpoint alone cannot authenticate weights.

Requested temperature remains 0.001; the installed constructor records 0.01,
top-p 0.8, top-k 20, n=1 and no seed. Its inherited repetition penalty is **1.05**,
versus **1.1** for the frozen small model. Both preserve their pinned model defaults;
the comparison concerns these model configurations, not an isolated parameter-
count effect. No post-result normalization or rerun is introduced. Constructor
observations are not independent proof of internal sampling on every request.

The small model has 19 parsed outputs and eleven unparsed/no-call outputs;
the fallback has 24 and six. Parser status is structural, not reference
correctness, schema validity, appropriate deferral or executed recovery. Complete
token evidence likewise is not correctness. Original endpoint limitations remain:
reference compliance and ToolEyes name relevance must be reported separately.

Times describe this sequential selected smoke. Supervisor time excludes the
notebook's dependency installation and full allocation/billing. They are not a
population latency estimate, a provider-unit measurement or a monetary-saving
result. The five groups have dependent fault variants. No gate benefit, final
threshold, held-out result or full-study readiness is established.

## Owner local import complete

The owner ran the importer at `d5be459`; fifteen tests completed successfully
with one Windows symlink skip. All 155 hashes, original parent pairs and exact
independent replay match the aggregate evidence above. Paired CPU scoring is also owner-complete at `1cf2bd7`: reference matches 4/24
versus 10/24 (six gains, zero losses); relevance 3/6 each (two gains, two losses).
The next action is the
[paired behaviour review](RECOVERY_MATCHED_SMOKE_BEHAVIOUR_REVIEW_V1.md).
The import instructions below remain for a fresh reproduction.

## Import on the owner's CPU

Keep the downloaded OUTPUT ZIP in Downloads, then run:

```bash
python tools/development_audits/recovery_fallback_smoke_import_v1/import_smoke.py
```

For another location, pass `--archive PATH`. Renamed downloads are accepted only
when their bytes match the pinned archive SHA256. The completed original small
smoke import must remain at its existing local path. Fifteen CPU checks cover
safe archive handling, unchanged parent histories/receipts, unknown outcomes,
model-specific sampling observations, tokenizer/usage contradictions and renamed
file discovery. The actual complete archive also passes the production importer.

The importer rechecks the known parent export and all thirty pairs, verifies
runtime/defaults/quantization/shutdown evidence, and replays from a sparse local
checkout of the pinned study sources. It sends no model requests or reference
scoring, accesses no held-out inputs and preserves original evidence.

Fresh ignored output:
`artifacts/local_development_audits/recovery_fallback_smoke_import_f85c1c51/`.
Existing output is never overwritten. Paste only the printed aggregate summary;
keep case-level files local. The owner local import is complete.

The [paired CPU diagnostic](RECOVERY_MATCHED_SMOKE_PAIRED_REFERENCE_SCORING_V1.md)
is owner-complete with unchanged original reference/relevance endpoints. Semantic/
execution recovery remains unevaluated. Review the paired structure next. Do not rerun either GPU
smoke or expand the cohort before the matched results are reviewed.
