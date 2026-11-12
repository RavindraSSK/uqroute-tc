# Close the matched smoke with a reference-preserving behaviour review

The owner completed paired reference scoring at `1cf2bd7`; all 24 tests passed,
and original small scores reproduced exactly. All thirty pairs remain.

| Endpoint | Rows / groups | Small matches | Fallback matches | Gained | Lost |
|---|---:|---:|---:|---:|---:|
| Reference compliance | 24 / 4 | 4 | 10 | 6 | 0 |
| ToolEyes name relevance | 6 / 1 | 3 | 3 | 2 | 2 |

Reference gains occur under server error (three), malformed response (two) and
timeout (one). Auth/rate-limit reference matches remain zero; schema-drift stays
at two. ToolEyes gains occur under rate limit and timeout, with losses under
schema drift and server error. These are owner-reported reference diagnostics,
not independently recomputed correctness or executed recovery in this checkout.

Across the saved text, the following structural transitions were independently
verified using the frozen parser. Their joins to scores still require the
owner's paired records; the two sets of six must not be assumed identical.

| Small-to-fallback structure | Episodes |
|---|---:|
| Neither parsed | 5 |
| Small no call to fallback call | 6 |
| Small call to fallback no call | 1 |
| Identical canonical calls | 2 |
| Same names, changed arguments | 6 |
| Changed names | 10 |

## Owner review complete

The existing completed output was preserved when a repeat command stopped.
The owner supplied its aggregate report: five of six primary-panel reference
gains are no-call-to-call changes and one is changed names. A sixth no-call-to-call
change remains a mismatch. Primary both-match rows are two identical calls and
two same-name argument changes; fourteen pairs mismatch under both models.
ToolEyes has two gained and two lost name-relevance matches, all with changed
names; its both-match/both-mismatch pairs both change arguments. All six initial
control-name episodes remain. These supplied score joins are owner-reported;
only structural totals are independently verified in this checkout.

The bounded smoke is closed. Run
[remaining development preparation](RECOVERY_REMAINING_DEVELOPMENT_V1.md) next.
The command below is retained for fresh reproduction; do not rerun completed
review or overwrite its outputs.

## Final smoke review on CPU

```bash
python tools/development_audits/recovery_matched_smoke_review_v1/review_pairs.py
```

This joins the unchanged reference outcomes to structural transitions, then
writes every original task/fault/small/fallback example to a private review.
It retains all thirty cases, including control actions, no calls, matches and
mismatches. It does not assign semantic correctness, rewrite scores or select an
uncertainty threshold. A no-call-to-call change is not automatically beneficial.

Before joining, the command reexecutes the paired scorer into a fresh nested
output. Records, summary and provenance must match the original paired scores
byte for byte. That scorer itself verifies both imports, all request contexts,
source/runtime hashes and original small-score reproduction. All verified input
fingerprints are checked again before output publication. Generic workflow
imports remain scoped to their verified source checkouts.

Fresh ignored output:
`artifacts/local_development_audits/recovery_matched_smoke_behaviour_review_v1/`.

- `REPORT.md` and `summary.json`: aggregate transition/outcome tables, with separate
  reference and ToolEyes panels.
- `records.json`: private per-episode structural descriptions and unchanged scores.
- `PRIVATE_REVIEW.md`: all thirty original task turns, initial outputs, fault
  feedback and both post-fault outputs, with existing scores and structural flags.
- `provenance.json` and `scores/`: original input/score fingerprints and the
  independent score reproduction.

Read `PRIVATE_REVIEW.md` locally; paste only the printed aggregate report.
Keep all detailed task/output text private. Reference gains/losses can coexist
with inappropriate arguments or appropriate refusal. Literal control names and
argument-key changes are descriptive flags, not execution or schema-validity
judgments. ToolEyes name relevance and released parameter matching retain their
previous limitations. Pinned repetition penalties remain 1.1 and 1.05.

Fourteen CPU tests pass using the real frozen parser: six structural transitions,
argument/type/order distinctions, label-independent buckets, all four paired
reference cells, unknown/duplicate rejection, endpoint separation, literal
control scope, argument removals/replacements, unchanged rows, private-text
fencing and identifier-free reporting. Ruff passes. Actual thirty-pair structural
counts match independent checks. The complete owner reference join was subsequently supplied as recorded above;
protected scoring inputs remain unavailable here.

This review closes interpretation of the bounded smoke. Review the fault-feedback
semantics and choose the next recovery scope/endpoint and resource plan before
larger collection. Preserve all existing scores/cases. Five selected groups with
dependent faults do not establish population effects, a deployable gate,
monetary savings or final held-out readiness. No additional GPU batch is enabled.
