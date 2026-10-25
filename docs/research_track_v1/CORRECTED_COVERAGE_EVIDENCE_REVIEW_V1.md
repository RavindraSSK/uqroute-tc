# Corrected Qwen 1.5B coverage evidence and CPU scoring v1

Baseline: `65058a0cce3867c10fe5ede19114a9c06a777f22`.
Evidence scope: one constructed primary-development case per available
benchmark/source-file stratum; 69 cases / 55 canonical groups, with five clean
and 64 perturbed cases. Only one selected perturbed case has its selected clean
anchor. This is a coverage diagnostic, not a paired robustness design or a
population estimate. The five clean cases deliberately repeat the previous
feasibility selection in a separate run; outcomes must not be pooled.

## Artifact verification

Reviewed archive: `uqroute_qwen15b_corrected_coverage_217d4a47.zip`.

- Archive SHA256: `700c65c545d5965d72e0f6c9796f589a69ebd8080a924562fca1c832048155f8`.
- Prepared manifest SHA256: `a00a33c9bbc40a15acb02a3a26ebcfdcb6bfdf00aa0dcdde39544e658f075ffb`.
- ZIP integrity passes, with 293 unique archive members. The new versioned
  scoring policy binds every member to its original bytes.
- All 279 outcome-file hashes listed by the archived CPU replay reconcile.
- All 69 request-body hashes and saved response validations reproduce using
  the unchanged generation, parser and Task 2 uncertainty methods.
- One session recorded 69 processed slots, zero resumed visits, no unfinished
  sessions and all 69 outcomes complete. There are no missing usage counters.
- Whole-output evidence is eligible on 69/69 cases; meaningful-token evidence
  is eligible on 39/69 cases. These are availability counts, not correctness.

The recorded L4 runtime used the pinned Qwen2.5-1.5B-Instruct model/tokenizer
revision, BF16 and vLLM 0.30.0. Requested temperature stays 0.001; constructor
normalization to 0.01 is recorded separately. Launch metadata is an operator
attestation, not an independent weight-byte verification.

Tokenizer preflight reports 88,220 prompt tokens total, maximum 4,633, no
context overflow, no prompt truncation and no dropped requests. Server usage
also totals 88,220 prompt tokens, plus 3,519 completion tokens: 91,739 overall.
Session wall is 55.488206979 seconds; summed request elapsed time is
54.439490916 seconds. Neither includes all setup/loading/idle allocation and
neither is GPU active time or a monetary-cost measurement. Remaining platform
quota was not recorded. No broad-run time or cost estimate is established.

## Meaningful-token exclusions

| Benchmark | Rows | Eligible | Unavailable | Interpretation |
|---|---:|---:|---:|---|
| APIBank | 17 | 5 | 12 | Five outputs have no parsed call; seven parsed outputs fail the frozen complete-call format restrictions. |
| BFCL v3 | 12 | 12 | 0 | All meet the frozen alignment rules; correctness remains separate. |
| RoTBench | 17 | 16 | 1 | One output contains two ReAct actions; meaningful-token alignment requires one complete action/input pair. |
| ToolAlpaca | 17 | 0 | 17 | Existing scoped exclusion; no new alignment rule is introduced. |
| ToolEyes | 6 | 6 | 0 | All meet alignment rules; only relevance is scored against the reference sidecar. |
| Total | 69 | 39 | 30 | No exclusion changes official labels or removes a case from official scoring. |

The 30 unavailable cases form four bounded diagnostic categories:
17 ToolAlpaca scope exclusions, five APIBank no-parsed-call outcomes, seven
APIBank format exclusions and one ReAct single-action-rule exclusion.

For APIBank, the frozen alignment function raises its standalone/fenced-JSON
format error for 11 cases and an unsupported-preamble error for one. Five of
the 11 have no parsed calls; seven total have parsed calls but unsupported
alignment formats. Examples include XML-wrapped JSON, thought text mixed with
call markup inside a fence, prose preambles and placeholder arguments. These
are format/evidence diagnoses, not semantic correctness labels. The no-call
category may include unsupported model syntax or plain responses; it does not
establish whether a tool was required.

The RoTBench two-action response is not truncated. The pinned official ReAct
parser and the stricter meaningful-token rule have different scopes; retain
both behaviors. No extra action is removed to make alignment pass.

The generation workflow saved a generic fallback message ending with
"ToolAlpaca remains excluded" for every caught alignment error, including
APIBank and RoTBench cases. That message is overly broad. It remains unchanged
in saved evidence. The new scoring sidecar adds benchmark-specific diagnostic
categories and frozen exception reasons without changing alignment functions,
eligibility, parser/scorer definitions or saved outcomes.

The repeated clean APIBank case is alignment-ineligible in this run because it
uses XML-wrapped JSON, whereas the earlier feasibility output was eligible.
Different output formats can change eligibility under unchanged rules. This
is not evidence that the alignment implementation regressed.

## Development-only scoring boundary

`tools/development_audits/coverage_scoring_v1/score_coverage.py` is a separate,
versioned, evidence-bound adapter. It does not modify or generalize the earlier
five-case scoring policy. It accepts only this reviewed archive's extracted
file set and hashes, the approved primary-development export attestation and
payloads, and the preserved reviewed inventory. It checks the baseline
ancestor, frozen generation/scorer hashes, selected identities, prompt lineage,
reference hashes and development membership before producing output.

The reference sidecar is checked by the previously approved development export
attestation before opening it. The full development sidecar is read, but only
the 69 selected cases are scored. Raw benchmark files, the split and development
`samples.jsonl` are not opened. This trusts the reviewed exporter; hashes do not
independently authenticate the partition. There is no network or inference.

Original response text is reparsed with the pinned benchmark parser, preserving
Python value types. JSON replay call views are never passed to the scorer.
The unchanged official score dictionary and original evaluation configuration
are retained for every case, including no-parsed-call and alignment-unavailable
outcomes. Reference flags do not change a score or exclude a row.

Panel sizes are 63 reference-compliance cases and six separate ToolEyes
name-relevance cases. Per-source-file summaries also retain this separation;
no combined headline accuracy is produced. Existing reference ambiguity flags
and explicit cost/latency-objective detector outputs are carried forward.
Reward-source overlap is reported as diagnostics, not an additional independent
panel. Preference success remains unassessed; regex nondetection does not prove
absent intent. Official reference compliance is not tool execution success.
Actual reference scores and flags remain pending local scoring against the
owner's reference sidecar; this review does not invent correctness counts or
classify failures as semantic model errors versus reference mismatches.

The fresh output directory contains `scores.json`, `summary.json`,
`provenance.json` and `alignment_diagnostics.json`. Eligibility summaries include
separate official outcomes for meaningful-token eligible/unavailable rows, so
missingness does not silently redefine the official denominator. All input
files are rehashed before publication. Paths are normalized before temporary
output publication, retaining the prior Windows portability fixes. Existing
outputs, references, evidence and scores are never overwritten.

## Tests and remaining work

Package-author CPU verification: 37 new synthetic scoring tests, 31 unchanged
five-case scoring tests, and 34 generation regression tests pass. The symlink
test may be skipped on Windows. Tests cover raw Python tuple preservation,
unaltered official scores despite alignment exclusions, reference flags without
exclusions, multi-action ReAct diagnostics, no-call denominator retention,
separate panels and objective diagnostics, provenance, input tampering,
reference lineage, source identity, readiness blocks, output overlap and
relative-path publication. Synthetic fixture integration isolates Git ancestry
and dependency binding; production performs those checks.

Owner local import/replay/scoring and test output are still pending. Subsequent
work includes reference-score interpretation, corrected feasibility for other
selected model roles, broader development experiments and tested static metrics.
Task 3 is not complete. Task 4 routing/recovery is separate. Held-out access and
main-experiment readiness remain false until the final shared protocol freeze.

## Directory-publication maintenance — 2026-10-25

The owner's 37-test Windows run encountered one PermissionError during the
final temporary-directory rename, despite absolute paths. The unchanged
five-case scorer (31 tests, one symlink skip) and generation workflow (34 tests)
passed. The traceback does not independently identify the process holding the
directory open. The previously published real coverage scores remain preserved.

A bounded helper now retries only PermissionError from final CPU output
publication: six rename attempts with at most 3.1 seconds total delay. An
existing or newly appearing destination still stops publication; other errors
are not retried. There is no partial-copy fallback, evidence deletion, model
request retry or scoring/reference/policy change. Adapter fingerprints in
future outputs identify the changed implementation; old provenance is not
rewritten. Five synthetic regression tests cover transient and persistent
permission failures, nonpermission errors and preservation of existing or
competing destinations. The package-author CPU suite now passes 42 tests;
owner Windows verification remains pending.
