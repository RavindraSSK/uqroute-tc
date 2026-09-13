# UQRoute-TC Literature Review

## Purpose

This directory records the research foundation for UQRoute-TC. The literature review identifies what is already known about tool-calling evaluation, deployment robustness, language-model uncertainty, selective prediction, and cost-aware model routing.

The review is used to justify the research questions, experimental design, metrics, baselines, and proposed contribution. Links alone do not count as reviewed literature. Each reviewed paper must have an evidence-matrix entry and a structured note written in our own words.

## Project focus

UQRoute-TC studies whether uncertainty calculated from a small language model's generated tool call can identify incorrect calls under deployment perturbations. It then tests whether an uncertainty gate can improve the trade-off between task success and inference cost by accepting suitable small-model calls and escalating uncertain cases to a larger fallback model.

The literature review addresses four connected areas:

1. Tool-calling evaluation and correctness.
2. Robustness under deployment perturbations.
3. Uncertainty estimation and selective prediction.
4. Cost-aware model routing and cascades.

## Core literature

### Theme A — Tool-calling evaluation and robustness

| ID | Paper | Role in UQRoute-TC | Status |
|---|---|---|---|
| P01 | [The Berkeley Function Calling Leaderboard (BFCL): From Tool Use to Agentic Evaluation of Large Language Models](https://proceedings.mlr.press/v267/patil25a.html) | Tool-call tasks, structured correctness evaluation, and benchmark background | Not started |
| P02 | [When Simulation Lies: A Sim-to-Real Benchmark and Domain-Randomized RL Recipe for Tool-Use Agents](https://arxiv.org/abs/2605.11928) | Primary deployment-perturbation benchmark and experimental population | Not started |
| P03 | [ToolRobustBench: Stage-Wise Perturbation Evaluation and Failure Diagnosis for Tool-Calling Agents](https://arxiv.org/abs/2608.23635) | Recent robustness benchmark and failure-diagnosis comparison | Not started |

### Theme B — Language-model uncertainty

| ID | Paper | Role in UQRoute-TC | Status |
|---|---|---|---|
| P04 | [Semantic Uncertainty: Linguistic Invariances for Uncertainty Estimation in Natural Language Generation](https://arxiv.org/abs/2302.09664) | Semantic equivalence and the motivation for canonical tool-call clustering | Not started |
| P05 | [Benchmarking Uncertainty Quantification Methods for Large Language Models with LM-Polygraph](https://arxiv.org/abs/2406.15627) | Uncertainty-method comparison and evaluation methodology | Not started |
| P06 | [Rethinking Uncertainty Estimation in LLMs: A Principled Single-Sequence Measure](https://arxiv.org/abs/2412.15176) | Cost-efficient uncertainty calculated from one generated sequence | Not started |

### Theme C — Selective prediction and cost-aware routing

| ID | Paper | Role in UQRoute-TC | Status |
|---|---|---|---|
| P07 | [Selective Classification for Deep Neural Networks](https://arxiv.org/abs/1705.08500) | Risk-coverage evaluation and confidence-based acceptance | Not started |
| P08 | [FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance](https://arxiv.org/abs/2305.05176) | Cost-quality trade-offs and language-model cascades | Not started |
| P09 | [RouteLLM: Learning to Route LLMs with Preference Data](https://arxiv.org/abs/2406.18665) | Learned pre-generation routing baseline and comparison boundary | Not started |

## Review workflow

For each selected paper:

1. Verify the title, authors, year, venue, paper link, and code link when available.
2. Read the abstract, introduction, method, experiments, limitations, and conclusion.
3. Create a structured note in `notes/` using `PAPER_NOTE_TEMPLATE.md`.
4. Record the problem, method, data, models, metrics, findings, and limitations in `EVIDENCE_MATRIX.md`.
5. Add the verified citation to `../../paper/references.bib`.
6. Record any direct effect on the UQRoute-TC protocol.
7. Mark the paper as `Reviewed` only when all required records are complete.

## Evidence rules

- Prefer original papers, official benchmark pages, and official repositories.
- Write findings in our own words and preserve the meaning of the source.
- Do not infer a result that the paper did not test.
- Record section, table, figure, or page locations for important evidence.
- Keep short quotations only when exact wording is necessary.
- Distinguish published results from our interpretation.
- Do not treat a saved link or abstract-only reading as a completed review.

## Planned synthesis

The completed review will support:

- A precise statement of the research gap.
- A comparison between pre-generation routing and post-generation uncertainty gating.
- Justification for single-sample and repeated-sample uncertainty measures.
- Justification for canonical tool-call clustering.
- Selection of correctness, calibration, risk-coverage, and cost metrics.
- Clear boundaries between UQRoute-TC and existing robustness benchmarks.
- Evidence-based revisions to the draft evaluation protocol.

Detailed claims and conclusions will be written only after the corresponding papers have been reviewed and recorded in the evidence matrix.
