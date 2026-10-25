# Development failure review v1

## Scope and evidence

This retrospective review follows commit bbb1387 and examines six selected
Qwen2.5-1.5B-Instruct development responses across five benchmarks.
Examples were selected after inspecting official noncompliance and mean-token
NLL rankings. The ToolEyes example is included as a separate relevance case;
it is not a low-uncertainty failure.

This is an illustrative review, not a complete failure audit, independent
semantic adjudication, population estimate or final protocol freeze.
Low token uncertainty is not calibrated confidence in correctness.

Evidence comes from the existing coverage prepared requests, saved HTTP
responses, selected development references, CPU scores and uncertainty report
under artifacts/local_development_audits. No new inference or tool execution
was performed. Official scores, references, labels and prior outputs are
unchanged. Held-out examples and labels are outside this review.

Ranks below use ascending mean-token NLL within each benchmark. They are
exploratory positions, not deployment thresholds. Equal scores must not be
interpreted as having a meaningful internal ordering.

## Reviewed examples

### BFCL: unsupported location assumption

Case: `paraphrase_parameter_description.jsonl:bfcl_v3__BFCL_v3_multiple__multiple_61`

Mean-token NLL: 0.006627321536473119; rank 5 of 12.

The user requests a landscape architect in Portland with five years of
experience in small space garden design. The reference uses location
"Portland"; the model uses "Portland, OR". Tool name, specialization and
experience match.

The model adds a state not specified by the user. The schema contains
"Portland, OR" as an example, which is a possible influence, not an established
cause. Record an unsupported location assumption and exact-reference mismatch.
The intended state and semantic equivalence are unresolved. Official score: 0.

### BFCL: latency preference in the reference

Case: `TD_AB.jsonl:bfcl_v3__BFCL_v3_multiple__multiple_13`

Mean-token NLL: 0.005508262007522262; rank 4 of 12.

The model selects corporate_finance.revenue_forecast, annotated 2016 ms.
The reference selects cor_fin.rev_for, annotated 73 ms. Their task descriptions
and parameter schemas otherwise match, and all generated argument values match
the reference. Neither the user nor system explicitly requests minimum latency.

Record a reference preference mismatch without an explicit latency objective.
Tool equivalence is not execution-tested. The latency values are supplied
annotations, not measured execution times. Official score: 0.

### RotBench: argument mismatch and underspecified length

Case: `TD_NT.jsonl:rotbench__Turn 1: What is the translation of the English phrase 'See you later' in Japanese?`

Mean-token NLL: 0.1474796528479608; rank 1 of 17.

The model selects get_translation_nllb, which appears in the reference and
is annotated 63 ms. It adds access_token="your_access_token" although no token
value is supplied. It also uses max_length="50", whereas the reference uses
the literal string "None". The schema requires max_length but provides no
default, and the user specifies no length.

Record an unsupported credential placeholder alongside an underspecified
length parameter and reference mismatch. The placeholder is not an observed
credential and does not demonstrate executable authentication.

Saved rule-based components: tool_selection=true,
parameter_identification=false, content_filling=false.
Partial score: 1/3; correct=false. These components alone do not attribute
each failure to an individual argument. Execution success was not assessed.

### ToolAlpaca: callable identifier substitution

Case: `realistic_typos.jsonl:toolalpaca__Free Dictionary__inst6`

Mean-token NLL: 0.027063192918937128; rank 3 of 17.

The declared identifier and reference are api_v2_entries_en_{word}.
The model generates api_v2_entries_en_ephemeral with word="ephemeral".
The system explicitly states that declared names are exact callable
identifiers. The argument matches, but substituting into the identifier
violates that instruction.

Record a model error in callable naming. Official score: 0.
The original evaluation configuration records gpt_judge; the saved CPU scorer
uses exact_match. This result is deterministic reference compliance, not an
LLM-judge verdict or an execution result.

### APIBank: format error with reference and schema ambiguity

Case: `same_name_D.jsonl:apibank__level1_166`

Mean-token NLL: 0.07733771223787476; rank 3 of 17.

The model uses a timestamp containing "T", while the declared format requires
a space between date and time. This is a clear declared-format violation.
It also uses "gym workout" instead of the reference's "Gym workout";
execution sensitivity to this capitalization is untested.

Both model and reference use year 2023, although the supplied dialogue and
system do not establish a year. Two DeleteAgenda declarations share a name
but expose different parameter sets. Record the format error separately from
the unsupported year, strict text mismatch and duplicate-name schema ambiguity.
Official noncompliance is retained. No credential values are reproduced here.

### ToolEyes: separate next-tool relevance mismatch

Case: `clean.jsonl:tooleyes__Turn 1: Give me a mapping of all cryptocurrencies to unique CoinMarketCap ids`

Mean-token NLL: 0.3458530668720075; rank 6 of 6.

The model selects get_cryptocurrency_listing_latest. The reference expects
get_cryptocurrency_coinmarketcap_id_map. Several supplied tool descriptions
repeat generic category text, which is an input-quality caveat, not a proven
cause of the selection.

The original configuration records gpt_judge with relevance. The saved CPU
scorer uses name_match and returns score 0, correct=false. Record a
deterministic next-tool relevance mismatch. Arguments, full workflow success
and execution are not assessed. This case has the highest uncertainty in its
six-case panel, so it is not evidence of a low-uncertainty failure.

## Interpretation and remaining work

The reviewed mismatches include clear instruction violations, unsupported
assumptions, reference preference ambiguity and scorer limitations. These
observations can overlap; they are not mutually exclusive error labels.
No official outcome is relabeled and no case is excluded.

Official reference compliance, ToolEyes name-only relevance and cost/latency
preference must remain separate. Supplied latency annotations do not establish
measured latency or preference success.

These examples do not identify the best uncertainty measure or a routing
threshold. Benchmark-specific score scales, small samples, repeated canonical
groups and meaningful-token missingness limit comparisons. Future reporting
must retain per-benchmark results and same-case measure comparisons.

Remaining work includes a reproducible review selection and evidence manifest,
broader development failure review, resolution of protocol decisions, further
required model experiments and the planned statistical analysis. Calibration,
routing benefits and Task 3 completion are not established by this document.
Held-out evaluation remains blocked until the final protocol freeze.
