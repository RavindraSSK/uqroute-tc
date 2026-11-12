# Remaining recovery development inventory

The matched smoke is closed: both GPU runs, imports, paired scoring and behaviour
review are complete. The owner reports five of the six reference gains as
small-no-call to fallback-call changes and one as changed tool names. One other
no-call-to-call change still mismatches. All ToolEyes gains/losses involve changed
names. Six initial control-name episodes remain. Scores and all thirty pairs are
unchanged; these are reference/structural findings, not executed recovery.

The next step returns to the original three-model development plan. It packages
the remaining pair-collection inventory instead of another smoke audit. No new
cases, fault templates, label-based exclusions or thresholds are introduced.

```bash
python tools/development_audits/recovery_remaining_development_v1/prepare.py
```

## Fixed remaining workload

| Initial small model | Original eligible episodes | Known small + fallback slots reused | Pending small | Pending fallback | Maximum potential new calls |
|---|---:|---:|---:|---:|---:|
| Qwen 1.5B | 750 | 30 + 30 | 720 | 720 | 1,440 |
| Llama 3B | 828 | 0 | 828 | 828 | 1,656 |
| Qwen 7B | 834 | 0 | 834 | 834 | 1,668 |
| Total | 2,412 | 60 | 2,382 | 2,382 | 4,764 |

These are potential collection slots, **not requests dispatched or an approved
GPU allocation**. The original 108 terminal no-injection plans remain separate
(90/12/6), with no generated outcome imputed. All eligible fault histories remain,
including control-action and no-call/matching smoke cases. All-pair evidence
collection is distinct from executing an uncertainty-gated recovery policy.

## Preparation checks and output

The command verifies the completed paired review's summary/records/provenance
and unchanged prior scores, then rechecks the two existing smoke imports and
known small/fallback responses. The 60 completed slots must equal the original
full request rows exactly before being reused. They are removed only from the
pending dispatch inventory, not from the study cohort.

All three original recovery transfer archives and manifests are checked against
their original owner pins. The existing production preflight validator verifies
the 140 clean-source groups and six released fault templates per group. Full
saved pinned-tokenizer reports must cover every original role/request/context
with its frozen model/revision and 1,024-token allowance inside 8,192. No tokenizer
download or inference occurs. Verified input fingerprints are checked again
before publication.

Pending episodes are sorted by benchmark, canonical group and fault, independent
of labels/uncertainty. Each role is partitioned into batches of at most thirty
requests. The six fault variants of each original eligible group stay together.
Qwen has 24 batches per role; Llama 28 and Qwen 7B 28 (last batches 18 and 24 requests).
This yields 160 batch inventories across both roles. Fallback slots carry an
explicit scheduling requirement for an observed known saved small response.
Unknown/HTTP-failure slots must stop future execution without automatic retries;
a parsed call or reference match is not required to retain a known small response.

Fresh ignored output:
`artifacts/local_development_audits/recovery_remaining_development_preparation_v1/`.

- One deterministic transfer ZIP per initial small model, containing the original
  episode inventory, pending role requests, batch inventory and frozen manifest.
- `summary.json`: known/pending/no-injection counts and actual transfer/manifest
  fingerprints for each model.
- `provenance.json`: fixed policy and verified input hashes.

The ZIPs contain no reference answers or correctness labels. Detailed prompts,
outputs and identifiers remain private. Existing outputs are never overwritten.
The preparation supplies **no runnable executor**. Old static/smoke dispatchers
are incompatible with these transfers; readiness and dispatch flags stay false.

Fourteen CPU tests use the production episode builder and original preflight
validator to check complete coverage, known-response reuse, no resubmission,
parent requirements, context/token boundaries, unchanged label-independent
selection, deterministic ordering and completed-review score bindings. Ruff
passes. The original three full owner transfers, full tokenizer reports and
completed review files are unavailable in this implementation checkout, so
actual owner preparation/fingerprints remain pending.

After preparation, review the actual inventories and current resource/quota
feasibility, then pin a durable bounded executor starting with the already-smoked
Qwen 1.5B role. No full-run completion, throughput extrapolation, monetary saving,
semantic-success endpoint, threshold freeze or held-out authorization follows
from this preparation. Resolve scoring/interpretation and full policy objectives
before confirmatory claims; preserve all original labels and scope boundaries.
