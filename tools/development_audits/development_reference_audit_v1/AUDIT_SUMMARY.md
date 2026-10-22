# UQRoute-TC: 69-case corrected development reference audit

Scope: all 69 selected corrected development cases, not the full development or held-out population. This is a deterministic review-signal audit. No model responses, official correctness outcomes or uncertainty scores were used. References were checked against model-visible inputs and tool definitions. No official label was changed and no case was excluded.

## Main finding: reward objectives are inconsistently explicit

| Reward cell family | Selected cases | Explicit objective detected | No explicit objective detected |
| --- | ---: | ---: | ---: |
| Cost: CD, CD_AB, CD_NT | 10 | 2 | 8 |
| Latency: TD, TD_AB, TD_NT | 10 | 2 | 8 |
| Total | 20 | 4 | 16 |

All four detected objectives are in APIBank:

- CD / level1_265: “Please use a cost-effective option.”
- CD_NT / level1_193: “Select the most economical option.”
- TD / level1_166: “Choose the fastest option available.”
- TD_NT / level1_36: “Please use the quickest method.”

No explicit objective was detected in the selected CD_AB/TD_AB cases or the selected RoTBench, ToolAlpaca and BFCL reward cases. The audit inspects system instructions outside JSON tool arrays and actual user turns, excluding assistant text embedded in APIBank dialogue history. Price/latency metadata in tool definitions is not itself an instruction to minimize it.

Interpretation: 16 reward cases need a declared analytical treatment. Their preferred reference tool cannot automatically be called the only user-task-correct tool merely because its displayed cost/latency is lower. The detector is limited to documented literal forms; no hit means not detected, not proof of absence or an assertion that an implicit objective is impossible.

## Reference review signals

| Signal | Case count | Interpretation |
| --- | ---: | --- |
| Latest explicit user time range differs from reference | 1 | Concrete dialogue/reference mismatch requiring review |
| Reference date year is not literal in explicit user turns | 4 | Grounding question; not proof that the year is wrong |
| Reference name has multiple schema occurrences | 19 | Expected ambiguity in same-name perturbations; not automatically bad data |
| Reward cell without detected explicit objective | 16 | Objective/label interpretation needs documentation |

Flags overlap. Thirty-nine cases have one or more signals. This does **not** mean 39 cases are incorrect or should be removed. A no-signal case is not semantically certified. ToolEyes has no signals under these particular rules, but its name-only references still cannot establish argument correctness or task execution.

The audit also confirms that all 69 cases' reference names and argument keys have at least one candidate declaration. This is a structural compatibility check, not type, value, required-input or semantic verification.

## Specific unresolved references

### Alarm dialogue

CD_AB.jsonl:apibank__level1_301 has a latest explicit request of 9:00AM to 10:00AM. The reference's from_time/to_time are 07:00 and 08:00. The range detector reads user turns and reference arguments only; it does not use the smoke output. The official reference remains unchanged and the case remains included.

### Date years

The date-year signal appears in:

- CD.jsonl:apibank__level1_265
- TD.jsonl:apibank__level1_166
- clean.jsonl:apibank__level1_166
- redundant.jsonl:apibank__level1_166

These are four rows involving two source row IDs, not four independent ambiguities. User turns do not state the reference year. External context or source conventions might supply it; this audit does not resolve that historical grounding.

### Duplicate names

Nineteen rows have more than one tool schema with the reference name. Preserve every occurrence. Literal-name matching alone cannot identify which occurrence was intended. Do not merge the schemas or declare every duplicate a broken reference. Use occurrence-level diagnostic results and report unresolved semantic identity.

## Recommended handling before larger experiments

1. Preserve all official labels and original denominators; continue calling the label official reference compliance.
2. Keep ToolEyes name relevance separate, as implemented in analysis-policy v1.
3. Report the 20 reward cases separately, splitting objective-detected from objective-not-detected cases. Do not silently remove the latter or relabel outcomes as semantic task failure.
4. Decide a declared objective policy before new reward experiments. Adding a cost/latency-minimization instruction requires a new prompt version and fresh generations. Do not modify v2 retroactively or tune wording to the observed outputs.
5. Keep the alarm/year cases flagged. Any reference correction requires source-supported justification, a new dataset version and a deterministic population-wide policy, not a score edit for one model.
6. Retain duplicate-name perturbations and their occurrence-level ambiguity. Define their evaluation interpretation before claiming schema-sensitive correctness.
7. Audit the full intended corrected development population using the same reviewed rules before freezing the main study. These 69 coverage-stratified rows cannot substitute for that population. Do not inspect held-out cases while choosing repairs or objectives.

No main experiment, gate threshold selection, confidence interval or GPU run is performed by this audit. The next work is protocol/population preparation, not another model run.

## Reproduction and tests

The package includes reference_audit.py, audit_rules_v1.json, test_reference_audit.py and reference_audit.json with every case's evidence and flags. Python 3.10+; standard library only:

```bash
python -m unittest discover -s . -p 'test_reference_audit.py'
python reference_audit.py --audit /path/to/prompt_audit.json --candidates /path/to/candidates.json --output /path/to/new_reference_audit.json
```

The CLI checks exact content hashes for both approved development inputs, retains all 69 keys and does not scan directories or access a model, network, split or held-out source. The candidate input is the already produced prompt_adapter_v2/candidates.json from UQRoute_TC_Prompt_Repair_v2.zip.

Seventeen unit tests passed. Real-population integration verified input immutability, all 69 case identities and the objective denominators. Adding arbitrary prediction, correctness and uncertainty fields to inputs did not change the result. This proves noninterference from those fields in this implementation, not independence of rule design from prior development knowledge. The rules were developed after earlier development inspection; this is explicitly not a preregistration.

The official scoring files and saved score reports were not modified. The audit does not load model outcome archives. It is a standalone package, not a commit to the GitHub branch.
