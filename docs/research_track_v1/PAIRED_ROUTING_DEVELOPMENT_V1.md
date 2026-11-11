# Paired development routing diagnostics v1

This CPU subtask follows the owner's successful fallback scoring at `6962586`.
It implements saved-pair development evaluation. The owner subsequently completed
the command at `ca417d1` and supplied the aggregate terminal summary. No final
routing threshold or held-out evaluation is claimed.

Run once from the repository root after pulling `feat/task3-throughput`:

```bash
python tools/development_audits/paired_routing_v1/run_analysis.py
```

No additional upload, model generation or Colab session is required. The command
uses the four existing imported primary-development runs, their existing official
scores, and the preserved primary export/audit sidecars. It names missing inputs
before computation, rejects mismatched fingerprints, and preserves prior outputs.
No prior model request should be repeated to repair an evidence status.

## Evidence and cohort binding

The versioned policy pins the existing routing kernel, all four scorer adapters
and their immutable policies. Each bound scorer revalidates its raw evidence and
recomputes official scores; these must exactly match saved scores and summaries.
The frozen generation workflow also reproduces each full replay and compares all
records and summary fields with its export. Original source/input fingerprints
are checked again before publication and recorded in provenance.

Each of the three small models joins to the fallback on all 1,728 constructed
primary-development cases. The join checks case lineage, benchmark, primary
candidate membership, endpoint, audit flags, and actual prompt/request content
apart from the model field. All 140 clean cases and 1,588 perturbed cases remain
in the corresponding outcome denominators. The 26 construction blocks have no
model outcome and receive no imputed score. Sensitivity cases remain separate.

Invalid/truncated token evidence does not imply incorrect output. Official labels
come from reparsing the original generated text. The gate's parsed-call presence
comes from the frozen canonical parser replay, not the official scorer's parser
call count. Complete parsed small output and finite whole-output mean NLL are
required for acceptance. Missing evidence, truncation or absent parsed calls
force fallback. Fallback is terminal, even if unusable or less reference-compliant;
there is no label-based return to the small response. Fallback token-evidence
eligibility never filters the cohort.

## Diagnostic policies

Reference compliance and ToolEyes name relevance are evaluated separately, with
per-benchmark views. ToolEyes panel and benchmark repeat the same cases and do
not constitute independent evidence. Related clean/perturbed variants remain
dependent within their canonical groups.

The outputs include small-only, fallback-only and always-cascade baselines,
all-pair CC/CI/IC/II counts (small first, fallback second), and every distinct
eligible small-NLL threshold plus accept-none. Inclusive acceptance preserves
entire exact-score ties. Potential rescues are IC pairs and potential harms are
CI pairs; actual gated counts depend on which cases escalate. Aggregate model
accuracy differences alone do not determine either count.

Fixed escalation caps of 0%, 10%, 25%, 50% and 100% provide retrospective views.
The diagnostic cut uses the greatest attainable escalation count within each cap,
without consulting labels, while respecting forced fallback and tie blocks. A cap
below forced escalation is infeasible. Ten fixed seeds (1729–1738) supply random
baselines with exactly the same actual fallback count over the entire cohort.
The random comparator samples cases independently of labels and scores; unlike
the gate, it does not force escalation for unavailable evidence. This distinction
and final-output usability are explicit in the results.

These caps are descriptive choices, not a fitted objective or deployment budget.
Per-benchmark thresholds are exploratory cuts, not selected deployment thresholds.
No best-looking point is selected, group-separated threshold validation performed,
or confidence interval derived from the ten random seeds. Existing calibration
is not refitted and raw NLL is not called a correctness probability.

## Accounting and outputs

Small-only/fallback-only charge one saved attempt per case. Always-cascade
charges two. Gated/random policies charge the small attempt plus each chosen
fallback attempt, including unsuccessful outputs. Saved prompt/completion tokens
and request elapsed seconds are included. Unknown usage retains known sums and
missing-call counts; totals and efficiency ratios remain unavailable when needed.
Elapsed sums are cached request-time proxies, not measured online cascade latency,
billed GPU time or monetary savings. Setup, idle time, recovery, uncertainty
computation and repeated-sampling overhead are not supplied as measured policy
costs by this package.

Fresh ignored output: `artifacts/local_development_audits/paired_routing_development_v1/`.

- `REPORT.md` and `summary.json`: endpoint totals, potential rescues/harms and fixed-cap views.
- `baselines.json`: full baseline accounting and transition counts by model/scope.
- `frontiers.json`: compact per-threshold metrics; no quadratic saved prediction lists.
- `budget_views.json`: gated cuts and every count-matched random run.
- `paired_inputs.json`: normalized per-case labels, evidence, gate scores and usage.
- `provenance.json` and `revalidation/`: policy, source/input hashes and reproduced scores/replays.

An existing output directory is rejected. No original score, reference, label,
raw output or frozen implementation is changed. The command runs 28 new synthetic
checks plus 20 existing routing-kernel checks before accessing model evidence.
Ruff passes on the new implementation/tests. Actual execution requires the
owner's preserved sidecars and all four scoring outputs; those complete inputs
are not available in the working implementation checkout.

Remaining work includes reviewing actual paired diagnostics, recording a fixed
development objective and validating its operating point by canonical group,
complete policy cost measurement, live escalation and post-fault recovery, and
the final shared protocol freeze before separately authorized held-out access.

## Owner execution and aggregate review — 2026-11-11

The supplied successful terminal output reports all 28 new synthetic checks and
20 routing-kernel checks passing, followed by revalidation of all four actual
saved scorers/replays and computation of all 21 model/scope analyses. Output was
published to the expected ignored directory. This records owner execution; the
complete original sidecars and generated policy report are not present in the
working implementation checkout.

| Small model | Endpoint | Rows | Small matches | Fallback matches | IC | CI | Minimum forced fallback |
|---|---|---:|---:|---:|---:|---:|---:|
| Qwen 1.5B | Reference compliance | 1,512 | 572 | 787 | 326 | 111 | 227 |
| Llama 3B | Reference compliance | 1,512 | 621 | 787 | 263 | 97 | 43 |
| Qwen 7B | Reference compliance | 1,512 | 790 | 787 | 141 | 144 | 12 |
| Qwen 1.5B | ToolEyes relevance | 216 | 174 | 208 | 35 | 1 | 2 |
| Llama 3B | ToolEyes relevance | 216 | 181 | 208 | 28 | 1 | 1 |
| Qwen 7B | ToolEyes relevance | 216 | 204 | 208 | 4 | 0 | 0 |

IC denotes small mismatch/fallback match; CI denotes small match/fallback
mismatch. They describe every saved pair, not the cases selected by an uncertainty
gate. All six transition tables sum to their full endpoint denominators, contain
zero unknown labels, and reproduce the model totals; IC minus CI equals the
fallback-minus-small match count. No superiority, execution-success or
cost-saving conclusion follows from these totals.

The Qwen 1.5B reference gate forces at least 227/1,512 fallback calls even at its
most permissive threshold, so a 10% escalation cap is infeasible under this
candidate-acceptance rule. This is an evidence/parser availability constraint,
not a correctness relabeling. Qwen 7B's 141 potential rescues and 144 potential
harms show why its aggregate near tie with fallback does not resolve selective
routing performance.

The terminal summary does not print fixed-cap gated/random metrics or usage
accounting. Review those in the already generated `REPORT.md`, `budget_views.json`
and `baselines.json` before choosing an objective or drawing a policy comparison.
Do not rerun generation or overwrite the existing analysis to retrieve the report.
Held-out access, final readiness and threshold-selection flags remain false;
no inference or monetary-cost measurement was performed.
