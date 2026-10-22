# UQRoute-TC: Uncertainty-Gated Routing and Recovery for Reliable Tool Calling

## Current position

Task 1 and Task 2 are complete within their recorded scope. The benchmark,
split, model settings, parser, and uncertainty definitions are frozen.
Task 2 was approved and published in
[`b03ddf4`](https://github.com/RavindraSSK/uqroute-tc/commit/b03ddf49eacfebeff69ca65014e5b0a36e708c40),
with 53 tests passing in the local Windows verification.

| Stage | Status |
|---|---|
| Task 1 — Benchmark and experiment engine | Complete; settings frozen |
| Task 2 — Parser and uncertainty engine | Complete; methods frozen with scoped format exclusions |
| Task 3 — Robustness study | Four-model timing artifacts checked; full saved-record audit, correctness and broader evaluation pending |
| Task 4 — Routing and recovery | Pending |
| Task 5 — Final package | Pending |

The reference Llama 3B clean run scored 102/199 against 103/199 on the seeded leaderboard. We accepted the one-case difference as a near reproduction after reviewing the result; the published score was not matched exactly. The split uses dataset identities alone, without model scores.

Task 2 has working single-sample and repeated-sample measures, with scoped
development evidence for the conservative alignment rules. The expanded
APIBank rule has been re-audited on all 24 saved APIBank/ToolAlpaca format
responses. The recorded exclusions remain part of the frozen methods:
ToolAlpaca has no meaningful-token score, and unsupported or ambiguous
formats retain an unavailable status. Qwen 1.5B has a checked 69-case
development throughput diagnostic. Llama 3B has a checked fresh 69-request run:
61 complete and eight truncated outcomes in 508.11 seconds. Both fresh server
logs show requested temperature 0.001 clamped to 0.01; this effective setting
must be disclosed without rewriting the frozen request configuration.
Qwen 7B has a checked fresh 69-request run: 68 complete and one truncated
outcome in 661.17 seconds. The 14B AWQ fallback has 62 complete, five
invalid-evidence and two truncated outcomes in 480.57 seconds. The invalid
records contain internal generated special tokens absent from visible text;
the frozen validator correctly leaves their probability scores unavailable.
Held-out perturbed
evaluation has not begun. Literature review completion remains separate from
these implementation milestones; see `docs/literature/EVIDENCE_MATRIX.md`.

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
- [x] Verify conservative token-to-call alignment for supported BFCL, single-action ReAct, and bounded APIBank formats. The full 24-record APIBank/ToolAlpaca re-audit gives 10/12 eligible APIBank outputs, with the eight previously valid scores unchanged and zero validation errors or regressions. The APIBank `<tool>` response remains ineligible because the saved parser drops its JSON arguments; one further APIBank response has no parsed call. ToolAlpaca remains outside meaningful-token scoring. This is scoped development evidence, not general format coverage.
- [x] Implement ten-sample canonical-call entropy and disagreement, with exact-string ablation.
- [x] Review and commit the deterministic 30-case development repeated-sample subset.
- [x] Validate ten seeded requests on one selected clean development BFCL case with Qwen 1.5B; all ten user-reported records were complete, byte-aligned, and parsed as calls.
- [x] Complete the selected 30-case development repeated-sample subset for all three small models. Uploaded status-aware audits score all 30 cases for each model.
- [x] Review and freeze the repeated-sample settings and status policy before held-out evaluation. The truncation policy was added after inspecting Qwen 1.5B development outputs and is disclosed as a retrospective development decision.
- [x] Approve and publish the parser and uncertainty freeze in `docs/config/task2_uncertainty_v1.json` at commit `b03ddf4`. It pins the implementation fingerprints, score formulas, format eligibility, and unavailable-evidence rules. The full patched suite passed 53 tests on Windows. ReAct duplicate JSON keys are rejected; Task 3–4 analysis, calibration, routing, and recovery decisions remain draft.

## Task 3 — Robustness study

- [ ] Measure representative per-model throughput and available GPU capacity before full inference.
- [x] Implement the separate development-only throughput runner; user verified 68 tests and Ruff on Windows.
- [x] Check supplied Qwen 1.5B manifest, original summary, runtime metadata and server log; retain the resume-accounting limitation.
- [x] Verify Llama 3B and Qwen 7B timing artifacts and replay their supplied truncated token evidence.
- [x] Verify 14B AWQ timing artifacts and replay all seven supplied non-complete records without changing frozen validation.
- [ ] Audit all 276 saved model–case records and record current platform quota before scheduling broader inference.
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
of the 2,477 primary static cases would require 9,908 generations. The frozen
30-case repeated-sample subset has generated 900 saved slots across the three
small models, before retries, recovery experiments, or other ablations. Run
and time a representative batch for each model, record GPU hours and current
platform quota, then schedule resumable batches. Reassess external compute
only if those measurements show the available resources are insufficient.

## Verified evidence

| Evidence | Result |
|---|---|
| Qwen 1.5B throughput diagnostic | 69 primary development cases (5 clean / 64 perturbed), 51 canonical groups, 69 nonempty benchmark/file strata, 17 files. Original summary reports 69 complete attempts in 106.46709268199993 s, with 74,949 prompt and 7,164 completion tokens; observed GPU window at least 769.8995201580001 s. Settings/source fingerprints, split membership, arithmetic and 69 HTTP-200 generation requests checked. Raw attempt evidence was not locally replayed; official correctness is unscored. See `docs/evidence/qwen15b_throughput_dev69_summary.json`. |
| Throughput resume limitation | Later pasted aggregate has 2 sessions, the same 69 attempts/tokens, and 208.10106126399978 s total session wall time. Aggregate rate includes checking overhead; retain the original run for fresh timing. Later per-session processed/resumed records still need inspection. |
| Task 3 runner and Llama timing | Runner published at `adb48d1`; user verified 68 tests and Ruff. Llama-specific notebook at `d031146` produced 69 fresh requests: 61 complete, eight truncated, 508.107638493 s; 76,347 prompt / 18,056 completion tokens. Manifest/session/runtime/log checked, including 69 HTTP 200 responses; the eight truncations were subsequently replayed as recorded below. Raw replay of 61 complete responses and correctness remain pending. See `docs/evidence/llama3b_throughput_dev69_summary.json`. |
| Server temperature observation | Fresh Qwen and Llama logs each contain 69 warnings: requested temperature 0.001 is clamped to 0.01 by the server. Frozen request settings are preserved; effective settings must accompany reported results. |
| Llama truncation evidence replay | Uploaded archive contains the 69-row compact audit and eight full truncated attempts: four ToolAlpaca / four RoTBench, across five base-task groups. All eight finish at length 1,024; pinned token-evidence replay matches every saved dictionary and reconstructed original-record hashes match the audit. Patterns: three holiday lists, two racing lists, one country example, two repetitive result-like outputs. Six have nonempty saved parser outputs, illustrating that extraction does not establish correctness. Truncations consumed 8,192/18,056 completion tokens and 229.56 s measured attempt time. Official correctness and raw replay of the other 61 responses remain pending. See `docs/evidence/llama3b_truncation_dev69_audit.json`. |
| Benchmark revision | `d5d03180de41eb30a6c796d04a9bfbd9dad85c1d` |
| 14B AWQ throughput diagnostic | 69 fresh requests on the same development cases; 62 complete, five invalid-evidence and two truncated outcomes. Batch wall 480.565455616 s; 74,949 prompt / 12,067 completion tokens; observed GPU window at least 1,018.707215394 s. Manifest/configuration, split membership, arithmetic and 69 HTTP 200 responses checked. Frozen validator replay matches all seven supplied non-complete records. Five APIBank cases across three groups contain internal `<\|im_start\|>` tokens omitted from visible text; probability scores remain unavailable. Two ToolAlpaca holiday cases from one group truncate at 1,024 tokens with valid evidence. No automatic repair/retry; official correctness unscored. See `docs/evidence/qwen14b_awq_throughput_dev69_summary.json`. |
| Four-model timing diagnostic total | Summaries account for 276 model–case attempts: 260 complete, 11 truncated and five invalid-evidence. This is inference/evidence accounting, not accuracy. Full raw-record audit remains pending; complete response counts do not establish routing benefit. |
| Qwen 7B throughput diagnostic | Same 69 case identities as the Llama audit, all primary development, 51 groups; fresh session processed 69 and resumed zero. Summary: 68 complete / one truncated, 661.167963701 s batch wall, 74,949 prompt / 11,226 completion tokens. Manifest, split membership, summary arithmetic and 69 HTTP 200 responses checked. All 69 server warnings clamp requested temperature 0.001 to 0.01. The one supplied truncated record reaches 1,024 tokens and its token evidence replays exactly; it is the ToolAlpaca holiday case in `paraphrase_tool_description.jsonl`, also truncated for Llama. The other 68 raw records and official correctness are unreviewed/unscored. Evidence: `docs/evidence/qwen7b_throughput_dev69_summary.json`. |
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
| Task 1 settings freeze | `docs/config/task1_single_sample_v1.json` records all four pinned model/tokenizer revisions and the benchmark/split/generation settings. The fallback revision `539535859b135b0244c91f3e59816150c8056698` was verified against the saved Drive pilot manifest. The 14B notebook is pinned to the same revision for a fresh run. At this scoped Task 1 freeze, Task 2–4 methods and the full held-out protocol were still draft. |
| Four-model development audit | The user supplied the official case-score comparison for the same five clean development BFCL cases: Qwen 1.5B, Llama 3B, Qwen 7B, and Qwen 14B AWQ each scored 5/5. The fallback rescued 0/5 errors for each small model because all small-model predictions were correct. The audit notebook saved `pilots/four_model_pilot_audit.json` in Drive; the user-supplied table is summarized in `docs/evidence/four_model_five_case_summary.json`. This is a feasibility check, not a routing-effectiveness estimate. |
| Canonical-call implementation | The pinned benchmark parser's output is converted into type-aware keys without altering scorer inputs. A direct compatibility check using the pinned parser found one shared key for equivalent Python, JSON, XML, ReAct, and ToolAlpaca examples. The saved 20-prediction audit found 20 parsed calls matching saved calls and 20 valid single-sample scores. The frozen parser-status policy keeps nonempty outputs without calls in an explicit `unparsed_or_no_call` cluster without inferring whether no tool was intended. |
| CPU uncertainty measures | Saved chosen-token responses are revalidated for exact visible-byte alignment before computing sequence NLL, mean token NLL, and maximum token surprisal. Ten-output canonical and exact-string clustering computes entropy in nats and disagreement with failed/empty outcomes in the denominator. Uploaded 30-case development audits for all three small models were checked locally; the raw Drive responses were validated in Colab and not uploaded here. |
| BFCL meaningful-token pilot | The 20 saved outputs from four models and five clean development BFCL cases have exact visible-byte alignment after excluding 15 `<|im_end|>` and five `<|eot_id|>` end tokens. The committed AST-to-parser rule accepted all 20; 317 visible tokens overlapped names or values, of which 55 also covered syntax or whitespace. The broader-format rule remains under development. |
| Four-format development diagnostic | Qwen 1.5B produced four complete, byte-aligned records on one clean development case each from APIBank, RotBench, ToolAlpaca, and ToolEyes. The user reported official scores of 0/4. The released parser returned one call each for RotBench and ToolEyes and no call for APIBank and ToolAlpaca. All four were outside the committed BFCL-only meaningful-token rule. A local ReAct draft matched the two saved parsed calls and token streams: RotBench 11 selected / 2 boundary-crossing tokens; ToolEyes 6 / 1. This is a format and failure-case diagnostic, not an accuracy estimate; compact evidence is in `docs/evidence/qwen15b_four_format_development.json`. |
| APIBank and ToolAlpaca format audit | The uploaded 24-case audit contains 12 clean development cases per benchmark, all unique, complete, byte-aligned, and consistent with saved calls. APIBank: 11 parsed, 1 `unparsed_or_no_call`, 7/12 officially correct. ToolAlpaca: 4 parsed, 8 `unparsed_or_no_call`, 1/12 correct. A local APIBank JSON rule aligned two exported calls: 50 and 14 selected tokens, both with 0 boundary crossings. Two exported ToolAlpaca outputs mix prose and examples; one scored correct because its expected call was present alongside two example country names that the parser also treated as calls. Neither ToolAlpaca output has a trusted meaningful-token span. These file-order development counts are descriptive; compact evidence is in `docs/evidence/apibank_toolalpaca_format_alignment.json`. |
| APIBank markup alignment diagnostic | Two further saved, byte-aligned APIBank development responses were exported from the same 24-case run. A bounded rule aligned one fenced `<toolcall>` response with its saved parsed call: 45 selected tokens and zero boundary crossings. The other response uses `<tool>` and includes JSON arguments, but its saved parsed call has empty parameters. Its meaningful-token score remains unavailable. This does not establish wider markup coverage; the official parser remains unchanged. Compact evidence: `docs/evidence/apibank_markup_alignment.json`. |
| Saved alignment eligibility audit | The 24 saved Qwen 1.5B APIBank/ToolAlpaca development records were rechecked on CPU. All 24 were complete with valid token bytes and matched the pinned parser and prior audit. APIBank: 8/12 received valid meaningful-token scores with zero boundary-crossing tokens; three parsed outputs did not match a supported complete-call format, and one had no parsed call. ToolAlpaca: 0/12 eligible under its scoped exclusion. This file-order diagnostic does not estimate population coverage or correctness. Compact evidence: `docs/evidence/qwen15b_alignment_coverage_dev24_summary.json`. |
| Remaining APIBank format replay | Two of the three parsed APIBank outputs marked unsupported in the first 24-case audit were exported with full chosen-token evidence. One has prose before a single fenced JSON call; the other has a separate fenced thought block before one JSON call. A narrow rule matched their saved parsed calls and exact UTF-8 token bytes, selecting five tokens per response with zero boundary crossings. The third parsed output, `<tool>GetUserToken</tool>`, remains unavailable because the released parser drops its arguments. These two cases were selected after the first coverage audit; the expanded rule was subsequently rechecked on all 24 saved outputs. Compact evidence: `docs/evidence/apibank_remaining_alignment.json`. |
| Expanded alignment re-audit | The uploaded v2 audit reports 24 unique complete development records, valid token evidence and saved-parser agreement for all 24, and zero validation-error cases. APIBank eligibility increases from 8/12 to 10/12; only `apibank__level3_26` and `apibank__level1_217` become eligible. All eight previously valid scores remain unchanged; no case regresses. The ten eligible APIBank outputs have zero boundary-crossing tokens. ToolAlpaca remains 0/12 eligible. Local checks verified the uploaded report's identities, counts, comparison fields, split membership, and exact notebook-script fingerprint. Full responses were revalidated in Colab; eight earlier raw exports were replayed locally. Compact evidence: `docs/evidence/qwen15b_alignment_reaudit_dev24_summary.json`. These are development eligibility counts, not correctness or population coverage. |
| Repeated-sample subset | The committed selector identifies 15 development groups and 30 clean/perturbed cases. The user reported ten valid Qwen 1.5B BFCL pilot responses with canonical clusters `(9, 1)`. The uploaded Qwen 1.5B status-aware audit reports 300 saved slots: 299 complete and one truncated, with all 30 cases scored and zero validation-error cases. The clean RoTBench case retains its truncated slot in the ten-sample denominator; its canonical entropy is `2.0253` nats and disagreement `0.8`. All 29 previously scored cases match the first uploaded audit on reported score fields. Parser statuses total 252 `calls` and 48 `unparsed_or_no_call`; these are not correctness labels. The raw Drive records were validated by the Colab audit, but only its two uploaded audit summaries were inspected locally. Compact evidence: `docs/evidence/qwen15b_repeated_dev30_summary.json`. |
| Llama 3B repeated-sample run | The uploaded status-aware audit uses the same 30 selected development cases, split, and ten seeds as Qwen 1.5B. It reports 300 slots: 297 complete and three truncated, with 30/30 cases scored and zero validation-error cases. The three truncations occur in two RoTBench cases and one ToolEyes case, with their slots retained as explicit outcomes. Local checks confirmed unique case identities, settings, totals, and canonical score arithmetic; raw Drive records were validated in Colab but not uploaded. Parser statuses total 251 `calls` and 49 `unparsed_or_no_call`; these and the clusters do not measure official correctness. Compact evidence: `docs/evidence/llama3b_repeated_dev30_summary.json`. |
| Qwen 7B repeated-sample run | The uploaded status-aware audit uses the same 30 selected development cases, split, and ten seeds as the other small models. It reports 300 complete slots, 30/30 cases scored, and zero validation-error cases. Local checks confirmed unique case identities, settings, totals, and canonical score arithmetic; raw Drive records were validated in Colab but not uploaded. Parser statuses total 251 `calls` and 49 `unparsed_or_no_call`; these are not correctness labels. Compact evidence: `docs/evidence/qwen7b_repeated_dev30_summary.json`. |
| Three-model repeated-sample development total | The three uploaded audits account for 900 saved model responses on 30 shared cases: 896 complete, four truncated, and 90/90 model–case cluster scores with zero reported validation-error cases. The per-model records remain distinct; these diagnostic cluster scores do not establish tool-call accuracy, detection quality, or a routing threshold. |
| Repeated-sample settings and status freeze | `docs/config/task2_repeated_sampling_v1.json` fixes the development-only 30-case subset, ten seeds, generation parameters, ten-slot denominators, parser-status clusters, truncation/error handling, and exact-string ablation. This decision followed inspection of all three development audits; the truncation rule followed inspection of Qwen 1.5B outputs. Parser and uncertainty definitions are recorded separately in `docs/config/task2_uncertainty_v1.json`. |
| Task 2 method freeze | Approved and published at `b03ddf4`. `docs/config/task2_uncertainty_v1.json` records the pinned official parser, type-aware canonical keys, three whole-output scores, the scoped meaningful-token score, repeated-sample definitions, and unavailable-evidence rules. The freeze rejects duplicate ReAct JSON keys, including nested keys, before meaningful-token scoring. All 31 focused parser/uncertainty tests pass, and the user verified the full patched suite on Windows with 53 tests passing. A local replay of 30 available saved raw responses preserves all 27 eligible scores and three unavailable outcomes. The source hashes and development decision context are recorded in the configuration. Held-out analysis and routing choices remain draft. |
| Saved-output audit | `src/uqroute_tc/parsing/audit.py` and `notebooks/UQRoute_TC_Task2_Saved_Pilot_Audit.ipynb` audited four saved five-case pilot folders on a CPU runtime. The user supplied the 20-record audit showing 20 parser statuses `calls`, 20 saved-call matches, and 20 valid single-sample scores. |
| Source/test maintenance verification | `python -m ruff check src tests` passes with Ruff 0.16.10, and `python -m pytest -q` passes all 53 tests on Python 3.12. A saved 30-response replay retains all 27 eligible scores and three unavailable outcomes. The original freeze is preserved; `docs/config/task2_implementation_maintenance_v1.json` records the behavior-preserving lint changes and updated implementation hashes. |
| Dependency check | Passed |
| Foundation commit | `ac01cbc` |

## Protocol status

The Task 1 subset is frozen: 199 clean-anchored groups for the primary
population, all 248 single-turn groups for sensitivity analysis, the grouped
split manifest, four model revisions/roles, and single-sample serving settings.
Task 2 definitions are frozen in `docs/config/task2_uncertainty_v1.json`
by the approved, published commit `b03ddf4`. The full protocol remains
draft until calibration, routing, recovery, cost, and held-out analysis
decisions are frozen.

Clean results for Qwen 1.5B and Llama 3B and five Qwen 7B clean cases were seen before splitting. Report those clean scores descriptively. Use development groups for tuning and reserve unseen perturbed test cases for confirmatory analysis.

## Next action

Run `notebooks/UQRoute_TC_Task3_Four_Model_Record_Audit.ipynb` on CPU to
validate all 276 saved model–case records, replay frozen token evidence,
reconcile usage/session accounting, and export eligible whole-output scores.
Retain five fallback evidence failures and all 11 truncations; internal-marker
filtering is outside the frozen rule and is not applied. Then perform official
correctness evaluation before assessing uncertainty effectiveness or routing.
All four timing artifacts are checked; a later resume must not be reported
as fresh inference or replace the original speed measurement. Record individual
session outcomes, setup/observed allocation time, tokens, and current quota.
Use those measurements to schedule resumable development inference batches.
Keep literature/protocol/evidence links synchronized before drafting paper claims.

Use the frozen model and single-sample settings. Complete the broader
development clean and perturbation runs before selecting calibration and
gate thresholds. Keep held-out perturbation groups untouched until the
remaining analysis and routing decisions are frozen. The five-case pilot did
not test whether escalation helps.

The seeded per-case predictions are not in the pinned release, so the differing Llama case cannot be identified from it. The one-case tolerance was chosen after observing the result and must be disclosed when reporting the reproduction.



