# Full-development illustrative failure review v1

## Scope

Retrospective review following commit 6992084.
Two selected development cases are compared across Qwen 1.5B,
Llama 3B and Qwen 7B using saved requests, responses and CPU scores.
This is an illustrative review, not an exhaustive semantic adjudication.
Selection followed inspection of the development failure catalogue.

Official scores, references, labels and previous outputs remain unchanged.
No inference, tool execution or held-out evaluation was performed.
Raw uncertainty values are not calibrated correctness probabilities
and do not establish a common threshold across models.

## Unsupported location assumption

Case: `paraphrase_parameter_description.jsonl:bfcl_v3__BFCL_v3_multiple__multiple_61`

The user specifies Portland. The reference uses location="Portland".
Both Qwen models generate "Portland, OR"; Llama generates "Portland".
All three match the reference tool, specialization and years of experience.

| Model | Official correct | Whole mean NLL | Meaningful mean NLL |
|---|---|---|---|
| Qwen 1.5B | false | 0.006793318721847754 | 0.009236657978274505 |
| Llama 3B | true | 0.03812659299307558 | 0.0009733792029180677 |
| Qwen 7B | false | 0.001581659795623125 | 0.0021965775251639266 |

The Qwen responses add a state that the user does not specify.
The schema contains Portland, OR as an example: possible influence,
not an established cause. The intended state, semantic equivalence
and execution outcome remain unresolved.

Disposition: unsupported location assumption and exact-reference mismatch.
No reference-review flags were detected; this is not semantic clearance.
All responses finished with stop.

## Reference cost preference without an explicit objective

Case: `CD_AB.jsonl:bfcl_v3__BFCL_v3_multiple__multiple_13`

All three models select corporate_finance.revenue_forecast, annotated
$0.213/call. The reference selects cor_fin.rev_for, annotated $0.015/call.
The supplied task descriptions and parameter schemas otherwise match.
All generated argument values match the reference.

Neither the supplied user request nor system instruction explicitly
requires minimizing cost. Supplied prices are annotations, not measured
spending. Functional equivalence has not been execution-tested.

| Model | Official correct | Whole mean NLL | Meaningful mean NLL |
|---|---|---|---|
| Qwen 1.5B | false | 0.005031738148852582 | 0.003709226764474099 |
| Llama 3B | false | 0.04224860756835369 | 0.05032120378157689 |
| Qwen 7B | false | 0.02359914263840068 | 0.0007703435401439486 |

All three saved scores retain these diagnostic flags:
- reference_preference_without_detected_cost_objective
- reward_cell_without_detected_explicit_objective

Disposition: official exact-reference noncompliance with reference
preference ambiguity. This is not an adjudicated reference error,
measured preference-success result or demonstrated execution failure.
All responses finished with stop.

## Interpretation and remaining work

Unsupported argument assumptions and reference preference ambiguity
must remain distinguishable in qualitative interpretation.
No case is removed or relabeled.

These selected examples do not estimate category failure rates,
establish model superiority or validate routing thresholds.
Within-model ranks and diagnostic-band membership must be read from
the reporting artifacts rather than inferred from raw cross-model NLL.

Remaining work includes broader illustrative review across benchmarks,
evidence hashes for the review, resolution of outstanding protocol
decisions and requirements, and final reproducible evaluation artifacts.
Held-out access remains disabled pending the final protocol freeze.
Task 3 completion and Task 4 routing benefits are not established here.
