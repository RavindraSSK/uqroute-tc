# UQRoute-TC: Uncertainty-Gated Routing and Recovery for Reliable Tool Calling

## Weekly timeline

This is a working schedule for personal progress tracking. It was rebaselined on September 27, 2026, after the original Week 2 reproduction gate and Week 3 parser target were missed. Future dates are planning targets, subject to GPU access, measured throughput, and the course submission deadline. A later task cannot bypass its prerequisite just because its target week has arrived.

| Week | Dates | Main task | Focus | Status |
|---|---|---|---|---|
| Week 1 | Sep 7-13 | Task 1 | Project setup, benchmark and Transition audits, literature foundation, and draft protocol | Done |
| Week 2 | Sep 14-20 | Task 1 | Published-number reproduction, grouped split, runner, pilot, protocol freeze | Incomplete: reproduction gate not met |
| Week 3 | Sep 21-27 | Task 2 | Canonical tool-call parser | Not started; original target missed |
| Recovery 1 | Sep 28-Oct 4 | Task 1 | Reproduce and independently verify one published benchmark model result; record settings and discrepancy analysis | Planned |
| Recovery 2 | Oct 5-11 | Task 1 | After gate: grouped split and isolation checks, five-case runner, log-probabilities, model pilot, protocol freeze | Planned; depends on gate |
| Recovery 3 | Oct 12-18 | Task 2 | Canonical parser, token alignment, single-sample uncertainty, ten-sample subset definition | Planned |
| Recovery 4 | Oct 19-25 | Tasks 2-3 | Validate uncertainty measures; begin clean and static-perturbation inference with frozen settings | Planned |
| Recovery 5 | Oct 26-Nov 1 | Task 3 | Complete static runs, failure detection, calibration, risk-coverage, held-out analysis | Planned |
| Recovery 6 | Nov 2-8 | Task 4 | Implement frozen routing policies, fallback inference, and separate post-fault recovery | Planned |
| Recovery 7 | Nov 9-15 | Task 4 | Evaluate routing, recovery, baselines, and full inference-cost accounting | Planned |
| Recovery 8 | Nov 16-22 | Task 5 | Ablations, group-aware intervals, failure analysis, reproducible tables and figures | Planned |
| Recovery 9 | Nov 23-29 | Task 5 | Clean-environment check, toolkit and cached demo, capstone report and paper draft | Planned |
| Recovery 10 | Nov 30-Dec 6 | Task 5 | Verify claims; finish report, presentation, and submission-ready paper | Planned |

A week is marked **Done** only after its completed work and supporting evidence have been committed to the repository.

The recovery schedule leaves a short buffer before the stated December 13 graduation date. Confirm the actual course deadline and revise these targets if it is earlier. If the model pilot shows that the full model matrix cannot fit available compute, make a documented scope decision before running the main study; do not present omitted experiments as completed.
