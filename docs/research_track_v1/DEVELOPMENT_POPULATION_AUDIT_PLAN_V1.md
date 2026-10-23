# Development-population audit plan v1

Status: design plan, not an executed full-development audit. This package reads only source code/configuration/documentation. Its verifier does not read a split manifest, benchmark row, reference answer or model response. The existing 69-case scripts remain hash-locked to their diagnostic inputs and must not be unlocked by editing a hash or renaming files.

## Target and access boundary

The baseline records 140 primary development groups and 1,754 static development rows. Treat these as expected historical source counts for inventory reconciliation. Corrected usable counts, per-benchmark counts and paired counts are not yet measured. The 34-group / 35-row sensitivity-only development extension remains separate.

A future audit must consume an explicitly prepared development-only bundle plus a metadata-only export attestation derived from the existing frozen partition. It must not search the benchmark tree for missing cases, regenerate the split or infer membership from correctness. The bundle contains only permitted development records, all their variants, source-file-qualified keys and trusted canonical group IDs. If a group or record cannot be proven to belong to development, reject it.

There is a difference between a trusted partition/export job and analysis access. Building the development-only bundle from files that mix partitions requires a separately reviewed partition/filter implementation; it is not implemented or run here. The analysis auditor must open only the resulting allowlisted development bundle. Do not use a generic full-benchmark loader inside this audit and then describe the run as never having loaded held-out rows.

The export attestation should include split-version/hash, benchmark revision/source-file hashes, membership algorithm and code revision, row/group counts, development key-set digest, bundle digest and an explicit zero held-out-content-exported statement. It must not include held-out case IDs, prompts or references. A digest alone is not evidence of correct partitioning: review the exporter and test it with synthetic partitions before trusting the attestation.

## Planned stages and deliverables

| Stage | Operation | Output and acceptance check |
| --- | --- | --- |
| A — Partition provenance | Review a metadata-only attestation and development bundle | Exact frozen partition/source linkage; reject unexpected group/key, duplicate key or digest mismatch |
| B — Source inventory | Enumerate every permitted development case before repair | Inventory reconciles historical source counts or explains discrepancies; no silently skipped rows |
| C — Identity and pairing | Use existing canonical identity on allowed metadata; group variants | One partition per group; qualified row keys unique; every required clean/perturbed join is counted |
| D — Prompt construction | Apply the reviewed, committed research adapter without reading gold in its builder | Before/after hashes, edits, target-boundary and tool-schema checks; blocked cases retained with reasons |
| E — Reference/objective audit | Apply reviewed rules to prompts/tools/reference calls, not model outcomes | Literal name/key checks, objective excerpts, year/time signals, duplicate occurrences and limitations |
| F — Disposition | Review rule-defined buckets and record unresolved findings | No relabeling or exclusions without a versioned policy; retain chronology and row/group effects |
| G — Scope/feasibility plan | Count calls and estimate bounded development work | Primary/sensitivity/panel denominators, pairing coverage and compute budget; no extrapolation from an unweighted 69-case mean |
| H — Development pilot gate | Only after audit acceptance, prepare limited four-model evidence checks | Request capture and frozen Task 2 validation on corrected prompts; no main/held-out run yet |

These stages are proposed interfaces, not existing runnable commands. Implement a separate versioned full-development auditor; keep the committed eight-response and 69-case tools unchanged for reproduction.

## Inventory contract

Each row should record: case key, source file/hash/row identifier, benchmark, population label, canonical base group, attested development membership, clean-anchor status, perturbation category, original prompt hash, adapter/version/hash, corrected prompt hash, construction outcome and reason, tool-occurrence schema hashes, objective-detection evidence, reference-review signals and disposition provenance.

Gold references live in an audit/scoring sidecar. Builder inputs exclude them; request records must not contain the expected answer. No model correctness, uncertainty, fallback outcome or serving latency enters the repair/objective rules. Verify this with noninterference tests that mutate such fields without altering prompt/audit output. The 69-case rule design followed development inspection and is not a preregistration, even when its later application is outcome-independent.

Aggregate separately by source population, benchmark, source file, perturbation family, construction status, objective status and canonical group. Report row and group counts for every denominator. In particular, distinguish all attempted source rows from repaired candidates and score-eligible responses; the last category cannot be known before inference. Never count an excluded/unresolved row as a successful repair.

## Clean/perturbed joins

Join by the frozen canonical group, never source.original_id alone or a user-text similarity rule. Retain all variants in a group. A clean row is not assumed to exist for sensitivity-only groups. Track missing anchors, missing variants, duplicate joins and reference changes across variants. Use exact declared pairs for paired perturbation comparisons and publish the number of groups/rows that contribute. Do not silently require complete-case eligibility across all uncertainty measures and discard the rest; give measure-specific and common-subset denominators.

Do not create new data splits from a changed row inventory. If repair reveals a grouping problem, record it as a protocol issue rather than moving a group across the existing partition.

## Reference and objective review

Retain the following non-exclusive categories: absent declared reference name/key, required/type metadata unavailable, duplicate-name occurrence ambiguity, date-year grounding question, latest explicit time-range conflict, objective detected/not detected/uncertain, and reference preference within syntactically identical advertised schemas/descriptions.

Regex non-detection is not proof that no objective exists; zero flags is not semantic clearance. Identical advertised schemas/descriptions do not demonstrate identical live behavior. Duplicate-name perturbations are expected and must not be globally deleted. Keep ToolEyes name-only scoring limitations visible regardless of automatic flags.

The 20 selected reward cases in the diagnostic are not the reward population count for the full development bundle. Recompute counts on the full bundle. Report literal reference compliance for all intended reward rows, plus separate objective-detected/not-detected/uncertain strata. Do not infer a minimization instruction from the preferred reference. If the study chooses an explicit-objective new prompt track, version it, define the policy for every relevant row without model-outcome selection, rerun required development generations, and retain v2 results as their own track.

## Disposition policy to review before execution

Recommended default: retain official labels and all source rows in inventory; quarantine only structurally unconstructable rows from inference, with explicit reasons and counts. Reference ambiguity alone does not quarantine a row or change its official label. Primary analytical exclusions or a corrected-reference version require a separate recorded decision and denominator impact. No manually cherry-picked successful repair or easier replacement case is permitted.

Manual reference findings should contain the exact input/reference evidence, source revision, classification, rationale, reviewer decision and whether model outcomes had already been inspected. A semantic ambiguity that cannot be resolved from approved development evidence stays unresolved. Ground-truth disagreements are not automatically model failures.

## Required future tests

- Synthetic partition/export tests prove no held-out content enters the analysis bundle; wrong membership/digests fail before analysis.
- Unknown identities, duplicate keys and cross-partition groups fail closed; variants remain together.
- Repair handles duplicate names, explicit empty schemas and missing/ambiguous source declarations without guessing.
- Target-answer removal respects the exact prediction boundary and preserves historical observations.
- Name/schema/reference diagnostics do not mutate scores or reference objects.
- Objective detectors ignore metadata and assistant-history text but preserve explicit user/system instruction excerpts.
- Source-corrected names, required/type unknowns and occurrence matching remain distinct from execution validity.
- Noninterference tests prevent model outcomes, seeds, uncertainty or fallback success from selecting repairs/exclusions.
- Population accounting reconciles every input row as candidate or unresolved; unknowns cannot silently disappear.

## Readiness outputs

The future audit should produce a metadata-only inventory summary, local per-row evidence ledger, unresolved-decision register, pair-count report, code/config/input hashes and a feasible development pilot proposal. Raw prompts/references remain local artifacts. No output may state held-out readiness merely because the 69-case script passes or because a manifest field has been set to true.

A full-development audit has not been run by this plan. Local checks supplied with this package verify only the plan/config/source baseline and readiness protections. They do not certify a development export, reference semantics, a repaired dataset or any model result.
