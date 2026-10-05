# UQRoute-TC: Uncertainty-Gated Routing and Recovery for Reliable Tool Calling

## Weekly timeline

This schedule tracks the project milestones. Dates are planning targets and may move as experiments progress.

| Week | Dates | Main task | Focus | Status |
|---|---|---|---|---|
| Week 1 | Sep 7-13 | Task 1 | Project setup, benchmark and Transition audits, literature foundation, and draft protocol | Done |
| Week 2 | Sep 14-20 | Task 1 | Near reproduction of a published RobustBench-TC result, grouped split, pilot runner, model pilots, and scoped Task 1 freeze | Done |
| Week 3 | Sep 21-27 | Task 2 | Canonical tool-call parser | Done |
| Week 4 | Sep 28-Oct 4 | Task 2 | Single-sample and repeated-sample uncertainty measures; scoped method freeze | Done |
| Week 5 | Oct 5-11 | Task 3 | Representative model throughput measurement and broader clean/static-perturbation development batches | Next |
| Week 6 | Oct 12-18 | Task 3 | Static-perturbation metrics, held-out evaluation, and failure analysis | Not started |
| Week 7 | Oct 19-25 | Task 4 | Uncertainty gate, fallback routing, and Transition recovery | Not started |
| Week 8 | Oct 26-Nov 1 | Task 4 | Recovery evaluation, routing baselines, and cost analysis | Not started |
| Week 9 | Nov 2-8 | Task 5 | Ablations, final analysis, tables, and figures | Not started |
| Week 10 | Nov 9-15 | Task 5 | Toolkit release, report, presentation, and research-paper preparation | Not started |

A week is marked **Done** only after its completed work and supporting evidence have been committed to the repository.

Current focus: measure representative development throughput on the L4 for
Qwen 1.5B, Llama 3B, Qwen 7B, and the Qwen 14B AWQ fallback, then plan
resumable development batches. Task 1 and Task 2 are complete within their
recorded scope. The three small models each have a scored 30-case repeated
development diagnostic; held-out evaluation and routing calibration remain
pending. The five-case pilots establish inference and evidence feasibility.
