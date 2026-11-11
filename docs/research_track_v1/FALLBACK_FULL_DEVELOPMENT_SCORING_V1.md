# Corrected 14B AWQ full-development evidence and CPU scoring

Recorded 2026-11-10 after the owner's completed Colab run. This is development
evidence and an evidence-bound CPU scoring implementation, not a final protocol
freeze, held-out evaluation or routing-benefit result.

## Verified run

| Item | Recorded and verified value |
|---|---|
| Model | Qwen/Qwen2.5-14B-Instruct-AWQ |
| Model/tokenizer revision | `539535859b135b0244c91f3e59816150c8056698` |
| Engine checkout | `683c05928b8a40274b787b4942fe4f2683d085c4` |
| Scope | All 1,728 constructed primary-development cases; same prompts/settings as the small-model plans apart from request model |
| Source inventory | 1,754 rows / 140 groups; 26 construction blocks remain unscored |
| GPU / format | NVIDIA L4; float16; pinned AWQ 4-bit checkpoint |
| Attempt accounting | 1,728 durable intents and saved HTTP responses; one finished session; no resumed visits or unfinished sessions |
| Evidence statuses | 1,558 complete; 128 invalid evidence; 42 truncated |
| Whole-output / meaningful-token eligibility | 1,558 / 631 |
| Generation session wall time | 8,214.175516429 seconds, approximately 2 h 16 min 54 s |
| Sum of saved request elapsed time | 8,184.334868880017 seconds |
| Usage | 1,948,503 prompt tokens; 194,553 completion tokens; 2,143,056 total; no missing usage fields |
| Context / completion | All-request tokenizer preflight records no overflow; generation/replay finished; server shutdown recorded |

Requested temperature remains 0.001. The installed constructor records an
effective temperature of 0.01, with its existing local-constructor rather than
independent per-request server-observation limitation. Settings and probabilities
are not renamed or rewritten. Generation session time excludes setup/model
loading; it is not billed GPU time or measured online cascade latency. Remaining
provider quota was not measured.

Archive: `uqroute_qwen14b_awq_full_development_e21e0f54.zip`.

SHA-256: `190bd8db0ec9884bd136fcf03f6b3ef414e4683b894571fc973f42c097211a23`.

Prepared manifest SHA-256:
`a282281b6370b6c029135e933314a2104bbbdc5ba998f12e1db622c6fc9ee887`.

Execution-source SHA-256:
`1d343f7e229773a728bac44619fcd4c644d94bd636ccddd8b42bd6e7d2dc649c`.

The ZIP contains 6,943 files, including an inventory that fingerprints 6,942
evidence members. The notebook-attested outer ZIP hash, every member hash,
approved plan, runtime/launch/log bindings, preflight and shutdown records were
verified. An independent CPU replay reproduced the **full exported records and
summary, including outcome-file hashes**. Repeated import/replay verifies prior
bytes and preserves existing outputs. Hashes establish local consistency, not
authenticated provenance of the loaded weights or dataset.

## Correctness is measured separately from evidence status

Complete/invalid/truncated are evidence statuses, not official correctness
labels. All 1,728 generated texts are scored as saved. The 170 outputs
without whole-output uncertainty are retained in correctness denominators;
there are no repairs, replacement generations, retries, automatic zero labels
or exclusions based on reference-review flags.

The owner subsequently ran the CPU command successfully at `6962586` and
provided its full terminal scoring summary on 2026-11-11 UTC. All 64 import/scoring
tests passed (one Windows skip), and all 34 frozen generation checks passed.
The command verified the archive/member/runtime bindings and full replay before
scoring the preserved owner reference/audit inputs. The raw scoring sidecars
remain on the owner checkout; this working checkout independently verified
archive/replay and records the official results from the supplied terminal output.
Synthetic tests are not the source of these model results.

| Endpoint | Correct / rows | Fraction |
|---|---:|---:|
| Reference compliance | 787 / 1,512 | 52.05% |
| APIBank reference compliance | 483 / 826 | 58.47% |
| BFCL reference compliance | 149 / 182 | 81.87% |
| RoTBench reference compliance | 58 / 253 | 22.92% |
| ToolAlpaca reference compliance | 97 / 251 | 38.65% |
| ToolEyes relevance, separate | 208 / 216 | 96.30% |

Reference whole-output / meaningful-token eligibility is 1,342 / 415; ToolEyes
eligibility is 216 / 216. All 128 invalid-evidence and 42 truncated outputs occur
in APIBank and remain in its reference denominator. The 802 flagged reference
rows remain scored without relabeling or exclusion. Qwen 7B has 790/1,512
reference matches and 204/216 ToolEyes matches, so the aggregate fallback results
do not establish uniform improvement or reveal individual rescues/harms.
The quantized 14B and unquantized small-model configurations also differ in
more than parameter count.

Only aggregate results are recorded here. Detailed case identifiers and the
owner scoring sidecars are not published by this update.

The new scorer is a separate version of the reviewed full-development scoring
adapter, with the new archive, file inventory, fallback model, manifest and
policy fingerprints. All existing small-model scorers, policies, references and
outputs are unchanged. It reparses original raw text using the pinned official
parser, retaining Python value/type distinctions rather than scoring the JSON
view of parsed calls. The same released-reference scorer dispatch and reference
diagnostics are preserved. ToolEyes name relevance stays separate from reference
compliance; cost/latency preference and executable task success are not measured.

## Run the CPU subtask on the owner's checkout

Download the completed ZIP from the existing `UQRoute_TC/fallback_outputs` Drive
folder into the normal Downloads directory, retaining its filename. Then run:

```bash
python tools/development_audits/fallback_full_development_scoring_v1/run_cpu.py
```

Use `--archive /path/to/uqroute_qwen14b_awq_full_development_e21e0f54.zip` if
stored elsewhere. No Colab GPU is required for this step.

The command runs synthetic CPU tests and the frozen generation regression
suite, verifies the bound ZIP/file inventory/runtime, imports without overwrite,
replays the full run and checks exported records/summary before scoring. Scoring
requires these existing, unchanged inputs:

- `artifacts/local_development_audits/full_primary_export_v1/attestation.json`
- `artifacts/local_development_audits/full_primary_export_v1/membership.json`
- `artifacts/local_development_audits/full_primary_export_v1/references.jsonl`
- `artifacts/local_development_audits/full_primary_audit_v1/inventory.json`

The attestation is pinned before the reference sidecar is opened. Membership,
reference lineage and the 1,754-row inventory are checked; held-out and unknown
groups cannot be substituted. The new plan is checked against all 1,728
construction candidates, including 140 clean rows and 1,588 perturbations.
The 26 blocked rows receive no imputed score. Missing or different inputs cause
a stop; preserve them rather than regenerating or bypassing their hashes.

Fresh ignored outputs:

- `corrected_qwen14b_awq_full_development_import_e21e0f54/`
- `corrected_qwen14b_awq_full_development_local_replay_v1/`
- `corrected_qwen14b_awq_full_development_official_scoring_v1/`

All are beneath `artifacts/local_development_audits/`. Imported evidence and
replay outputs can be reverified. An existing scoring output is preserved and
rejected rather than overwritten. `--replay-only` verifies/imports/replays
without reading reference sidecars or claiming correctness scores.

The command does not infer, retry model requests, change labels, stage, commit
or push Git changes. It opens no raw benchmark or split records.

### Windows ZIP-name regression

The owner's first Windows run stopped in the synthetic import tests, before
processing the real evidence. Python normalized the fixture's backslash when
constructing its ZIP name. The fixture now preserves the original header name,
and import validates `ZipInfo.orig_filename` before accepting Python's sanitized
filename. Backslash and null-byte aliases are rejected on both platforms.
Tests explicitly exercise Windows separator normalization and valid forward-slash
names. The approved archive, fingerprints, scoring rules and saved GPU outputs
are unchanged; rerun the same CPU command after pulling this correction.

## Subsequent routing work

The reference-scoring output is now reviewed. The next CPU command joins fallback and each
small-model result by qualified case key, lineage, original prompt fingerprint,
panel and development membership. Preserve unavailable probability evidence and
all outcome statuses. Then measure rescues and harms, compare baselines and
threshold frontiers, and select an operating point under a recorded grouped
development objective. The fallback's size alone does not establish better
outcomes or justify extra cost. Held-out access remains disabled until the final
shared protocol freeze.

The [paired-routing development command](PAIRED_ROUTING_DEVELOPMENT_V1.md)
implements this evidence-bound join and fixed diagnostic frontiers. Its actual
owner execution and grouped threshold selection remain pending.
