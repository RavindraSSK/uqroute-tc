# Conditional paired group-bootstrap routing intervals v1

The owner completed five-fold group-separated development routing. Point estimates
show reliability/usability/time tradeoffs, but do not quantify uncertainty or
establish efficiency gains. This CPU subtask adds paired percentile intervals
conditional on the existing OOF thresholds and decisions. Actual execution and
interval review remain pending; synthetic checks are not model results.

Run once from the updated owner repository root:

```bash
python tools/development_audits/grouped_routing_intervals_v1/run_intervals.py
```

No Colab session, model request, replacement response or upload is required.
The command preserves all existing outputs and publishes only a fresh ignored
directory. It stops rather than overwriting an existing interval result.

## Reproduction and evidence binding

The new policy pins the unchanged grouped runner, grouped threshold algorithm,
prior policy, paired-input loader and all underlying routing/scoring policies.
All four source runs are re-scored and fully replayed with their frozen adapters.
Original normalized pairs must exactly match the earlier paired-input file.
Fold assignments and every complete grouped result, including infeasibility,
OOF predictions, baseline accounting and random aggregates, are recomputed and
compared with the saved grouped artifacts before bootstrap contrasts are emitted.

The analysis stays within the 1,728 constructed primary-development cases per
small model. Reference compliance and ToolEyes relevance remain distinct. The
26 construction blocks receive no model outcome. Existing reference flags,
non-complete outputs, unavailable uncertainty and official labels are unchanged.
No raw benchmark, split or held-out records are opened. Original source/input
fingerprints are checked again before publication.

## Resampling and contrasts

For each endpoint, canonical groups are sampled with replacement within benchmark,
retaining each sampled group's complete set of case contributions. Each benchmark
retains its original number of sampled groups per draw. Metrics are case-weighted,
not equal-group-weighted. One shared sequence of 2,000 group-multiplicity draws
(seed 1729) is reused across all models, caps and baselines in that endpoint.
The full 0%, 10%, 25%, 50% and 100% training-cap results are retained.

Each fixed OOF gate is contrasted with small-only, fallback-only and always-cascade
on the same full endpoint cohort. Differences are gate minus baseline:

- Reference/relevance match fraction and unusable-final-output fraction.
- Model attempt slots per reference/relevance match.
- Saved request seconds per match.
- Prompt and completion tokens per match, separately.

Every selected attempt contributes usage, including unsuccessful attempts.
The cascade baseline charges both model attempts and returns fallback. A terminal
unusable fallback is not replaced using a reference-label oracle. Usability
requires complete evidence and a canonical parsed call; it is not execution success.

Intervals are the 2.5th/97.5th percentiles with linear interpolation. They require
at least 10 canonical groups and at least 90% valid replicates. Point estimates
remain separate from interval availability. Incomplete OOF coverage receives no
full-cohort interval or zero-imputed prediction. Unknown reference labels withhold
affected metrics; missing usage withholds the corresponding usage metric. Zero
match denominators make efficiency ratios unavailable. Draw eligibility and
undefined-replicate counts are recorded explicitly.

## What these intervals do not establish

The original OOF fold assignment, thresholds and predictions stay fixed inside
bootstrap draws. There is no fold reallocation, threshold refitting, model/cap
selection or repeated nested validation during resampling. Thus intervals quantify
conditional variation in the saved paired case/group contributions, not every
source of uncertainty in learning thresholds or running future deployments.

The method was specified after prior inspection of full-development reports.
Group resampling does not undo that exposure. No multiplicity correction,
statistical-superiority claim, best-cap selection, final deployment threshold or
independent held-out confirmation is supplied. Random-control means from the
prior analysis are not being turned into confidence intervals.

Saved request seconds are separate-run sequential-time proxies, not measured
online cascade latency, billed GPU time or monetary cost. Token totals across
models are not priced savings. Setup, idle time, recovery and other policy overhead remain outside these
saved request-time proxies. ToolEyes name relevance
is not argument correctness, and reference compliance is not executed task success.

## Output and verification

Fresh directory: `artifacts/local_development_audits/grouped_routing_intervals_v1/`.

- `REPORT.md`: both endpoint panels at 10%, 25% and 50% training caps; match differences against both single-model baselines and timing-proxy differences against fallback.
- `intervals.json`: all five caps, all three baselines, all six contrast metrics, counts and unavailable reasons.
- `provenance.json`: policy, source/input hashes, Python version, group ordering, sampler seed and stratum counts.
- `revalidation/`: reproduced official scoring and full generation replays.

The command runs 26 new synthetic checks, 27 grouped-validation checks and
20 routing-kernel checks before model evidence. Unit checks cover group/stratum
multiplicities, case versus group weighting, paired contrasts, missing data,
zero denominators, low group counts, invalid coverage, reproducibility and source
pins. Ruff passes. Complete owner model sidecars are unavailable in the working
implementation checkout; actual interval results remain pending owner execution.

After reviewing these conditional intervals, resolve the final development
objective and protocol choices. Full policy costs, live escalation, post-fault
recovery, final shared freeze and separately authorized held-out evaluation remain
outstanding. This subtask changes no readiness flags.
