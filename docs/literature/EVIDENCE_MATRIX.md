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
| Benchmark selection | P01, P02 | BFCL provides structured tool-call tasks; RobustBench-TC adds deployment perturbations | No benchmark change proposed | Task 1 selection frozen |
| Evaluation population | P02 and local dataset audit | Released rows, runtime predictions, and canonical groups are distinguished; grouped development/test split validated | Broader development throughput and current quota remain to be measured across models | Task 1 population/split frozen |
| Correctness scoring | P01, P02, P03 and local scorer checks | Structured scoring is separate from parsing and successful inference; near reproduction and diagnostic scores are recorded | Broader Task 3 official correctness scoring remains pending | Scorer pinned; full results pending |
| Single-sample uncertainty | P04–P06 literature review pending; local Task 2 evidence | Three whole-output scores and a scoped meaningful-token score are implemented and frozen | Complete literature justification; evaluate error detection and calibration | Methods frozen; literature and Task 3 effectiveness pending |
| Repeated-sample uncertainty | P04–P06 literature review pending; local Task 2 evidence | Ten-slot canonical/exact-string entropy and disagreement implemented; status policy tested on 900 development slots | Complete literature justification; assess predictive value and sampling overhead | Methods and diagnostic subset frozen; effectiveness pending |
| Canonical-call clustering | P01; P04 review pending; local Task 2 evidence | Type-aware keys follow the pinned parser, with explicit ambiguous/no-call clusters and scoped alignment exclusions | Complete semantic-uncertainty comparison; preserve distinction from correctness | Task 2 definitions frozen; literature synthesis pending |
| Calibration | Pending uncertainty literature | No conclusion established yet | Define confidence mapping and calibration metrics | Pending |
| Risk-coverage analysis | Pending selective-prediction literature | No conclusion established yet | Define coverage, selective risk, and threshold-selection procedure | Pending |
| Routing baselines | Pending routing literature | No conclusion established yet | Finalize fair uncertainty and random-routing comparisons | Pending |
| Cost accounting | Pending routing literature | All model calls must be represented in policy comparisons | Define latency, GPU-time, and cost scenarios | Pending |
| Post-fault recovery | P02, P03 | Runtime feedback occurs after execution and must be analyzed separately | Define bounded recovery policies and complete cost accounting | Defined in draft protocol |

## Implementation-to-paper checkpoints

| Checkpoint | Literature link | Code / local evidence | Protocol location | Paper use and limit |
|---|---|---|---|---|
| Published-number near reproduction and grouped split | P01, P02 | `../PROGRESS.md`; `../splits/group_split_v1.json`; `../config/task1_single_sample_v1.json` | §§3–10 | Methods and reproducibility; 102/199 versus 103/199 is a disclosed near reproduction, not an exact match |
| Frozen parser and uncertainty engine | P01; P04–P06 reviews pending | `../../src/uqroute_tc/parsing/`; `../../src/uqroute_tc/uncertainty/`; `../config/task2_uncertainty_v1.json`; `../config/task2_repeated_sampling_v1.json` | §§11–12 | Implementation and development validation; no demonstrated error-detection or routing advantage yet |
| Qwen 1.5B static throughput diagnostic | P02 supplies the benchmark; cost/routing literature P08–P09 still needs review | `../../src/uqroute_tc/inference/throughput.py`; `../TASK3_THROUGHPUT.md`; `../evidence/qwen15b_throughput_dev69_summary.json` | §15 | Runtime feasibility: 69 development cases, not an accuracy estimate; retain setup and resume overhead separately |
| Llama 3B static throughput diagnostic | Same benchmark/cost links as above | `../../notebooks/UQRoute_TC_Task3_Llama3B_Throughput.ipynb`; `../evidence/llama3b_throughput_dev69_summary.json` | §§10, 15 | Checked summary/session/runtime/log: 69 fresh requests, 61 complete and eight truncated, 508.11 s; raw attempt replay and correctness pending |
| Effective temperature observation | Local server logs, not a published-paper finding | Both model throughput evidence summaries | §§10, 15 | vLLM clamps requested 0.001 to 0.01 in both fresh runs; disclose effective settings and preserve freeze history |

The Llama saved-attempt follow-up in
`../evidence/llama3b_truncation_dev69_audit.json` connects P01's distinction
between extraction and correctness with P03's descriptive failure diagnosis.
All eight truncated records from five groups replay valid token evidence;
six have nonempty saved parser outputs. Extended listings/repetition are local
post hoc observations, not published findings, official correctness or causal
perturbation evidence. Protocol §§12 and 15 retain the status and incurred cost.

The Qwen 7B throughput follow-up in
`../evidence/qwen7b_throughput_dev69_summary.json` adds a fresh 69-request
development diagnostic: 68 complete / one truncated outcome in 661.17 seconds.
The same ToolAlpaca holiday case truncated for Llama; its supplied Qwen token
evidence replays exactly. A function-like call followed by result-like text and
saved holiday-name extractions reinforces the need to separate parsing from
official correctness (P01), while remaining a local descriptive diagnosis
(P03). This adds no correctness, calibration, causal or routing-benefit claim.
Cost/routing literature reviews P08–P09 remain pending; protocol §15 records
the accounting and evidence limitations.

The 14B AWQ diagnostic in
`../evidence/qwen14b_awq_throughput_dev69_summary.json` completes timing
collection for the four frozen models. Five APIBank records contain internal
generated special tokens absent from visible text; the frozen validator
retains unavailable probability scores. Two holiday responses truncate with
valid evidence. This is a local measurement/representation limitation, not
a published-paper result or causal finding about quantization. P04–P06
reviews must distinguish score definitions from evidence availability, while
P08–P09 cost/routing reviews must account for all attempted calls and unavailable
signals. Protocol §15 retains statuses/costs; Task 4 missing-evidence routing
remains to be frozen. Full correctness and routing benefit are unmeasured.

The four-model CPU record audit is summarized in
`../evidence/four_model_static_dev69_record_audit_summary.json`: 276
development responses, 271 with valid token evidence and 260 complete responses
eligible for whole-output scores. Uncertainty values are not correctness
labels. P01/P02 motivate the next pinned official-scoring step with source-file
qualified identities, while P04–P06 justification and effectiveness remain
pending. Qwen 1.5B resume-only overhead is now identified explicitly in session
accounting (protocol §15); cost/routing conclusions still require correctness.
No new literature review or held-out result is claimed.

These local checkpoints do not upgrade any paper to `Reviewed` or establish a
new research gap. Before claiming novelty, complete the relevant routing and
uncertainty reviews and compare question, signal, routing stage, perturbation
setting, and measured outcomes. Model names alone are not a contribution.

## Review quality checks

- Every factual claim identifies its supporting paper or local audit.
- Reported findings are separated from UQRoute-TC interpretations.
- Negative and mixed findings are retained.
- Limitations are recorded before using a paper to justify a decision.
- Closely related work is compared by research question, benchmark, signal, routing stage, and metrics.
- Entries are revised when later evidence changes their interpretation.




