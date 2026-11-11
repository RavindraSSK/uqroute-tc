# Completed Qwen 1.5B recovery resource smoke

The uploaded owner evidence ZIP is
`uqroute_qwen15b_recovery_smoke_4a529063.zip`, SHA256
`dd91a73f5f565269f83d70773fd25fd64c82785029e3d96b139682c072b59595`.
Its CRC, exact 153-member inventory and all 152 indexed file hashes were verified.
Prepared manifest, client, supervisor and ledger bytes match their published
fingerprints. All 30 local/server token sequences and returned prompt-token
counts reconcile. No raw prompt, output or case identifier is published here.

| Check | Verified result |
|---|---:|
| Post-fault small requests / saved responses | 30 / 30 |
| Observed local submission records | 30 |
| Canonical groups / benchmarks | 5 / 5 |
| Each released fault type | 5 episodes |
| HTTP failures / unknown slots | 0 / 0 |
| Complete frozen token-evidence records | 30 |
| Parser status `calls` | 19 |
| Parser status `unparsed_or_no_call` | 11 |
| Parsed candidates with finite mean NLL | 19 |
| Prompt / completion tokens | 56,606 / 1,798 |
| Missing usage slots | 0 |
| Summed request elapsed seconds | 26.103 |
| Dispatch process wall seconds | 28.002 |
| Supervisor wall seconds | 244.132 |
| Fallback generation | 0 |
| Generation/server stopped | Both recorded true |

The aggregate evidence is in
`docs/evidence/qwen15b_recovery_resource_smoke_v1_summary.json`.
All 30 records were independently replayed on CPU with the frozen parser and
token-evidence methods at study-source revision
`fbe1e3ed1892cfa4b71fb69559af8235107ad0dc`. Both reproduced `summary.json` and
`records.json` match the owner's saved bytes exactly. A sparse pinned-source
checkout was also exercised on the actual archive for the local import command.
No new inference, reference scoring or changes to original evidence occurred.

## What this establishes

This is a completed bounded L4 serving/evidence smoke. All 30 known fault-feedback
contexts were submitted, responses saved, uncertainty evidence replayed and usage
retained. Submission means the local HTTP write returned, not proof of an actual
external tool failure or independent authentication of model weights.
The runtime retained requested temperature 0.001 and recorded the local
constructor's 0.01 clamp, top-p 0.8, top-k 20 and repetition penalty 1.1. These
sampling observations and the operator quota note are not independent server
internal-sampler or provider-quota measurements.

Complete generation/token evidence does not imply a valid call or correct
recovery: 11 responses are unparsed or contain no call. Even the 19 parsed calls
have not been checked for reference correctness, argument correctness or execution
success. Official scoring and RQ3 outcomes remain unevaluated. The five groups
share dependent fault scenarios and cannot establish broader recovery performance.
The measured times exclude full installation/allocation/billing and must not be
extrapolated as full-study cost or a monetary-saving result.

## Import on the owner machine, CPU only

Keep the downloaded OUTPUT ZIP in Downloads and run:

```bash
python tools/development_audits/recovery_smoke_import_v1/import_smoke.py
```

Renamed downloads are accepted only when their bytes match the evidence SHA256.
For another location, supply `--archive PATH`. The command verifies archive/member
and source fingerprints, runtime/shutdown/sampling and token-count evidence,
then independently replays the saved responses in a local sparse checkout of the
pinned study sources. The checkout is cloned locally; it sends no model requests.
Returned records and summary must match the saved owner bytes exactly.

Fresh ignored output:
`artifacts/local_development_audits/recovery_smoke_qwen15b_import_dd91a73f/`.
It contains original evidence, reproduced replay/source checkout and an aggregate
summary. Existing output is preserved rather than overwritten. Keep detailed
case-level files private. Nine synthetic import checks pass, including archive
paths/hashes, runtime completion, tokenizer/usage contradictions and renamed-file
discovery; lint and actual complete-archive replay also pass.

Do not rerun the completed GPU smoke. Owner import should finish before staging
broader recovery collection with explicit accounting for these 30 occupied
requests. Remaining full-development Qwen 1.5B small-stage slots are 750 - 30 = 720;
that arithmetic does not itself authorize or prepare another batch. Other model
roles, fallback generation, post-fault scoring dispositions, a final objective/
threshold, baselines, complete cost accounting and held-out evaluation remain open.
