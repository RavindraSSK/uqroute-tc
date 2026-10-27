# Corrected repeated-sampling development preparation v1

Baseline a2fb64d. Preparation proposal only: no inference or held-out access.
This does not change the existing Task 2 freeze or its historical subset digest.

The original design selects three disjoint groups per benchmark, each contributing
one clean and one perturbed case. Perturbations are query_paraphrase, redundant
and CD_AB; ToolEyes uses realistic_typos instead of CD_AB. The same seed 1729,
SHA256 ranking string and benchmark/source ordering are retained. The new rule
ranks only constructed primary-development full-run candidates with constructed
clean anchors. This eligibility change is explicit: the result is a new subset,
not a claim to reproduce the original 30-case digest. Outcomes, references,
uncertainty, model errors and flags are not selection inputs. All 26 construction
blocks remain in the original inventory; no blocked outcome is imputed.

The three hash-bound full-development plans are validated with the existing
workflow.load_plan. Case order, lineage, prompts and request settings must agree
across models apart from model ID. The same selected keys are expanded into
300 independent one-choice requests/model, 900 total. Each case has sample
indices 0-9, seeds 1729-1738, temperature 0.7, top_p 1.0, cap 1024, logprobs and
five alternatives. Prompt messages and pinned model settings are retained.
No original repeated responses or single-sample responses are transferred into
the new repeated-sample analysis. Comparisons may later join the existing exact
single-sample prompts, but their different sampling settings remain explicit.

Slots are keyed by case identity and sample index within a model-specific run.
The preparation includes no dispatcher. The single-sample workflow.run cannot
execute these manifests. A dedicated repeated-slot runner, model-specific context
preflight, runtime checks and review are required before generation. Unknown
outcomes must never be automatically resubmitted; any retry-policy difference
from the historical Task 2 diagnostic must be documented before execution.
Frozen probability-free clustering/status semantics remain the authority.

Outputs are fresh locally ignored folders with per-model manifest/requests,
three transfer ZIPs, summary and provenance. They contain prompts, which can
include benchmark conversation literals; they are not promised credential-free.
No reference sidecar or correctness score is packaged. Publication uses the
existing no-replace helper, and original prepared inputs are hashed again.

The selected 15 groups and fixed perturbation types provide a small exploratory
paired diagnostic, not full-population uncertainty effectiveness. Coverage of
all perturbation types, sensitivity-only development, final calibration/routing
selection, recovery, costs and held-out evaluation remain separate requirements.
Review the selected identities and resource budget before a dedicated execution
package. This proposal does not authorize dispatch or establish Task 3 completion.
