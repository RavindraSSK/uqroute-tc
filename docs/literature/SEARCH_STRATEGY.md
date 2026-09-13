# UQRoute-TC Literature Search Strategy

## Purpose

This document defines how research literature is identified, screened, and recorded for UQRoute-TC. The goal is a focused and reproducible review of work that directly informs the research questions, experimental protocol, metrics, baselines, or interpretation.

## Review scope

The search covers four connected areas:

1. Tool-calling benchmarks and correctness evaluation.
2. Tool-agent robustness under deployment perturbations.
3. Language-model uncertainty, calibration, and selective prediction.
4. Cost-aware model routing, cascades, and tool-error recovery.

## Research questions guiding the search

- How is structured tool-call correctness evaluated?
- Which deployment perturbations cause tool-calling failures?
- Which uncertainty measures can be calculated from a single generation?
- How is semantic disagreement calculated across repeated generations?
- How are risk, coverage, calibration, and failure detection evaluated?
- How are small-to-large model cascades compared fairly on quality and cost?
- How is recovery after an observed tool-execution fault evaluated?

## Preferred sources

Use primary and authoritative sources whenever possible:

- Official conference or journal proceedings.
- arXiv paper records maintained by the authors.
- OpenReview pages for reviewed conference submissions.
- Official benchmark websites and repositories.
- Publisher or institutional paper pages.

Secondary summaries may help discover papers but are not used as evidence for research claims.

## Search terms

Search terms may be combined using `AND` and `OR`.

### Tool calling and robustness

- `LLM tool calling benchmark`
- `function calling evaluation large language models`
- `tool use agent perturbation robustness`
- `tool calling failure diagnosis`
- `tool execution recovery language model agent`

### Uncertainty and calibration

- `language model uncertainty estimation token log probability`
- `single sequence uncertainty LLM`
- `semantic entropy language model`
- `LLM calibration selective prediction`
- `risk coverage language model`
- `high confidence language model errors`

### Routing and cascades

- `LLM routing small large model cascade`
- `cost aware language model routing`
- `confidence based LLM escalation`
- `selective generation model routing`
- `post generation uncertainty routing`

## Inclusion criteria

A paper is included when it satisfies at least one of these conditions:

- Directly evaluates structured tool or function calls.
- Introduces or evaluates relevant deployment perturbations.
- Defines an uncertainty measure used or adapted by UQRoute-TC.
- Provides calibration, failure-detection, or risk-coverage methodology.
- Evaluates a model-routing or cascade baseline relevant to UQRoute-TC.
- Provides evidence needed to interpret recovery after tool-execution faults.

The paper must also provide enough methodological or experimental detail to support a verifiable note.

## Exclusion criteria

Exclude or deprioritize papers that:

- Mention tool use, uncertainty, or routing only briefly.
- Provide no accessible primary paper or authoritative record.
- Duplicate another version without adding relevant evidence.
- Focus on model training without relevance to inference-time evaluation or routing.
- Are opinion pieces, marketing pages, or unverified summaries.
- Do not affect a project claim, comparison, or design decision.

## Screening process

1. Verify the title, authors, year, venue, and primary URL.
2. Screen the abstract and introduction for direct relevance.
3. Inspect the method, experiments, limitations, and conclusion.
4. Classify the paper as core, supporting, contextual, or excluded.
5. Create a structured note for included papers.
6. Add evidence to `EVIDENCE_MATRIX.md`.
7. Add verified citation metadata to `../../paper/references.bib`.
8. Record any effect on `../PROTOCOL.md`.

## Search log

| Date | Source | Search query or discovery path | Papers screened | Papers included | Notes |
|---|---|---|---:|---:|---|
| | | | | | |

## Stopping rule

The review does not use an arbitrary paper-count target. Searching stops when the core research areas have direct evidence, recent closely related work has been checked, and additional searches no longer change the research gap or experimental design.

New papers may still be added when they support a missing claim, address a newly identified limitation, or provide a necessary comparison.
