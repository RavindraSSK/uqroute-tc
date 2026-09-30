# UQRoute-TC: Uncertainty-Gated Routing and Recovery for Reliable Tool Calling

## Weekly timeline

This is a working schedule for personal progress tracking. Future dates are planning targets and may move if experiments or GPU access require more time.

| Week | Dates | Main task | Focus | Status |
|---|---|---|---|---|
| Week 1 | Sep 7-13 | Task 1 | Project setup, benchmark and Transition audits, literature foundation, and draft protocol | Done |
| Week 2 | Sep 14-20 | Task 1 | Near reproduce a published RobustBench-TC number; create the grouped split, pilot runner, model pilots, and scoped Task 1 freeze (completed Sep 30) | Done, late |
| Week 3 | Sep 21-27 | Task 2 | Canonical tool-call parser | In progress, late: canonical keys and tests committed; saved-output audit pending |
| Week 4 | Sep 28-Oct 4 | Task 2 | Single-sample and repeated-sample uncertainty measures | In progress: CPU measures implemented; token-to-call audit and ten-sample inference pending |
| Week 5 | Oct 5-11 | Task 3 | Clean and static-perturbation experiments | Not started |
| Week 6 | Oct 12-18 | Task 3 | Static-perturbation metrics, held-out evaluation, and failure analysis | Not started |
| Week 7 | Oct 19-25 | Task 4 | Uncertainty gate, fallback routing, and Transition recovery | Not started |
| Week 8 | Oct 26-Nov 1 | Task 4 | Recovery evaluation, routing baselines, and cost analysis | Not started |
| Week 9 | Nov 2-8 | Task 5 | Ablations, final analysis, tables, and figures | Not started |
| Week 10 | Nov 9-15 | Task 5 | Toolkit release, report, presentation, and research-paper preparation | Not started |

A week is marked **Done** only after its completed work and supporting evidence have been committed to the repository.

As of Sep 30, finish the Week 3 saved-output parser audit and Week 4
token-to-call alignment before selecting and generating the repeated-sample
subset. The current four-model five-case results do not contain ten samples
per case, so they cannot validate repeated-sample uncertainty or routing.
