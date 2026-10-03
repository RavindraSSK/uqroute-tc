# Colab development pilots

The model pilot notebooks run five clean **development** BFCL cases from the pinned RobustBench-TC release. The first format audit runs four additional clean development cases, one per remaining benchmark. The APIBank/ToolAlpaca audit selects 12 further development cases from each of those two benchmarks. They save manifests, per-case responses, token evidence, and scorer output under `MyDrive/UQRoute-TC/pilots/`. The generated records stay in Drive; no model output or Hugging Face token is committed here.

| Notebook | Role |
|---|---|
| `UQRoute_TC_Qwen15B_Development_Pilot.ipynb` | Small-model pilot (Qwen 1.5B) |
| `UQRoute_TC_Llama3B_Development_Pilot.ipynb` | Small-model pilot (Llama 3B); validates or recovers saved responses containing the Llama end token and backs up the originals |
| `UQRoute_TC_Qwen7B_Development_Pilot.ipynb` | Small-model pilot (Qwen 7B) |
| `UQRoute_TC_Qwen14B_AWQ_Fallback_Feasibility.ipynb` | Larger fallback serving and evidence feasibility check |
| `UQRoute_TC_Four_Model_Pilot_Audit.ipynb` | CPU-only audit of the four saved five-case pilots and official case scores |
| `UQRoute_TC_Task2_Saved_Pilot_Audit.ipynb` | CPU-only Task 2 reparse and token-evidence check of the 20 saved records |
| `UQRoute_TC_Qwen15B_Format_Development_Audit.ipynb` | Four clean development cases across APIBank, RotBench, ToolAlpaca, and ToolEyes; saved parser audit and official per-case scores |
| `UQRoute_TC_Qwen15B_XML_JSON_Development_Audit.ipynb` | Up to 24 additional clean development cases across APIBank and ToolAlpaca; parser audit and selected token-evidence export |
| `UQRoute_TC_Qwen15B_Repeated_Sample_Development_Check.ipynb` | Ten seeded requests on one selected clean development BFCL case; saved response and clustering check before the full repeated subset |
| `UQRoute_TC_Qwen15B_Repeated_Development_Subset.ipynb` | Ten seeded requests per case for Qwen 1.5B on the 30-case development subset, with resumable saving and a compact cluster audit |
| `UQRoute_TC_Qwen15B_Repeated_Status_Audit.ipynb` | CPU-only audit of the saved 30-case run; includes truncated and request-error slots explicitly in the canonical clusters |
| `UQRoute_TC_Llama3B_Repeated_Development_Subset.ipynb` | Ten seeded Llama 3B generations per selected development case; resumable records and a status-aware audit of all ten slots |
| `UQRoute_TC_Qwen7B_Repeated_Development_Subset.ipynb` | Ten seeded Qwen 7B generations per selected development case; resumable records and a status-aware audit of all ten slots |

Run one model notebook at a time. Each notebook pins its benchmark and pilot-code revisions, and the saved manifest records the run settings. Llama inference reads `HF_TOKEN` from Colab Secrets. The notebooks are development checks, not full benchmark reproductions or held-out evaluations.

The earlier Llama pilot notebook is superseded by the fixed notebook here. The four-model audit completed on the saved artifacts; its compact, user-reported five-case score table is in `docs/evidence/`.
