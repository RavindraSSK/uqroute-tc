# UQRoute-TC analysis policy 1.0.0

Status: implemented and tested for the approved eight-response development smoke archive. This version establishes reporting and diagnostic rules. It does not freeze or enable the full corrected experiment, inference harness or routing policy.

## Implemented policy

Official score dictionaries are copied unchanged into the output. APIBank, BFCL, RoTBench and ToolAlpaca form the official-reference-compliance stratum. ToolEyes is reported separately as tool-name relevance. A supplementary all-benchmark table retains every original official outcome. Reference ambiguity never excludes a response or changes its score.

The separation was selected after development smoke inspection because benchmark labels measure different properties. This is disclosed in the configuration; it is not a preregistered decision. The resulting 1/7 and 1/1 denominators describe this deliberately selected smoke sample, not population accuracy or independent tasks.

Argument diagnostics preserve duplicate-name tool occurrences, check literal name availability, declared argument keys, explicitly specified required keys and shallow types. Type aliases are explicit; values are never coerced. Missing required metadata remains unknown. A declared-interface incompatibility does not imply JSON Schema invalidity: additionalProperties behavior, nested schemas, enums, patterns and semantic contracts are not evaluated. Full schema validity and real execution success are not measured.

A duplicate-name call is compatible with known shallow checks if any occurrence passes; it is unknown if none passes and at least one occurrence is unknown. All occurrence results and duplicate ambiguity remain visible. The aggregate is not evidence that the intended duplicate occurrence was selected.

Explicit one-call compliance uses parsed calls and a documented literal phrase detector, not a full natural-language contract interpreter. Raw ReAct action-marker counts can expose parser omissions but are not a replacement parser. Fabricated success and latest-dialogue interpretation are manual, post hoc development observations in the review ledger, not automatic semantic judgments.

The reference ledger distinguishes ambiguity flags from scorer/vocabulary limitations and observed model issues. It marks four smoke cases as reference/objective ambiguous. Eight cases have some review note; this does not mean all eight references are ambiguous. Missing review entries yield unknown status. No sensitivity exclusions are implemented.

Uncertainty stays unavailable for all eight smoke responses. Raw log-probabilities do not establish validated alignment. No ranking metric, threshold, calibration, gate or routing result is computed. Missing-score gate behavior remains pending final protocol design rather than silently assigning scores or routing decisions.

## Results and verification

- 24 unit tests pass.
- Real integration run replays every request fingerprint, parser output and saved-method score calculation.
- All official labels remain unchanged: supplementary 2/8, reference-compliance 1/7 and separate ToolEyes relevance 1/1.
- Four ambiguity-flagged cases remain in their original denominators.
- One literal unknown tool call and one explicit one-call violation are reported.
- All eight uncertainty scores remain unavailable; no imputation is performed.
- Source archive and audit fingerprints are unchanged.

The pinned scorer and parser bytes are included and verified by SHA256. Replay uses the saved benchmark-specific scoring method; it does not independently reconstruct the original sample eval_config dispatch. The exact hashes of the configuration, annotation ledger, diagnostics implementation and inputs are written to the result.

## Development input boundary

The CLI accepts only the exact audit and smoke-archive content hashes listed in analysis_config_v1.json. It rejects other input content before dataset parsing or scoring. It reads the explicitly named development inputs and local implementation/configuration files. There is no directory scan, network call, split traversal, model client or held-out access. This implementation does not certify broader datasets or silently generalize its smoke-only eligibility rule.

The current code was run only on the uploaded development evidence. No held-out data was read. To extend the policy to a different approved development dataset, create a reviewed, versioned input adapter/configuration and validation tests; do not reuse this result as a full-population analysis.

## Files

- analysis_config_v1.json: versioned label, diagnostic, evidence and readiness rules.
- reference_flags_v1.json: explicit post hoc development review ledger, with no score changes or exclusions.
- diagnostics.py: standard-library-only CPU diagnostics.
- test_diagnostics.py: unit tests for schema unknowns, type boundaries, duplicate names, label preservation, separated reporting, uncertainty unavailability and input rejection.
- development_diagnostics.json: generated result on the approved smoke evidence.
- replay_review.py, official_runner.py, official_scorer.py: pinned scoring replay support.

## Reproduce

Python 3.10+; standard library only. Run from this directory:

```bash
python -m unittest discover -s . -p 'test_diagnostics.py'
python diagnostics.py --archive /path/to/UQRoute_TC_Research_Prompt_v2_Smoke.zip --audit /path/to/prompt_audit.json --output /path/to/new_diagnostics.json
```

Input evidence and implementation files cannot be used as the output path. No GPU is needed. No diagnostic changes the input ZIP, prompt audit or official scores.

## Remaining before main experiments

The full corrected population, grouped exclusions/pairing, development-wide reference/objective audit, four-model evidence validation, missing-uncertainty gate behavior, fallback acceptance, threshold selection, baselines, confidence intervals and timing/cost configuration remain pending. The configuration lists these items and explicitly keeps main_experiment_ready=false.

This package is standalone and has not been committed to the GitHub branch. It does not modify earlier inference or repair files.
