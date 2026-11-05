# Corrected repeated and sensitivity development reproduction

Run CPU commands from the repository root. These entry points preserve the
exact delivered analysis sources and evidence pins. They require the original
ignored local development artifacts, including development reference sidecars;
a Git checkout alone does not contain the private/local evidence payloads.
Existing outputs are verified or rejected, never overwritten to force a rerun.
Do not delete outputs or alter hashes to bypass a refusal.

## Corrected repeated sampling

Run in model order: the Qwen 7B comparison verifies the earlier two result
directories and the exact analysis sources saved with them.

```bash
python tools/development_audits/corrected_repeated_results_v1/import_qwen15b_corrected_repeated_v1.py /path/to/uqroute_qwen15b_corrected_repeated_6e710e52.zip
python tools/development_audits/corrected_repeated_results_v1/run_qwen15b_corrected_repeated_analysis_v1.py
python tools/development_audits/corrected_repeated_results_v1/run_llama3b_corrected_repeated_analysis_v1.py /path/to/uqroute_llama3b_corrected_repeated_91340333.zip
python tools/development_audits/corrected_repeated_results_v1/run_qwen7b_corrected_repeated_analysis_v1.py /path/to/uqroute_qwen7b_corrected_repeated_de99cdcc.zip
```

Qwen 1.5B import is a one-time step; if already imported, retain the verified
import/replay directories and start with analysis only when its output does
not already exist. Llama and Qwen 7B verify or import their exact evidence
archives. The analysis scripts use each model's saved full-development single
responses, pinned reference inputs, frozen canonical clustering and the
existing metrics implementation. They do not send generation requests.
Qwen 7B writes `THREE_MODEL_REPORT.md` and `three_model_comparison.json` inside
`artifacts/local_development_audits/qwen7b_corrected_repeated_analysis_v1/`.

## Sensitivity development

Audit and preparation are one-time prerequisites, already completed for the
reported runs. They use a local checkout of the pinned benchmark and export
only sensitivity-only development content. Top-level metadata is scanned to
select membership; unselected nested payloads are not decoded. No new held-out
export or evaluation is authorized by these commands.

```bash
python tools/development_audits/sensitivity_development_v1/run_sensitivity_development_audit_v1.py --benchmark-root /path/to/pinned/robustbench-tc-release
python tools/development_audits/sensitivity_development_v1/prepare_sensitivity_small_models_v1.py
python tools/development_audits/sensitivity_development_v1/run_sensitivity_results_v1.py /path/to/uqroute_sensitivity_development_evidence_b5718d0f.zip
```

The audit/preparation retain their original source and input pins. ZIP bytes
can vary with platform serialization or container metadata; the notebooks
require the exact approved original transfer bytes. A regenerated package
must not be substituted by merely changing its expected hash. Preparation
authorizes no dispatch. Scoring requires the preserved 35-row audit/export and
verifies the outer archive, three inner archives, 168 evidence-file hashes per
model, runtime bindings, frozen local replay records/summary and references.
It reparses original saved response text for official scoring and keeps
reference-review flags separate from official outcomes.

## Colab notebooks

The three `UQRoute_TC_*_Corrected_Repeated_v1.ipynb` notebooks and two
`UQRoute_TC_Sensitivity_Development_*_v1.ipynb` notebooks in `notebooks/`
preserve the runners used for these development experiments. They pin the
reviewed generation-engine checkout and model/tokenizer revisions; committing
them at a later revision does not update the engine automatically.

The sensitivity Google Drive notebook reads approved transfers from
`MyDrive/UQRoute_TC/sensitivity_inputs` and persists completed exports under
`MyDrive/UQRoute_TC/sensitivity_outputs`. It does not require the upload picker.
An existing saved model archive blocks generation in a fresh runtime. A run
interrupted before export still requires preserving/recovering its original
runtime; Drive export is not a continuous backup of every request intent.

These are reproduction entry points, not an instruction to regenerate completed
responses. Existing durable request intents occupy their slots, including
unknown outcomes; there are no automatic retries. Llama access uses the user's
authorized `HF_TOKEN` environment/Colab secret, never committed credentials.

The Qwen 1.5B repeated notebook includes one upload-only repair: when Colab has
already saved the approved bytes at the canonical input filename, it reuses
the file after verifying its hash. Different existing bytes are preserved and
rejected. Embedded generation/client sources and sampling settings are unchanged.

## Offline checks

```bash
python -m unittest discover -s tools/development_audits/corrected_repeated_results_v1 -p 'test_*.py'
python -m unittest discover -s tools/development_audits/sensitivity_development_v1 -p 'test_*.py'
```

Synthetic checks cover cohort identity, model-specific labels, one-class
metrics, missingness, unsafe archive members, retained reference flags,
notebook syntax/embedded source, and upload recovery. They neither access
benchmark records nor generate model responses. Existing frozen engine and
metric suites remain separate regression checks.
