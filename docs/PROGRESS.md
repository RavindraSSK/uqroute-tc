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
- [ ] Freeze the Task 1 protocol.

## Task 2 — Parser and uncertainty engine

- [ ] Implement canonical tool-call parsing.
- [ ] Test equivalent and different tool calls.
- [ ] Implement single-sample uncertainty measures.
- [ ] Verify token-to-call alignment.
- [ ] Implement ten-sample disagreement and entropy.
- [ ] Freeze the parser and uncertainty protocol.

## Task 3 — Robustness study

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
| Ruff | Passed |
| Dependency check | Passed |
| Foundation commit | `ac01cbc` |

## Protocol status

The draft protocol uses 199 clean-anchored groups for the primary population and all 248 single-turn groups for sensitivity analysis. The manifest assigns every group.

Clean results for Qwen 1.5B and Llama 3B and five Qwen 7B clean cases were seen before splitting. Report those clean scores descriptively. Use development groups for tuning and reserve unseen perturbed test cases for confirmatory analysis.

## Next action

Audit the four saved pilot manifests, records, and scores together. The 14B AWQ checkpoint is a feasible fallback candidate; choose and freeze the fallback and remaining Task 1 settings before full experiments or held-out perturbation analysis. Five-case accuracy is descriptive only.

The seeded per-case predictions are not in the pinned release, so the differing Llama case cannot be identified from it. The one-case tolerance was chosen after observing the result and must be disclosed when reporting the reproduction.
