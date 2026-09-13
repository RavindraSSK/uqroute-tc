# P01 - Berkeley Function Calling Leaderboard

## Review status

- Status: Reviewed
- Review date: 2026-09-12
- Evidence type: Peer-reviewed primary research
- Publication: Proceedings of the 42nd International Conference on Machine Learning
- Year: 2025
- Citation key: `patil2025bfcl`

## Paper

**Title:** The Berkeley Function Calling Leaderboard (BFCL): From Tool Use to Agentic Evaluation of Large Language Models

**Authors:** Shishir G Patil, Huanzhi Mao, Fanjia Yan, Charlie Cheng-Jie Ji, Vishnu Suresh, Ion Stoica, and Joseph E. Gonzalez

**Official source:** https://proceedings.mlr.press/v267/patil25a.html

**Paper PDF:** https://raw.githubusercontent.com/mlresearch/v267/main/assets/patil25a/patil25a.pdf

## Research problem

The paper addresses the lack of a standardized and reproducible way to evaluate whether language models generate correct structured function calls.

A model must do more than produce plausible text. It must:

- Select an appropriate function.
- Produce the required arguments.
- Preserve argument types and values.
- Handle serial and parallel function calls.
- Recognize when none of the available functions should be called.
- Maintain correct behavior in multi-step interactions.

## Main contribution

BFCL provides an evaluation framework and public leaderboard for measuring function-calling capabilities across models.

The benchmark covers:

- Simple function calls.
- Multiple and parallel function calls.
- Function relevance and abstention.
- Multiple programming-language representations.
- Multi-turn and stateful agentic settings.

The framework uses structured evaluation instead of relying only on exact output-string matching.

## Evaluation method

BFCL parses generated calls and compares their structure with the expected calls using abstract syntax tree based evaluation.

This is important because two outputs can express the same function call while differing in formatting, whitespace, argument ordering, or surface syntax.

The evaluation examines whether the model selected the correct function and supplied compatible argument names, values, and types.

## Main findings

The paper reports that leading models perform strongly on several single-turn function-calling tasks.

However, performance remains less reliable when evaluation requires:

- Multi-turn interaction.
- State tracking.
- Dynamic decisions.
- Long-horizon behavior.
- Correct handling of irrelevant functions.

The results show that strong performance on ordinary single-turn calls does not establish reliable behavior across more complex tool-use conditions.

## Strengths

- Provides a widely used function-calling evaluation framework.
- Evaluates structured calls rather than only natural-language responses.
- Includes multiple function-calling categories.
- Supports reproducible comparison across models.
- Makes benchmark results and leaderboard information publicly available.

## Limitations relevant to UQRoute-TC

BFCL primarily measures whether generated function calls are correct.

It does not directly determine:

- Whether token-level uncertainty predicts incorrect calls.
- Whether uncertainty remains reliable under controlled deployment perturbations.
- When a small model should escalate a request to a larger model.
- Whether escalation improves the success-cost trade-off.
- How uncertainty should be used after a runtime tool failure.

These are comparisons made for the UQRoute-TC research scope, not limitations claimed directly by the BFCL authors.

## Relationship to UQRoute-TC

BFCL provides the underlying function-calling evaluation concepts used by part of the RobustBench-TC data.

UQRoute-TC extends this evaluation perspective by studying:

1. Model uncertainty associated with generated tool calls.
2. Changes in uncertainty under deployment perturbations.
3. Small-model acceptance versus fallback-model escalation.
4. Task success relative to total inference cost.
5. Separate recovery decisions after an observed execution fault.

BFCL helps establish whether a call is correct. UQRoute-TC investigates whether the model's uncertainty can predict that correctness before execution.

## Protocol implications

This paper supports the following UQRoute-TC decisions:

- Evaluate structured tool-call correctness rather than raw text similarity alone.
- Preserve meaningful differences in tool names, arguments, values, and types.
- Canonicalize formatting differences before repeated-sample disagreement analysis.
- Record parsing failures explicitly.
- Report results separately for task categories where appropriate.
- Avoid treating clean single-turn accuracy as sufficient evidence of deployment reliability.

## Evidence used from this paper

| UQRoute-TC component | Evidence supplied by BFCL |
|---|---|
| Tool-call evaluation | Structured function-call correctness is required |
| Canonical parsing | Surface-form differences should not automatically imply different calls |
| Benchmark foundation | BFCL supplies function-calling tasks used by later benchmarks |
| Failure analysis | Function selection and argument construction can fail separately |
| Research gap | Correctness evaluation alone does not provide an uncertainty-gated routing policy |

## Claims this paper does not support

This paper does not provide evidence that:

- A particular uncertainty measure is calibrated.
- A small-model cascade reduces inference cost.
- A 14B fallback always corrects small-model errors.
- Ten-sample disagreement is superior to single-sample uncertainty.
- A routing threshold transfers across perturbation types.

Those claims require evidence from UQRoute-TC experiments.

## One-sentence synthesis

BFCL provides the structured correctness foundation for evaluating tool calls, while UQRoute-TC studies whether uncertainty can identify incorrect calls and support cost-aware escalation under deployment perturbations.
