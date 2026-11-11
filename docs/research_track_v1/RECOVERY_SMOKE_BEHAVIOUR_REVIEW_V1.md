# Recovery smoke: reference results and structural behaviour review

The owner completed smoke reference scoring at `e25c8e6`; all 16 scoring checks
passed. The supplied terminal report gives:

| Endpoint | Episodes / groups | Initial matches, repeated per episode | Post-fault matches | Match to mismatch | Mismatch to match |
|---|---:|---:|---:|---:|---:|
| Original reference compliance | 24 / 4 | 18 | 4 | 14 | 0 |
| ToolEyes name relevance | 6 / 1 | 6 | 3 | 3 | 0 |

The original reference-panel post-fault counts are 0/4 auth error, 1/4 malformed
response, 0/4 rate limit, 2/4 schema drift, 0/4 server error and 1/4 timeout.
ToolEyes relevance is respectively 0/1, 1/1, 0/1, 1/1, 1/1 and 0/1.
These are owner-reported reference results, not independently recomputed here:
the protected references and original initial-response files are on the owner
machine. Four reference groups and one relevance group, each repeated across six
faults, are not a general recovery-performance sample or an executed baseline.

## Independent structural inspection

The already verified uploaded smoke responses were independently parsed with the
frozen canonical parser. This requires no reference answers. The observed counts
are:

| Structural bucket | Episodes |
|---|---:|
| Identical canonical calls | 4 |
| Same name sequence, changed arguments/types | 7 |
| Changed name sequence or call order | 8 |
| No parsed post-fault call | 11 |

Six episodes have an initial first parsed action literally named `finish` in a
ReAct benchmark. Eight post-fault episodes include the literal `finish` or
`ask_to_user` name in RoTBench/ToolEyes. Two same-name episodes remove initial
top-level argument keys; one replaces an initially empty string argument with a
nonempty string. These are structural observations, not semantic success/failure
labels, schema judgments or verification of credentials.

Manual inspection of the private text suggests that requests for help, later
retry suggestions, changed actions and changed arguments contribute to the low
reference counts. This is qualitative interpretation, not adjudicated correctness.
The released injection rule permits feedback after any initial official parsed
call, including an action named `finish`; it does not establish an external tool
execution. Retain these cases and disclose this boundary rather than dropping
them after observing outcomes. Appropriate deferral under unavailable credentials
or schema information can still mismatch an unchanged clean reference.

The frozen BFCL matcher and ToolEyes name-relevance rule also have documented
argument limits. A reference match does not establish general argument validity
or fault repair. The next review explicitly measures whether any matching
responses removed initial keys or replaced empty strings; those per-outcome
cross-tabs remain pending the owner's complete reference-score recomputation.

## Run the CPU review

```bash
python tools/development_audits/recovery_smoke_review_v1/review.py
```

It first reruns the existing source/context/reference-bound CPU scorer into a
fresh nested output and requires its records and summary to match the previous
owner scores byte-for-byte. It preserves the original scoring directory and
reads the same protected development-only sidecars. No inference or external
judge is called. It then parses the preserved initial and actual post-fault text
using the frozen methods and constructs structural buckets without consulting
the reference labels. Labels are joined afterward for separate endpoint counts.

The bucket rule preserves canonical call order/types and ignores only dictionary
insertion order, as already frozen. No-call output remains opaque: it can mean
intentional deferral or an unrecognized format. Missing initial canonical calls
have their own bucket rather than being dropped. Control-name flags are literal
diagnostics restricted to RoTBench/ToolEyes. Argument-key and empty-string changes
are assessed only for the same name sequence, not across incompatible tools.

Fresh ignored output:
`artifacts/local_development_audits/recovery_smoke_behaviour_review_v1/`.

- `REPORT.md` and `summary.json`: aggregate structural counts and separate
  reference/relevance cross-tabs; the report is printed for review.
- `records.json`: private per-episode structural observations and unchanged
  reference outcomes.
- `PRIVATE_REVIEW.md`: original user request, initial output, fault feedback,
  post-fault output and original reference flags for every episode.
- `recomputed_reference_scores/` and `provenance.json`: independent scoring and
  input/policy fingerprints.

Keep the example text local. Paste only the printed aggregate report. The 14
new tests use the actual frozen parser to check unchanged/reordered dictionaries,
argument/type changes, name/order changes, no-call ambiguity, control-name scope,
empty strings, endpoint separation, reference-independent buckets, private text
fencing and identifier-free aggregate rendering. Ruff passes. Actual saved-text
structural counts above were verified locally; the complete owner-side review
and per-outcome cross-tabs remain pending because the private references are not
available in this checkout.

Review fault semantics and the benchmark endpoint before further GPU allocation.
No original label, cohort, uncertainty definition or score is changed; no control
episode is excluded, and no final threshold, causal recovery effect, monetary
saving or held-out conclusion is selected. Broader small/fallback collection is
still unprepared and not dispatched.
