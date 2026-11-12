# UQRoute-TC: Uncertainty-Gated Routing and Recovery for Reliable Tool Calling

## Progress update — 2026-11-11

Task 1 and Task 2 remain complete within their recorded scope. Task 3 now has
completed corrected primary-development generation/scoring for all three small
models, full-development statistical reporting, corrected repeated sampling,
and the sensitivity-only development extension. Task 3 remains open for final
protocol decisions and held-out evaluation. Task 4 has a tested development
routing kernel and a completed, independently replayed 1,728-response corrected
14B fallback run. The owner has completed reference scoring and the paired-routing
CPU replay against all three small models. All four saved scorers and full replays
were revalidated, and the owner supplied the gated/random policy report.
Retrospective fixed-cap matches and saved usage/usability accounting are reviewed.
The owner has completed group-separated development validation and conditional
paired group-bootstrap analysis on the saved evidence.
Recovery context preparation and a bounded CPU controller are now implemented
and tested. The owner completed preparation at `f2bbb44`: 2,412 pending eligible
episodes and 108 terminal no-injection plans across the three small models. A CPU
pinned-tokenizer preflight is owner-complete: all 4,824 potential role/context
requests fit with zero overflows. Bounded Qwen 1.5B resource-smoke staging and
a tested write-once small-stage ledger are supplied. Owner smoke staging is
complete: 30 planned post-fault small requests, five groups and all five benchmarks, with no fallback
requests. The owner completed that L4 smoke: all 30 responses and submission
records are present, all token evidence is complete, and independent CPU replay
matches every saved record exactly. Nineteen outputs contain parsed calls; eleven
are unparsed or contain no call. The owner local import is complete with identical results (nine checks, one
Windows symlink skip). The owner completed reference scoring: 4/24 post-fault reference matches versus
18/24 repeated initial matches; separate ToolEyes relevance is 3/6 versus 6/6.
The owner completed the structural review: eleven no-call outputs account for
eleven of fourteen lost reference matches; the other three losses involve
changed calls. The owner completed the matched thirty-response 14B L4 smoke; all 155 export
hashes and exact independent replay pass. Twenty-four outputs contain parsed
calls and six are unparsed/no-call. Owner fallback import is complete. Paired scoring is owner-complete: reference 4/24 versus 10/24, with six gains
and zero losses; relevance 3/6 each, with two gains/losses. A final smoke behaviour
review is supplied. Semantic/execution recovery, broader
collection, the final objective/operating point and full costs remain open. Task 5 final
packaging remains outstanding. No defensible overall completion percentage is
assigned.

| Workstream | Completed development evidence | Status / remaining boundary |
|---|---|---|
| Primary static study | 1,728 responses per model; 5,184 total; 140 groups; 26 construction blocks retained separately | Three-model scoring, matched uncertainty and 1,588 pairs/model analyzed |
| Statistics and calibration | 35 bootstrap entries / SVGs, 2,000 draws; 21 calibration scopes; constrained group-separated OOF calibration and paired-change intervals | Diagnostic policies; final choices and fitted mapping not frozen |
| Categories and failures | Released clean/Observation/Action/Reward summaries; 489 catalogue entries / 460 unique model-cases; illustrative reviews | Reference flags retained; no executable-success or exhaustive semantic-adjudication claim |
| Corrected repeated sampling | 30 cases / 15 groups per model, ten slots/case; 900 slots, scored and compared | Small selected development subset; dependent samples, no confidence guarantee |
| Sensitivity extension | 35 BFCL same-name cases / 34 additional development groups per model; all 105 responses complete, verified and scored | Separate population without clean anchors; no paired estimate or calibration refit |
| Corrected 14B AWQ fallback | 1,728 responses; 1,558 complete / 128 invalid evidence / 42 truncated; all 6,942 evidence hashes and full local replay verified | Owner CPU scoring: 787/1,512 reference matches; separate ToolEyes relevance 208/216. Owner paired replay complete; Fixed-cap matches and saved accounting reviewed; Group-separated development validation and conditional intervals complete; no fallback dominance/cost-saving claim. Owner recovery preparation complete (2,412 eligible episodes / 108 terminal no injection); all 4,824 tokenizer contexts fit; bounded smoke staging/ledger supplied; owner staging complete (30 requests, five groups); pinned L4 notebook supplied; 30-response L4 smoke complete and independently replayed; owner CPU import complete; owner reference diagnostic complete (4/24; separate relevance 3/6); owner structural review complete; owner matched 30-response fallback smoke complete; 155 file hashes and exact independent replay verified; 24 parsed / six no-call outputs; owner import and paired scoring complete (reference 4/24 versus 10/24, six gains/zero losses; relevance 3/6 each, two gains/losses); paired behaviour review supplied; broader recovery and final objective remain pending |
| Final static evaluation | No new held-out evaluation | Final shared protocol freeze and immutable development decision artifact still required |

Primary reference compliance is Qwen 1.5B 572/1,512, Llama 3B 621/1,512 and
Qwen 7B 790/1,512. Separate ToolEyes relevance is 174/216, 181/216 and 204/216.
Fallback reference compliance is 787/1,512 (52.05%); separate ToolEyes relevance
is 208/216 (96.30%). Qwen 7B has three more reference matches, while fallback
has four more ToolEyes relevance matches. These totals alone do not reveal
which cases are rescued or harmed by escalation. All 128 invalid-evidence and
42 truncated outputs remain scored as generated; their uncertainty is unavailable.
Owner verification passed 64 import/scoring tests (one skip) and 34 frozen
generation tests. The supplied terminal output supports these aggregate figures.
The working analysis checkout independently verified generation/replay; the
new official scores are recorded from owner output, not recomputed here.

The owner ran the paired-routing command at `ca417d1` successfully: 28 new
synthetic checks and 20 routing-kernel checks passed, then all four actual saved
runs were re-scored/replayed before matching. The supplied terminal summary
reports these aggregate reference-panel transitions on the same 1,512 cases:

| Small model | Small matches | Fallback matches | Potential rescues (IC) | Potential harms (CI) | Minimum forced fallback rows |
|---|---:|---:|---:|---:|---:|
| Qwen 1.5B | 572 | 787 | 326 | 111 | 227 |
| Llama 3B | 621 | 787 | 263 | 97 | 43 |
| Qwen 7B | 790 | 787 | 141 | 144 | 12 |

IC means small reference mismatch/fallback match; CI is the reverse. These are
all-pair opportunities and tradeoffs, not the counts selected by a particular
gate. All six endpoint/model transition tables reconcile with their raw model
totals, with no unknown labels. Separate ToolEyes potential rescues/harms are
35/1, 28/1 and 4/0, respectively. The CPU command generated compact frontiers,
fixed-cap and count-matched random views. The owner subsequently supplied the
full `REPORT.md`, confirming these reference-panel diagnostic points:

| Small model | 25% cap gated matches | Same-count random mean matches | Gated rescues / harms | 50% cap gated matches |
|---|---:|---:|---:|---:|
| Qwen 1.5B | 722/1,512 | 624.50 | 162 / 12 | 768/1,512 |
| Llama 3B | 671/1,512 | 660.70 | 78 / 28 | 737/1,512 |
| Qwen 7B | 830/1,512 | 790.00 | 68 / 28 | 817/1,512 |

All 25% points escalate 378 cases. The Qwen 7B example has 40 more matches
than small-only and 43 more than fallback-only, but requires 1,890 model attempt
slots versus 1,512 for either single-model baseline. The 378 fallback calls are
75% fewer than fallback-only; this is not a measured 75% reduction in total cost.
Qwen 7B's 50% view yields fewer matches than its 25% view; escalation need not
monotonically improve reference compliance. These inspected points are
retrospective development findings, not a selected optimum, independent
validation or statistical superiority claim. The ten-seed random mean is not
a confidence interval. The owner subsequently supplied the saved-accounting display.
Qwen 7B's 25% reference point has 51 unusable final outputs (small-only 12;
fallback-only 220), and 9,044.055 summed request seconds (fallback-only 7,503.086).
Its saved request-time proxy per match is 10.896 versus 9.534 for fallback-only;
there is no established timing-efficiency improvement at that point. Qwen 1.5B's
25% point has a smaller time proxy per match (5.346), but fewer reference matches
than fallback-only (722 versus 787). These are reference-compliance/usability
tradeoffs, not executable-success or monetary-cost measurements. Missing usage
was not reported in the supplied displayed totals.
The owner completed the five-fold grouped validation at `5528f84`, with all
75 focused checks passing and all four source runs revalidated. Selected
reference-panel OOF diagnostics from the supplied report are:

| Model | Training cap | OOF matches | Actual fallback calls | Unusable final | Request seconds/match proxy |
|---|---:|---:|---:|---:|---:|
| Qwen 1.5B | 25% | 721/1,512 | 381 | 90 | 5.390 |
| Llama 3B | 25% | 673/1,512 | 380 | 65 | 10.781 |
| Qwen 7B | 10% | 812/1,512 | 150 | 20 | 9.512 |
| Qwen 7B | 25% | 829/1,512 | 382 | 53 | 10.988 |
| Qwen 7B | 50% | 818/1,512 | 754 | 120 | 14.068 |

Qwen 7B's 25% training-cap view has 39 more reference matches than small-only
and 42 more than fallback-only, but a higher saved time proxy per match than
fallback-only (10.988 versus 9.534). Its realized escalation is 382/1,512
(25.26%), and the training cap is exceeded in three validation folds. The 10%
view has 812 matches and a proxy close to fallback-only (9.512 versus 9.534);
no timing or reliability superiority is established by those point estimates.

Reference zero-cap views and Qwen 1.5B's reference 10% view have no OOF
predictions because the rule is infeasible on training groups. ToolEyes zero-cap
Qwen 1.5B/Llama views cover only 42/216 rows and have no full-cohort rate.
Other displayed nonzero-cap views cover every endpoint case. ToolEyes 25%
OOF relevance matches are 194/216, 196/216 and 206/216, respectively.
Group-separated fitting prevents direct fold-group overlap; it does not undo
prior inspection of the full development data. No final threshold is refitted.
The owner subsequently completed the conditional paired group bootstrap at
`ec2317e`: 26 interval, 27 grouped-validation and 20 routing-kernel checks passed,
all source evidence was revalidated, and saved OOF results reproduced before
2,000 within-benchmark group draws. Key reference-panel contrasts are:

| OOF view | Match difference vs small, pp [95% interval] | Match difference vs fallback, pp [95% interval] | Saved seconds/match difference vs fallback [95% interval] |
|---|---|---|---|
| Qwen 1.5B, 25% training cap | 9.854 [7.015, 12.755] | -4.365 [-9.007, -0.064] | -4.144 [-5.568, -2.891] |
| Qwen 1.5B, 50% training cap | 13.095 [8.895, 17.357] | -1.124 [-4.137, 1.982] | -2.022 [-3.163, -0.985] |
| Qwen 7B, 10% training cap | 1.455 [-0.066, 3.465] | 1.653 [-2.331, 5.674] | -0.021 [-1.471, 1.254] |
| Qwen 7B, 25% training cap | 2.579 [0.197, 5.468] | 2.778 [-0.653, 6.512] | 1.454 [0.064, 2.776] |

These unadjusted percentile intervals condition on fixed OOF thresholds/decisions;
they neither refit thresholds nor undo prior full-development exposure. An
interval spanning zero is not an equivalence or noninferiority finding. The
Qwen 7B 25% view does not establish fallback superiority and has a higher saved
time proxy per match. Qwen 1.5B shows a reliability/time-proxy tradeoff. No final
model, cap, threshold or monetary-saving claim is selected.

The owner completed reference-free recovery preparation at `f2bbb44`; all 52
checks passed and all three saved initial model runs were revalidated without
reference scoring. Each model has 140 clean anchors and 840 scenario slots:

| Initial model | Pending eligible episodes | Terminal no injection | Maximum new calls if both roles dispatched |
|---|---:|---:|---:|
| Qwen 1.5B | 750 | 90 | 1,500 |
| Llama 3B | 828 | 12 | 1,656 |
| Qwen 7B | 834 | 6 | 1,668 |

All 108 terminal plans have reason `initial_no_official_call`. The 2,412 eligible
episodes have planned small/fallback contexts, totaling 4,824 potential requests;
these are not occupied attempt slots or incurred generation costs. The three
archive and manifest fingerprints are recorded in the new
[CPU context preflight](research_track_v1/RECOVERY_CONTEXT_PREFLIGHT_V1.md).
Counts and pins come from the supplied owner terminal summary; private transfer
payloads were not independently inspected in this checkout. The preflight
verifies the archives before rendering every role/context with its pinned tokenizer.
The owner attempted preflight at `1908f8f`: 17 synthetic checks passed, but actual
request validation stopped before tokenizer loading because the validator omitted
`stream: false` from its expected body. The correction requires the preserved
nonstreaming field and builds regression fixtures with the production static and
recovery request constructors. All 19 corrected context checks and 52 existing
preparation/controller/routing checks pass. Original archive pins and prepared
outputs remain unchanged; rerun preflight only. Actual token counts, context fit
and runtime/quota feasibility were pending at that point. The owner subsequently
completed preflight at `2b9527d`, with all 19 context tests passing and all 4,824
potential request contexts fitting without overflow, truncation or dropping:

| Initial small model | Small contexts | Fallback contexts | Maximum small prompt tokens | Maximum fallback prompt tokens |
|---|---:|---:|---:|---:|
| Qwen 1.5B | 750 | 750 | 4,937 | 4,937 |
| Llama 3B | 828 | 828 | 5,474 | 5,603 |
| Qwen 7B | 834 | 834 | 4,954 | 4,954 |

The largest prompt plus its full completion allowance is 5,603 + 1,024 = 6,627
of 8,192 tokens. Prompt-token totals are 900,620/900,620 for Qwen 1.5B
small/fallback roles, 1,029,804/1,017,510 for Llama-history small/fallback roles,
and 986,566/986,566 for Qwen 7B. All role tokenizer/template/backend identities
were reported. The original Qwen/Llama tokenizer differences remain explicit.
These aggregate figures are owner-reported, not independently recomputed here.
The new [bounded resource-smoke preparation](research_track_v1/RECOVERY_RESOURCE_SMOKE_V1.md)
checks the actual saved per-request preflight before selecting at most one
eligible clean group per benchmark, all six faults, and only Qwen 1.5B small-stage
requests (at most 30). A tested write-once ledger distinguishes intents, observed
local HTTP writes and saved/unknown responses; it is not a GPU launcher or final
adaptive recovery executor. Owner smoke staging is now complete according to
the supplied saved summary: 30 planned small-stage requests, five eligible groups, all five benchmarks,
zero fallback requests and no missing benchmark group. The occupied-output check
preserved this earlier successful preparation. The owner-reported ZIP SHA256 is
`ecd1e39441ddffdd4623d699cd6112dc791c322bfcec9336390f71d1cde2f453` and
manifest SHA256 is `3b747531cb19eb6e11a5fd74cdf338382f47e22ac0b5c9f596c84f08006d105c`.
The private archive was not independently inspected here. A
[pinned Colab L4 smoke notebook](research_track_v1/RECOVERY_GPU_SMOKE_V1.md)
validates those actual bytes and sends at most 30 new post-fault small requests,
with matching local/server tokenization, explicit execution, preserved unknown
slots, automatic shutdown and partial-evidence export. It retains the requested
0.001 temperature and records the prior constructor clamp to 0.01. All 18 new
CPU tests and 96 existing focused checks pass; actual GPU execution is untested
in this checkout. No actual smoke generation, observed injection, correctness
scoring, recovery result, final policy or readiness change is claimed. Runtime/
quota results, responses/replay, full recovery/scoring and policy costs remain
pending at that point. The owner subsequently uploaded the completed smoke
archive, SHA256 `dd91a73f5f565269f83d70773fd25fd64c82785029e3d96b139682c072b59595`.
All 152 indexed evidence-file hashes, exact ZIP inventory, prepared/source
fingerprints, local/server token sequences and returned prompt-token counts
were verified. The 30 actual responses and all ledger records independently
replay with both saved records and summary matching byte-for-byte. Results:

| Qwen 1.5B recovery smoke metric | Verified value |
|---|---:|
| Requests / observed submissions / saved responses | 30 / 30 / 30 |
| Frozen token-evidence status complete | 30 |
| Parsed calls / unparsed or no call | 19 / 11 |
| Parsed finite-NLL candidates | 19 |
| HTTP errors / unknown slots | 0 / 0 |
| Prompt / completion tokens | 56,606 / 1,798 |
| Request elapsed sum / dispatch wall seconds | 26.103 / 28.002 |
| Supervisor wall seconds | 244.132 |
| Fallback requests | 0 |

Both generation and server shutdown were recorded true. Official correctness
and RQ3 outcomes remain unscored: complete evidence and a parsed call do not
establish correct recovery. This is five groups with dependent fault scenarios,
not a full-development effectiveness estimate. Times omit full environment setup,
allocation and billing, with no monetary claim. See the
[verified smoke evidence and owner import](research_track_v1/RECOVERY_SMOKE_EVIDENCE_V1.md)
and aggregate-only `docs/evidence/qwen15b_recovery_resource_smoke_v1_summary.json`.
A CPU owner import/replay command is supplied with nine synthetic safeguards and
actual archive replay validation. Full source and raw case-level evidence remain
ignored/private. No new generation was performed by the independent verification.
The owner subsequently completed local import at `be2ef44`: nine tests finished
with one Windows symlink skip; all 152 hashes and exact 30-record replay match,
with the same counts/tokens/timings and no inference. The new
[CPU smoke reference diagnostic](research_track_v1/RECOVERY_SMOKE_REFERENCE_SCORING_V1.md)
uses unchanged clean references/configuration, as retained by the released
Transition writer. It will score all 30 saved outputs and their reused initial
clean outputs with the pinned parser/scorer, preserve original audit flags and
report the 24-row reference and six-row ToolEyes relevance panels separately.
Auth/schema fault appropriateness and executed recovery are explicitly unmeasured;
these are post-inspection development diagnostics, not a final scoring freeze.
Sixteen new tests with production request/context builders and the actual frozen
parser/scorer pass. Actual smoke hashes, runtime/context and ledger checks were
exercised locally up to the protected reference-loader boundary; the private
reference sidecars and initial raw responses are unavailable in this checkout.
The owner completed that reference diagnostic at `e25c8e6`, with all 16 tests
passing. Supplied aggregate results are:

| Endpoint | Episodes / groups | Initial matches, repeated per episode | Post-fault matches | Match to mismatch | Mismatch to match |
|---|---:|---:|---:|---:|---:|
| Original reference compliance | 24 / 4 | 18 | 4 | 14 | 0 |
| ToolEyes name relevance | 6 / 1 | 6 | 3 | 3 | 0 |

Reference-panel post-fault counts by auth/malformed/rate/schema/server/timeout
are 0/4, 1/4, 0/4, 2/4, 0/4 and 1/4. ToolEyes counts are 0/1, 1/1, 0/1,
1/1, 1/1 and 0/1. These supplied scores were not independently recomputed here
because the protected references/initial responses remain on the owner machine.
The previously verified raw smoke text was independently parsed locally: 4
identical canonical outputs, 7 same-name-sequence argument changes, 8 name/order
changes and 11 no-parsed-call outputs. Six episodes start from a literal control
name and eight post-fault outputs include a literal control name in the ReAct
benchmarks. Two same-name episodes remove initial argument keys, and one replaces
an empty string with a nonempty string. These structural observations neither
assign semantic correctness nor justify any case exclusion.
The new [CPU smoke behaviour review](research_track_v1/RECOVERY_SMOKE_BEHAVIOUR_REVIEW_V1.md)
recomputes the original scores exactly, joins structural buckets to the separate
reference/relevance outcomes and writes local private examples. All 14 new frozen-
parser tests pass; actual structural buckets were verified against saved outputs.
The owner completed review at `4f7b584`, with all fourteen checks passing and
exact score reproduction. Supplied endpoint cross-tabs are:

| Structural group | Reference rows / post-fault matches / lost initial matches | ToolEyes rows / post-fault matches / lost initial matches |
|---|---:|---:|
| Changed name sequence | 5 / 0 / 2 | 3 / 0 / 3 |
| Identical canonical calls | 2 / 2 / 0 | 2 / 2 / 0 |
| No parsed post-fault call | 11 / 0 / 11 | 0 / 0 / 0 |
| Same name sequence, changed arguments | 6 / 2 / 1 | 1 / 1 / 0 |

Eleven no-call outputs account for eleven of fourteen lost reference matches;
the other three have changed names/arguments. All three ToolEyes relevance losses
have changed names. These cross-tabs are owner-reported, not recomputed here.
They do not label deferral or control actions semantically wrong, exclude cases,
or establish executed recovery. The next
[matched fallback smoke preparation](research_track_v1/RECOVERY_MATCHED_FALLBACK_SMOKE_V1.md)
retains all thirty contexts and known small responses, preparing only the frozen
14B AWQ fallback role. It selects no cases by correctness or uncertainty and
appends no later small answer. The original full fallback plan, review, parent
ledger and saved 14B tokenizer counts are checked before any transfer publication.
Thirty new fallback staging/ledger checks pass; production context construction
also matches all thirty actual saved histories locally. The owner completed staging at `c3cbf9f` (thirty checks, one Windows skip),
with maximum selected prompt length 3,872 and zero overflows. Both archive and
manifest fingerprints match independent reconstruction from preserved parent
histories. The
[pinned L4 fallback notebook](research_track_v1/RECOVERY_MATCHED_FALLBACK_GPU_SMOKE_V1.md)
loads the exact transfer, validates known parent receipts and preserves unknown
slots. Twenty-five GPU-client CPU tests pass. The owner completed the fallback
smoke on L4: thirty saved responses, no HTTP errors/unknown slots, thirty complete
token-evidence records, 24 parsed calls and six unparsed/no-call outputs. All 155
indexed hashes match; exact independent CPU replay reproduces all records and
the summary. All thirty parent histories/receipts remain unchanged. The fallback
retains pinned inherited repetition penalty 1.05 versus small-model 1.1. Recorded
usage is 56,606 prompt and 1,754 completion tokens, summed request time 71.953s,
dispatch wall 74.007s and supervisor wall 370.675s; these exclude full installation/
allocation/billing and are not a cost-saving result. The
[owner CPU import](research_track_v1/RECOVERY_MATCHED_FALLBACK_SMOKE_EVIDENCE_V1.md)
is owner-complete at `d5be459`: fifteen tests passed with one Windows skip,
and all counts/hashes/exact replay match. The new
[paired reference scorer](research_track_v1/RECOVERY_MATCHED_SMOKE_PAIRED_REFERENCE_SCORING_V1.md)
reproduces the original small scores byte for byte and compares all thirty
fallback outputs with unchanged references, preserving separate ToolEyes
relevance. Twenty-four new tests and all sixteen original scorer tests pass;
actual fallback/runtime/pair verification is exercised locally without opening
reference sidecars. Protected original references/small-score files are not
available here; the owner subsequently completed scoring at `1cf2bd7`, with all
24 checks passing and exact original small-score reproduction. The supplied
reference panel is 4/24 small versus 10/24 fallback, with six gains and no losses;
ToolEyes is 3/6 each, with two gains and two losses. Gains in the reference panel
are server error 3, malformed response 2 and timeout 1; no auth/rate-limit matches
and no schema-drift gain occur. No labels/cases change. The
[paired behaviour review](research_track_v1/RECOVERY_MATCHED_SMOKE_BEHAVIOUR_REVIEW_V1.md)
is supplied with fourteen passing tests. Actual saved structural counts were
independently checked: six small-no-call to fallback-call, one converse,
five neither-parsed, two identical, six same-name argument changes and ten name
changes. Their score joins remain owner-only, and cannot be inferred by equating
the two counts of six. The review retains all thirty cases and private text. Literal control-action injection, appropriate
deferral and the released matcher's argument limits remain explicit boundaries. No original score/label/cohort is changed,
and no larger collection, final threshold or held-out access is enabled.
Planned fault feedback is not observed injection or measured recovery. No new
inference, reference scoring, held-out access or final threshold selection occurred.

These are development results under the pinned deterministic reference scorer;
they do not measure executable task success or cost/latency preference success.

On the corrected 24-case repeated-sampling reference subset, canonical-entropy
AUROC is 0.7685, 0.5898 and 0.9185 respectively; matched single mean-NLL AUROC
is 0.7963, 0.6484 and 0.7481. The small cohort and extra ten-call cost prevent a
final method-selection or superiority claim. Sensitivity reference matches
are 10/35, 7/35 and 10/35, with all structural reference flags retained.

See [readiness v3](research_track_v1/TASK3_DEVELOPMENT_READINESS_V3.md),
[reproduction instructions](research_track_v1/DEVELOPMENT_RESULTS_REPRODUCTION_V1.md)
and [evidence fingerprints](research_track_v1/DEVELOPMENT_RESULTS_EVIDENCE_V1.json).
New scripts/notebooks preserve the delivered source and input pins. The Qwen
1.5B repeated notebook has an upload-only verified-file reuse fix; embedded
execution sources and frozen sampling settings are unchanged.

## Historical progress snapshot — 2026-10-25

The following snapshot records the evidence available at that date. Its pending
items are superseded by the current update and readiness v3 above.


Latest owner-verified milestone: `6a09541`, committed and pushed on
`feat/task3-throughput`; the owner confirmed a clean working tree.
Task 1 and Task 2 remain complete within their recorded scope. Task 3 is
partially complete: corrected development generation and reference scoring
are verified for two of the three selected small models. Task 4 and Task 5
remain pending. No defensible overall completion percentage is assigned.

| Workstream | Verified evidence | Status |
|---|---|---|
| Development population | 1,754 rows / 140 groups; 1,728 candidates and 26 retained blocks (12 missing declarations, 14 conflicting schemas); 19 population-policy tests | Development reconciliation complete; not final metric denominators |
| Corrected Qwen 1.5B coverage | 69 cases / 55 groups; 69 complete; owner local replay matches; whole-output eligibility 69, meaningful-token eligibility 39 | Development generation and evidence verified |
| Qwen coverage scoring | 21/63 reference-compliant; ToolEyes relevance 5/6 separately; 38 flagged reference cases retained; 42-test suite with one Windows skip; `478d46a` | Development scoring verified and published |
| Bounded reference review | 69 rows; 11 credential-literal-absence signals, not confirmed reference errors; supplemental cost/latency phrase signals kept separate; 27 tests; `e3c7b61` | Retrospective diagnostic complete within bounded scope |
| Qwen uncertainty analysis | 37 tests; AUROC, score-block AP and tied-score risk–coverage on available and common eligible cohorts, by panel and benchmark; `bbb1387` | Development ranking diagnostics verified; calibration and thresholds not selected |
| Illustrative failure review | Six selected examples across five benchmarks; model errors, reference ambiguity and scorer limits distinguished; `48ab2eb` | Illustrative catalogue only; not a full confidence-band audit |
| Review evidence manifest | Six case identities, rank intervals and 17 verified source/evidence hashes; `a88688c` | Retrospective explicit selection documented; hashes are not authenticated provenance |
| Corrected Llama 3B coverage | Same 69 selected cases, prompt messages, order and request settings as Qwen apart from model ID; 68 complete, one truncated; owner local replay fully matches Colab including evidence hashes | Development generation and evidence verified |
| Llama coverage scoring | 21/63 reference-compliant; ToolEyes name-only relevance 6/6 separately; all 69 retained, including truncation; 46 tests with one Windows skip; `6a09541` | Development scoring verified and published |
| Other required experiments | Corrected Qwen 7B coverage, broader static populations, validated O/A/R comparisons, calibration, group-aware intervals and final reproducible figures | Pending |
| Task 4 and held-out evaluation | Routing/fallback/recovery policies and final shared protocol freeze are not complete | Held-out access remains disabled |

### Current corrected development scores

| Benchmark/panel | Qwen 1.5B correct/rows | Llama 3B correct/rows |
|---|---:|---:|
| APIBank reference compliance | 5/17 | 7/17 |
| BFCL reference compliance | 10/12 | 10/12 |
| RoTBench reference compliance | 3/17 | 1/17 |
| ToolAlpaca reference compliance | 3/17 | 3/17 |
| Reference-compliance panel | 21/63 | 21/63 |
| ToolEyes name-only relevance, separate panel | 5/6 | 6/6 |

Equal reference-panel totals do not establish equal per-case outcomes or model
quality. These selected development cases do not estimate population accuracy.
Reference compliance is not semantic correctness or executable task success.
ToolAlpaca source configurations recording gpt_judge use the pinned deterministic
exact-match implementation here; ToolEyes uses deterministic name matching,
not an LLM judge. Cost/latency preference success remains unassessed.

### Uncertainty evidence and missingness

For Qwen's 63 reference cases, mean-token NLL AUROC is 0.7982 and AP is
0.8821; sequence NLL AUROC is 0.7982 and AP is 0.8725; maximum surprisal
AUROC is 0.7268 and AP is 0.8022. Meaningful-token NLL uses only 33 reference
cases (16 compliant, 17 noncompliant), with AUROC 0.8824 and AP 0.9316.
That different subset prevents treating its larger values as evidence of the
best measure. The implementation also reports common eligible cohorts and
per-benchmark results. Mean-token AUROC varies from 0.8333 on APIBank to
0.3000 on BFCL; pooled benchmark scales and outcome rates can confound ranking.
ToolEyes has only six Qwen cases and one relevance mismatch.

Llama whole-output eligibility is 63/63 reference cases and 5/6 ToolEyes cases.
Meaningful-token eligibility is 19/63 reference cases and 5/6 ToolEyes cases:
APIBank 0/17, BFCL 12/12, RoTBench 7/17, ToolAlpaca 0/17, ToolEyes 5/6.
All 17 APIBank outcomes retain frozen format exclusions; ten RoTBench outcomes
retain single-action-rule exclusions. These are eligibility findings, not
correctness labels. Llama ranking metrics and matched-cohort model comparisons
remain pending; the existing Qwen uncertainty adapter is evidence-bound and
must not be repointed by changing its hashes.

The one Llama truncation is a ToolEyes response that passes name-only relevance.
It remains in the six-row relevance denominator, but both uncertainty measures
are unavailable for that response. No completion, replacement, retry or
automatic zero label was applied.

### Llama run provenance and runtime limits

Prepared manifest SHA256:
`5c1bea90df16b527257e6303f44806a3ca03c2279b3cc4d39b0480e9dae6521f`.

Export archive: `uqroute_llama3b_corrected_coverage_08f32900.zip`;
SHA256 `43e0868797e40fdc6c5c627b34dd501d4f6a7f85f68a2b90f80e853c8b68bac4`.
The archive contains 292 files, including an inventory of 291 evidence-file
hashes. Owner import and full local replay match the exported summary.
Generation used repository revision
`a88688c8a2e3dcb548103303f1dd70b7ac98ebaf` and the frozen Llama model/tokenizer
revision `0cb88a4f764b7a12671c53f0838cd831a0843b95`, BF16 on an L4.
The runtime reports vLLM 0.30.0, Torch 2.13.0 with CUDA 13.0 and Transformers
5.20.2. Model revision/loading identity is operator-attested.

The valid tokenizer preflight counted 89,327 prompt tokens, maximum 4,513;
adding the 1,024-token output allowance fits the 8,192 context for every case.
An earlier two-per-prompt container-length count was invalid and superseded.
Requested temperature stays 0.001; a local installed constructor check observed
normalization to 0.01 and inherited top-p 0.9, not an independent per-request
server observation. Model-default sampling can differ across models.

The run processed 69 slots with zero resumed visits, one finished session and
no missing usage counters. Usage: 89,327 prompt plus 7,028 completion tokens,
96,355 total. Session wall time: 206.907237585 seconds; summed request elapsed
time: 205.805151834 seconds. These exclude full setup/loading/idle allocation,
are not GPU active time or monetary cost, and do not establish a controlled
speed comparison with Qwen. Remaining provider quota was not measured.
The server was stopped and evidence exported; GPU disconnection was advised.

Official labels, reference files, original split, frozen methods and prior
outputs remain unchanged. All 38 flagged reference rows remain included.
No ambiguity exclusions, calibration, routing threshold, final protocol freeze
or new held-out evaluation is asserted.

Related records:
[Qwen analysis](research_track_v1/DEVELOPMENT_UNCERTAINTY_ANALYSIS_V1.md),
[reference review](research_track_v1/COVERAGE_REFERENCE_REVIEW_V1.md),
[failure review](research_track_v1/DEVELOPMENT_FAILURE_REVIEW_V1.md),
[review manifest](research_track_v1/DEVELOPMENT_FAILURE_REVIEW_MANIFEST_V1.json),
[Llama scoring](research_track_v1/LLAMA_COVERAGE_SCORING_V1.md).

## Historical progress snapshot — 2026-10-24

The following snapshot preserves the earlier status. Pending coverage scoring
and Llama statements in this historical section are superseded by the update
above and the current Task 3 checklist below.

Verified repository milestone: `65058a0` (`65058a0cce3867c10fe5ede19114a9c06a777f22`),
committed and pushed by the owner; the supplied Git status was clean.
This update separates verified local results from prepared implementation
packages and experiments that have not yet run.

| Workstream | Latest evidence | Status |
|---|---|---|
| Development population reconciliation | Owner supplied the reconciled 1,754-row / 140-group denominator report and 19 passing population-policy tests. All 26 construction blocks remain retained. | Verified development denominators; metric denominators and final freeze remain pending |
| Corrected generation workflow | `9ee8393`; owner verified 34 CPU tests, source fingerprints and the five-benchmark request plan. | Implemented and locally verified |
| Corrected Qwen 1.5B feasibility | Five prepared clean development requests completed on an L4; no retries or unfinished sessions. | Serving and evidence feasibility verified for this model and selection |
| CPU evidence replay | All five raw-response validations reproduced; whole-output eligibility 5/5, meaningful-token eligibility 4/5. ToolAlpaca retains its frozen meaningful-token exclusion. Owner also replayed the imported archive locally. | Verified; eligibility is not correctness |
| Development-only reference scoring | Four reference-compliance rows: APIBank 1/1, BFCL 1/1, RoTBench 0/1, ToolAlpaca 0/1; combined 2/4. ToolEyes relevance is separate: 0/1. | Locally measured five-case diagnostic; no population-accuracy claim |
| Scoring implementation and Windows portability | `6dfed20`; owner verified 31 tests with one Windows symlink skip after the relative-path fixes; 34 generation regression tests also passed. | Committed and pushed |
| Bounded development coverage implementation | Owner verified 25 new CPU tests and 34 generation tests; six files committed and pushed as `65058a0`. | Locally verified and published |
| Corrected Qwen 1.5B coverage run | 69 cases / 55 groups: five clean and 64 perturbed; all 69 complete. Context preflight passed; whole-output eligibility 69/69 and meaningful-token eligibility 39/69. | GPU generation and uploaded raw-evidence validation verified; owner local coverage replay/scoring pending |
| Coverage CPU-scoring package | Separate evidence-bound adapter and aggregate review supplied; package-author checks: 37 new tests, 31 unchanged five-case scoring tests and 34 generation tests pass. | Prepared only; owner import, tests, reference scores and commit not yet supplied |
| Final Task 3 results and Task 4 policies | Broader corrected runs, uncertainty effectiveness, calibration, risk–coverage, group-aware intervals, failure catalogue, routing and recovery remain outstanding. | Not complete; held-out access remains disabled |

The corrected feasibility batch recorded 4.731887112 seconds of session wall
time and 4.661208910 seconds of summed request elapsed time, with 9,176 prompt
tokens and 286 completion tokens (9,462 total). These figures exclude setup,
model loading and idle GPU allocation; they are not GPU-seconds, monetary cost
or a reliable forecast for perturbed coverage runs. Requested temperature
remains 0.001; the runtime constructor probe recorded effective normalization
to 0.01. That probe is an observation, not an independent per-request setting
or loaded-weight attestation.

No reference-review flags were detected on these five cases. Absence of a
bounded signal does not certify semantic reference validity. Cost/latency
preference was not assessed. The official scorer results and original labels
are retained; no ambiguity exclusions, reference corrections or held-out
evaluation were applied.

The owner prepared and ran the bounded coverage selection: one constructed
candidate per available benchmark/source-file stratum, selected using the
existing outcome-independent hash rule. The measured plan contains 69 requests
across 55 groups: APIBank 17, BFCL 12, RoTBench 17, ToolAlpaca 17 and ToolEyes six.
All 26 original construction blocks remain retained. Sixteen possible
benchmark/source combinations have no construction candidate; they are not
silently treated as completed strata. The five clean cases deliberately repeat
the earlier feasibility selection in a separate run, never retried or pooled.
Only one of the 64 selected perturbed cases has its clean anchor selected.
This is a coverage diagnostic, not a paired robustness design or a
representative accuracy estimate.

The coverage notebook passed context preflight: maximum rendered prompt length
4,633 tokens, plus the frozen 1,024-token completion allowance, within the
8,192-token context. No prompts were truncated and no rows were dropped.
Generation completed all 69 requests with zero resumed visits, no unfinished
sessions and no missing usage counters. Recorded usage is 88,220 prompt and
3,519 completion tokens (91,739 total); session wall is 55.488206979 seconds
and summed request elapsed time is 54.439490916 seconds. These exclude complete
setup/loading/idle allocation and do not measure GPU active time or monetary
cost. Remaining GPU quota is unrecorded.

The uploaded coverage ZIP passes integrity checks. All 293 archive members
are bound by the new scoring policy; all 279 recorded outcome-file hashes
reconcile and all 69 request hashes and frozen response validations reproduce.
Whole-output eligibility is 69/69. Meaningful-token eligibility is 39/69:
APIBank 5/17, BFCL 12/12, RoTBench 16/17, ToolAlpaca 0/17 and ToolEyes 6/6.
The 30 unavailable cases comprise 17 existing ToolAlpaca scope exclusions,
five APIBank no-parsed-call outcomes, seven APIBank format exclusions and one
RoTBench output with two ReAct actions. The generic saved alignment message is
preserved; new diagnostic categories explain the exclusions without modifying
frozen methods or scores. Ineligibility is not an official correctness label.

Coverage reference scoring remains pending locally. The supplied separate
adapter will retain 63 reference-compliance cases and six ToolEyes relevance
cases, including alignment-unavailable outcomes. Reference flags and explicit
cost/latency-objective diagnostics remain distinct; preference success is not
assessed. No coverage accuracy, AUROC/AP, calibration, risk–coverage result,
routing benefit or Task 3 completion is asserted.

## Corrected development-generation implementation

The [corrected development workflow](research_track_v1/CORRECTED_DEVELOPMENT_GENERATION_V1.md)
prepares hash-bound requests from the preserved development audit, supports
explicit local-server dispatch with write-once intent and response records,
and replays frozen Task 2 evidence on CPU. Synthetic tests do not establish
corrected full-population results. Local source/request-plan verification and
the corrected Qwen 1.5B five-case feasibility and 69-case coverage generation/
evidence checks have now passed, as recorded above.
Corrected Llama 3B 69-case development generation and scoring are now verified.
Corrected Qwen 7B and fallback runs and broader static runs remain pending;
the earlier serving pilots are distinct evidence.
Held-out access and main readiness remain disabled; official labels and existing outputs are unchanged.

## Development-only preparation implementation

A [trusted development exporter and separate full-population auditor](research_track_v1/DEVELOPMENT_PIPELINE_V1.md)
have been implemented from commit `05a95bf` and tested on synthetic partitions.
The original local primary-development audit retained 1,754 rows / 140 groups,
with 1,728 construction candidates and 26 retained blocks. The subsequent
diagnostic replay classified 12 missing declarations and 14 conflicting
schemas; candidate eligibility was unchanged. No model or held-out analysis is performed
by the auditor; the exporter necessarily reads mixed source bytes to filter
partitions. Official references and the existing split remain unchanged.

## Corrected research-track planning

A [main-experiment proposal](research_track_v1/MAIN_EXPERIMENT_PROTOCOL_V1.md)
and [full-development audit design](research_track_v1/DEVELOPMENT_POPULATION_AUDIT_PLAN_V1.md)
have been prepared from commit `344234f`. These documents remain planning
artifacts, not a final protocol freeze or a claim of completed main experiments. The separate full-development audit and
corrected generation/scoring implementations have since been completed within
their recorded development-only scopes. The existing 69-case corrected
diagnostic and eight-response smoke do not certify the full 140-group development inventory.
Reference labels and the grouped split are unchanged; ToolEyes relevance and
cost/latency-preference interpretation remain distinct. No held-out record is
needed for the supplied plan/configuration checks.

## Current position

Task 1 and Task 2 are complete within their recorded scope. The benchmark,
split, model settings, parser, and uncertainty definitions are frozen.
Task 2 was approved and published in
[`b03ddf4`](https://github.com/RavindraSSK/uqroute-tc/commit/b03ddf49eacfebeff69ca65014e5b0a36e708c40),
with 53 tests passing in the local Windows verification.

| Stage | Status |
|---|---|
| Task 1 — Benchmark and experiment engine | Complete; settings frozen |
| Task 2 — Parser and uncertainty engine | Complete; methods frozen with scoped format exclusions |
| Task 3 — Robustness study | Development studies complete for three small models: primary static, corrected repeated and sensitivity; diagnostics/reporting supplied. Final protocol decisions, held-out evaluation and final result freeze remain pending |
| Task 4 — Routing and recovery | Offline gate/frontier/baseline accounting implemented; corrected matched fallback generation and local replay complete. Owner reference scoring and paired CPU replay complete; Fixed-cap matches and saved accounting reviewed; tested group-separated validation supplied. Owner group-separated development validation complete. Conditional paired intervals reviewed; no final dominance/cost claim. Owner recovery preparation complete; All 4,824 CPU tokenizer contexts fit; bounded smoke staging/ledger supplied; owner smoke staging complete (30 requests); pinned L4 notebook supplied; 30-response L4 smoke complete and independently replayed; owner CPU import complete; owner reference diagnostic complete (4/24; relevance 3/6); owner structural review complete; owner matched fallback smoke complete, all 155 hashes and exact independent replay verified; owner import and paired scoring complete (reference 4/24 versus 10/24, six gains/zero losses; relevance 3/6 each, two gains/losses); paired behaviour review supplied; broader recovery, final objective, live escalation and full costs pending |
| Task 5 — Final package | Pending |

The reference Llama 3B clean run scored 102/199 against 103/199 on the seeded leaderboard. We accepted the one-case difference as a near reproduction after reviewing the result; the published score was not matched exactly. The split uses dataset identities alone, without model scores.

Task 2 has working single-sample and repeated-sample measures, with scoped
development evidence for the conservative alignment rules. The expanded
APIBank rule has been re-audited on all 24 saved APIBank/ToolAlpaca format
responses. The recorded exclusions remain part of the frozen methods:
ToolAlpaca has no meaningful-token score, and unsupported or ambiguous
formats retain an unavailable status. Qwen 1.5B has a checked 69-case
development throughput diagnostic. Llama 3B has a checked fresh 69-request run:
61 complete and eight truncated outcomes in 508.11 seconds. Both fresh server
logs show requested temperature 0.001 clamped to 0.01; this effective setting
must be disclosed without rewriting the frozen request configuration.
Qwen 7B has a checked fresh 69-request run: 68 complete and one truncated
outcome in 661.17 seconds. The 14B AWQ fallback has 62 complete, five
invalid-evidence and two truncated outcomes in 480.57 seconds. The invalid
records contain internal generated special tokens absent from visible text;
the frozen validator correctly leaves their probability scores unavailable.
Held-out perturbed
evaluation has not begun. Literature review completion remains separate from
these implementation milestones; see `docs/literature/EVIDENCE_MATRIX.md`.

## Completion standard

Every completed component must include:

1. Working code.
2. Credible evidence.
3. A clear explanation of the decision and its limitations.

## Task 1 — Benchmark and experiment engine

- [x] Create the Python package structure.
- [x] Configure the local Python environment.
- [x] Implement base-task identity rules.
- [x] Implement the benchmark population audit.
- [x] Add identity and audit unit tests.
- [x] Pass Ruff, pytest, and dependency checks.
- [x] Create the local foundation commit.
- [x] Write the draft evaluation protocol.
- [x] Select the primary and sensitivity evaluation populations in the draft protocol.
- [x] Verify a published clean result within one case, with the post hoc tolerance disclosed.
- [x] Create grouped development/held-out partitions.
- [x] Verify partition isolation.
- [x] Implement the resumable five-case experiment runner.
- [x] Capture and validate token log-probabilities on five development cases for each small model.
- [x] Verify scoring and saving in Colab; verify the runner's resume path.
- [x] Confirm that the proposed 14B AWQ fallback serves and yields five valid development records on the L4.
- [x] Freeze the Task 1 benchmark, model, split, and single-sample settings; keep later methods draft.

## Task 2 — Parser and uncertainty engine

- [x] Implement canonical keys for the pinned benchmark parser's tool calls.
- [x] Test equivalent and different tool calls.
- [x] Implement and validate the three whole-output single-sample token measures.
- [x] Review and commit the meaningful-token score for BFCL Python-call output.
- [x] Verify conservative token-to-call alignment for supported BFCL, single-action ReAct, and bounded APIBank formats. The full 24-record APIBank/ToolAlpaca re-audit gives 10/12 eligible APIBank outputs, with the eight previously valid scores unchanged and zero validation errors or regressions. The APIBank `<tool>` response remains ineligible because the saved parser drops its JSON arguments; one further APIBank response has no parsed call. ToolAlpaca remains outside meaningful-token scoring. This is scoped development evidence, not general format coverage.
- [x] Implement ten-sample canonical-call entropy and disagreement, with exact-string ablation.
- [x] Review and commit the deterministic 30-case development repeated-sample subset.
- [x] Validate ten seeded requests on one selected clean development BFCL case with Qwen 1.5B; all ten user-reported records were complete, byte-aligned, and parsed as calls.
- [x] Complete the selected 30-case development repeated-sample subset for all three small models. Uploaded status-aware audits score all 30 cases for each model.
- [x] Review and freeze the repeated-sample settings and status policy before held-out evaluation. The truncation policy was added after inspecting Qwen 1.5B development outputs and is disclosed as a retrospective development decision.
- [x] Approve and publish the parser and uncertainty freeze in `docs/config/task2_uncertainty_v1.json` at commit `b03ddf4`. It pins the implementation fingerprints, score formulas, format eligibility, and unavailable-evidence rules. The full patched suite passed 53 tests on Windows. ReAct duplicate JSON keys are rejected; Task 3–4 analysis, calibration, routing, and recovery decisions remain draft.

## Task 3 — Robustness study

The [requirements review](research_track_v1/TASK3_REQUIREMENTS_REVIEW_V1.md)
records the historical baseline. [Readiness v3](research_track_v1/TASK3_DEVELOPMENT_READINESS_V3.md)
updates the completed development evidence and remaining closure requirements.
The preserved original audit and denominator sidecar retain all 26 construction
blocks. All three small models have now completed corrected primary-development
runs, the corrected repeated subset and the separate sensitivity extension.
Final analysis freeze and new held-out access remain disabled.

- [x] Complete the original primary-development construction/reference audit with all rows retained.
- [x] Diagnose all 26 construction blocks without changing schemas or official labels.
- [x] Run and review the separate development denominator sidecar on the preserved original audit; owner supplied the reconciled report and 19 passing tests.
- [x] Verify corrected generation source fingerprints and the five-benchmark development request plan; 34 workflow tests passed locally.
- [x] Run corrected Qwen 1.5B five-clean-case feasibility and preserve the transferred raw-response evidence.
- [x] Reproduce all five saved response validations and complete the owner's local CPU replay; whole-output eligibility 5/5 and meaningful-token eligibility 4/5.
- [x] Implement and locally verify the development-only reference-scoring adapter, including Windows relative-path regression coverage; publish at `6dfed20`.
- [x] Record the five-case reference-compliance result (2/4) separately from ToolEyes relevance (0/1), without changing labels or applying exclusions.
- [x] Integrate and locally verify bounded coverage preparation: owner supplied 25 new tests and 34 generation tests passing; implementation committed and pushed as `65058a0`.
- [x] Prepare and review the measured 69-case / 55-group coverage report, approved manifest hash, five intentionally repeated clean cases and pairing limits.
- [x] Pass the pinned-tokenizer context preflight, complete all 69 corrected Qwen coverage requests and export a new evidence archive.
- [x] Verify the uploaded coverage archive, 279 recorded outcome-file hashes and all 69 request hashes/frozen response validations; document the 30 meaningful-token exclusions without changing methods.
- [x] Import and locally verify Qwen coverage CPU scoring; owner passed the 42-test suite with one Windows skip; published at `478d46a`.
- [x] Replay Qwen coverage locally and score unchanged development references: 21/63 reference compliance, separate ToolEyes relevance 5/6.
- [x] Complete bounded reference/objective diagnostics (`e3c7b61`) and Qwen available/common-cohort uncertainty diagnostics (`bbb1387`), with per-benchmark results and missingness retained.
- [x] Publish six illustrative failure reviews and a six-case evidence manifest with 17 verified hashes (`48ab2eb`, `a88688c`); no exhaustive confidence-band catalogue claim.
- [x] Complete corrected Llama 3B 69-case development generation, full local replay, separate-panel scoring and 46-test Windows verification with one skip (`6a09541`).
- [x] Complete three-model primary-development uncertainty analysis on explicitly matched eligible cohorts.
- [x] Complete corrected Qwen 7B coverage and all three 1,728-response primary-development small-model runs and CPU scoring.
- [x] Verify corrected context/evidence feasibility for the three small models used in the completed five-benchmark primary-development runs.
- [x] Complete corrected matched 14B AWQ fallback generation, context/runtime verification, replay and owner reference scoring; routing benefit remains a separate question.

- [x] Record completed per-model development session timings, usage and runtime allocation attestations.
- [ ] Check available quota and resource capacity before scheduling any further inference; session timing is not full policy cost.
- [x] Implement the separate development-only throughput runner; user verified 68 tests and Ruff on Windows.
- [x] Check supplied Qwen 1.5B manifest, original summary, runtime metadata and server log; retain the resume-accounting limitation.
- [x] Verify Llama 3B and Qwen 7B timing artifacts and replay their supplied truncated token evidence.
- [x] Verify 14B AWQ timing artifacts and replay all seven supplied non-complete records without changing frozen validation.
- [x] Check the uploaded 276-record CPU audit, its score eligibility, record fingerprints, usage and session accounting.
- [ ] Preserve current quota/budget evidence for future inference scheduling; do not infer it from completed runs.
- [x] Run corrected primary-development clean/static experiments for all three small models; retain non-complete evidence statuses.
- [x] Complete corrected repeated sampling: 900 slots across 30 selected cases per model, with saved-slot scoring and three-model signal comparisons.
- [x] Complete separate sensitivity-only development audit, preparation, 105 responses, local replay and scoring; no clean anchors.
- [x] Calculate development reference compliance, separate ToolEyes relevance, AUROC and noninterpolated AP, including missingness and shared cohorts.
- [ ] Finalize success-proxy and reference/objective dispositions; execution success remains unmeasured.
- [x] Analyze development risk–coverage and group-separated OOF calibration, including the constrained mapping diagnostic.
- [ ] Freeze final mapping, validation, denominator, risk–coverage and figure rules; record immutable development-only method selection.
- [x] Produce retrospective development failure bands/catalogue and illustrative cross-model review.
- [ ] Finalize catalogue interpretation and failure-band rules for final evaluation.
- [ ] Approve the final shared protocol, then evaluate frozen methods on held-out groups and preserve immutable final results.
- [x] Calculate diagnostic group-bootstrap metric intervals and clean/perturbed paired-change intervals.
- [ ] Freeze final interval/weighting settings and reproduce final result figures before Task 3 closure.

## Task 4 — Routing and recovery

See [development routing and fallback preparation](research_track_v1/DEVELOPMENT_ROUTING_V1.md).
The implementation and actual saved-pair replay are development-only. The owner
supplied all-pair transition totals and the gated/random report. Fixed-cap match
counts and saved usage/usability accounting are reviewed. Group-separated validation
and conditional intervals are owner-executed and reviewed. Recovery preparation
and the bounded controller/ledger are implemented. Owner context checks and
the 30-response L4 smoke are complete, with exact independent frozen replay.
Owner local import, reference scoring and structural review are complete.
Matched thirty-episode fallback preparation is owner-complete, with an exact
independently reconstructed transfer. The L4 fallback smoke is owner-complete; all thirty responses independently
replay exactly, with all 155 export hashes verified. Owner CPU import is complete;
paired reference scoring is owner-complete, with six primary-panel gains and
zero losses. Paired structural review, broader recovery and the final objective
remain pending.
No final threshold or held-out routing-effectiveness claim is supplied.

- [x] Implement a label-independent CPU gate with inclusive threshold ties and explicit unavailable/invalid-evidence escalation.
- [x] Implement offline threshold-frontier replay without choosing an operating point.
- [x] Implement small-only, fallback-only, always-cascade and exact-count seeded random baseline replay, including rescues/harms and missing-usage accounting.
- [x] Supply and execute the preparation command for the prompt-matched 1,728-case corrected 14B AWQ development plan.
- [x] Verify all-request fallback context/runtime, generate all 1,728 corrected matched development responses, check all 6,942 evidence-file hashes and independently reproduce full local replay.
- [x] Supply a separately evidence-bound fallback CPU scorer and import/replay command; synthetic regression tests pass.
- [x] Run/review owner fallback reference scoring against preserved development sidecars: 787/1,512 reference matches and separate ToolEyes relevance 208/216; no exclusions or label changes.
- [x] Implement evidence-bound paired-input loading, compact threshold frontiers and fixed-cap/random-count diagnostic views; 28 new synthetic checks and 20 existing kernel checks pass.
- [x] Execute the paired-routing command on all four saved owner runs at `ca417d1`; full scorer/replay revalidation passed and all-pair aggregate counts reconcile.
- [x] Review supplied fixed-cap gated/random match counts, including Qwen 7B 830/1,512 matches at 378 fallback calls, 68 rescues and 28 harms; retrospective only.
- [x] Review supplied saved final-output usability, token totals and cached elapsed-time accounting; Qwen 7B's 25% reference gate has a higher time proxy per match than fallback-only.
- [x] Implement five benchmark-stratified canonical-group folds, training-only label-independent cap thresholds, same-fold random controls, incomplete-coverage reporting and OOF accounting; 27 new synthetic checks pass.
- [x] Execute/review owner five-fold group-separated validation at `5528f84`: all 75 focused checks pass; reference and ToolEyes OOF results/realized budgets supplied with incomplete views retained.
- [x] Implement paired group-bootstrap contrasts conditional on fixed OOF decisions, with shared benchmark-stratified draws, usage/missingness safeguards and explicit learning-uncertainty limits; 26 new tests pass.
- [x] Execute/review owner conditional intervals at `ec2317e`, with 73 focused checks passing; no final reliability, timing-efficiency or monetary-saving conclusion is recorded.
- [x] Implement a reference-free clean-development recovery preparer and bounded decision controller; separate planned/observed injection, no-fault/unknown partitions and context-bound responses. Owner preparation completed at `f2bbb44` with 52 checks passing.
- [ ] Select and validate a grouped development operating point under a fixed objective.
- [ ] Implement and measure live fallback escalation; offline cached timing is not online latency.
- [x] Execute/review owner recovery preparation: 750/828/834 pending eligible episodes and 90/12/6 terminal no-injection plans; zero generation or observed injection.
- [x] Supply an owner-archive-bound CPU tokenizer preflight for both roles, complete context inventories and overflow reporting; 19 synthetic checks pass, including production-built nonstreaming requests.
- [x] Run/review owner pinned-tokenizer context preflight at `2b9527d`: all 4,824 contexts fit with zero overflows; largest prompt plus output allowance is 6,627/8,192 tokens.
- [x] Supply bounded, label-independent Qwen 1.5B smoke staging and a separate write-once small-stage ledger; 25 synthetic checks pass, including complete staging/publication and unknown-slot handling.
- [x] Execute/review owner smoke-staging summary: 30 small-stage requests, five groups, all five benchmarks and zero fallback requests; generation remains zero.
- [x] Supply an archive/manifest-bound Colab L4 smoke notebook with matching local/server token sequences, bounded dispatch, frozen replay, shutdown and partial export; 18 new CPU tests pass.
- [x] Execute/review the bounded L4 smoke: 30 complete responses, 30 recorded submissions, zero unknown/HTTP-failure slots, all 152 hashes verified and exact independent frozen replay; 19 parsed candidates, not a correctness claim.
- [x] Supply a source/archive-bound CPU owner importer with nine synthetic safeguards; actual archive replay matches all records and summary exactly.
- [x] Run/review owner local import at `be2ef44`: all nine checks completed with one Windows symlink skip; all 152 hashes, records and summary match, with no inference.
- [x] Specify a development-only unchanged-clean-reference endpoint after fault feedback and supply CPU smoke scoring with context/initial-source/reference guards; 16 new tests pass.
- [x] Run/review owner reference diagnostic at `e25c8e6`: 4/24 post-fault reference matches versus 18/24 repeated initial matches; separate relevance 3/6 versus 6/6, with no mismatch-to-match episodes.
- [x] Independently inspect saved-text structure and supply a reference-preserving CPU behaviour/private-example review; 14 new frozen-parser tests pass.
- [x] Run/review owner behaviour cross-tabs at `4f7b584`, with all 14 checks passing and exact score reproduction; eleven no-call outputs account for eleven of fourteen reference losses, with no relabeling/exclusion.
- [x] Supply all-thirty-context matched 14B AWQ fallback staging and a separate no-retry fallback ledger with known-parent binding; 30 tests pass and actual saved-history construction checks pass.
- [x] Execute/review owner matched fallback staging at `c3cbf9f`: thirty successful checks, one Windows skip, all 30 pairs retained, max prompt 3,872 and no overflow; independently reconstruct both transfer hashes and supply a pinned L4 launcher with 25 passing CPU checks.
- [x] Generate/review all thirty matched fallback smoke responses on L4; verify all 155 indexed hashes and exact independent replay, with no unknown/HTTP failures; supply owner CPU import with fifteen passing checks.
- [x] Run/review owner fallback import at `d5be459`: fifteen checks, one Windows skip, all 155 hashes and exact independent replay match.
- [x] Supply a reference-preserving paired CPU scorer with byte-exact original small-score reproduction, all 30 pairs and separate ToolEyes relevance; 24 new plus 16 original scorer tests pass.
- [x] Run/review owner paired scores at `1cf2bd7`: 24 tests pass; reference 4/24 versus 10/24 with six gains/no losses; relevance 3/6 each with two gains/two losses. Original scores and all 30 pairs remain.
- [x] Supply a paired structural/private-example review with 14 passing frozen-parser checks and independently verified all 30 structural transitions.
- [ ] Execute/review owner structural/reference joins and fault semantics before choosing recovery scope/endpoint/resource plan or expanding GPU collection.
- [ ] Complete broader recovery model/resource checks, collection and scoring dispositions; the smoke does not certify other roles or full-study quota/cost.
- [ ] Implement durable recovery dispatch, record actual injection/response evidence, and evaluate recovery/baselines with the frozen scoring dispositions.
- [ ] Add complete policy cost measurement, including repeated sampling/recovery/overhead and uncertainty in usage/pricing.
- [ ] Validate all routing baselines on group-separated development evidence, then review full policy costs and uncertainty.
- [ ] Freeze the shared protocol and selected threshold before held-out evaluation.

## Task 5 — Final package

- [ ] Complete the required ablations.
- [ ] Reconstruct figures from saved records.
- [ ] Run a clean-environment test.
- [ ] Package the code and documentation.
- [ ] Build the cached demonstration.
- [ ] Complete the report and presentation.

## Compute readiness

The Colab L4 has served all four pinned models on five development cases each,
including the 14B AWQ fallback. Colab Pro+ and Kaggle T4 are the planned
inference resources; local CPU work covers scoring, analysis, figures, and
writing. No additional GPU has been identified as required by the pilot.

Full-run capacity is not yet measured. Running all four models once on each
of the 2,477 primary static cases would require 9,908 generations. The frozen
30-case repeated-sample subset has generated 900 saved slots across the three
small models, before retries, recovery experiments, or other ablations. Run
and time a representative batch for each model, record GPU hours and current
platform quota, then schedule resumable batches. Reassess external compute
only if those measurements show the available resources are insufficient.

## Verified evidence

| Evidence | Result |
|---|---|
| Corrected Qwen 1.5B five-case evidence | Archive SHA256 `b0c985069e6c68c03eaa238bdcdf7d012ca5426a8ed19976a533e06a0d069191`; prepared manifest SHA256 `f83f7398e2cfb465f397f247a7e7cd815c422ecf6ba7d55fc95aef517ef8c3cf`. ZIP integrity and all 23 recorded outcome-file hashes checked; five frozen raw-response validations reproduced. Owner local replay reports five complete slots, no resumed visits or unfinished sessions, 5/5 whole-output and 4/5 meaningful-token eligibility, no missing usage and no prior file modification. |
| Corrected five-case reference scores | Owner local scorer output: APIBank and BFCL pass; RoTBench and ToolAlpaca fail reference compliance, yielding 2/4. ToolEyes relevance is reported separately at 0/1. No bounded reference flags detected; cost/latency preference unassessed; no label changes or ambiguity exclusions. This result is not comparable to the earlier four-model BFCL-only five-case pilot as a model-performance trend. |
| Corrected scoring verification | Owner supplied 31 tests passing with one Windows symlink skip and clean staged whitespace checks; four source/configuration/documentation files committed and pushed as `6dfed20`. Generation regression suite: 34 tests passed. See `research_track_v1/CORRECTED_DEVELOPMENT_SCORING_V1.md`. |
| Development denominator reconciliation | Owner report: 1,754 rows / 140 groups, 1,728 constructed candidates / 26 blocks; 1,538 reference-panel inventory rows (1,512 candidates) and 216 separate ToolEyes relevance rows. Reward overlap: 498 rows, 486 assessed and 12 construction-blocked; 61 cost-objective and 61 latency-objective detections, with 364 objective-nondetected rows. Flags do not exclude cases and detection is not semantic adjudication. All 1,614 perturbed rows have a clean anchor; 1,588 pairs have both prompts constructed. Owner population-policy suite: 19 tests pass. |
| Bounded coverage implementation and plan | Owner verified 25 new CPU tests plus 34 generation regression tests, then committed/pushed six files as `65058a0`. Prepared plan: 69 cases / 55 groups, five clean / 64 perturbed; per-benchmark counts 17 APIBank, 12 BFCL, 17 RoTBench, 17 ToolAlpaca and six ToolEyes. All 26 blocks remain retained. Only one selected perturbed case has its selected clean anchor; this is not a paired robustness design. |
| Corrected 69-case coverage evidence | Archive SHA256 `700c65c545d5965d72e0f6c9796f589a69ebd8080a924562fca1c832048155f8`; prepared manifest SHA256 `a00a33c9bbc40a15acb02a3a26ebcfdcb6bfdf00aa0dcdde39544e658f075ffb`. ZIP integrity and 279 recorded outcome hashes checked; all 69 request hashes and frozen response validations reproduced. All 69 complete; 69 whole-output eligible, 39 meaningful-token eligible, no missing usage, resumed visits or unfinished sessions. Raw evidence review is complete; owner local coverage replay/reference scoring remains pending. |
| Coverage meaningful-token exclusions | 17 ToolAlpaca scoped exclusions, five APIBank no-parsed-call outcomes, seven APIBank frozen-format exclusions and one RoTBench multi-action response. Saved messages and frozen methods remain unchanged; exclusion is not an incorrect-call label. The repeated clean APIBank output changes format from the prior run and is now alignment-ineligible; this does not establish an implementation regression. |
| Coverage context/runtime observation | Maximum rendered prompt 4,633 tokens; frozen completion allowance 1,024, context 8,192, no truncation or dropped prompts. Usage 88,220 prompt / 3,519 completion / 91,739 total tokens; session wall 55.488206979 s, request elapsed sum 54.439490916 s. Setup/loading/idle allocation and monetary cost are not included; provider quota remains unrecorded. |
| Coverage scoring package status | Separate archive-bound development adapter supplied from `65058a0`; package-author synthetic CPU checks: 37 new scoring, 31 unchanged five-case scoring and 34 generation tests pass. Proposed output retains 63 reference-compliance and six separate ToolEyes relevance cases; actual scores, flags, owner checks and publication remain pending. No held-out access or preference-success scoring is enabled. |
| Qwen 1.5B throughput diagnostic | 69 primary development cases (5 clean / 64 perturbed), 51 canonical groups, 69 nonempty benchmark/file strata, 17 files. Original summary reports 69 complete attempts in 106.46709268199993 s, with 74,949 prompt and 7,164 completion tokens; observed GPU window at least 769.8995201580001 s. Settings/source fingerprints, split membership, arithmetic and 69 HTTP-200 generation requests checked. Raw attempt evidence was not locally replayed; official correctness is unscored. See `docs/evidence/qwen15b_throughput_dev69_summary.json`. |
| Throughput resume reconciliation | The uploaded CPU audit includes Qwen 1.5B's original 69-processed / zero-resumed session (106.467092682 s) and later zero-processed / 69-resumed session (101.633968582 s). Aggregate wall is 208.101061264 s. Retain original fresh inference speed and report resume checking as additional overhead. |
| Task 3 runner and Llama timing | Runner published at `adb48d1`; user verified 68 tests and Ruff. Llama-specific notebook at `d031146` produced 69 fresh requests: 61 complete, eight truncated, 508.107638493 s; 76,347 prompt / 18,056 completion tokens. Manifest/session/runtime/log checked, including 69 HTTP 200 responses; the eight truncations were subsequently replayed as recorded below. Raw replay of 61 complete responses and correctness remain pending. See `docs/evidence/llama3b_throughput_dev69_summary.json`. |
| Server temperature observation | Fresh Qwen and Llama logs each contain 69 warnings: requested temperature 0.001 is clamped to 0.01 by the server. Frozen request settings are preserved; effective settings must accompany reported results. |
| Llama truncation evidence replay | Uploaded archive contains the 69-row compact audit and eight full truncated attempts: four ToolAlpaca / four RoTBench, across five base-task groups. All eight finish at length 1,024; pinned token-evidence replay matches every saved dictionary and reconstructed original-record hashes match the audit. Patterns: three holiday lists, two racing lists, one country example, two repetitive result-like outputs. Six have nonempty saved parser outputs, illustrating that extraction does not establish correctness. Truncations consumed 8,192/18,056 completion tokens and 229.56 s measured attempt time. Official correctness and raw replay of the other 61 responses remain pending. See `docs/evidence/llama3b_truncation_dev69_audit.json`. |
| Benchmark revision | `d5d03180de41eb30a6c796d04a9bfbd9dad85c1d` |
| 14B AWQ throughput diagnostic | 69 fresh requests on the same development cases; 62 complete, five invalid-evidence and two truncated outcomes. Batch wall 480.565455616 s; 74,949 prompt / 12,067 completion tokens; observed GPU window at least 1,018.707215394 s. Manifest/configuration, split membership, arithmetic and 69 HTTP 200 responses checked. Frozen validator replay matches all seven supplied non-complete records. Five APIBank cases across three groups contain internal `<\|im_start\|>` tokens omitted from visible text; probability scores remain unavailable. Two ToolAlpaca holiday cases from one group truncate at 1,024 tokens with valid evidence. No automatic repair/retry; official correctness unscored. See `docs/evidence/qwen14b_awq_throughput_dev69_summary.json`. |
| Four-model timing diagnostic total | Summaries account for 276 model–case attempts: 260 complete, 11 truncated and five invalid-evidence. The uploaded CPU audit reports frozen validation of all saved Drive records; local compact-report checks reconcile identities, scores, tokens, statuses and sessions. Of 271 token-evidence-valid records, 260 are whole-output-score eligible because truncations remain excluded. The 16 previously supplied non-complete raw records match audit fingerprints and pinned-parser replay; the other 260 raw records were not uploaded. Official correctness is pending. See `docs/evidence/four_model_static_dev69_record_audit_summary.json`. |
| Qwen 7B throughput diagnostic | Same 69 case identities as the Llama audit, all primary development, 51 groups; fresh session processed 69 and resumed zero. Summary: 68 complete / one truncated, 661.167963701 s batch wall, 74,949 prompt / 11,226 completion tokens. Manifest, split membership, summary arithmetic and 69 HTTP 200 responses checked. All 69 server warnings clamp requested temperature 0.001 to 0.01. The one supplied truncated record reaches 1,024 tokens and its token evidence replays exactly; it is the ToolAlpaca holiday case in `paraphrase_tool_description.jsonl`, also truncated for Llama. The other 68 raw records and official correctness are unreviewed/unscored. Evidence: `docs/evidence/qwen7b_throughput_dev69_summary.json`. |
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
| Llama 3B reference / observed | 103/199 (`0.5176`) / 102/199 (`0.5126`) strict clean accuracy |
| Llama run settings | Model/tokenizer revision `0cb88a4f764b7a12671c53f0838cd831a0843b95`; temperature 0, 16 workers, 1,024 max tokens, BF16, L4, vLLM 0.30.0, PyTorch 2.13.0+cu130 |
| Llama run integrity | 199 unique predictions, 199 scored IDs, no missing or extra clean IDs, 0 inference errors (checked in Colab) |
| Grouped split | `docs/splits/group_split_v1.json`; seed 1729, 70/30 target, benchmark-stratified SHA-256 group ranking |
| Primary split | 140 development / 59 test groups; 1,754 / 723 static rows |
| Sensitivity-only split | 34 development / 15 test groups; 35 / 15 static rows |
| Split validation | 16 tests pass; all 2,527 retained rows map to 248 groups without leakage; manifest regenerates identically |
| Qwen 7B smoke check | Revision `a09a35458c702b33eeacc393d103063234e8bc28`; first five clean BFCL cases scored 5/5 with 0 inference errors. This is a feasibility check, not a full benchmark result. |
| Qwen 7B token evidence | On the same five cases, all calls parsed and all visible-token log-probabilities were finite. Visible token bytes aligned after excluding the trailing `<|im_end|>` token. Saved in Colab Drive. |
| Five-case runner | `src/uqroute_tc/inference/pilot.py` selects clean development cases, records token evidence, writes scorer-compatible output, and resumes without repeating completed cases. The three small-model five-case pilots completed in Colab; Qwen 7B and Qwen 1.5B completion was user-reported, and the Llama 3B final verification message was supplied. No aggregate five-case accuracy is recorded here. |
| Small-model development pilot outputs | Qwen 7B: `pilots/qwen25-7b-dev-five-v1`; Qwen 1.5B: `pilots/qwen25-15b-dev-five-v1`; Llama 3B: `pilots/llama32-3b-dev-five-v1` under `/content/drive/MyDrive/UQRoute-TC/`. These are five-case development checks, not full benchmark reproductions. |
| Llama token-evidence recovery | All five Llama responses had a trailing `<|eot_id|>` log-probability token; excluding it made chosen-token bytes exactly match the visible UTF-8 output. Validator fix `8f919e3` admits this terminator only after exact byte alignment. Original invalid records were backed up by the corrected recovery notebook; the user reported five unique scored-ready records with valid token evidence. |
| Qwen 14B AWQ fallback feasibility | The user reported five unique scored-ready records with valid token evidence on the L4, saved in `pilots/qwen25-14b-awq-feasibility-five-v1`. This establishes a serving/evidence feasibility check only; five cases cannot establish routing benefit or full benchmark accuracy. |
| Task 1 settings freeze | `docs/config/task1_single_sample_v1.json` records all four pinned model/tokenizer revisions and the benchmark/split/generation settings. The fallback revision `539535859b135b0244c91f3e59816150c8056698` was verified against the saved Drive pilot manifest. The 14B notebook is pinned to the same revision for a fresh run. At this scoped Task 1 freeze, Task 2–4 methods and the full held-out protocol were still draft. |
| Four-model development audit | The user supplied the official case-score comparison for the same five clean development BFCL cases: Qwen 1.5B, Llama 3B, Qwen 7B, and Qwen 14B AWQ each scored 5/5. The fallback rescued 0/5 errors for each small model because all small-model predictions were correct. The audit notebook saved `pilots/four_model_pilot_audit.json` in Drive; the user-supplied table is summarized in `docs/evidence/four_model_five_case_summary.json`. This is a feasibility check, not a routing-effectiveness estimate. |
| Canonical-call implementation | The pinned benchmark parser's output is converted into type-aware keys without altering scorer inputs. A direct compatibility check using the pinned parser found one shared key for equivalent Python, JSON, XML, ReAct, and ToolAlpaca examples. The saved 20-prediction audit found 20 parsed calls matching saved calls and 20 valid single-sample scores. The frozen parser-status policy keeps nonempty outputs without calls in an explicit `unparsed_or_no_call` cluster without inferring whether no tool was intended. |
| CPU uncertainty measures | Saved chosen-token responses are revalidated for exact visible-byte alignment before computing sequence NLL, mean token NLL, and maximum token surprisal. Ten-output canonical and exact-string clustering computes entropy in nats and disagreement with failed/empty outcomes in the denominator. Uploaded 30-case development audits for all three small models were checked locally; the raw Drive responses were validated in Colab and not uploaded here. |
| BFCL meaningful-token pilot | The 20 saved outputs from four models and five clean development BFCL cases have exact visible-byte alignment after excluding 15 `<|im_end|>` and five `<|eot_id|>` end tokens. The committed AST-to-parser rule accepted all 20; 317 visible tokens overlapped names or values, of which 55 also covered syntax or whitespace. The broader-format rule remains under development. |
| Four-format development diagnostic | Qwen 1.5B produced four complete, byte-aligned records on one clean development case each from APIBank, RotBench, ToolAlpaca, and ToolEyes. The user reported official scores of 0/4. The released parser returned one call each for RotBench and ToolEyes and no call for APIBank and ToolAlpaca. All four were outside the committed BFCL-only meaningful-token rule. A local ReAct draft matched the two saved parsed calls and token streams: RotBench 11 selected / 2 boundary-crossing tokens; ToolEyes 6 / 1. This is a format and failure-case diagnostic, not an accuracy estimate; compact evidence is in `docs/evidence/qwen15b_four_format_development.json`. |
| APIBank and ToolAlpaca format audit | The uploaded 24-case audit contains 12 clean development cases per benchmark, all unique, complete, byte-aligned, and consistent with saved calls. APIBank: 11 parsed, 1 `unparsed_or_no_call`, 7/12 officially correct. ToolAlpaca: 4 parsed, 8 `unparsed_or_no_call`, 1/12 correct. A local APIBank JSON rule aligned two exported calls: 50 and 14 selected tokens, both with 0 boundary crossings. Two exported ToolAlpaca outputs mix prose and examples; one scored correct because its expected call was present alongside two example country names that the parser also treated as calls. Neither ToolAlpaca output has a trusted meaningful-token span. These file-order development counts are descriptive; compact evidence is in `docs/evidence/apibank_toolalpaca_format_alignment.json`. |
| APIBank markup alignment diagnostic | Two further saved, byte-aligned APIBank development responses were exported from the same 24-case run. A bounded rule aligned one fenced `<toolcall>` response with its saved parsed call: 45 selected tokens and zero boundary crossings. The other response uses `<tool>` and includes JSON arguments, but its saved parsed call has empty parameters. Its meaningful-token score remains unavailable. This does not establish wider markup coverage; the official parser remains unchanged. Compact evidence: `docs/evidence/apibank_markup_alignment.json`. |
| Saved alignment eligibility audit | The 24 saved Qwen 1.5B APIBank/ToolAlpaca development records were rechecked on CPU. All 24 were complete with valid token bytes and matched the pinned parser and prior audit. APIBank: 8/12 received valid meaningful-token scores with zero boundary-crossing tokens; three parsed outputs did not match a supported complete-call format, and one had no parsed call. ToolAlpaca: 0/12 eligible under its scoped exclusion. This file-order diagnostic does not estimate population coverage or correctness. Compact evidence: `docs/evidence/qwen15b_alignment_coverage_dev24_summary.json`. |
| Remaining APIBank format replay | Two of the three parsed APIBank outputs marked unsupported in the first 24-case audit were exported with full chosen-token evidence. One has prose before a single fenced JSON call; the other has a separate fenced thought block before one JSON call. A narrow rule matched their saved parsed calls and exact UTF-8 token bytes, selecting five tokens per response with zero boundary crossings. The third parsed output, `<tool>GetUserToken</tool>`, remains unavailable because the released parser drops its arguments. These two cases were selected after the first coverage audit; the expanded rule was subsequently rechecked on all 24 saved outputs. Compact evidence: `docs/evidence/apibank_remaining_alignment.json`. |
| Expanded alignment re-audit | The uploaded v2 audit reports 24 unique complete development records, valid token evidence and saved-parser agreement for all 24, and zero validation-error cases. APIBank eligibility increases from 8/12 to 10/12; only `apibank__level3_26` and `apibank__level1_217` become eligible. All eight previously valid scores remain unchanged; no case regresses. The ten eligible APIBank outputs have zero boundary-crossing tokens. ToolAlpaca remains 0/12 eligible. Local checks verified the uploaded report's identities, counts, comparison fields, split membership, and exact notebook-script fingerprint. Full responses were revalidated in Colab; eight earlier raw exports were replayed locally. Compact evidence: `docs/evidence/qwen15b_alignment_reaudit_dev24_summary.json`. These are development eligibility counts, not correctness or population coverage. |
| Repeated-sample subset | The committed selector identifies 15 development groups and 30 clean/perturbed cases. The user reported ten valid Qwen 1.5B BFCL pilot responses with canonical clusters `(9, 1)`. The uploaded Qwen 1.5B status-aware audit reports 300 saved slots: 299 complete and one truncated, with all 30 cases scored and zero validation-error cases. The clean RoTBench case retains its truncated slot in the ten-sample denominator; its canonical entropy is `2.0253` nats and disagreement `0.8`. All 29 previously scored cases match the first uploaded audit on reported score fields. Parser statuses total 252 `calls` and 48 `unparsed_or_no_call`; these are not correctness labels. The raw Drive records were validated by the Colab audit, but only its two uploaded audit summaries were inspected locally. Compact evidence: `docs/evidence/qwen15b_repeated_dev30_summary.json`. |
| Llama 3B repeated-sample run | The uploaded status-aware audit uses the same 30 selected development cases, split, and ten seeds as Qwen 1.5B. It reports 300 slots: 297 complete and three truncated, with 30/30 cases scored and zero validation-error cases. The three truncations occur in two RoTBench cases and one ToolEyes case, with their slots retained as explicit outcomes. Local checks confirmed unique case identities, settings, totals, and canonical score arithmetic; raw Drive records were validated in Colab but not uploaded. Parser statuses total 251 `calls` and 49 `unparsed_or_no_call`; these and the clusters do not measure official correctness. Compact evidence: `docs/evidence/llama3b_repeated_dev30_summary.json`. |
| Qwen 7B repeated-sample run | The uploaded status-aware audit uses the same 30 selected development cases, split, and ten seeds as the other small models. It reports 300 complete slots, 30/30 cases scored, and zero validation-error cases. Local checks confirmed unique case identities, settings, totals, and canonical score arithmetic; raw Drive records were validated in Colab but not uploaded. Parser statuses total 251 `calls` and 49 `unparsed_or_no_call`; these are not correctness labels. Compact evidence: `docs/evidence/qwen7b_repeated_dev30_summary.json`. |
| Three-model repeated-sample development total | The three uploaded audits account for 900 saved model responses on 30 shared cases: 896 complete, four truncated, and 90/90 model–case cluster scores with zero reported validation-error cases. The per-model records remain distinct; these diagnostic cluster scores do not establish tool-call accuracy, detection quality, or a routing threshold. |
| Repeated-sample settings and status freeze | `docs/config/task2_repeated_sampling_v1.json` fixes the development-only 30-case subset, ten seeds, generation parameters, ten-slot denominators, parser-status clusters, truncation/error handling, and exact-string ablation. This decision followed inspection of all three development audits; the truncation rule followed inspection of Qwen 1.5B outputs. Parser and uncertainty definitions are recorded separately in `docs/config/task2_uncertainty_v1.json`. |
| Task 2 method freeze | Approved and published at `b03ddf4`. `docs/config/task2_uncertainty_v1.json` records the pinned official parser, type-aware canonical keys, three whole-output scores, the scoped meaningful-token score, repeated-sample definitions, and unavailable-evidence rules. The freeze rejects duplicate ReAct JSON keys, including nested keys, before meaningful-token scoring. All 31 focused parser/uncertainty tests pass, and the user verified the full patched suite on Windows with 53 tests passing. A local replay of 30 available saved raw responses preserves all 27 eligible scores and three unavailable outcomes. The source hashes and development decision context are recorded in the configuration. Held-out analysis and routing choices remain draft. |
| Saved-output audit | `src/uqroute_tc/parsing/audit.py` and `notebooks/UQRoute_TC_Task2_Saved_Pilot_Audit.ipynb` audited four saved five-case pilot folders on a CPU runtime. The user supplied the 20-record audit showing 20 parser statuses `calls`, 20 saved-call matches, and 20 valid single-sample scores. |
| Source/test maintenance verification | `python -m ruff check src tests` passes with Ruff 0.16.10, and `python -m pytest -q` passes all 53 tests on Python 3.12. A saved 30-response replay retains all 27 eligible scores and three unavailable outcomes. The original freeze is preserved; `docs/config/task2_implementation_maintenance_v1.json` records the behavior-preserving lint changes and updated implementation hashes. |
| Dependency check | Passed |
| Foundation commit | `ac01cbc` |

## Protocol status

The Task 1 subset is frozen: 199 clean-anchored groups for the primary
population, all 248 single-turn groups for sensitivity analysis, the grouped
split manifest, four model revisions/roles, and single-sample serving settings.
Task 2 definitions are frozen in `docs/config/task2_uncertainty_v1.json`
by the approved, published commit `b03ddf4`. The full protocol remains
draft until calibration, routing, recovery, cost, and held-out analysis
decisions are frozen.

Clean results for Qwen 1.5B and Llama 3B and five Qwen 7B clean cases were seen before splitting. Report those clean scores descriptively. Use development groups for tuning and reserve unseen perturbed test cases for confirmatory analysis.

## Current next action

Run the [paired behaviour review](research_track_v1/RECOVERY_MATCHED_SMOKE_BEHAVIOUR_REVIEW_V1.md):
`python tools/development_audits/recovery_matched_smoke_review_v1/review_pairs.py`.
Paired reference scoring is complete at `1cf2bd7`. The final smoke review
reproduces all prior scores exactly, joins reference gains/losses to frozen
structural changes, and writes all thirty private examples. Read PRIVATE_REVIEW.md
locally and paste only the aggregate report. This closes smoke interpretation
before deciding recovery scope, endpoint and resource feasibility for larger
collection. It performs no inference, relabeling, exclusions, threshold choice
or held-out access; preserve both completed GPU runs and original scores.

Review [readiness v3](research_track_v1/TASK3_DEVELOPMENT_READINESS_V3.md)
and record the final development-only signal decision. Resolve population,
reference/objective interpretation, uncertainty applicability/missingness,
calibration mapping and fitting, weighting, bootstrap settings, risk–coverage,
failure-band and figure rules in an immutable shared protocol artifact.
Completed diagnostic policies are not a final freeze.

Keep the primary and sensitivity populations, reference compliance and ToolEyes
relevance distinct. Preserve official labels, all previous outputs and the
pre-split clean-exposure disclosure. Repeated-sampling slots are dependent;
small-cohort ranking gains do not establish deployment confidence or routing
benefits. Mean NLL is a practical single-response candidate; Qwen 7B canonical
entropy remains a ten-call challenger for further development comparison.

Implement and validate the separate Task 4 gate/fallback/recovery workflow and
full policy cost accounting under its own requirements. Freeze final shared
evaluation decisions before any new held-out access; then run the separately
authorized final static evaluation, reproduce final figures/catalogue and close
Task 3 only after reviewing its original requirements.

## Earlier diagnostic next action (historical)

The following describes the earlier saved-output scoring workflow, not
a claim that those outputs evaluate the corrected research adapter.

Run `notebooks/UQRoute_TC_Task3_Four_Model_Official_Scoring.ipynb` on CPU.
Use the pinned benchmark loader, parser and deterministic scorer for all 276
saved model–case responses, keyed by source file plus row ID. Preserve official
correctness independently of response status and retain unavailable uncertainty
scores. No threshold, calibration mapping or deployment acceptance rule is
selected in this diagnostic. Then review official per-case scores before
assessing uncertainty effectiveness or routing.
All four timing artifacts are checked; a later resume must not be reported
as fresh inference or replace the original speed measurement. Record individual
session outcomes, setup/observed allocation time, tokens, and current quota.
Use those measurements to schedule resumable development inference batches.
Keep literature/protocol/evidence links synchronized before drafting paper claims.

Use the frozen model and single-sample settings. Complete the broader
development clean and perturbation runs before selecting calibration and
gate thresholds. Keep held-out perturbation groups untouched until the
remaining analysis and routing decisions are frozen. The five-case pilot did
not test whether escalation helps.

The seeded per-case predictions are not in the pinned release, so the differing Llama case cannot be identified from it. The one-case tolerance was chosen after observing the result and must be disclosed when reporting the reproduction.
