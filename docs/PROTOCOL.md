# UQRoute-TC Evaluation Protocol

## Protocol status

The Task 1 benchmark, population, split, model roles/revisions, and
single-sample generation settings are frozen in
`docs/config/task1_single_sample_v1.json`. This document
remains a draft for the Task 2 parser/uncertainty rules and Task 3–4 analysis,
cost, routing, and recovery choices. The full protocol must be frozen before
held-out evaluation begins.

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

The Task 1 published-number gate uses a **post hoc, one-case tolerance** approved after
the initial clean runs were viewed. A near reproduction is sufficient to start the
grouped split only if the pinned reference runner and scorer process all 199 unique
clean cases without errors, exact model and inference settings are recorded, and
strict accuracy differs from the seeded leaderboard by no more than one case.
This is a feasibility decision, not an exact reproduction of the published result.
For `meta-llama/Llama-3.2-3B-Instruct`, the observed strict score is 102/199
(`0.5126`) and the seeded leaderboard reports 103/199 (`0.5176`). The saved
Colab check found 199 unique predictions and scores, with no missing or extra
clean IDs. The release does not contain the seeded per-case predictions, so
the differing case and its cause cannot be established from the release.

Partitioning will occur at the canonical base-task level, not at the individual-row level.

All clean, paraphrased, perturbed, and same-name variants belonging to a base task must remain in the same partition.

The planned primary population will be divided into:

- Development groups used for engineering checks, uncertainty-method selection, calibration, and routing-threshold selection.
- Held-out test groups used only after the parser, metrics, routing policies, and thresholds are frozen.

The split in `docs/splits/group_split_v1.json` uses seed `1729` and a 70/30
development/test target. Within each population and benchmark, base-task IDs
are ranked by SHA-256 of the fixed seed, population, benchmark, and canonical ID.
The benchmark for primary groups comes from their clean source row. The first
`round_half_up(0.3 * n)` groups in each stratum go to test; the rest go to
development. The primary population has 140
development and 59 test groups (1,754 and 723 static rows). The 49
sensitivity-only BFCL groups are split separately: 34 development and 15 test
groups (35 and 15 static rows). Every variant follows its base-task group.
Regenerate the manifest with `python -m uqroute_tc.data.split --data-dir
<benchmark-clone>/hf_data/datasets/api_eval --output docs/splits/group_split_v1.json`.

This split was fixed **after** aggregate clean-run results for Qwen 1.5B and
Llama 3B, several Qwen clean case IDs, and a five-case Qwen 7B clean pilot
had been viewed. Those clean results are not a fully untouched held-out test;
report them descriptively and disclose this exposure. Method selection and
threshold tuning must use development groups only. Confirmatory held-out
claims must be limited to subsequently unseen perturbed cases under the
frozen analysis protocol; do not inspect their test labels while developing.

The pinned runner generates Transition cases only from `clean.jsonl`. The 49 sensitivity-population groups without a clean source row cannot receive Transition cases. RQ3 is therefore scoped to the clean-anchored population of 199 base-task groups; the full 248-group population is not an RQ3 population.

Additional leakage controls are:

- Ground-truth calls may be used by the scorer but never by the router.
- Held-out correctness labels must not influence threshold selection.
- Test results must not be used to choose uncertainty measures.
- Related variants must remain together during confidence-interval resampling.
- Any post-freeze protocol change must be documented.


## 8. Model roles and revisions

The frozen principal small models are:

- `Qwen/Qwen2.5-1.5B-Instruct`
- `meta-llama/Llama-3.2-3B-Instruct`
- `Qwen/Qwen2.5-7B-Instruct`

The frozen fallback model is:

- `Qwen/Qwen2.5-14B-Instruct-AWQ`

These models have fixed roles in the study. The three principal models produce the initial tool call, and the 14B model is the escalation target. Model weights remain frozen; UQRoute does not fine-tune them.

The Task 1 configuration records all four exact model/tokenizer revisions,
including `539535859b135b0244c91f3e59816150c8056698` for the 14B AWQ
fallback (read by the user from the saved Drive pilot manifest). It also
records the quantization, numerical dtype, vLLM version, default chat-template
selection, and observed pilot access. The model-card license tags are recorded
from the [Qwen 1.5B](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct),
[Qwen 7B](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct),
[Qwen 14B AWQ](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct-AWQ), and
[Llama 3.2](https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct) model
cards; Llama was accessed through the user's gated-model token. The code does
not bundle model weights or credentials. Each main experiment manifest must
also record the exact run configuration and code revision.

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

The primary single-sample study uses the frozen Task 1 settings: temperature
`0.001`, maximum completion length 1,024 tokens, chosen-token log-probabilities
with `top_logprobs=5`, prompt-based tool calling, and the pinned benchmark's
message builder. The vLLM server setting is version `0.30.0`, maximum model
length 8,192, and GPU memory utilization `0.88`. No per-request seed was set
in the reference-style pilots; this is a recorded limitation for stochastic
reproduction. The separate 199-case Llama near reproduction used temperature
`0` and is not conflated with the five-case pilot or main single-sample setting.

The five-case pilots verified serving, scorer output, and valid token evidence
on the L4. They do not establish throughput or absence of truncation across
the full population; larger development runs must record those outcomes and
would require a logged protocol amendment if the frozen setting proves
infeasible. Main inference will record the same settings in each run manifest.

Prompt-based tool calling is the primary protocol. Native function calling is not part of the primary comparison unless it is separately predeclared as an ablation, because it changes both the output channel and the availability of token-level evidence.

### 10.2 Repeated-sample protocol

Repeated-sample uncertainty will use ten generations per selected case. The sampling temperature, nucleus-sampling value, seed procedure, and subset size will be fixed before repeated-sample results are inspected.

The proposed diagnostic subset is selected without prediction values or
correctness labels by `src/uqroute_tc/data/repeated_subset.py`: three distinct
development groups in each of BFCL, APIBank, RotBench, ToolAlpaca, and
ToolEyes. Each group contributes its clean row and one perturbation, giving
15 groups and 30 static cases. For each benchmark the perturbation choices
are query paraphrase, redundant tools, and CD_AB. ToolEyes has no CD_AB rows,
so its third choice is realistic typos. Eligible groups are ranked by SHA-256
of the selector version, seed 1729, benchmark, perturbation file, and base ID;
previously selected groups in the benchmark are skipped. The current pinned
release and split produce selection digest
`082e150679277d7d55eaa88b0b82cb236a82a32a0d6853c2cae8dc307b41fa67`
over the compact, sorted-key JSON case list. At ten generations for each of
three small models, this is 900 calls. The 30 cases are a limited diagnostic
subset, and any claims about the full population require its larger evaluation.
This selection and the remaining generation settings are draft until approved.

Each generated output will be parsed and converted to a canonical tool-call representation. Canonical-call frequencies will be used to calculate disagreement and entropy. Exact-string clustering will be retained as an ablation.

The repeated-sample subset and the claims supported by it must be stated explicitly. Results from a subset will not be presented as if every benchmark case received ten samples.

### 10.3 Invalid and incomplete generations

Parsing failures, missing log-probabilities, truncated completions, request errors, and empty outputs are explicit recorded outcomes. They must not be silently removed from denominators.


## 11. Uncertainty measures

All uncertainty scores are oriented so that a larger value means greater uncertainty.

The provisional canonical-call implementation uses the pinned benchmark's
`parse_tool_calls` output and does not replace or change the scorer's parser.
It ignores mapping insertion order, but preserves tool names and case,
argument names, nested value types and values, list order, and call order.
Empty output, an explicit `[]`, malformed parsed calls, and nonempty outputs
with no parsed calls remain distinct. The last category can contain both
intentional no-tool replies and unrecognized syntax, so it is labelled
`unparsed_or_no_call` pending the saved-output audit. These rules, including
how that ambiguous category enters repeated-sample clustering, are not frozen.

For a generated sequence containing tokens indexed by `i = 1, ..., L`, let `log p_i` be the model-returned log-probability of the selected token.

The planned single-sample measures are:

- Sequence negative log-likelihood: `-sum(log p_i)`.
- Mean token negative log-likelihood: `-sum(log p_i) / L`.
- Maximum token surprisal: `max(-log p_i)`.
- Meaningful-token negative log-likelihood: the mean negative log-likelihood over aligned tokens representing tool names, argument names, and argument values.

The meaningful-token index set must be produced by an audited alignment procedure. If alignment fails or produces an empty set, the meaningful-token score is invalid and the failure is recorded.

The current BFCL Python-call draft parses the complete visible output as a
single call or a list of calls with literal keyword arguments. It verifies
that the reconstructed calls match the pinned benchmark parser's type-aware
canonical key, and that the returned chosen-token bytes exactly reconstruct
the UTF-8 output after any verified final end token is removed. It maps the
source byte spans for tool names, argument names, and argument values to
visible tokens. String quotes are excluded for nonempty simple literals;
empty-string quotes represent the otherwise zero-length value. A token is
selected if it overlaps a meaningful span. Because token boundaries can
include syntax as well as content, the procedure reports which selected
tokens also cover punctuation or whitespace. It rejects truncated responses,
unsupported syntax, mismatched parser calls, missing probabilities, and
unaligned bytes. This rule has been checked on the 20 saved outputs from five
BFCL development cases across four models. JSON, XML, and mixed output
formats still need alignment validation before this measure can be used
across the full benchmark. The selection rule remains draft.

A local ReAct alignment draft handles a single `Action:` and `Action Input:`
pair with one complete JSON object for RoTBench and ToolEyes. It requires the
extracted call to match the pinned parser and selects the action name, JSON
argument names, and JSON argument values by UTF-8 byte spans. Trailing text,
multiple actions, non-JSON inputs, and parser disagreement invalidate the
meaningful-token score. Local tests pass. The saved Qwen 1.5B RoTBench and
ToolEyes development responses both passed exact token-byte and call-alignment
checks: 11 and 6 selected tokens, with 2 and 1 tokens crossing syntax
boundaries respectively. Four Qwen 1.5B clean development
diagnostic cases across APIBank, RoTBench, ToolAlpaca, and ToolEyes completed
with valid token evidence and received official scores of 0/4. The released
parser returned a call in the RoTBench and ToolEyes cases, and no call in the
other two. These cases establish neither a cross-benchmark accuracy estimate
nor a complete alignment rule for XML/JSON and mixed outputs.

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

The Task 1 subset (dataset/populations/split, model roles and revisions,
prompt-based single-sample generation settings) is frozen in
`docs/config/task1_single_sample_v1.json`. Before held-out evaluation, the
remaining choices must also be frozen:

- Parser and token-alignment rules.
- Uncertainty formulas and repeated-sample subset.
- Correctness metrics and calibration procedure.
- Routing policies and threshold-selection rule.
- Cost scenarios and statistical procedure.

Any correction to the frozen Task 1 subset or later full freeze must be
recorded in a change log with its reason, affected runs, and whether held-out
results had been viewed. Exploratory analyses added after the full freeze must
be labelled post hoc.

The protocol is complete only when all provisional choices have been resolved or explicitly approved as scoped exclusions.
