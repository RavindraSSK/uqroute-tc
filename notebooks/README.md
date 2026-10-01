# Colab development pilots

These notebooks run five clean **development** cases from the pinned RobustBench-TC release. They save manifests, per-case responses, token evidence, and scorer output under `MyDrive/UQRoute-TC/pilots/`. The generated records stay in Drive; no model output or Hugging Face token is committed here.

| Notebook | Role |
|---|---|
| `UQRoute_TC_Qwen15B_Development_Pilot.ipynb` | Small-model pilot (Qwen 1.5B) |
| `UQRoute_TC_Llama3B_Development_Pilot.ipynb` | Small-model pilot (Llama 3B); validates or recovers saved responses containing the Llama end token and backs up the originals |
| `UQRoute_TC_Qwen7B_Development_Pilot.ipynb` | Small-model pilot (Qwen 7B) |
| `UQRoute_TC_Qwen14B_AWQ_Fallback_Feasibility.ipynb` | Larger fallback serving and evidence feasibility check |
| `UQRoute_TC_Four_Model_Pilot_Audit.ipynb` | CPU-only audit of the four saved five-case pilots and official case scores |
| `UQRoute_TC_Task2_Saved_Pilot_Audit.ipynb` | CPU-only Task 2 reparse and token-evidence check of the 20 saved records |

Run one model notebook at a time. Each notebook pins its benchmark and pilot-code revisions, and the saved manifest records the run settings. The Llama notebook reads `HF_TOKEN` from Colab Secrets only if new inference is necessary. The notebooks are pilot checks, not full benchmark reproductions or held-out evaluations.

The earlier Llama pilot notebook is superseded by the fixed notebook here. The four-model audit completed on the saved artifacts; its compact, user-reported five-case score table is in `docs/evidence/`.
