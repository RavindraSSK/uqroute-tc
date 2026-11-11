# CPU recovery context preflight v1

The owner completed preparation at `f2bbb44`. The supplied terminal output
reports 140 clean development anchors and 840 scenario slots per small model:

| Initial small model | Pending eligible episodes | Terminal no injection | Potential small / fallback contexts | Maximum new calls if both roles dispatched |
|---|---:|---:|---:|---:|
| Qwen 1.5B | 750 | 90 | 750 / 750 | 1,500 |
| Llama 3B | 828 | 12 | 828 / 828 | 1,656 |
| Qwen 7B | 834 | 6 | 834 / 834 | 1,668 |
| Total | 2,412 | 108 | 2,412 / 2,412 | 4,824 |

All terminal no-injection plans have reason `initial_no_official_call`. They
remain separate from future injected-case RQ3 denominators. These are owner
preparation counts, not independently recomputed counts in this checkout or
observed recovery outcomes. All 52 owner checks passed. No model requests or
observed injections occurred, and no reference scoring was performed. Original
generation/preparation sources and evidence remain unchanged.

## Run on CPU

Use Python 3.10–3.13 and the tokenizer runtime recorded by the existing corrected
generation notebooks. From the updated repository root:

```bash
python -m pip install "transformers==5.20.2"
python tools/development_audits/recovery_context_preflight_v1/preflight.py
```

The Llama tokenizer requires your existing authorized Hugging Face access
(cached login or `HF_TOKEN` in your local environment). Do not paste tokens into
chat, commit them or add them to reports. The command downloads tokenizer/config
assets when absent; it does not load model weights or start a model server.
Prepared messages are rendered locally, not sent as model requests.
`--local-files-only` restricts loading to cached pinned assets.

The command first runs synthetic checks without downloads. It verifies all three
owner-reported ZIP and manifest fingerprints, exact payload inventories, frozen
model/server/request settings, primary-development membership, six scenarios per
group, pending versus terminal dispositions, both complete role inventories and
message/request identity bindings before loading tokenizers. The ZIP pins are
copied from the supplied owner summary; they are not an independent rerun of
preparation provenance. It reads the prepared transfer archives and frozen Task 1
configuration, not raw benchmark data, reference sidecars, outcome scores or test
groups. The original preparer must not be rerun over its occupied output.

Each of the 4,824 potential request contexts is rendered with its own model's
exact tokenizer revision, default chat template and `add_generation_prompt=True`.
The full requested 1,024-token completion allowance must fit within the frozen
8,192-token server limit. Shared fallback instances use the pinned AWQ model's
tokenizer, while all three initial-model histories remain distinct. All contexts
are counted, including overflows; no trimming, selection or silent dropping occurs.

Fresh ignored output is
`artifacts/local_development_audits/recovery_context_preflight_v1/`:

- `summary.json`: six role summaries, token ranges, overflow counts and scope flags.
- `report.json`: per-request token counts and identity bindings, input/source pins,
  tokenizer/backend/template fingerprints and package versions.

An occupied output is rejected. Input ZIPs are rehashed before publication.
If any context overflows, reports are saved and the command exits unsuccessfully;
review the frozen configuration conflict before dispatch. A missing dependency,
gated-tokenizer access failure or integrity mismatch also stops the check, without
generation or changes to the prepared plans. Keep detailed reports private with
the existing ignored artifacts; only aggregate results belong in public progress.

## Remaining boundary

Passing this check establishes tokenizer rendering feasibility only. Server-side
tokenization/runtime validation, GPU memory and quota feasibility, durable unique
stage intents, actual injection/attempt records, response replay, recovery policy
baselines, full cost accounting and scoring dispositions remain pending. There
is no selected recovery threshold or final operating objective. All dispatch,
held-out access and main-experiment readiness flags remain false.

The 19 synthetic checks exercise archive/JSON integrity, population and stage
coverage, frozen settings, injection partitions, exact context boundaries,
overflow preservation, invalid token IDs and all four distinct tokenizer roles.
A synthetic complete-run test publishes both reports using fake tokenizers and
the existing publication helper, verifies preserved inputs and rejects a second
write. These tests do not establish actual tokenizer counts or context fit.

## Nonstreaming request compatibility correction

The owner attempted preflight at `1908f8f`. All 17 then-current synthetic checks
passed, but real-plan validation stopped at `Role request/context binding differs`
before actual tokenizer loading or report publication. The corrected-generation
producer includes explicit `stream: false`, and recovery preparation preserves
that body field. The first preflight expected-body dictionary omitted it, so
its exact comparison rejected valid prepared requests. This was a validator
compatibility bug, not evidence of altered owner plans or a context overflow.

The expected body now requires `stream: false`. Synthetic fixtures now use the
production `workflow.make_requests` and `prepare.episode` constructors with the
released fault templates, replacing the manually duplicated request schema.
Regression checks cover both model roles and reject a missing field or
`stream: true` even after recomputing the body hash. All 19 context checks and
52 existing preparation/controller/routing checks pass. The original archive pins,
prepared payloads, request hashes and all authorization flags are unchanged.
Rerun only the preflight command after pulling the correction; Transformers is
already installed. Actual owner token counts, context fit and runtime feasibility
remain pending.
