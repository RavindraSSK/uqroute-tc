# Corrected development feasibility scoring v1

This adapter is based on commit `9ee839341dc93fc53b2a96ea1a613b0f04c2a0b6`.
It scores only the reviewed Qwen2.5-1.5B five-clean-case evidence archive,
identified by ZIP SHA256
`b0c985069e6c68c03eaa238bdcdf7d012ca5426a8ed19976a533e06a0d069191`.
The versioned policy pins all 36 extracted evidence files, the prepared plan,
reviewed development-export attestation, full-development inventory, generation
implementation and official scorer. There is no CLI override for these pins.
A different run or population requires a reviewed version amendment.

## Three distinct interpretations

- **Official reference compliance:** APIBank, BFCL v3, RoTBench and ToolAlpaca
  retain the pinned scorer's original per-case result, including partial scores
  and method-specific leniency. Four rows form this panel.
- **ToolEyes relevance:** the fifth row is reported separately using the pinned
  deterministic name-only relevance scorer. It does not validate arguments or
  establish successful execution. No combined five-row headline accuracy is
  produced.
- **Cost/latency preference:** unassessed for this clean feasibility selection.
  Existing explicit-objective detector results are carried forward as bounded
  diagnostics. They are not preference success, measured runtime cost or
  evidence that an undetected objective is absent.

The scorer and benchmark dispatch are reused, without modifying reference
values, scorer definitions, parser definitions or existing analysis policies.
Unexpected benchmark/method combinations stop validation instead of silently
using a different metric. The adapter never replaces an incorrect official
result because a reference-review flag is present.

## Input boundary and provenance

The only data inputs are the existing extracted five-response evidence,
`full_primary_export_v1/{attestation.json,membership.json,references.jsonl}`,
and `full_primary_audit_v1/inventory.json`. All paths must reside beneath
`artifacts/local_development_audits`. The adapter never opens development
`samples.jsonl`, raw benchmark files or the frozen split. It never runs
inference, HTTP requests, an external judge or held-out evaluation.

Before opening references, it verifies the approved development attestation
hash and partition boundary. Membership and reference bytes must match its
payload hashes. Inventory bytes must match the previously reviewed hash.
Every reference must match the inventory's reference hash and every inventory
row must belong to the approved primary-development membership. Selected rows
must be constructed clean candidates with matching prompt and group lineage.
This trusts the reviewed exporter; hashes establish consistency, not an
independent or authenticated partition proof. The development-only reference
sidecar is read in full, but only the selected five rows are scored.

All archived evidence bytes are checked before scoring. The frozen workflow
revalidates the prepared plan and each raw response against saved validation.
The original raw response text is then reparsed with the pinned benchmark
parser. JSON replay call views are not scoring inputs: serialization can turn
Python tuples into lists and change scorer behavior.

## Flags and output

`scores.json` stores original evaluation configuration, the unchanged official
score dictionary, panel, frozen uncertainty measures and existing reference
review flags/objective diagnostics. Flagged rows remain in their panel.
No signal means no bounded signal detected, not semantic clearance. The
ToolAlpaca meaningful-token exclusion remains in effect and does not suppress
its whole-output evidence or official score.

`summary.json` reports separate panels, per-benchmark values and flag counts.
`provenance.json` records the baseline/current commit, adapter/policy/scorer
fingerprints and every evidence/reference/inventory file read. Inputs are
rehashed before publishing. All three files are written to a fresh directory;
existing output directories and input/output overlap are rejected. No prior
replay, reference, score or audit file is rewritten. Readiness stays false.

## CPU verification

From the repository root:

```bash
python -m unittest discover \
  -s tools/development_audits/corrected_scoring_v1 -p 'test_*.py'

python -m unittest discover \
  -s tools/development_audits/corrected_generation_v1 -p 'test_*.py'

python tools/development_audits/corrected_scoring_v1/score_corrected.py \
  --repo-root . \
  --evidence-dir artifacts/local_development_audits/corrected_qwen15b_import_03ab50c3 \
  --bundle artifacts/local_development_audits/full_primary_export_v1 \
  --audit-dir artifacts/local_development_audits/full_primary_audit_v1 \
  --output artifacts/local_development_audits/corrected_qwen15b_official_scoring_v1
```

Expected test counts are 31 and 34; the symlink test may be skipped where the
platform does not permit symlink creation. Tests use synthetic references and
responses with real hash-checked parser/scorer/uncertainty methods. Git ancestry
and dependency binding are isolated in integration fixtures; the production
CLI performs those checks. No benchmark dataset is required by tests.

The real scoring run requires the unchanged local development export and audit.
Expected panel sizes are four reference-compliance rows and one relevance row.
Actual correct counts are measured locally, not prescribed by this package.
The three scoring files must be inspected before recording results. Passing
synthetic tests does not certify real reference results.

This five-case run does not complete Task 3, estimate population accuracy,
validate uncertainty discrimination or demonstrate routing benefit. Larger
experiments and held-out evaluation remain behind their unresolved protocol
choices and final freeze.
