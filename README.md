# UQRoute-TC

**Uncertainty-Gated Routing and Recovery for Reliable Tool Calling**

UQRoute-TC studies whether a language model can recognize when its proposed tool call may be unreliable. Tool-calling models must choose the correct tool and produce valid arguments, but they can fail when instructions, tool descriptions, argument schemas, observations, or runtime responses change.

The system uses a smaller model for the first attempt. It accepts the proposed call when uncertainty is low and sends the original request to a stronger fallback model when uncertainty is high. Runtime failures, such as timeouts or malformed responses, are handled as a separate recovery problem. The study measures whether these decisions improve reliability enough to justify their added inference cost.

The models remain frozen. This project does not train a separate routing classifier.

## How the study works

1. Generate a tool call with a principal small model.
2. Calculate uncertainty from the generated tokens or from repeated generations.
3. Accept a low-uncertainty call or escalate an uncertain request to the fallback model.
4. Evaluate post-fault recovery separately after an execution fault is observed.
5. Compare task success, confident failures, coverage, fallback use, latency, GPU usage, and cost per successful task.

## Benchmark

The evaluation uses the official [RobustBench-TC release](https://github.com/WillChow66/robustbench-tc-release) pinned at revision:

```text
d5d03180de41eb30a6c796d04a9bfbd9dad85c1d
```

The audited study populations are:

| Population | Rows | Base-task groups | Use |
|---|---:|---:|---|
| Clean-anchored population | 2,477 | 199 | Primary evaluation |
| Complete single-turn population | 2,527 | 248 | Sensitivity analysis |
| Runtime-generated Transition predictions | 1,194 | 199 | Post-fault recovery |

Transition cases are generated at runtime from the clean source rows. They are not stored in the static JSONL files. The benchmark's published total is reconciled as 2,527 retained single-turn records plus 1,194 runtime Transition predictions, giving 3,721 predictions per model.

## Planned model roles

Principal small models:

- `Qwen/Qwen2.5-1.5B-Instruct`
- `meta-llama/Llama-3.2-3B-Instruct`
- `Qwen/Qwen2.5-7B-Instruct`

Fallback model:

- `Qwen/Qwen2.5-14B-Instruct-AWQ`

Exact model revisions, tokenizer revisions, inference settings, and hardware details will be recorded after the feasibility pilot and before the main experiments.

## Current status

Task 1 is in progress.

Completed:

- Python package and test structure
- Base-task identity rules
- Static benchmark population audit
- Runtime Transition population audit
- Draft evaluation protocol
- Benchmark-and-robustness literature foundation
- Project task plan and weekly timeline

Next:

- Create and verify the grouped development and held-out split
- Build the resumable experiment runner
- Capture and validate token log-probabilities
- Run the model-feasibility pilot
- Freeze the Task 1 protocol

The [GitHub Project board](https://github.com/users/RavindraSSK/projects/8/views/1) tracks the five main tasks and their current subtasks.

## Setup

UQRoute-TC requires Python 3.10 through 3.13.

```bash
git clone https://github.com/RavindraSSK/uqroute-tc.git
cd uqroute-tc
python -m venv .venv
```

Activate the environment on Windows Git Bash:

```bash
source .venv/Scripts/activate
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

Install the package with the existing analysis, client, and development extras:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[analysis,client,dev]"
```

Run the current checks:

```bash
ruff check .
pytest -q
```

The RobustBench-TC clone, model weights, credentials, and generated experiment outputs are kept outside this repository.

## Repository guide

- `src/uqroute_tc/data/`: benchmark identity and audit code
- `src/uqroute_tc/parsing/`: canonical tool-call parsing
- `src/uqroute_tc/uncertainty/`: uncertainty measures
- `src/uqroute_tc/inference/`: model inference and run records
- `src/uqroute_tc/routing/`: routing and recovery policies
- `src/uqroute_tc/evaluation/`: metrics and evaluation
- `tests/unit/`: unit tests
- `docs/`: protocol, progress, task plan, timeline, and literature evidence
- `paper/`: paper references and future manuscript material

Some package areas are placeholders and will be implemented in their corresponding project tasks.

## Project documents

- [Project description and tasks](docs/PROJECT_TASKS.md)
- [Evaluation protocol](docs/PROTOCOL.md)
- [Technical progress](docs/PROGRESS.md)
- [Weekly timeline](docs/WEEKLY_TIMELINE.md)
- [Literature evidence matrix](docs/literature/EVIDENCE_MATRIX.md)

## Expected outcome

The final package will include a reproducible routing toolkit, experiment records, failure analysis, capstone report, presentation, and a submission-ready research paper. Submission will follow only after the experimental results and claims have been verified; publication acceptance depends on external peer review.
