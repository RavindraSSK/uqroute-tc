# UQRoute-TC Evaluation Protocol

## Protocol status

This document is the draft evaluation protocol for the UQRoute-TC capstone. It will be frozen before held-out evaluation begins.

Any later change must record:

- What changed.
- Why it changed.
- Whether model results had already been inspected.

Git history will preserve all protocol revisions.

## 1. Project objective

UQRoute-TC studies whether uncertainty calculated from a small language model's generated tool call can identify requests that should be escalated to a larger fallback model.

The project evaluates this behavior under clean inputs and deployment perturbations. It measures whether uncertainty remains useful for detecting incorrect tool calls and whether an uncertainty-gated cascade can improve the trade-off between task success and inference cost.

The language models remain frozen. This project does not train or fine-tune a routing classifier.

## 2. Research questions

### RQ1 — Uncertainty reliability

How well do single-sample and repeated-sample uncertainty measures distinguish correct tool calls from incorrect tool calls under clean and perturbed conditions?

### RQ2 — Uncertainty-gated routing

Can an uncertainty-gated cascade preserve task success while reducing inference cost relative to the submitted comparison policies?

### RQ3 — Post-fault recovery

After a tool-execution fault is observed, can a bounded uncertainty-gated recovery policy improve task success enough to justify its additional cost?

## 3. Benchmark provenance

The evaluation data comes from the official RobustBench-TC release:

- Repository: `https://github.com/WillChow66/robustbench-tc-release`
- Pinned revision: `d5d03180de41eb30a6c796d04a9bfbd9dad85c1d`
- Evaluation directory: `hf_data/datasets/api_eval`

The local benchmark clone is an external dependency and is not copied into this repository. The dataset revision is recorded in every audit and experiment manifest.

## 4. Audited evaluation population

The released evaluation directory was audited using `src/uqroute_tc/data/audit.py`. At the pinned revision, the audit reports:

| Population | Rows | Base-task groups |
|---|---:|---:|
| Stored static records | 2,718 | Not applicable |
| Excluded multi-turn records | 191 | Not part of the static study |
| All retained single-turn records | 2,527 | 248 |
| Clean-anchored primary candidate | 2,477 | 199 |
| Perturbation-only records | 50 | 49 |
| Runtime-generated Transition predictions | 1,194 | 199 |

The benchmark README describes 3,721 predictions per model in total, not 3,721 stored dataset rows. At the pinned revision, 2,718 records are stored in the static JSONL files. After excluding 191 multi-turn rows, 2,527 static single-turn records remain; the runtime-generated Transition population adds 1,194 predictions, so `2,527 + 1,194 = 3,721`. Adding the runtime predictions to all stored rows would instead give 3,912 because that sum includes the 191 excluded multi-turn rows.

The proposed primary population is the clean-anchored population containing 2,477 rows from 199 base-task groups. It preserves the clean-task universe and its recognized perturbation variants.

The complete single-turn population containing 2,527 rows from 248 groups will be retained as a sensitivity population. It adds 50 perturbation-only rows from 49 groups that do not have clean counterparts in the released `clean.jsonl` file.


The clean-anchored population is the primary population, and the complete single-turn population is the sensitivity population. Any later population change must be supported by a documented audit or feasibility finding and recorded in the protocol change log.

## 5. Base-task identity

Each JSONL record is an evaluation case. Related cases are connected through a canonical base-task identifier.

The identity rules are:

1. If a row identifier exactly matches an identifier in `clean.jsonl`, that clean identifier is used as its base-task identifier.
2. Recognized BFCL same-name identifiers are normalized to their corresponding clean-style identifier.
3. Recognized same-name cases without a clean counterpart receive a stable normalized identifier and are labelled `perturbation_only`.
4. Unknown identifier patterns cause the audit to fail. The system does not silently invent an identifier or silently fall back to another field.
5. `source.original_id` is not used alone as the group key because released benchmark sources reuse those values across unrelated tasks.

The implementation is in `src/uqroute_tc/data/identity.py`. Unit tests cover exact clean identifiers, same-name normalization, perturbation-only identifiers, unknown patterns, and multi-turn classification.

## 6. Multi-turn exclusion

Rows whose `category` contains `multi_turn` are excluded from the static single-turn population.

The audit confirmed that category, row-identifier, and source-identifier indicators agree for all 191 excluded rows.

Stateful transition-recovery experiments will be conducted and reported separately. They will not be mixed with static single-turn results.

## 7. Partitioning and leakage prevention

Partitioning will occur at the canonical base-task level, not at the individual-row level.

All clean, paraphrased, perturbed, and same-name variants belonging to a base task must remain in the same partition.

The planned primary population will be divided into:

- Development groups used for engineering checks, uncertainty-method selection, calibration, and routing-threshold selection.
- Held-out test groups used only after the parser, metrics, routing policies, and thresholds are frozen.

The exact split ratio, deterministic seed, and benchmark-stratification procedure will be implemented, validated, and recorded before model-result analysis begins.

The pinned runner generates Transition cases only from `clean.jsonl`. The 49 sensitivity-population groups without a clean source row cannot receive Transition cases. RQ3 is therefore scoped to the clean-anchored population of 199 base-task groups; the full 248-group population is not an RQ3 population.

Additional leakage controls are:

- Ground-truth calls may be used by the scorer but never by the router.
- Held-out correctness labels must not influence threshold selection.
- Test results must not be used to choose uncertainty measures.
- Related variants must remain together during confidence-interval resampling.
- Any post-freeze protocol change must be documented.


## 8. Model roles and revisions

The planned principal small models are:

- `Qwen/Qwen2.5-1.5B-Instruct`
- `meta-llama/Llama-3.2-3B-Instruct`
- `Qwen/Qwen2.5-7B-Instruct`

The planned fallback model is:

- `Qwen/Qwen2.5-14B-Instruct-AWQ`

These models have fixed roles in the study. The three principal models produce the initial tool call, and the 14B model is the escalation target. Model weights remain frozen; UQRoute does not fine-tune them.

Before main inference begins, each model's exact model revision, tokenizer revision, quantization method, numerical dtype, chat template, inference-engine version, and license/access status must be recorded in an experiment manifest.

If a planned model cannot run within the available hardware or access constraints, the pilot report must document the failure and the resulting scope decision before the main study begins.

## 9. Reference runner and UQRoute extensions

The pinned RobustBench-TC `scripts/run_eval.py` remains the reference for sample loading, benchmark-specific message construction, multi-turn exclusion, transition injection, output parsing, and compatibility with the released scorer.

At the pinned revision, the reference runner:

- Uses an OpenAI-compatible endpoint, normally served by vLLM.
- Uses prompt-based tool calling by default rather than native `tools=[...]` function calling.
- Uses a default temperature of `0.001` and a default maximum completion length of 1,024 tokens.
- Runs one request per case in static mode.
- Runs an initial request followed by a fault-conditioned request in transition mode.
- Records `prediction.transition_injected` as `false` when pass one errors or produces no tool call, and as `true` when a fault-conditioned second pass is attempted.
- Mirrors the injection-status value in `perturbation.metadata.pass1_had_tool_calls`; transition-mode records retain `perturbation.mdp_category` as `transition` even when no fault was injected.
- Saves raw output, parsed tool calls, and errors.
- Supports file selection, case limits, checkpoint-style output, and resume by row identifier.

UQRoute will preserve the benchmark's message-building and scoring semantics while extending the inference record with:

- Canonical base-task identifier and population label.
- Model and tokenizer identifiers and revisions.
- Complete generation configuration.
- Chosen-token log-probabilities and returned token-byte information.
- Log-probability availability and alignment status.
- Prompt-token and completion-token counts when available.
- Per-request latency and total run time.
- Finish reason, parsing status, retry count, and error details.
- Raw output and parsed tool calls.
- Dataset revision and UQRoute code revision.

When log-probabilities are required by an experiment, a missing or malformed log-probability response must cause an explicit failure instead of silently producing a partial uncertainty score.

Output writing must remain resumable. Re-running a completed batch must not duplicate successful records, and every record must retain enough configuration information to identify the run that produced it.

## 10. Generation protocols

### 10.1 Single-sample protocol

The primary single-sample study will use near-deterministic decoding consistent with the reference runner. The initial candidate setting is temperature `0.001` with a maximum completion length of 1,024 tokens.

The smoke test and feasibility pilot will verify model compatibility, output truncation, log-probability capture, byte alignment, memory use, and throughput. The final decoding settings will be frozen before main inference and recorded in the experiment manifest.

Prompt-based tool calling is the primary protocol. Native function calling is not part of the primary comparison unless it is separately predeclared as an ablation, because it changes both the output channel and the availability of token-level evidence.

### 10.2 Repeated-sample protocol

Repeated-sample uncertainty will use ten generations per selected case. The sampling temperature, nucleus-sampling value, seed procedure, and subset size will be fixed before repeated-sample results are inspected.

Each generated output will be parsed and converted to a canonical tool-call representation. Canonical-call frequencies will be used to calculate disagreement and entropy. Exact-string clustering will be retained as an ablation.

The repeated-sample subset and the claims supported by it must be stated explicitly. Results from a subset will not be presented as if every benchmark case received ten samples.

### 10.3 Invalid and incomplete generations

Parsing failures, missing log-probabilities, truncated completions, request errors, and empty outputs are explicit recorded outcomes. They must not be silently removed from denominators.


## 11. Uncertainty measures

All uncertainty scores are oriented so that a larger value means greater uncertainty.

For a generated sequence containing tokens indexed by `i = 1, ..., L`, let `log p_i` be the model-returned log-probability of the selected token.

The planned single-sample measures are:

- Sequence negative log-likelihood: `-sum(log p_i)`.
- Mean token negative log-likelihood: `-sum(log p_i) / L`.
- Maximum token surprisal: `max(-log p_i)`.
- Meaningful-token negative log-likelihood: the mean negative log-likelihood over aligned tokens representing tool names, argument names, and argument values.

The meaningful-token index set must be produced by an audited alignment procedure. If alignment fails or produces an empty set, the meaningful-token score is invalid and the failure is recorded.

For ten repeated generations, canonical tool calls are grouped into clusters. If canonical cluster `k` has empirical frequency `q_k`, the planned repeated-sample measures are:

- Canonical-call entropy: `-sum(q_k * log(q_k))`.
- Canonical disagreement: `1 - max(q_k)`.

Exact-string entropy and disagreement will be retained as an ablation. Parser failures will be represented explicitly rather than discarded before clustering. The exact treatment of parser-failure clusters will be frozen after parser validation and before repeated-sample evaluation.

## 12. Correctness and evaluation outcomes

The released RobustBench-TC scorer is the primary source of tool-call correctness. UQRoute may adapt interfaces around the scorer but will not use ground-truth answers as routing inputs.

A successfully parsed call is not automatically correct. Parsing status and task correctness are recorded as separate outcomes.

For each evaluated case, the record must distinguish:

- Successful request and correct tool call.
- Successful request and incorrect tool call.
- Parser failure.
- Empty or truncated output.
- Inference or transport error.
- Missing or invalid uncertainty evidence.

For transition evaluation, pass-one output, injection status, injected fault type, pass-two output, and final scored outcome are retained separately.

A transition-labelled record with `prediction.transition_injected == false` did not receive a fault. Such records are excluded from all RQ3 denominators and reported separately as a no-fault-injected count; they are not treated as recovery successes or failures.

## 13. Primary metrics

The study will report:

- Tool-call task success.
- Parser-failure and inference-error rates.
- AUROC and AUPRC for detecting incorrect calls, with incorrectness as the positive class.
- Risk-coverage curves and area under the risk-coverage curve.
- Fallback rate and achieved coverage.
- High-confidence failure counts and rates under a predeclared definition.
- Brier score and expected calibration error after fitting a monotonic confidence mapping on development data only.
- End-to-end task success, latency, token use, GPU time, and estimated cost for routing policies.

The confidence-mapping method, calibration-bin rule, and high-confidence-failure definition must be frozen before held-out evaluation.

Results will be reported by model and condition. Aggregated results will not hide condition-specific failures. Individual perturbation types with small sample sizes will be labelled exploratory.

## 14. Routing policies and baselines

For an uncertainty score `U` and threshold `tau`, the deployable gate accepts the small-model call when `U <= tau` and escalates otherwise.

Thresholds and any score transformations are selected using development data only. The threshold-selection rule must be fixed before held-out evaluation.

The submitted comparisons are:

- Small-model-only.
- Fallback-model-only.
- Always-cascade, which runs the small model and then always runs the fallback.
- Matched-coverage random routing.
- Global uncertainty gate.
- Model-specific uncertainty gates.
- Perturbation-class oracle thresholds for analysis only.
- Correctness-oracle routing for analysis only.

Oracle policies are diagnostic references, not deployable systems. They must not be described as practical routing methods.

For static cases, one cached fallback output per case and frozen fallback configuration will be reused across policy comparisons. Recovery requests with different observed context are separate inference events and cannot reuse a context-incompatible fallback record.

## 15. Cost accounting

Every routing comparison must count all model calls required by that policy.

For an escalated static case, total serving cost includes the initial small-model call, the fallback call, and measured routing overhead. For recovery, all initial, fault-conditioned, fallback, and repeated recovery calls are counted.

The study will report:

- Number of model calls.
- Prompt and completion tokens when available.
- Per-request and end-to-end latency.
- GPU time under controlled hardware.
- Estimated monetary cost under predeclared low, base, and high cost scenarios.

Repeated-sample generation is excluded from single-sample serving cost unless a routing policy actually requires repeated samples at inference time.

Timing results from different GPU types or materially different server settings will not be treated as directly comparable. Hardware and server configuration must accompany timing claims.

## 16. Statistical analysis

The base task is the dependence unit. Related perturbation variants are not treated as statistically independent tasks.

Primary confidence intervals and paired policy comparisons will use a cluster bootstrap that resamples canonical base-task groups and retains all selected variants belonging to each sampled group. The number of bootstrap replicates, random seed, stratification rule, and interval method will be fixed before held-out evaluation.

Point estimates, confidence intervals, denominators, and missing/error counts will be reported together. Development and held-out results will be clearly separated.

Exploratory subgroup findings will be labelled as exploratory, especially when a perturbation type contains few base-task groups. The report will emphasize effect sizes and uncertainty intervals rather than relying only on significance tests.

## 17. Protocol freeze and change control

Before held-out evaluation, the following must be frozen:

- Dataset revision, primary population, and sensitivity population.
- Canonical identity rules and development/test split manifest.
- Model and tokenizer revisions.
- Prompt templates and generation settings.
- Parser and token-alignment rules.
- Uncertainty formulas and repeated-sample subset.
- Correctness metrics and calibration procedure.
- Routing policies and threshold-selection rule.
- Cost scenarios and statistical procedure.

After the freeze, any correction must be recorded in a change log with its reason, affected runs, and whether held-out results had been viewed. Exploratory analyses added after the freeze must be labelled post hoc.

The protocol is complete only when all provisional choices have been resolved or explicitly approved as scoped exclusions.
