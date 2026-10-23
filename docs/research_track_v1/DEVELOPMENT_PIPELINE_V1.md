# Development-only export and full-population audit v1

Implementation baseline: 05a95bfb0d18755a834819862da46c014b4ccae2. Status: implemented and tested with synthetic data; real primary-development export/audit pending local execution. No model inference, split regeneration, official relabeling, threshold selection or main-experiment readiness is enabled.

## Access boundary

The trusted exporter must read the pinned mixed-partition JSONL bytes and top-level identity/category metadata to select development assignments from the frozen split. It therefore does access the mixed source during partitioning. Do not describe the exporter as never reading held-out source bytes. It verifies Git source blobs and requires the release's nested conversation/tool/reference fields to remain JSON-encoded strings. It decodes those payloads only after a row is proven to belong to the selected development population. Non-selected payloads are not decoded, analyzed, printed or exported. Unknown/duplicate/conflicting identities abort without printing their identifiers or contents.

The separate auditor has no raw-benchmark or split argument. It accepts only an exported bundle and an explicitly supplied attestation hash. It opens development samples, development references, development membership and the attestation; it has no network, Git or inference operations. It cannot search for missing rows in the raw benchmark. This separation is the protection against accidental held-out analysis.

Hashes verify internal consistency, not a cryptographic signature or semantic proof of correct partitioning. Trust depends on reviewing the exporter, verifying its frozen source/split provenance and its tests. A maliciously fabricated bundle with recomputed hashes cannot be authenticated by hashing alone.

## Immutable provenance

The exporter requires the project baseline to be an ancestor of local HEAD. It reads Task 1 settings and the existing split from that baseline's Git objects and verifies the frozen split SHA256. It does not regenerate, write, reassign or infer split membership. It requires benchmark HEAD d5d03180de41eb30a6c796d04a9bfbd9dad85c1d, all 17 expected static source files, clean source status and exact LF file bytes matching pinned Git blobs.

Canonical identity is the unchanged frozen identity logic, copied as identity_v1.py. Source.original_id is not substituted. Primary and sensitivity-only exports are separate. Project HEAD is recorded as provenance, while the actual working implementation files are separately fingerprinted; a HEAD value alone is not a claim that these new files were already committed. Python source hashes normalize CRLF to LF for cross-platform consistency. Raw data/split/payload hashes remain exact byte hashes.

## Bundle contract

The exporter writes a new directory containing exactly:

- samples.jsonl: selected development input records with canonical group and source-line provenance. It contains original conversations/tools but no golden_answers or model predictions at the sample top level. A source conversation may contain the target assistant response that the research adapter must remove; this is not a prevalidated model request.
- references.jsonl: development reference calls and source eval_config, joined by qualified case key. Existing source references are unchanged.
- membership.json: selected development groups only, without held-out identifiers.
- attestation.json: split/source/code hashes, selected counts, development key-set digest, payload hashes and explicit partitioning access limits. No held-out identifiers, prompts or references are included.

Outputs must be new directories. Code/source paths and existing outputs cannot be overwritten. The atomic staging path is temporary and incomplete output is not treated as a valid bundle.

## Auditor behavior

The auditor verifies attestation/payload/implementation fingerprints, unique keys, exact development group membership, canonical identity, reference/input joins and expected row/group totals. Primary groups require exactly one clean source anchor. Sensitivity-only groups cannot contain a clean anchor. No arbitrary model-outcome fields are accepted in audit input records.

Each development row remains in inventory. The pinned message builder receives only input fields. The v2 research repair builder receives benchmark/messages/tools, never the reference sidecar. It preserves the released structured vocabulary, restores unambiguous APIBank parameter maps and handles the supported RoTBench target boundary. Full-population layouts may remain blocked; a 69-case success does not guarantee broader repair. Blocked rows are retained with reasons and omitted only from candidate-request output. This construction quarantine is not an exclusion from the source inventory or a new scoring label.

Post-construction reference checks use the previously reviewed per-case audit rules and separate shallow schema diagnostics. They record objective evidence, name/key membership, required/type unknowns, duplicate occurrences, year/time signals and preference metadata. They never correct gold or treat regex non-detection as semantic certainty. ToolEyes argument validation is explicitly not applicable because its reference is name-only, rather than treating its empty reference arguments as a failed executable call. Reference-audit errors are retained separately from construction errors. Candidate status does not mean a reference has been validated or that inference is approved.

The report includes:

- inventory.json: every exported development row, hashes, edits, construction state and review diagnostics.
- candidates.json: successfully constructed candidate requests, without reference labels.
- clean_perturbed_pairs.json: canonical-group joins, including unconstructed pair members.
- unresolved.json: rows with construction/audit errors or review signals. Intentional duplicates are signals, not automatic errors.
- summary.json: row/group totals, benchmark/file summaries, audit-status denominators, reward-objective counts, clean pairing and a four-model call-count scenario. It contains aggregate metadata, not raw prompts/reference values.

No score eligibility is assigned before inference. The four-model call-count scenario assumes one call per constructed candidate and the frozen completion cap; it is not a runtime estimate, quota validation or main-experiment approval. Reward counts explicitly identify rows whose objective detector was not assessed because construction/auditing failed.

## Expected counts and readiness

The primary exporter must reconcile 1,754 rows and 140 groups with the frozen manifest. These are source-export counts; the number of repaired candidates is measured only by the later audit. The separate sensitivity-only development export should reconcile 35 rows and 34 groups. Neither component is silently pooled with the other.

The supplied tests used synthetic development/test partitions and the actual pinned message builder. They did not read the real split manifest or benchmark data. Sixty-one tests pass, including export/audit integration, held-out marker isolation, invalid nested test payload skipping, source identity/count failures, prompt/reference separation, repair/reference noninterference, duplicate schemas, evidence hash checks, output protection and absence of Git/network calls in the auditor.

Old eight-response and 69-case CLIs/configurations remain unchanged. Their per-case repair/objective functions are copied as a versioned dependency here rather than loosening their input hashes. The inherited original module CLIs are not the full-population entry points; use export_development.py and audit_development.py.

## Remaining boundary

This is a CPU preparation/audit milestone. Main-experiment decisions in main_experiment_plan_v1.json remain pending until the owner runs and reviews the full development outputs, dispositions, evidence feasibility and analysis choices. No held-out case is to be supplied to the auditor or used to resolve repairs/objectives. Clean-result exposure disclosed in the existing protocol remains unchanged.

## Subsequent local execution evidence

The owner's original primary-development run is recorded in
[development audit findings](DEVELOPMENT_AUDIT_FINDINGS_V1.md): 1,754 retained
rows, 1,728 candidates, and 26 construction blocks. This supersedes the
implementation-time pending-execution status above. The subsequent diagnostic
revision separates missing declarations from conflicting schemas without
changing candidate eligibility. Original run outputs and their implementation
fingerprints are retained; main readiness remains blocked.
