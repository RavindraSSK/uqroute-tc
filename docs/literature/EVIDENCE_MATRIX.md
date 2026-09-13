# UQRoute-TC Literature Evidence Matrix

## Purpose

This matrix connects reviewed research to verifiable evidence and a concrete role in UQRoute-TC.

A paper is marked `Reviewed` only after its note, evidence entry, and BibTeX citation have been checked.

The registry is a working collection. Papers may be added or removed based on their relevance to the implementation and research questions.

## Status definitions

- `Not started`: identified but not examined in detail.
- `Reading`: relevant sections are being examined.
- `Extracted`: evidence and limitations have been recorded.
- `Reviewed`: note, evidence entry, and citation have been checked.
- `Excluded`: examined but not sufficiently relevant, with the reason recorded.

## Paper registry

| ID | Theme | Short name | Primary source | Status | Note file |
|---|---|---|---|---|---|
| P01 | Tool-call evaluation | BFCL | https://proceedings.mlr.press/v267/patil25a.html | Reviewed | `notes/P01_BFCL.md` |
| P02 | Deployment robustness | RobustBench-TC | https://arxiv.org/abs/2605.11928 | Reviewed | `notes/P02_ROBUSTBENCH_TC.md` |
| P03 | Failure diagnosis | ToolRobustBench | https://arxiv.org/abs/2608.23635 | Reviewed | `notes/P03_TOOLROBUSTBENCH.md` |
| P04 | Semantic uncertainty | Semantic Uncertainty | https://arxiv.org/abs/2302.09664 | Not started | `notes/P04_SEMANTIC_UNCERTAINTY.md` |
| P05 | Uncertainty benchmarking | LM-Polygraph | https://arxiv.org/abs/2406.15627 | Not started | `notes/P05_LM_POLYGRAPH.md` |
| P06 | Single-sequence uncertainty | Rethinking Uncertainty Estimation | https://arxiv.org/abs/2412.15176 | Not started | `notes/P06_SINGLE_SEQUENCE_UNCERTAINTY.md` |
| P07 | Selective prediction | Selective Classification | https://arxiv.org/abs/1705.08500 | Not started | `notes/P07_SELECTIVE_CLASSIFICATION.md` |
| P08 | Model cascades | FrugalGPT | https://arxiv.org/abs/2305.05176 | Not started | `notes/P08_FRUGALGPT.md` |
| P09 | Model routing | RouteLLM | https://arxiv.org/abs/2406.18665 | Not started | `notes/P09_ROUTELLM.md` |

Additional papers will be included only when they directly support a research question, implementation choice, metric, or interpretation.

## Cross-paper evidence

| ID | Research problem | Method or contribution | Main evidence | Limitation relevant to UQRoute-TC | UQRoute-TC use | Evidence location |
|---|---|---|---|---|---|---|
| P01 | Standardized evaluation of structured function calls | BFCL benchmark and AST-based evaluation | Function selection and argument correctness require structured evaluation | Does not evaluate uncertainty-gated routing under deployment perturbations | Correctness scoring, canonical parsing, and benchmark foundation | `notes/P01_BFCL.md`; official abstract and evaluation methodology |
| P02 | Difference between clean benchmark behavior and deployment conditions | 22 perturbations organized by observation, action, reward, and transition components | Perturbations cause uneven accuracy losses, and model scale alone does not remove them | Focuses on correctness and robustness rather than uncertainty-based escalation | Primary benchmark, perturbation taxonomy, and transition-recovery workflow | `notes/P02_ROBUSTBENCH_TC.md`; Sections 4, 6, and 7 |
| P03 | Identifying where tool-calling failures originate and propagate | Stage-wise perturbation evaluation and failure diagnosis | Clean success does not reliably predict robust behavior; visible errors may have upstream causes | Does not evaluate token uncertainty or small-to-large model routing | Failure catalogue and separation of generation, argument, and recovery failures | `notes/P03_TOOLROBUSTBENCH.md`; benchmark design, results, and limitations |

## Protocol evidence map

| Protocol component | Supporting evidence | Evidence established | Remaining question | Status |
|---|---|---|---|---|
| Benchmark selection | P01, P02 | BFCL provides structured tool-call tasks; RobustBench-TC adds deployment perturbations | None for primary benchmark selection | Defined in draft protocol |
| Evaluation population | P02 and local dataset audit | The paper-level population must be distinguished from the pinned released files | Confirm feasibility using the audited primary population | Defined in draft protocol |
| Correctness scoring | P01, P02, P03 | Tool selection, argument structure, and execution outcomes require structured scoring | Validate the released scorer against inspected examples | Defined in draft protocol |
| Single-sample uncertainty | Pending uncertainty literature | Token probabilities can provide an inference-time signal | Select and validate exact formulas | Pending |
| Repeated-sample uncertainty | Pending uncertainty literature | Equivalent outputs should not be treated as different only because of wording or formatting | Define canonical clusters and parser-failure treatment | Pending |
| Canonical-call clustering | P01; pending P04 | Structured equivalence is more meaningful than raw-string equality | Validate equivalence rules for every supported format | Pending |
| Calibration | Pending uncertainty literature | No conclusion established yet | Define confidence mapping and calibration metrics | Pending |
| Risk-coverage analysis | Pending selective-prediction literature | No conclusion established yet | Define coverage, selective risk, and threshold-selection procedure | Pending |
| Routing baselines | Pending routing literature | No conclusion established yet | Finalize fair uncertainty and random-routing comparisons | Pending |
| Cost accounting | Pending routing literature | All model calls must be represented in policy comparisons | Define latency, GPU-time, and cost scenarios | Pending |
| Post-fault recovery | P02, P03 | Runtime feedback occurs after execution and must be analyzed separately | Define bounded recovery policies and complete cost accounting | Defined in draft protocol |

## Review quality checks

- Every factual claim identifies its supporting paper or local audit.
- Reported findings are separated from UQRoute-TC interpretations.
- Negative and mixed findings are retained.
- Limitations are recorded before using a paper to justify a decision.
- Closely related work is compared by research question, benchmark, signal, routing stage, and metrics.
- Entries are revised when later evidence changes their interpretation.