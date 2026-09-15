# UQRoute-TC: Uncertainty-Gated Routing and Recovery for Reliable Tool Calling

## Current position

Task 1 is in progress.

The project foundation, benchmark population audits, draft evaluation protocol, and primary/sensitivity population selection are complete. The next gate is to reproduce one published RobustBench-TC number. The grouped development/held-out split begins only after that result is independently verified.

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
- [ ] Reproduce one published RobustBench-TC number.
- [ ] Create grouped development/held-out partitions.
- [ ] Verify partition isolation.
- [ ] Build the five-case experiment runner.
- [ ] Capture and validate token log-probabilities.
- [ ] Verify scoring, saving, and resume behavior.
- [ ] Run the model-feasibility pilot.
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
| Unit tests | 11 passed |
| Ruff | Passed |
| Dependency check | Passed |
| Foundation commit | `ac01cbc` |

## Protocol status

The draft protocol selects the clean-anchored population containing 2,477 rows and 199 groups as the primary population and the complete single-turn population containing 2,527 rows and 248 groups as the sensitivity population.

These selections remain subject to supervisor review and the Task 1 protocol freeze.

## Next action

Reproduce and independently verify one published RobustBench-TC number. Only after that gate passes, create the reproducible group-level development/held-out split.
