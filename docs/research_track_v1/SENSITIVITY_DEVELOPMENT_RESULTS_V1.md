# Sensitivity-only development results

35 BFCL same-name perturbations from 34 development groups per model.
This extension has no clean anchors. Reference matching is not execution success.
All 105 responses completed. Every model replay matched the exported evidence.

| Model | Reference matches | Compliance | Whole eligible | Meaningful eligible | Flagged rows retained | Batch seconds |
|---|---:|---:|---:|---:|---:|---:|
| qwen15b | 10/35 | 28.6% | 35 | 23 | 35 | 24.36 |
| llama3b | 7/35 | 20.0% | 35 | 25 | 35 | 50.16 |
| qwen7b | 10/35 | 28.6% | 35 | 25 | 35 | 109.70 |

Reference-review flags are retained without exclusions or relabeling.
The flags are structural review signals, not adjudicated reference errors.
Inspect model scores.json and reference_flag_counts in summary.json.

## Matched cases across all three models

Each model uses its own reference-error labels; shared cases do not imply shared outcomes.
AP is noninterpolated average precision; compare it with error prevalence.

| Measure | Cases | Model | Error AUROC | AP | Error prevalence |
|---|---:|---|---:|---:|---:|
| max_token_surprisal | 35 | qwen15b | 0.712 | 0.864 | 0.714 |
| max_token_surprisal | 35 | llama3b | 0.827 | 0.922 | 0.800 |
| max_token_surprisal | 35 | qwen7b | 0.792 | 0.877 | 0.714 |
| mean_token_nll | 35 | qwen15b | 0.648 | 0.812 | 0.714 |
| mean_token_nll | 35 | llama3b | 0.811 | 0.900 | 0.800 |
| mean_token_nll | 35 | qwen7b | 0.704 | 0.772 | 0.714 |
| sequence_nll | 35 | qwen15b | 0.824 | 0.919 | 0.714 |
| sequence_nll | 35 | llama3b | 0.908 | 0.972 | 0.800 |
| sequence_nll | 35 | qwen7b | 0.780 | 0.853 | 0.714 |
| meaningful_mean_token_nll | 23 | qwen15b | 0.600 | 0.635 | 0.565 |
| meaningful_mean_token_nll | 23 | llama3b | 0.839 | 0.870 | 0.696 |
| meaningful_mean_token_nll | 23 | qwen7b | 0.677 | 0.681 | 0.565 |

Full measure comparisons belong on the all-model/all-measure intersection:
23 cases. See summary.json for those metrics.

Keep this extension separate from primary-development estimates. It contains
additional BFCL groups, not a new five-benchmark experiment. No clean/perturbed
paired change can be estimated for these cases. The observed success rates
condition on this small selected source population and do not establish model superiority.
No calibration refit, routing threshold, final freeze or held-out evaluation is performed.
Generation timing excludes setup/model loading and is not online cascade latency.
