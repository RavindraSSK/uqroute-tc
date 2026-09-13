# P02 - RobustBench-TC

## Review status

- Status: Reviewed
- Review date: 2026-09-12
- Evidence type: Primary research preprint and released benchmark
- Year: 2026
- arXiv identifier: `2605.11928`
- Citation key: `zhou2026simulation`

## Paper

**Title:** When Simulation Lies: A Sim-to-Real Benchmark and Domain-Randomized RL Recipe for Tool-Use Agents

**Authors:** Xiaolin Zhou, Aojie Yuan, Zheng Luo, Zipeng Ling, Xixiao Pan, Yicheng Gao, Haiyue Zhang, Jiate Li, Shuli Jiang, Prince Zizhuang Wang, Zixuan Zhu, Jinbo Liu, Ryan A. Rossi, Hua Wei, and Xiyang Hu

**Official paper:** https://arxiv.org/html/2605.11928v1

**Released repository:** https://github.com/WillChow66/robustbench-tc-release

**UQRoute-TC pinned repository revision:** `d5d03180de41eb30a6c796d04a9bfbd9dad85c1d`

## Research problem

Tool-calling benchmarks normally evaluate models under clean and controlled conditions.

Real deployments can contain:

- Typographical errors in user requests.
- Rephrased or ambiguous instructions.
- Modified tool and parameter descriptions.
- Duplicate or distracting tools.
- Misleading tool metadata.
- Timeouts, authentication failures, rate limits, server errors, malformed responses, and schema changes.

The paper studies the difference between clean benchmark performance and performance under these deployment-style perturbations.

## Main contribution

The paper introduces RobustBench-TC, a benchmark for evaluating tool-use agents under realistic perturbations.

The authors model tool use as a partially observable Markov decision process and organize perturbations around four components:

1. Observation.
2. Action space.
3. Reward-relevant metadata.
4. Transition dynamics.

The benchmark contains 22 perturbation types grounded in reported tool-calling failures or related empirical evidence.

## Perturbation taxonomy

### Observation perturbations

These modify information received by the model:

- User-query typographical errors.
- User-query paraphrasing.
- Tool-description paraphrasing.
- Parameter-description paraphrasing.

### Action-space perturbations

These modify the tools available to the model:

- Same-name distractor tools.
- Distractors with missing descriptions or parameters.
- Distractors with incorrect parameters.
- Distractors with swapped descriptions and parameters.
- Functionally similar redundant tools.

### Reward-relevant perturbations

These modify metadata that can influence tool selection:

- Misleading tool descriptions.
- Response-time descriptions.
- Neutral distractor naming.
- Abbreviated names.
- Combinations of misleading descriptions and naming changes.

### Transition perturbations

These modify what happens when a tool call is executed:

- Timeout.
- Rate limit.
- Authentication error.
- Server error.
- Malformed response.
- Schema drift.

Transition perturbations occur after the first tool call and give the model an opportunity to respond to an observed runtime failure.

## Benchmark construction

The benchmark draws tool-calling examples from five existing sources:

- BFCL V3.
- API-Bank.
- RoTBench.
- ToolAlpaca.
- ToolEyes.

These sources cover several output formats, including structured BFCL calls, JSON-style calls, and ReAct-style outputs.

The paper reports:

- 199 single-turn base samples.
- 3,522 perturbation samples.
- 3,721 total benchmark cases.

These are the paper-level benchmark figures and should not be substituted for the counts observed in a particular released directory.

## Released population used by UQRoute-TC

UQRoute-TC uses the pinned released repository rather than assuming that the paper-level counts exactly match the available static files.

Our audit of `hf_data/datasets/api_eval` found:

| Population | Rows | Base-task groups |
|---|---:|---:|
| Stored static cases | 2,718 | Not used directly |
| Excluded multi-turn cases | 191 | Excluded |
| Eligible single-turn cases | 2,527 | 248 |
| Clean-anchored primary population | 2,477 | 199 |
| Perturbation-only sensitivity addition | 50 | 49 |

The difference between the paper-level total and the pinned static release is treated as a versioned data-provenance fact, not as an experimental result.

All UQRoute-TC claims will use the audited counts associated with the pinned revision.

## Evaluation approach

The paper evaluates 21 language models ranging from approximately 1.5B to 32B parameters, including an additional closed-source model.

The evaluation measures model accuracy under clean and perturbed conditions.

Transition cases are evaluated through an execution workflow:

1. The model generates an initial tool call.
2. The environment injects a runtime failure.
3. The failure is returned to the model.
4. The model receives an opportunity to recover.
5. The recovery output is scored.

This workflow is different from static single-turn generation and must be recorded separately.

## Main findings

The paper reports an uneven robustness profile across perturbation categories:

- Observation perturbations reduce accuracy by less than approximately 5%.
- Reward-relevant perturbations reduce accuracy by approximately 40%.
- Transition perturbations reduce accuracy by approximately 30%.
- Increasing model size alone does not consistently eliminate these robustness gaps.

These findings show that clean accuracy is not enough to characterize deployment reliability.

## ToolRL-DR

The paper also introduces ToolRL-DR, a domain-randomization reinforcement-learning method.

ToolRL-DR trains a model using perturbation-augmented tool-use trajectories. The reported 3B model improves robustness and partially transfers to transition failures that were not directly included in training.

UQRoute-TC does not implement this training method.

The UQRoute-TC models remain frozen because the project studies inference-time uncertainty, escalation, and recovery rather than model training.

## Strengths

- Provides a unified taxonomy for deployment-style tool-use failures.
- Connects perturbations to documented real-world failure modes.
- Evaluates multiple models and model sizes.
- Separates static input perturbations from runtime transition failures.
- Releases benchmark data, code, and evaluation infrastructure.
- Demonstrates that clean performance can hide substantial robustness failures.

## Limitations relevant to UQRoute-TC

The paper primarily evaluates robustness through correctness changes.

It does not directly establish:

- Whether token-level uncertainty detects perturbation-induced failures.
- Whether canonical-call disagreement predicts incorrect calls.
- Whether uncertainty remains calibrated across perturbation categories.
- Whether uncertainty-based escalation reduces total inference cost.
- Which routing threshold should be used for a frozen small model.
- Whether a fallback model improves every escalated request.

The paper’s training method also changes model behavior, whereas UQRoute-TC studies frozen models and inference-time decisions.

## Relationship to UQRoute-TC

RobustBench-TC is the main evaluation benchmark used by UQRoute-TC.

UQRoute-TC builds on it by adding:

1. Single-sample uncertainty measurements from generated-token log-probabilities.
2. Repeated-sample entropy and disagreement over canonical tool calls.
3. Failure-detection evaluation under each perturbation category.
4. An accept-or-escalate cascade using a larger fallback model.
5. Complete accounting of initial, fallback, and recovery inference costs.
6. Separate analysis of static routing and post-fault recovery.

The central UQRoute-TC question is not only whether perturbations cause errors, but whether uncertainty identifies those errors well enough to support useful routing.

## Protocol implications

This paper supports the following protocol decisions:

- Pin the benchmark repository revision.
- Audit the released population instead of assuming paper-level counts.
- Keep related perturbation variants in the same data partition.
- Report perturbation categories separately.
- Keep static single-turn evaluation separate from transition recovery.
- Treat runtime failures as observed information available only after execution.
- Evaluate correctness independently from whether execution produced an exception.
- Record model scale without assuming that larger models are automatically robust.
- Use clean accuracy and perturbed accuracy as separate measurements.

## Evidence used from this paper

| UQRoute-TC component | Evidence supplied by RobustBench-TC |
|---|---|
| Main benchmark | Released deployment-perturbation evaluation data |
| Perturbation design | Observation, action, reward, and transition taxonomy |
| Model evaluation | Accuracy can fall substantially under perturbations |
| Recovery workflow | Runtime failures are injected after the first tool call |
| Model selection | Scale alone does not guarantee robustness |
| Research motivation | Clean benchmark performance can hide deployment failures |

## Claims this paper does not support

This paper does not provide evidence that:

- UQRoute-TC uncertainty scores are well calibrated.
- A selected routing threshold generalizes to held-out tasks.
- The fallback model always outperforms the small model.
- Ten-sample uncertainty is worth its additional cost.
- The proposed cascade reduces cost per successful task.
- Recovery routing is better than unconditional retrying.

Those claims require UQRoute-TC experiments.

## One-sentence synthesis

RobustBench-TC establishes that tool-calling models fail unevenly under realistic deployment perturbations, while UQRoute-TC investigates whether uncertainty can detect those failures and guide cost-aware escalation using frozen models.
