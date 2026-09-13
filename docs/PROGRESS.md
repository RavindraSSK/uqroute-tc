# UQRoute-TC Project Progress

## Current position

Task 1 is in progress.

The project foundation and benchmark population audit are complete. The next work is documenting the evaluation protocol and creating the development/test split.

## Completion standard

Every completed component must include:

1. Working code.
2. Credible evidence.
3. A clear explanation of the decision and its limitations.

## Task 1 — Benchmark and experiment engine

- [x] Create the local `capstone-dev` branch.
- [x] Create the Python package structure.
- [x] Configure the local Python environment.
- [x] Implement base-task identity rules.
- [x] Implement the benchmark population audit.
- [x] Add identity and audit unit tests.
- [x] Pass Ruff, pytest, and dependency checks.
- [x] Create the local foundation commit.
- [ ] Write the evaluation protocol.
- [ ] Select the primary evaluation population.
- [ ] Create grouped development/test partitions.
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

- [ ] Run the model and perturbation experiments.
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

## Pending decision

The proposed primary population is the clean-anchored population containing 2,477 rows and 199 groups.

The complete single-turn population containing 2,527 rows and 248 groups can be used as a sensitivity analysis.

This decision remains provisional until it is documented in the protocol and discussed with the supervisor.

## Next action

Create `docs/PROTOCOL.md`, document the evaluation population, and then implement a reproducible group-level development/test split.
