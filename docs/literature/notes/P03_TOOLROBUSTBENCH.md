# P03 - ToolRobustBench

## Review status

- Status: Reviewed
- Review date: 2026-09-12
- Evidence type: Primary research preprint
- Year: 2026
- arXiv identifier: `2608.23635`
- Citation key: `zheng2026toolrobustbench`

## Paper

**Title:** ToolRobustBench: Stage-Wise Perturbation Evaluation and Failure Diagnosis for Tool-Calling Agents

**Authors:** YiShan Zheng, Yuan Wu, and Yi Chang

**Official source:** https://arxiv.org/html/2608.23635v1

## Research problem

A tool-calling system can fail at several different stages.

The final visible error does not always identify where the failure originally occurred. For example, an incorrect tool selection can later appear as an argument error or runtime failure.

Evaluating only final task success can therefore hide:

- The stage where the failure began.
- Whether one failure caused later failures.
- Whether the model violated a stage boundary.
- Which perturbation family caused the system to break.

ToolRobustBench addresses this problem through stage-wise perturbation evaluation and failure diagnosis.

## Main contribution

The paper introduces a controlled benchmark that organizes tool-calling behavior into five capability stages:

1. Tool selection.
2. Schema grounding.
3. Argument binding.
4. Tool-output and runtime-feedback handling.
5. End-to-end task success.

It applies perturbations aligned with different parts of the tool-use process and records how failures propagate across stages.

## Perturbation families

The benchmark contains four main perturbation families.

### Tool-interface perturbations

These modify the available tool definitions or schemas.

They test whether the model can correctly understand:

- Tool names.
- Tool descriptions.
- Parameter schemas.
- Required and optional fields.

### User-intent perturbations

These modify how the request is expressed.

They test whether the model preserves the user's intended task when wording, clarity, or structure changes.

### Tool-output and observation perturbations

These modify the information returned to the model after tool execution.

They test whether the model can interpret unexpected, incomplete, misleading, or malformed observations.

### Runtime-environment perturbations

These introduce execution-level changes or failures.

They test whether the system can respond correctly when the tool environment does not behave as expected.

## Evaluation environment

ToolRobustBench uses a deterministic local tool environment.

This reduces variation caused by live APIs, network behavior, changing external services, and authentication requirements.

The paper reports:

- 40 tools across 12 functional groups.
- A main evaluation configuration using 16 tools with a fixed seed.
- 14 perturbation subtypes.
- Clean, light, medium, and heavy perturbation conditions.
- Seven evaluated models.
- 15,456 raw records in the single-family evaluation.

The reported single-family records include:

- 1,344 clean records.
- 14,112 perturbed records.

Mixed-perturbation experiments are analyzed separately.

## Stage-wise failure diagnosis

The benchmark records several diagnostic labels:

- Observed error.
- Primary error.
- Earliest failed stage.
- Failure source stage.
- Cascade indicator.
- Stage-boundary violation.

These labels help distinguish the first failure from its later consequences.

A cascade occurs when an upstream failure causes errors in later stages.

This is useful because final task failure alone cannot show whether the model selected the wrong tool, misunderstood the schema, bound the wrong arguments, or mishandled runtime feedback.

## Evaluation metrics

The paper reports:

- Clean success.
- Robust success for each perturbation family.
- Overall robust performance.
- Performance drop relative to clean conditions.
- Failure-cascade rate.
- Stage-boundary violation rate.
- Mixed-perturbation performance change.

Robust performance is evaluated across perturbation severity levels.

## Main findings

The paper reports that clean task performance does not reliably predict robustness under perturbations.

Across the evaluated models:

- Average clean performance is substantially higher than robust performance.
- Tool-output and observation perturbations are the most damaging family.
- Runtime perturbations also cause substantial degradation.
- Performance decreases as perturbation severity increases.
- Mixed perturbations can produce larger failures than either component alone.
- The visible failure stage may differ from the stage where the failure originated.

The reported average performance decreases from approximately `0.869` under light perturbations to `0.724` under medium perturbations and `0.491` under heavy perturbations.

For tool-output and observation perturbations, no evaluated model reaches a reported score of `0.60`.

These results reinforce the need to inspect failure mechanisms rather than relying only on aggregate clean accuracy.

## Mixed perturbations

The paper evaluates selected combinations of perturbations.

The results indicate that combined perturbations can interact non-additively.

This means the effect of two perturbations together cannot always be predicted by examining each perturbation independently.

For UQRoute-TC, this supports treating conclusions about individual perturbations carefully and avoiding unsupported claims about arbitrary perturbation combinations.

## Human validation

The paper reports a stratified human audit of 140 records.

The audit checks the reliability of automatically generated diagnostic labels.

Because the reviewed records were stratified, the audit supports label-quality assessment but should not be treated as an estimate of the natural prevalence of each failure type.

## Strengths

- Separates tool-calling behavior into interpretable stages.
- Distinguishes primary failures from observed downstream failures.
- Uses a deterministic local environment.
- Evaluates multiple perturbation families and severity levels.
- Includes mixed-perturbation experiments.
- Provides failure-cascade and boundary-violation measurements.
- Includes human checking of diagnostic labels.

## Limitations relevant to UQRoute-TC

The controlled local environment cannot represent every behavior of live APIs or production tool systems.

The study also has the following boundaries:

- It focuses primarily on single-step tool interaction.
- It does not fully test long-horizon state accumulation.
- Only selected mixed-perturbation pairs are evaluated.
- Absolute runtime and success values depend on the chosen environment.
- Provider and inference-backend differences can still affect results.
- Human validation checks a stratified subset rather than estimating population-wide failure prevalence.

ToolRobustBench does not directly study whether model uncertainty can drive small-model to large-model escalation.

## Relationship to UQRoute-TC

ToolRobustBench is closely related to UQRoute-TC because both projects investigate tool-calling failures under perturbations.

The main difference is their research objective.

ToolRobustBench asks:

- At which stage does a failure originate?
- How does that failure propagate?
- Which perturbation families damage tool-calling performance?

UQRoute-TC asks:

- Does the small model's uncertainty identify an incorrect call?
- Does uncertainty remain useful after deployment perturbations?
- Should the system accept the small-model call or escalate?
- Does escalation improve success enough to justify its cost?

ToolRobustBench provides a useful diagnostic perspective, while UQRoute-TC evaluates uncertainty-based routing.

## Protocol implications

This paper supports the following UQRoute-TC decisions:

- Record failure categories instead of reporting only aggregate accuracy.
- Distinguish wrong-tool, wrong-schema, wrong-argument, parsing, and recovery failures.
- Identify the earliest observable failure when possible.
- Keep initial-generation errors separate from runtime-recovery errors.
- Avoid assuming that the final error message identifies the original cause.
- Analyze severe and combined perturbations cautiously.
- Use deterministic execution settings where possible.
- Preserve raw outputs so failure labels can be audited.

ToolRobustBench does not replace the RobustBench-TC taxonomy used in the primary experiment. Its stage-wise framework is used as supporting guidance for failure analysis.

## Evidence used from this paper

| UQRoute-TC component | Evidence supplied by ToolRobustBench |
|---|---|
| Failure catalogue | Errors can be classified by tool-use stage |
| Diagnostic analysis | Observed failures may have upstream causes |
| Perturbation analysis | Clean accuracy does not predict robust behavior |
| Recovery analysis | Runtime feedback handling should be evaluated separately |
| Mixed perturbations | Combined effects may be non-additive |
| Evidence quality | Automated failure labels benefit from human auditing |

## Claims this paper does not support

This paper does not provide evidence that:

- Token-level uncertainty predicts the earliest failed stage.
- UQRoute-TC routing thresholds are calibrated.
- A larger fallback model corrects every failure category.
- Escalation reduces cost per successful task.
- A threshold learned on clean data transfers to perturbations.
- UQRoute-TC canonical disagreement is superior to exact-string disagreement.

These claims require evidence from UQRoute-TC experiments.

## One-sentence synthesis

ToolRobustBench shows that tool-calling failures originate and propagate across distinct stages, while UQRoute-TC tests whether uncertainty can identify those failures early enough to support cost-aware model escalation.
