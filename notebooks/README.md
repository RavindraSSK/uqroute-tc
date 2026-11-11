# Colab development pilots

The model pilot notebooks run five clean **development** BFCL cases from the pinned RobustBench-TC release. The first format audit runs four additional clean development cases, one per remaining benchmark. The APIBank/ToolAlpaca audit selects 12 further development cases from each of those two benchmarks. They save manifests, per-case responses, token evidence, and scorer output under `MyDrive/UQRoute-TC/pilots/`. The generated records stay in Drive; no model output or Hugging Face token is committed here.

| Notebook | Role |
|---|---|
| `UQRoute_TC_Task3_Four_Model_Official_Scoring.ipynb` | CPU-only pinned loader/parser/scorer for all 276 audited saved responses; source-file-qualified identities, response statuses and uncertainty eligibility retained separately |
| `UQRoute_TC_Task3_Four_Model_Record_Audit.ipynb` | CPU-only replay of 276 saved development attempts; frozen token evidence, status/usage reconciliation and eligible whole-output score export |
| `UQRoute_TC_Task3_Qwen14B_AWQ_Throughput.ipynb` | Pinned 14B AWQ fallback L4 timing diagnostic on the same development selection; no routing-effectiveness claim |
| `UQRoute_TC_Task3_Llama3B_Throughput.ipynb` | Pinned Llama 3B L4 throughput diagnostic; separate model/output guards and session accounting |
| `UQRoute_TC_Llama3B_Saved_Throughput_Audit.ipynb` | CPU-only saved-attempt audit/export; full truncated records reviewed separately |
| `UQRoute_TC_Task3_Qwen7B_Throughput.ipynb` | Pinned Qwen 7B L4 throughput diagnostic on the same 69 development cases; records server temperature-clamp observations |
| `UQRoute_TC_Qwen15B_Development_Pilot.ipynb` | Small-model pilot (Qwen 1.5B) |
| `UQRoute_TC_Llama3B_Development_Pilot.ipynb` | Small-model pilot (Llama 3B); validates or recovers saved responses containing the Llama end token and backs up the originals |
| `UQRoute_TC_Qwen7B_Development_Pilot.ipynb` | Small-model pilot (Qwen 7B) |
| `UQRoute_TC_Qwen14B_AWQ_Fallback_Feasibility.ipynb` | Larger fallback serving and evidence feasibility check |
| `UQRoute_TC_Four_Model_Pilot_Audit.ipynb` | CPU-only audit of the four saved five-case pilots and official case scores |
| `UQRoute_TC_Task2_Saved_Pilot_Audit.ipynb` | CPU-only Task 2 reparse and token-evidence check of the 20 saved records |
| `UQRoute_TC_Qwen15B_Format_Development_Audit.ipynb` | Four clean development cases across APIBank, RotBench, ToolAlpaca, and ToolEyes; saved parser audit and official per-case scores |
| `UQRoute_TC_Qwen15B_XML_JSON_Development_Audit.ipynb` | Up to 24 additional clean development cases across APIBank and ToolAlpaca; parser audit and selected token-evidence export |
| `UQRoute_TC_APIBank_Markup_Alignment_Export.ipynb` | CPU-only export of two saved APIBank development responses with `<tool>` or `<toolcall>` markup and chosen-token evidence |
| `UQRoute_TC_Qwen15B_Saved_Alignment_Coverage.ipynb` | CPU-only alignment eligibility audit of all 24 saved APIBank and ToolAlpaca development responses; exports a compact per-case report without model generation |
| `UQRoute_TC_Qwen15B_Saved_Alignment_Reaudit.ipynb` | CPU-only re-audit of the same 24 saved responses using the expanded APIBank rule; compares eligibility and score stability with the original audit and saves a separate v2 report |
| `UQRoute_TC_APIBank_Remaining_Alignment_Export.ipynb` | CPU-only export of two saved APIBank development responses whose parsed calls remain outside the bounded alignment rule; preserves full chosen-token evidence for review |
| `UQRoute_TC_Qwen15B_Repeated_Sample_Development_Check.ipynb` | Ten seeded requests on one selected clean development BFCL case; saved response and clustering check before the full repeated subset |
| `UQRoute_TC_Qwen15B_Repeated_Development_Subset.ipynb` | Ten seeded requests per case for Qwen 1.5B on the 30-case development subset, with resumable saving and a compact cluster audit |
| `UQRoute_TC_Qwen15B_Repeated_Status_Audit.ipynb` | CPU-only audit of the saved 30-case run; includes truncated and request-error slots explicitly in the canonical clusters |
| `UQRoute_TC_Llama3B_Repeated_Development_Subset.ipynb` | Ten seeded Llama 3B generations per selected development case; resumable records and a status-aware audit of all ten slots |
| `UQRoute_TC_Qwen7B_Repeated_Development_Subset.ipynb` | Ten seeded Qwen 7B generations per selected development case; resumable records and a status-aware audit of all ten slots |

Run one model notebook at a time. Each notebook pins its benchmark and pilot-code revisions, and the saved manifest records the run settings. Llama inference reads `HF_TOKEN` from Colab Secrets. The notebooks are development checks, not full benchmark reproductions or held-out evaluations.

The earlier Llama pilot notebook is superseded by the fixed notebook here. The four-model audit completed on the saved artifacts; its compact, user-reported five-case score table is in `docs/evidence/`.

## Corrected development experiments

The following notebooks reproduce the later corrected-prompt development
experiments. Completed evidence should be analyzed from saved archives rather
than regenerated. Their engine revisions and approved input hashes remain
pinned; these are not held-out evaluation notebooks.

| Notebook | Role |
|---|---|
| `UQRoute_TC_Qwen15B_Corrected_Repeated_v1.ipynb` | Corrected Qwen 1.5B 30-case / 300-slot development study; verified upload reuse repaired |
| `UQRoute_TC_Llama3B_Corrected_Repeated_v1.ipynb` | Corrected Llama 3B 30-case / 300-slot study; authorized HF token read from environment/Colab Secrets |
| `UQRoute_TC_Qwen7B_Corrected_Repeated_v1.ipynb` | Corrected Qwen 7B 30-case / 300-slot study with separate evidence identity |
| `UQRoute_TC_Sensitivity_Development_Three_Models_v1.ipynb` | Three models on 35 sensitivity-only BFCL development cases each; upload-based input |
| `UQRoute_TC_Sensitivity_Development_Google_Drive_v1.ipynb` | Same sensitivity runner with approved inputs and completed exports persisted through Google Drive |

See [CPU reproduction and recovery instructions](../docs/research_track_v1/DEVELOPMENT_RESULTS_REPRODUCTION_V1.md).
The Drive variant uses `MyDrive/UQRoute_TC/sensitivity_inputs` and
`sensitivity_outputs`; the earlier pilots above use the distinct `UQRoute-TC`
folder. Existing saved evidence blocks redispatch. Export to Drive is not a
continuous backup before a run finishes.

## Recovery resource smoke: Qwen 1.5B on L4

`UQRoute_TC_Qwen15B_Recovery_Resource_Smoke_v1.ipynb` runs the fingerprint-bound
30-request development small-stage smoke after completed owner staging and all
4,824 context checks. Select L4, upload the existing smoke-preparation INPUT ZIP,
record the current quota note, execute once, then download the OUTPUT evidence ZIP
and delete the GPU runtime. It preserves unknown slots, performs no fallback or
reference scoring, and exports frozen parser/token replay plus partial evidence.
See [execution scope](../docs/research_track_v1/RECOVERY_GPU_SMOKE_V1.md).
The owner completed this smoke; all 30 responses independently replay exactly.
Owner local import is also complete. Do not rerun the completed batch; use the
[CPU smoke reference diagnostic](../docs/research_track_v1/RECOVERY_SMOKE_REFERENCE_SCORING_V1.md)
next. Reference matches remain pending; semantic/execution recovery is unmeasured.
