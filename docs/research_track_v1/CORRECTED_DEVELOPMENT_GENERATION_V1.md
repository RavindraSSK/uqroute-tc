# Corrected development generation and evidence replay v1

Baseline: `85de7822d768d71548a1fbb7ceb45e65a2a5792e`.
Implementation status: CPU-tested; owner verification and real model feasibility
remain pending. Main-experiment readiness and held-out access remain disabled.

## Boundary and corrected prompt authority

This workflow consumes the preserved original primary-development audit's
summary.json, inventory.json and candidates.json, plus the reconciled
population-plan denominators.json. The original summary/inventory hashes are
pinned from the owner's reviewed report. Candidate and denominator files need
explicit expected hashes. The inventory contains development reference
diagnostics; they are used only for the existing population reconciliation.
Reference sidecars, raw benchmark files, split records, and held-out examples
are not inputs to this workflow. No reference/objective flags select requests.

The original audit's 1,754 rows / 140 groups are reconciled with 1,728 candidates
and 26 retained blocks. Each candidate must match the inventory's qualified key,
canonical group, benchmark, corrected message hash and ordered schema hashes.
Only a system turn followed by a user turn is admitted. No repairs are rerun.
Original audit output and its old implementation fingerprints remain unchanged.

Requests use the corrected research-track prompts. These are different from
the unmodified released prompt builder in Task 1; the manifest's inherited
Task 1 prompt-builder string is source history, not a description of the
corrected prompt authority. Earlier outputs are not relabeled as corrected
outputs or imported as completed slots. Official labels remain unchanged.

Hashes establish byte consistency with reviewed local inputs, not authenticated
partition membership. Trust continues to depend on the reviewed exporter/auditor.
Model response files contain no source gold labels, though a generated model
may itself emit arbitrary content. They remain private local evidence.

## CPU preparation and selections

Preparation checks source fingerprints and baseline ancestry, then creates a
fresh immutable manifest.json and requests.json directory. It never contacts
a server. The manifest binds the candidate/denominator/audit inputs, corrected
prompts and schemas, request bodies, model/tokenizer revisions, server/generation
settings, code fingerprints, selection and project revision.

All selection uses only development identities, benchmark and source-file
metadata; no correctness, reference flags or uncertainty values are used:

- feasibility-five: default, one clean candidate per benchmark, SHA256-ranked
  with selection seed 1729. This checks formats/serving, not population accuracy.
- coverage: one candidate per nonempty benchmark/source-file stratum with the
  same identity-only ranking. Its count is measured, not hard-coded as 69.
- full-development: all 1,728 candidates, in qualified-key order. The 26 blocks
  remain in source coverage and are not silently turned into model failures.

The same selected identities are used for every model role. Preparation does
not authorize broader inference or certify quota/context capacity. Candidate
prompt length is not a tokenizer-based context-length check; server context
rejections remain explicit failed attempts and do not justify prompt truncation.
The sensitivity-only population remains outside this primary-only workflow.

## Frozen methods and generation settings

Ten baseline source files are fingerprinted with CRLF normalized to LF,
including Task 1/2 configurations, maintained Task 2 implementation files,
the released parser copy and population-policy source. Method code is unchanged:

- The exact pilot.token_evidence definition is extracted from its checked AST.
- Checked single-sample and alignment modules receive that same function;
  their project imports are replaced by the corresponding checked definitions.
- Canonical parsing uses the maintained checked module and pinned released parser.
- Optional OpenAI/tqdm imports are omitted from the parser module for CPU use;
  its main function, data loaders and dispatch functions are never invoked.

No change is made to source files or frozen configuration hashes. The effective
maintenance fingerprints are pinned directly rather than pretending the older
pre-maintenance fingerprints match current source bytes.

Requests remain prompt-based, sequential and single-sample: temperature 0.001,
1,024 completion cap, chosen-token logprobs and top_logprobs=5. There is no request
seed, native tools argument, hidden retry, prompt rewrite, fallback or recovery.
Repeated-sampling settings and their existing subset are unchanged.

## Explicit future development dispatch

Dispatch requires --execute-development and a separate prepared-manifest hash.
It supports only unauthenticated local HTTP /v1 endpoints; proxies and redirects
are disabled. GET /models checks the served model identifier before POST calls.
No OpenAI SDK or automatic HTTP retry is used. Preparation/replay never calls HTTP.
A supported model server and frozen vLLM settings must already be running;
this package does not install dependencies, download weights or start a GPU.

A runtime JSON must record exactly the pinned model/tokenizer revision, dtype,
quantization, vLLM/server settings, observed effective temperature, GPU name and
memory, platform/quota note, and hashes of launch command and server-log snapshot.
Revision/settings entries are operator attestations: /models checks the model
ID, not the loaded weight bytes, dtype or launch configuration. A passing
attestation check must not be described as independent runtime verification.
Requested temperature and observed effective temperature remain separate;
previous 0.001-to-0.01 clamps do not justify rewriting the frozen request value.

A development run does not flip main readiness. Before broader model work,
review actual five-case serving/evidence results, context capacity and quota.
No inferential conclusion follows from this feasibility selection.

## Write-once attempts and resume

Every case gets one write-once intent.json before dispatch. Raw HTTP response
bytes are persisted before validation. HTTP metadata includes response SHA256,
status and measured request elapsed time. Validation is a separate write-once
file. Transport failures record an exception type and unknown-outcome status;
no credentials or exception URL strings are copied into error summaries.

Any existing durable intent occupies its slot permanently, including request
errors, truncations, invalid evidence and interrupted/unknown outcomes. Resume
skips it rather than risking duplicate generation or hidden cost. It may only
send requests for slots with no prior intent. Deliberate retries require a
separately reviewed run/attempt policy, not deletion of an occupied slot.
A run manifest must exactly match the prepared manifest, runtime attestation,
endpoint and code fingerprints. A single-writer lock prevents concurrent runs.
After a hard process death a stale lock stops dispatch; inspect process and
artifact state before any manual lock recovery. Never erase attempt evidence.

Session start and finish records are separate immutable files. Finished-session
wall time includes skip/check overhead; resume-only time is not fresh model
throughput. Interrupted sessions remain explicitly unfinished.

## Evidence and parser states, separate from correctness

The versioned corrected runner marks a response complete only for one text
choice, terminal stop, nonempty visible text and valid frozen token evidence.
Truncation, invalid evidence, empty output, unexpected finish reason, malformed
response, HTTP failure, transport error and interruption remain explicit.
This conservative generation-status contract does not retrospectively alter
old records or define a Task 4 deployment acceptance policy.

Whole-output scores require the frozen complete-record recheck. Meaningful-token
scores additionally require supported source layout and parser agreement;
ToolAlpaca remains excluded. Parser success is not correctness; complete
unparsed outputs may retain whole-output scores. No unavailable score is
imputed as zero. Raw responses, parser status, canonical key, finish status,
byte evidence and score availability remain distinct.

The parsed calls artifact is a JSON view. Python tuple/list distinctions can
be lost in that view; the canonical key retains them. Future official scoring
must reparse original raw output, not substitute the JSON view as scorer input.
Official correctness is null/not performed in this workflow. In particular,
truncated and invalid-evidence responses must not later disappear from official
scoring merely because their uncertainty is unavailable.

## CPU replay and accounting

Replay verifies the prepared/run bindings, request/response fingerprints and
saved validation against recomputation. It writes a new summary.json and
records.json directory and never updates original attempts. A response saved
before validation can be validated into the new replay output without filling
or changing its old slot. Intent-only and unattempted cases remain distinct.
A malformed raw response is retained and reported as a validation error.

All attempted slots count toward attempt reporting. Known prompt/completion/
total usage is summed; missing usage among attempts is explicit. Unattempted
slots are usage-not-applicable, not unknown billed attempts. Unknown outcomes
may have consumed tokens and cannot be treated as zero cost. Request elapsed,
finished-session wall, unfinished sessions and resumed slot visits are reported
separately. Neither elapsed measure is GPU kernel time or total allocated GPU
cost; setup, downloads, warm-up and idle allocation need separate observation.

## Completion limits

CPU tests use synthetic prompts/responses and fake HTTP. A full-count synthetic
preparation fixture mocks original input hashes and Git ancestry; it is not
an independent rerun of the real development audit. The owner must verify the
real local files and source checks. No model requests were made to validate
the package itself.

Task 3 still needs corrected generation/evidence feasibility, measured capacity,
broader development outputs, released-reference scoring, uncertainty metrics,
calibration/risk–coverage, group-aware intervals, failure catalogue and the
reviewed final static evaluation freeze. Task 4 routing/recovery is separate.
Held-out evaluation stays disabled until a distinct reviewed final-freeze
artifact and authorized evaluation workflow exist.

For a later GPU session, transfer only the approved prepared request folder
and use a checkout containing the verified code. The original audit inventory,
reference diagnostics and denominator inputs are needed for local preparation,
not for dispatch or replay. Never use the old mixed-source throughput entry
point as a shortcut to generate these corrected requests.
