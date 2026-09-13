# UQRoute-TC Research Gap and Contributions

## Status

This is a working synthesis. It becomes a final research-gap statement only after the relevant evidence-matrix entries are complete.

## Problem context

Tool-calling language models must select an appropriate tool and produce valid structured arguments. Clean benchmark accuracy alone may not show how reliably a model behaves when tool descriptions, observations, available actions, or execution feedback change during deployment.

UQRoute-TC studies whether uncertainty from the small model's generated tool call identifies cases that should be escalated to a larger fallback model. The project evaluates both failure detection and the resulting task-success versus inference-cost trade-off.

## Literature areas to connect

The research gap must be supported by evidence from all of these areas:

1. Tool-calling benchmarks define tasks and correctness.
2. Robustness benchmarks expose failures under perturbations.
3. Uncertainty research provides token-level and semantic uncertainty measures.
4. Selective-prediction research provides risk-coverage evaluation.
5. Routing and cascade research provides cost-aware comparisons.
6. Tool-agent research provides recovery settings after observed execution faults.

## Working gap statement

Existing research studies tool-call correctness, robustness perturbations, uncertainty estimation, and cost-aware model routing, but these components are often evaluated separately. The working gap is whether uncertainty derived from a small model's actual structured tool-call generation remains reliable under deployment perturbations and whether that signal supports a useful small-to-large cascade.

This statement is provisional evidence synthesis, not a claim of absolute novelty. It must be revised when closely related papers have been fully compared.

## Proposed contribution areas

### C1 - Structured-call uncertainty under perturbations

Evaluate whether single-sample token uncertainty and repeated-sample canonical-call disagreement distinguish correct from incorrect tool calls across clean and perturbed conditions.

### C2 - Canonical uncertainty representation

Measure disagreement over normalized tool calls so that equivalent formatting does not automatically count as semantic disagreement, while preserving meaningful differences in tools, argument values, types, call counts, and order where relevant.

### C3 - Uncertainty-gated model cascade

Evaluate a post-generation accept-or-escalate policy using the small model's realized tool call and uncertainty, with comparisons against small-only, fallback-only, unconditional cascade, matched-random routing, and analysis oracles.

### C4 - Cost-aware post-fault recovery

Evaluate a separate bounded recovery decision after an execution fault is observed, with complete accounting for initial generation, escalation, and recovery costs.

### C5 - Reproducible grouped evaluation

Provide a traceable implementation and evaluation protocol that keeps related benchmark variants together during partitioning and statistical resampling.

## Evidence required before finalizing each contribution

| Contribution | Prior work to compare | Evidence needed from literature | Evidence needed from UQRoute-TC |
|---|---|---|---|
| C1 | Tool robustness and UQ methods | Existing uncertainty settings, perturbations, and metrics | Failure-detection and calibration results |
| C2 | Semantic uncertainty and tool-call parsers | Treatment of equivalent generations | Parser audit and clustering ablation |
| C3 | Selective prediction and model routing | Routing stage, signals, baselines, and cost definitions | Frozen-policy success-cost curves |
| C4 | Tool-agent recovery | Fault and recovery definitions | Bounded recovery outcomes and costs |
| C5 | Benchmark and statistical methodology | Grouping and evaluation practices | Audit, split tests, and group-aware intervals |

## Closest-work comparison template

| Paper | Research question | Routing stage | Decision signal | Benchmark | Perturbations | Cost evaluation | Difference from UQRoute-TC |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## Claim boundaries

- Do not claim that uncertainty is reliable until held-out evidence supports it.
- Do not claim cost savings without counting all model calls used by the policy.
- Do not claim semantic equivalence without an audited canonicalization rule.
- Do not call analysis oracles deployable routing methods.
- Do not generalize beyond the evaluated models, task groups, perturbations, and hardware assumptions.
- Report a negative or mixed result if the uncertainty gate does not outperform matched alternatives.

## Finalization checklist

- [ ] Relevant paper notes are complete.
- [ ] Cross-paper evidence matrix is populated.
- [ ] Recent closely related work is compared directly.
- [ ] Each gap statement has supporting citations.
- [ ] Contributions describe completed work rather than planned work.
- [ ] Claims match the frozen evaluation protocol and final evidence.
