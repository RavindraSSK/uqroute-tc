# Main-experiment protocol proposal v1

Status: **proposal; not frozen; no inference or held-out access enabled**.

Baseline: RavindraSSK/uqroute-tc commit 344234f156dd4ea2fc1f6713330cf02ded38d5f1. This addendum proposes a corrected research track. It does not overwrite the released-pipeline reproduction protocol or the Task 1/Task 2 freezes. Configuration: main_experiment_plan_v1.json. Full-population work: DEVELOPMENT_POPULATION_AUDIT_PLAN_V1.md. Source paths and Git blob hashes: source_manifest.json.

## Evidence and scope

The baseline protocol records a primary clean-anchored population and a grouped split with 140 development groups / 1,754 static development rows. These are historical split totals, not newly measured corrected-prompt totals. The sensitivity-only development component is recorded as 34 groups / 35 rows; it remains a separate extension, not silently added to the primary denominator. The 69-case corrected diagnostic and eight-response Qwen smoke do not establish full-development repair coverage, model quality or routing benefit.

The existing split must not be regenerated. The baseline explicitly discloses clean-result exposure before split finalization and limits confirmatory claims to subsequently unseen perturbed cases under a frozen analysis protocol. Keep that limitation: do not describe all clean/test observations as pristine. No split file, held-out record or held-out label was fetched while preparing this proposal.

The recent 69-case audit found 20 reward cells, with explicit cost/latency objectives detected in four and not detected in 16. It also flagged one latest-time-range mismatch, four year-grounding rows and 19 duplicate-reference-name rows. These overlapping review signals were collected after earlier development inspection. They are not exclusions, semantic error labels, full-population rates or preregistration evidence. The audit package is not assumed committed at the baseline unless its source files are verified locally.

## Questions and defensible claims

RQ1 asks whether the frozen uncertainty signals rank official-reference errors under clean and perturbed inputs. RQ2 asks whether escalating requests improves the reference-compliance/cost tradeoff, considering both fallback rescues and harms. The fallback is not assumed better merely because it is larger.

These questions do not establish real tool execution, semantic user-task completion or production reliability. RQ3 post-fault recovery remains separately scoped and unresolved; static reference matching is not recovery evidence.

## Three reporting panels

| Panel | Included observations | Target and interpretation |
| --- | --- | --- |
| Official reference compliance | APIBank, BFCL, RoTBench, ToolAlpaca | Preserve the released Boolean label and exact parser/scorer semantics. Report by benchmark and condition. This is benchmark-reference matching, not execution success. |
| Tool-name relevance | ToolEyes | Preserve name-only matching. Report separately, never pool into a headline argument-correctness measure. |
| Cost/latency preference | CD, CD_AB, CD_NT, TD, TD_AB, TD_NT across their benchmarks | Preserve original preference/reference outcomes. Split objective-detected and objective-not-detected cases; distinguish literal reference preference from user-task semantics. |

The preference panel overlaps reference-compliance observations; do not add panel counts as independent samples. Every observation appears once within its reference-compliance denominator, with objective status as a subgroup. A supplementary all-benchmark released-match table remains available and is explicitly labelled as mixed benchmark outcomes.

No observed reward/reference result is retroactively relabelled. Adding an explicit minimization instruction would create a new prompt version and require fresh generations, not a re-interpretation of v2 outputs. Whether the new prompt version is warranted is a decision to resolve on development data before main evaluation.

## Data and prompt construction

Use canonical base-task identity and the existing group assignments. Audit source-file-qualified keys to prevent collisions across variants. Retain every source row in the inventory, including unresolved repair/reference rows, with explicit status. Define any future exclusion rule and its chronology before applying it; do not remove difficult rows based on model failure or ambiguity alone.

Keep released-pipeline outputs and corrected-track outputs in separate versioned directories. The v2 repair builder, its tests and the eight-case notebook were delivered separately; commit 344234f integrates the analysis/audit tools, not the full repair adapter. Commit and fingerprint the reviewed adapter before full-population preparation. Its current 69-case success cannot be extrapolated to all development rows. Full-development schema repair must fail closed on ambiguous matches, preserve intentional duplicates and reject unknown identity patterns.

Ground truth may support a post-construction reference-consistency audit and scorer. It must never be copied into model-visible input, used to select repairs case by case, or supplied to a deployable gate. Preserve legitimate conversation history while removing only the explicitly defined target answer boundary. APIBank embedded dialogue history requires review independently of top-level role count.

## Models and generation

Retain Qwen 1.5B, Llama 3B and Qwen 7B as principal models and Qwen 14B AWQ as fallback. Revisions, dtypes, quantization and serving settings remain sourced from docs/config/task1_single_sample_v1.json. Preserve requested temperature 0.001, cap 1,024, logprobs/top alternatives and other frozen settings unless a separately logged amendment is made. Record observed server clamping to 0.01 where logs establish it; do not silently rename the requested setting.

Single-sample requests have no automatic retries. Preserve attempt IDs, statuses, interrupted-request uncertainty and all incurred usage. New prompts require new responses from each model used in a comparison; do not transfer previous labels, uncertainty or latency measurements to changed requests.

Record exact request dictionaries, code/config/source hashes, default tokenizer template and revision, raw responses, token bytes/logprobs, usage, finish reasons, timestamps, parser outputs, independent evidence-validation status and official scores. Expected tokenizer rendering is not a capture of actual server token IDs. The smoke notebook did not validate token alignment, so its probabilities are not eligible uncertainty inputs.

## Uncertainty and evidence

Task 2 definitions remain unchanged: sequence NLL, mean-token NLL, max-token surprisal and the scoped meaningful-token measure. The natural-log definitions and larger-is-more-uncertain orientation remain fixed. ToolAlpaca meaningful-token uncertainty stays unavailable under the existing scoped exclusion. Use common eligible cases when comparing multiple signals and report per-signal availability; do not claim availability patterns are random.

A primary-score recommendation is mean-token NLL because whole-output length normalization is useful and it is not restricted to the aligned-call formats. This is a recommendation, not a frozen choice or a claim it wins. Evaluate the frozen alternatives on development data under a recorded selection rule; separately examine length/benchmark confounding. Missing scores remain null with reasons, never zero or a substituted method.

Canonical entropy/disagreement settings remain scoped to the existing 30-case diagnostic. A repeated-sample main subset, extra generations and compute budget require an amendment. No existing repeated responses can be transferred to changed prompts.

## Metrics and denominators

For each benchmark, condition, model and panel, report total selected rows/groups, attempted requests, returned/complete/truncated/error records, official matches, parser states, score eligibility and unavailable reasons. Report missing usage as unknown, never zero. Official scoring includes incomplete/evidence-invalid responses under the released rules and preserves their separate statuses.

Primary candidate metrics are reference compliance, error-positive AUROC, average precision (not trapezoidal PR area), reference-error risk versus accepted coverage, fallback rate, paired rescues/harms and inference accounting. For accepted set A, risk is errors in A divided by size of A; zero accepted cases yield undefined risk. Coverage uses the declared full selected-request denominator; eligibility-conditioned curves must be labelled separately. AP must accompany the error-prevalence baseline. One-class/empty subsets yield unavailable metrics where undefined, not fabricated values.

Propose row-weighted estimates within each panel, per-benchmark estimates and benchmark-macro sensitivity. Specify whether clean and perturbed rows are pooled or stratified; do not let a pooled value conceal benchmark mix or perturbation changes. High-confidence failure thresholds, risk-coverage tie conventions and AURC integration remain to be fixed. Raw uncertainty is not a probability: Brier/ECE require a predeclared development-fitted probability mapping and bin rule, or an explicit documented scope amendment.

## Routing and comparison design

For an eligible score U, a candidate gate accepts at U <= tau and escalates otherwise. Ground truth, perturbation identities not observable at serving time and fault labels must not enter a deployable gate. Model-specific versus shared score transforms/thresholds must be specified before evaluation.

Recommend deterministic grouped cross-validation inside development for measure/threshold decisions, followed by a documented refit/freeze on all approved development groups. Canonical groups, not variants, form folds. An escalation budget or error/cost objective, fold count, seeds, tie handling, infeasibility and no-benefit rules remain unresolved. Do not choose a held-out operating point or assume a feasible gate exists. Missing-score behavior, invalid/truncated output acceptance and fallback terminal behavior require explicit rules; a token-evidence error does not by itself prove an invalid tool call.

Core comparisons should include each small model alone, fallback alone, always-cascade, matched-coverage random routing and the selected uncertainty gate. The baseline protocol also lists global/model-specific gates and oracle diagnostics; record any removal or narrowing as a scope amendment. Oracles are analysis-only and never deployable routing. Random-route seeds and repetitions must be fixed.

Cache one fallback response per identical static request/configuration for fair policy comparisons. Maintain source-key, exact prompt and configuration joins; a recovery request with changed context cannot reuse it. A single cached fallback realization yields conditional policy estimates, not a variance estimate over stochastic generations. Count both rescues and regressions.

## Statistics and cost

Propose a paired, benchmark-stratified canonical-group bootstrap with 10,000 replicates, seed 1729 and 95% percentile intervals. These numbers are proposals. Each resampled group retains all included variants and paired model/policy outcomes. Specify group weighting, absent/small strata, AP/AUROC one-class replicates and tie handling before freezing. A group bootstrap does not prove the selected benchmark mixture represents deployment. Do not bootstrap eight smoke rows as independent tasks.

Count every call required by a policy, including the initial small-model call before escalation, fallback, uncertainty computation, retries/failed attempts and repeated sampling where actually used. Separate request latency, sequential replay estimates, measured cascade latency, batch time, setup/warmup and allocation window. Cached sums do not demonstrate online end-to-end latency or GPU-kernel-active time. Token proxies, wall-hours and monetary scenarios are distinct; price assumptions must be versioned. Cost per match is undefined for zero matches. Missing tokens/timing cannot silently become zero.

## Recovery, sensitivity and study boundaries

RQ3 needs a separate corrected-context recovery protocol, fixed injection templates, bounded attempts, missing-evidence behavior and accounting. Keep the existing rule that transition-labelled records without an actual injected fault are excluded from recovery denominators and reported separately. A simulated injected error is not proof that a real external tool failed or recovered. Sensitivity-only groups lacking clean anchors do not enter RQ3.

The complete single-turn sensitivity population is a separate analysis with its own recorded development membership and denominator. Repeated sampling, calibration and recovery cannot be declared complete by omission. Final scope decisions must acknowledge the original questions and retain their chronology.

## Freeze requirements

The decisions in main_experiment_plan_v1.json are pending. Main inference remains blocked until the full corrected development audit, adapter integration, population accounting, evidence feasibility, gate, baselines, statistics, cost and recovery/repeated-scope decisions are resolved in a separate reviewed freeze artifact. Verify code/config hashes and tests at that commit. Record every change, its rationale, inspected development evidence and exposure chronology.

Only after that freeze may a separately controlled evaluator access the intended held-out perturbed records. No test preview, semantic reference repair, threshold choice, new exclusion or prompt revision is selected on held-out outcomes. Clean-result exposure must remain disclosed. A post-freeze change requires a new version and an explicit claim boundary rather than silent retuning.
