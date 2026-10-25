# Coverage reference review and separate bounded diagnostics v1

Baseline: `478d46a30f07679d9fc9936b48656272e5a52b7b`.
Scope: the reviewed 69-case corrected Qwen 1.5B primary-development coverage
run. The official scorer, references, uncertainty definitions, old audit
signals and every prior output remain unchanged.

## Completed evidence

The owner completed generation, local replay and local scoring. The local
replay summary matches the archived Colab replay, including every recorded
outcome hash: 69 complete, 69 whole-output eligible, 39 meaningful-token
eligible, no resumed visits, unfinished sessions or missing usage.

The coverage scoring implementation was committed and pushed as `478d46a`.
The owner verified 42 coverage-scoring tests with one Windows symlink skip,
31 five-case scoring tests with one symlink skip, and 34 generation tests.
The five additional coverage tests concern bounded CPU-directory publication;
they do not retry model requests or change scoring semantics.

All 69 official per-case score dictionaries were independently reproduced from
the original raw responses and uploaded selected development references using
the pinned parser/scorer. Results remain 21/63 official reference compliance
and 5/6 separately reported ToolEyes relevance. There are 42 noncompliant
reference-panel cases, of which 27 have old reference-review signals and 15
do not. Of 38 flagged reference-panel cases, 11 nevertheless meet official
reference compliance. Flags overlap, are not correctness labels and cause no
exclusions. These counts describe this selected coverage diagnostic only.

The saved scoring provenance predates the later publication-only fix and
commit. Its original adapter fingerprint matches the supplied original source.
Old provenance must not be rewritten to claim that later code produced it.
All 293 archived evidence fingerprints and all 69 identities and uncertainty
views match that provenance and the original replay.

## Case interpretation

The review finds several different phenomena, without forcing every mismatch
into one mutually exclusive semantic category:

- Model errors supported by the input/schema include selecting a next-holiday
  endpoint for a requested specific year, and selecting departures-only charts
  when the user requested general/departure/arrival/approach charts.
- APIBank examples use a different timestamp representation from the explicitly
  requested `%Y-%m-%d %H:%M:%S` format. These are declared-format failures, not
  evidence that arbitrary date normalization should change official labels.
- Dictionary outputs substitute the requested word into a tool name containing
  `{word}`. The pinned scorer requires the declared name exactly; this is a
  name mismatch and does not authorize a parser/scorer repair.
- Some mismatches include reference credential values absent literally from
  every supplied message. Missing literal values do not alone prove that a
  reference is semantically erroneous or the model otherwise correct.
- Default arguments, duplicate declarations and multiple reference calls expose
  interpretation limits. The official deterministic scorer is retained,
  including its method-specific treatment of reference lists and arguments.

Two low-mean-NLL BFCL failures are not clean evidence of semantic overconfidence:
one selects a slower but functionally similar advertised tool without a
previously detected explicit latency objective; the other expands `Portland`
to `Portland, OR`. The latter may introduce an unsupported location assumption,
so it is not declared semantically equivalent merely because the city name
matches. Token uncertainty is not calibrated correctness probability.

## New diagnostic rules

`tools/development_audits/coverage_reference_review_v1/review_policy_v1.json`
versions retrospective diagnostic rules selected after inspecting development
outcomes. They are not a preregistration, new intent labels or a final protocol
freeze. The old detector and its recorded flags remain authoritative for their
original version; supplemental hits do not replace them.

### Credential literal-absence signal

For all selected cases, independently of correctness, inspect string-valued,
nonempty top-level reference arguments with the fixed names `access_key`,
`access_token`, `api_key`, `appid`, `key`, `password`, `token` and `username`.
Check exact case-sensitive substring presence in each original supplied
system/user message. Do not infer nested credentials, decode values, invent
missing values or execute tools. Output argument names, reference-call indices,
presence booleans and message indices only; never emit credential values or
credential hashes. A generic field such as `key` may have a noncredential
meaning. Literal presence does not establish that a value should be used;
absence is not proof of semantic unavailability. Manual interpretation remains
necessary.

On the approved inputs, 11 reference-panel cases carry this signal: ten
ToolAlpaca and one APIBank. All 11 are officially noncompliant, but some also
contain independent model errors. No ToolEyes row carries this signal. These
11 are not reclassified as 11 confirmed reference errors.

### Supplemental objective wording

Search user segments only for the fixed phrases `minimal cost` and
`most responsive option`, allowing case and whitespace variation. Use the old
audit's embedded `<user>` extraction convention; system tool advertisements
and embedded assistant replies do not become user objectives. For each phrase
kind, report matches and whether the old detector recorded nondetection. Retain
the old cost/latency booleans and reference-review flags without modification.

The selected inputs contain one cost and one latency supplemental match with
old nondetection. Negation, quoted instructions and malformed role tags still
require manual review: matching a phrase does not adjudicate final intent.
No-hit does not prove absent intent. Do not silently change the old 1/1 objective
detection counts, reward preference labels or any prior report.

## Input/output boundary

`review.py` reads only the previously hash-approved coverage `scores.json`,
scoring `provenance.json`, selected 69-reference review extract, and prepared
manifest/requests. The versioned policy pins their exact byte hashes. The
baseline must remain an ancestor of HEAD. The diagnostic validates case IDs,
panels, prompt/body hashes, development scope and reference provenance before
writing. It does not read the raw benchmark, full split, full reference sidecar,
model weights, unknown cases or held-out examples. It sends no requests.
Consistency trusts the reviewed export and its provenance; it is not an
independently authenticated partition proof.

All paths are restricted to local development artifacts; symlink inputs and
output/input overlap are rejected. The source bytes are rechecked before
publishing three files to a fresh directory: `diagnostics.json`, `summary.json`
and `provenance.json`. Publication handles transient permission errors with six
rename attempts and at most 3.1 seconds delay. Existing destinations are never
replaced. Official scores are copied verbatim, not recomputed or corrected;
reference compliance, ToolEyes relevance and preference success remain separate.
Preference success and semantic adjudication stay unassessed.

## Verification and remaining work

Package-author verification: 27 synthetic CPU tests pass. Tests cover credential
presence/absence and redaction, aliases, nested/empty exclusions, user-only phrase
scope, embedded dialogue, negation as a review signal, old-value preservation,
outcome-independent detection, identity/prompt tampering, panel separation,
strict JSON, output preservation, bounded publication and a synthetic 69-case
integration using relative paths. Git ancestry and input pins are isolated in
that synthetic integration. Production performs those checks. A separate
replay against the uploaded approved inputs reproduced the 11 credential and
two supplemental-phrase signals; only Git ancestry was isolated in that scratch
replay. Owner local import, tests and diagnostic execution remain pending.

Next work is to review these diagnostics locally, then resolve development
analysis rules for missingness, metric direction, ties, calibration and
risk-coverage before broader corrected model-result claims. These diagnostic
rules do not replace static-metric implementation, other model experiments,
group-aware intervals or the failure catalogue. Task 3 remains in progress;
Task 4 routing/recovery is separate. Held-out access and main-experiment readiness
remain disabled until the final shared protocol freeze.
