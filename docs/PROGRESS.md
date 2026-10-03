# UQRoute-TC: Uncertainty-Gated Routing and Recovery for Reliable Tool Calling

## Current position

The reference Llama 3B clean run scored 102/199 against 103/199 on the seeded leaderboard. We accepted the one-case difference as a near reproduction after reviewing the result; the published score was not matched exactly. The split uses dataset identities alone, without model scores.

## Completion standard

Every completed component must include:

1. Working code.
2. Credible evidence.
3. A clear explanation of the decision and its limitations.

## Task 1 — Benchmark and experiment engine

- [x] Create the Python package structure.
- [x] Configure the local Python environment.
- [x] Implement base-task identity rules.
- [x] Implement the benchmark population audit.
- [x] Add identity and audit unit tests.
- [x] Pass Ruff, pytest, and dependency checks.
- [x] Create the local foundation commit.
- [x] Write the draft evaluation protocol.
- [x] Select the primary and sensitivity evaluation populations in the draft protocol.
- [x] Verify a published clean result within one case, with the post hoc tolerance disclosed.
- [x] Create grouped development/held-out partitions.
- [x] Verify partition isolation.
- [x] Implement the resumable five-case experiment runner.
- [x] Capture and validate token log-probabilities on five development cases for each small model.
- [x] Verify scoring and saving in Colab; verify the runner's resume path.
- [x] Confirm that the proposed 14B AWQ fallback serves and yields five valid development records on the L4.
- [x] Freeze the Task 1 benchmark, model, split, and single-sample settings; keep later methods draft.

## Task 2 — Parser and uncertainty engine

- [x] Implement canonical keys for the pinned benchmark parser's tool calls.
- [x] Test equivalent and different tool calls.
- [x] Implement and validate the three whole-output single-sample token measures.
- [x] Review and commit the meaningful-token score for BFCL Python-call output.
- [ ] Verify token-to-call alignment across supported output formats; BFCL, two ReAct responses, two APIBank JSON responses, and one fenced APIBank `<toolcall>` response are checked. A second APIBank `<tool>` response remains unaligned because the saved parser drops its JSON arguments. ToolAlpaca is scoped out of meaningful-token scoring because the saved mixed outputs do not provide trusted call spans. Other APIBank markup and unverified formats remain pending.
- [x] Implement ten-sample canonical-call entropy and disagreement, with exact-string ablation.
- [x] Review and commit the deterministic 30-case development repeated-sample subset.
- [x] Validate ten seeded requests on one selected clean development BFCL case with Qwen 1.5B; all ten user-reported records were complete, byte-aligned, and parsed as calls.
- [x] Complete the selected 30-case development repeated-sample subset for all three small models. Uploaded status-aware audits score all 30 cases for each model.
- [x] Review and freeze the repeated-sample settings and status policy before held-out evaluation. The truncation policy was added after inspecting Qwen 1.5B development outputs and is disclosed as a retrospective development decision.
- [ ] Freeze the parser and uncertainty protocol.

## Task 3 — Robustness study

- [ ] Measure representative per-model throughput and available GPU capacity before full inference.
- [ ] Run the clean and static-perturbation experiments.
- [ ] Calculate accuracy and failure-detection metrics.
- [ ] Analyze risk–coverage and calibration.
- [ ] Catalogue high-confidence failures.
- [ ] Evaluate frozen methods on held-out groups.
- [ ] Calculate group-aware confidence intervals.

## Task 4 — Routing and recovery

- [ ] Implement the uncertainty gate.
- [ ] Implement fallback-model escalation.
- [ ] Implement post-fault recovery.
- [ ] Add complete cost measurement.
- [ ] Implement routing baselines.
- [ ] Freeze thresholds before held-out evaluation.

## Task 5 — Final package

- [ ] Complete the required ablations.
- [ ] Reconstruct figures from saved records.
- [ ] Run a clean-environment test.
- [ ] Package the code and documentation.
- [ ] Build the cached demonstration.
- [ ] Complete the report and presentation.

## Compute readiness

The Colab L4 has served all four pinned models on five development cases each,
including the 14B AWQ fallback. Colab Pro+ and Kaggle T4 are the planned
inference resources; local CPU work covers scoring, analysis, figures, and
writing. No additional GPU has been identified as required by the pilot.

Full-run capacity is not yet measured. Running all four models once on each
of the 2,477 primary static cases would require 9,908 generations. The draft
30-case repeated-sample subset has generated 900 saved slots across the three
small models, before retries, recovery experiments, or other ablations. Run
and time a representative batch for each model, record GPU hours and current
platform quota, then schedule resumable batches. Reassess external compute
only if those measurements show the available resources are insufficient.

## Verified evidence

| Evidence | Result |
|---|---|
| Benchmark revision | `d5d03180de41eb30a6c796d04a9bfbd9dad85c1d` |
| Static JSONL files | 17 |
| Stored rows | 2,718 |
| Excluded multi-turn rows | 191 |
| Single-turn rows | 2,527 |
| Clean-anchored population candidate | 2,477 rows / 199 groups |
| Complete single-turn population | 2,527 rows / 248 groups |
| Perturbation-only population | 50 rows / 49 groups |
| Transition source population | 199 rows / 199 groups from `clean.jsonl` |
| Runtime Transition fault types | 6: `timeout`, `rate_limit`, `auth_error`, `server_error`, `malformed_response`, `schema_drift` |
| Runtime Transition variants | 6 per eligible source row and base-task group |
| Runtime-generated Transition predictions | 1,194 |
| Static Transition storage | 0 rows / 0 files |
| Excluded multi-turn overlap with Transition source | 0 rows |
| Transition-capable groups | 199 in the clean-anchored population / 199 in the full population |
| Full-population groups without a Transition source | 49 |
| Published prediction-total reconciliation | 2,527 + 1,194 = 3,721 predictions per model |
| Llama 3B reference / observed | 103/199 (`0.5176`) / 102/199 (`0.5126`) strict clean accuracy |
| Llama run settings | Model/tokenizer revision `0cb88a4f764b7a12671c53f0838cd831a0843b95`; temperature 0, 16 workers, 1,024 max tokens, BF16, L4, vLLM 0.30.0, PyTorch 2.13.0+cu130 |
| Llama run integrity | 199 unique predictions, 199 scored IDs, no missing or extra clean IDs, 0 inference errors (checked in Colab) |
| Grouped split | `docs/splits/group_split_v1.json`; seed 1729, 70/30 target, benchmark-stratified SHA-256 group ranking |
| Primary split | 140 development / 59 test groups; 1,754 / 723 static rows |
| Sensitivity-only split | 34 development / 15 test groups; 35 / 15 static rows |
| Split validation | 16 tests pass; all 2,527 retained rows map to 248 groups without leakage; manifest regenerates identically |
| Qwen 7B smoke check | Revision `a09a35458c702b33eeacc393d103063234e8bc28`; first five clean BFCL cases scored 5/5 with 0 inference errors. This is a feasibility check, not a full benchmark result. |
| Qwen 7B token evidence | On the same five cases, all calls parsed and all visible-token log-probabilities were finite. Visible token bytes aligned after excluding the trailing `<|im_end|>` token. Saved in Colab Drive. |
| Five-case runner | `src/uqroute_tc/inference/pilot.py` selects clean development cases, records token evidence, writes scorer-compatible output, and resumes without repeating completed cases. The three small-model five-case pilots completed in Colab; Qwen 7B and Qwen 1.5B completion was user-reported, and the Llama 3B final verification message was supplied. No aggregate five-case accuracy is recorded here. |
| Small-model development pilot outputs | Qwen 7B: `pilots/qwen25-7b-dev-five-v1`; Qwen 1.5B: `pilots/qwen25-15b-dev-five-v1`; Llama 3B: `pilots/llama32-3b-dev-five-v1` under `/content/drive/MyDrive/UQRoute-TC/`. These are five-case development checks, not full benchmark reproductions. |
| Llama token-evidence recovery | All five Llama responses had a trailing `<|eot_id|>` log-probability token; excluding it made chosen-token bytes exactly match the visible UTF-8 output. Validator fix `8f919e3` admits this terminator only after exact byte alignment. Original invalid records were backed up by the corrected recovery notebook; the user reported five unique scored-ready records with valid token evidence. |
| Qwen 14B AWQ fallback feasibility | The user reported five unique scored-ready records with valid token evidence on the L4, saved in `pilots/qwen25-14b-awq-feasibility-five-v1`. This establishes a serving/evidence feasibility check only; five cases cannot establish routing benefit or full benchmark accuracy. |
| Task 1 settings freeze | `docs/config/task1_single_sample_v1.json` records all four pinned model/tokenizer revisions and the benchmark/split/generation settings. The fallback revision `539535859b135b0244c91f3e59816150c8056698` was verified against the saved Drive pilot manifest. The 14B notebook is pinned to the same revision for a fresh run. This is a scoped Task 1 freeze; Task 2–4 methods and the full held-out protocol remain draft. |
| Four-model development audit | The user supplied the official case-score comparison for the same five clean development BFCL cases: Qwen 1.5B, Llama 3B, Qwen 7B, and Qwen 14B AWQ each scored 5/5. The fallback rescued 0/5 errors for each small model because all small-model predictions were correct. The audit notebook saved `pilots/four_model_pilot_audit.json` in Drive; the user-supplied table is summarized in `docs/evidence/four_model_five_case_summary.json`. This is a feasibility check, not a routing-effectiveness estimate. |
| Canonical-call prototype | The pinned benchmark parser's output is converted into type-aware keys without altering scorer inputs. A direct compatibility check using the pinned parser found one shared key for equivalent Python, JSON, XML, ReAct, and ToolAlpaca examples. The saved 20-prediction audit found 20 parsed calls matching saved calls and 20 valid single-sample scores. The no-call versus unparsed distinction remains provisional because these cases all parsed as calls. |
| CPU uncertainty measures | Saved chosen-token responses are revalidated for exact visible-byte alignment before computing sequence NLL, mean token NLL, and maximum token surprisal. Ten-output canonical and exact-string clustering computes entropy in nats and disagreement with failed/empty outcomes in the denominator. Uploaded 30-case development audits for all three small models were checked locally; the raw Drive responses were validated in Colab and not uploaded here. |
| BFCL meaningful-token pilot | The 20 saved outputs from four models and five clean development BFCL cases have exact visible-byte alignment after excluding 15 `<|im_end|>` and five `<|eot_id|>` end tokens. The committed AST-to-parser rule accepted all 20; 317 visible tokens overlapped names or values, of which 55 also covered syntax or whitespace. The broader-format rule remains under development. |
| Four-format development diagnostic | Qwen 1.5B produced four complete, byte-aligned records on one clean development case each from APIBank, RotBench, ToolAlpaca, and ToolEyes. The user reported official scores of 0/4. The released parser returned one call each for RotBench and ToolEyes and no call for APIBank and ToolAlpaca. All four were outside the committed BFCL-only meaningful-token rule. A local ReAct draft matched the two saved parsed calls and token streams: RotBench 11 selected / 2 boundary-crossing tokens; ToolEyes 6 / 1. This is a format and failure-case diagnostic, not an accuracy estimate; compact evidence is in `docs/evidence/qwen15b_four_format_development.json`. |
| APIBank and ToolAlpaca format audit | The uploaded 24-case audit contains 12 clean development cases per benchmark, all unique, complete, byte-aligned, and consistent with saved calls. APIBank: 11 parsed, 1 `unparsed_or_no_call`, 7/12 officially correct. ToolAlpaca: 4 parsed, 8 `unparsed_or_no_call`, 1/12 correct. A local APIBank JSON rule aligned two exported calls: 50 and 14 selected tokens, both with 0 boundary crossings. Two exported ToolAlpaca outputs mix prose and examples; one scored correct because its expected call was present alongside two example country names that the parser also treated as calls. Neither ToolAlpaca output has a trusted meaningful-token span. These file-order development counts are descriptive; compact evidence is in `docs/evidence/apibank_toolalpaca_format_alignment.json`. |
| APIBank markup alignment diagnostic | Two further saved, byte-aligned APIBank development responses were exported from the same 24-case run. A bounded rule aligned one fenced `<toolcall>` response with its saved parsed call: 45 selected tokens and zero boundary crossings. The other response uses `<tool>` and includes JSON arguments, but its saved parsed call has empty parameters. Its meaningful-token score remains unavailable. This does not establish wider markup coverage; the official parser remains unchanged. Compact evidence: `docs/evidence/apibank_markup_alignment.json`. |
| Repeated-sample subset | The committed selector identifies 15 development groups and 30 clean/perturbed cases. The user reported ten valid Qwen 1.5B BFCL pilot responses with canonical clusters `(9, 1)`. The uploaded Qwen 1.5B status-aware audit reports 300 saved slots: 299 complete and one truncated, with all 30 cases scored and zero validation-error cases. The clean RoTBench case retains its truncated slot in the ten-sample denominator; its canonical entropy is `2.0253` nats and disagreement `0.8`. All 29 previously scored cases match the first uploaded audit on reported score fields. Parser statuses total 252 `calls` and 48 `unparsed_or_no_call`; these are not correctness labels. The raw Drive records were validated by the Colab audit, but only its two uploaded audit summaries were inspected locally. Compact evidence: `docs/evidence/qwen15b_repeated_dev30_summary.json`. |
| Llama 3B repeated-sample run | The uploaded status-aware audit uses the same 30 selected development cases, split, and ten seeds as Qwen 1.5B. It reports 300 slots: 297 complete and three truncated, with 30/30 cases scored and zero validation-error cases. The three truncations occur in two RoTBench cases and one ToolEyes case, with their slots retained as explicit outcomes. Local checks confirmed unique case identities, settings, totals, and canonical score arithmetic; raw Drive records were validated in Colab but not uploaded. Parser statuses total 251 `calls` and 49 `unparsed_or_no_call`; these and the clusters do not measure official correctness. Compact evidence: `docs/evidence/llama3b_repeated_dev30_summary.json`. |
| Qwen 7B repeated-sample run | The uploaded status-aware audit uses the same 30 selected development cases, split, and ten seeds as the other small models. It reports 300 complete slots, 30/30 cases scored, and zero validation-error cases. Local checks confirmed unique case identities, settings, totals, and canonical score arithmetic; raw Drive records were validated in Colab but not uploaded. Parser statuses total 251 `calls` and 49 `unparsed_or_no_call`; these are not correctness labels. Compact evidence: `docs/evidence/qwen7b_repeated_dev30_summary.json`. |
| Three-model repeated-sample development total | The three uploaded audits account for 900 saved model responses on 30 shared cases: 896 complete, four truncated, and 90/90 model–case cluster scores with zero reported validation-error cases. The per-model records remain distinct; these diagnostic cluster scores do not establish tool-call accuracy, detection quality, or a routing threshold. |
| Repeated-sample settings and status freeze | `docs/config/task2_repeated_sampling_v1.json` fixes the development-only 30-case subset, ten seeds, generation parameters, ten-slot denominators, parser-status clusters, truncation/error handling, and exact-string ablation. This decision follows inspection of all three development audits; the truncation rule followed inspection of Qwen 1.5B outputs. Parser/alignment and the full Task 2 protocol remain open. |
| Saved-output audit | `src/uqroute_tc/parsing/audit.py` and `notebooks/UQRoute_TC_Task2_Saved_Pilot_Audit.ipynb` audited four saved five-case pilot folders on a CPU runtime. The user supplied the 20-record audit showing 20 parser statuses `calls`, 20 saved-call matches, and 20 valid single-sample scores. |
| Ruff | Passed on the previous committed gate; unavailable locally for the current draft. |
| Dependency check | Passed |
| Foundation commit | `ac01cbc` |

## Protocol status

The Task 1 subset is frozen: 199 clean-anchored groups for the primary
population, all 248 single-turn groups for sensitivity analysis, the grouped
split manifest, four model revisions/roles, and single-sample serving settings.
The full protocol is still draft until parser, uncertainty, routing, and
held-out analysis decisions are frozen.

Clean results for Qwen 1.5B and Llama 3B and five Qwen 7B clean cases were seen before splitting. Report those clean scores descriptively. Use development groups for tuning and reserve unseen perturbed test cases for confirmatory analysis.

## Next action

Task 1 settings and the repeated-sample diagnostic settings/status policy are frozen, with the 14B AWQ checkpoint as the feasible fallback candidate. ToolAlpaca meaningful-token uncertainty is scoped out following the saved-output audit; whole-output scores remain available. Finish the remaining parser/alignment validation and freeze the rest of Task 2 methods before held-out evaluation. Then measure representative throughput and run the broader clean and perturbation inference. Keep held-out perturbation groups untouched until methods and thresholds are frozen. The five-case pilot did not test whether escalation helps.

The seeded per-case predictions are not in the pinned release, so the differing Llama case cannot be identified from it. The one-case tolerance was chosen after observing the result and must be disclosed when reporting the reproduction.
