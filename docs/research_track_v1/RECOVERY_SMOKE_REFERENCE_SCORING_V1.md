# Development smoke: reference compliance after fault feedback

Owner local import at `be2ef44` completed successfully: all 152 hashes verify,
all 30 saved records independently replay exactly, and no new generation occurred.
Nine importer checks finished with one Windows symlink check skipped. The next
step is deterministic CPU reference scoring of these saved outputs, before
expanding GPU collection. The owner subsequently completed the command: reference matches are 4/24
versus 18/24 repeated initial matches, and separate ToolEyes relevance is 3/6
versus 6/6. No mismatch-to-match episodes were reported. See the
[behaviour review](RECOVERY_SMOKE_BEHAVIOUR_REVIEW_V1.md) before larger collection.

```bash
python tools/development_audits/recovery_smoke_scoring_v1/score_smoke.py
```

## Endpoint and development decision

The pinned released `run_transition_pass` scores the second response after
appending fault feedback. Its prediction writer retains
`golden_answers: s["golden_answers"]` and `eval_config: s.get("eval_config")`.
It does not create a fault-specific reference. The new command checks that source
structure and uses the existing hash-bound parser and deterministic official
scorer against the original clean reference/configuration.

The reported endpoint is **benchmark reference compliance after error feedback**.
ToolEyes name relevance remains a separate endpoint. These scores do not establish
that an external tool ran, an API fault was repaired, arguments were universally
correct, or the response was semantically appropriate for the fault. In particular,
auth/schema messages provide neither new credentials nor a replacement schema.
A refusal can be appropriate yet mismatch the original reference. No response
repair, reference rewriting or manual semantic relabeling is performed.

This is a development-only diagnostic disposition recorded after the smoke
outputs/parser counts were inspected. It does not freeze the final RQ3 endpoint,
deployment threshold, objective or held-out analysis. Failure-specific semantic
recovery remains unmeasured. No larger generation batch is authorized by scoring.

## Evidence and reference boundaries

The command verifies the completed owner import using a pinned export-manifest
hash and all 152 original file hashes, execution-source pins, runtime/token counts
and the exact saved independent replay. It revalidates all ledger bindings with
the pinned smoke client/ledger. Unknown or no-injection records cannot enter this
30-episode injected cohort or silently become reference failures.

The existing primary-development reference loader verifies its immutable
attestation, membership, full inventory and source-reference hashes before
reference access. No raw benchmark file or held-out sidecar is read. The original
corrected Qwen 1.5B saved run supplies the five clean source requests and responses.
Selected response/metadata/validation files are checked against their original
file pins, and the clean reference group/benchmark/prompt lineage is retained.

For each episode, the command reconstructs fault feedback from the preserved
initial raw text and official initial parser call, using all six released
templates. Its messages and hash must equal the actual submitted post-fault
request. The initial label-source request is used only to locate and validate the
unchanged clean reference. It never substitutes a static response for the actual
fault-conditioned response. Both original and post-fault text are independently
validated and passed to the unchanged scorer. Original reference-review flags,
format exclusions, parser statuses and token uncertainty remain visible.

Expected local inputs already used by the preceding workflows:

- `recovery_smoke_qwen15b_import_dd91a73f` under the local audit root.
- `corrected_qwen15b_full_development_import_8517fd5d`, the saved original run.
- `full_primary_export_v1` and `full_primary_audit_v1`, the protected development
  reference and membership/audit sidecars.

## Output and interpretation

Fresh ignored output:
`artifacts/local_development_audits/recovery_smoke_reference_scoring_v1/`.

- `records.json`: private per-episode reference scores, original flags and paired
  initial/post-fault diagnostic fields; no execution/semantic-success label.
- `summary.json`: separate reference and ToolEyes panels, each with fault-specific
  counts and paired match/mismatch changes.
- `REPORT.md`: aggregate display printed by the command.
- `provenance.json`: fixed policy and verified input hashes.

The expected cohorts are 24 reference-compliance episodes from four groups and
six ToolEyes relevance episodes from one group. Initial outcomes are reused six
times per group, not 30 independent initial calls or an executed baseline policy.
Paired match changes are text/reference diagnostics, not executed recovery rescues
or evidence of a gate's causal effect. No confidence intervals or best-policy
selection are supplied for this tiny selected smoke. Keep detailed records private
and paste only the printed aggregate report for review.

The command changes no original evidence or labels and refuses occupied output.
It sends no model/external-judge requests and does not alter held-out/readiness
flags. The 16 new tests use production request/context constructors and the real
frozen parser/scorer to check matching/wrong/no-call outputs, empty references,
all six faults, unchanged review flags, context/source identity, unknown/no-fault
handling, separate ToolEyes relevance and paired aggregation. Ruff passes.
Actual smoke input, runtime and ledger revalidation was exercised locally up to
the protected reference-loader boundary; the owner-only reference sidecars and
initial raw responses are unavailable in this implementation checkout, so actual
post-fault scores have not been computed here.

Review these diagnostics before broader recovery collection. Preserve the 30
completed requests; the remaining 720 Qwen 1.5B small-stage slots are not yet a
prepared or authorized execution batch. Other model roles, fallback, final scoring
dispositions, threshold/objective selection, baselines, full costs and held-out
evaluation remain pending.
