# UQRoute-TC

**Uncertainty-Gated Routing and Recovery for Reliable Tool Calling**

## Project overview

UQRoute-TC studies whether a language model can recognize when its proposed tool call may be unreliable. Tool-calling models must select the correct tool and generate valid arguments, but changes to instructions, tool descriptions, schemas, observations, or runtime responses can cause incorrect calls even when the model appears confident.

The system uses a smaller model for the first attempt. It accepts the call when uncertainty is low and sends uncertain requests to a stronger fallback model. Recovery after an observed runtime fault is evaluated separately. Using the official RobustBench-TC release, the project measures whether uncertainty-based routing improves reliability enough to justify the additional inference cost.

The models remain frozen, and the project does not train a separate routing classifier.

## Workflow

1. A principal model generates a structured tool call.
2. The system calculates uncertainty from token probabilities or repeated generations.
3. A low-uncertainty call is accepted; an uncertain request is sent to the fallback model.
4. Runtime faults receive a separate, bounded recovery evaluation.

## Benchmark and scope

The study uses the official [RobustBench-TC release](https://github.com/WillChow66/robustbench-tc-release) pinned at `d5d03180de41eb30a6c796d04a9bfbd9dad85c1d`.

| Population | Rows | Base-task groups | Use |
|---|---:|---:|---|
| Clean-anchored population | 2,477 | 199 | Primary evaluation |
| Complete single-turn population | 2,527 | 248 | Sensitivity analysis |
| Runtime-generated Transition predictions | 1,194 | 199 | Post-fault recovery |

The benchmark clone, model weights, credentials, and generated outputs are kept outside this repository.

## Current status

**Task 1 is in progress. Full model experiments have not started.**

Completed:

- Python package, environment, tests, and base-task identity rules
- Static and runtime Transition population audits
- Draft evaluation protocol
- Benchmark-and-robustness literature foundation
- Project task plan and weekly timeline

Next:

- Create and verify the grouped development and held-out split
- Build the resumable experiment runner
- Capture and validate token log-probabilities
- Run the model-feasibility pilot
- Freeze the Task 1 protocol

Progress is tracked on the [GitHub Project board](https://github.com/users/RavindraSSK/projects/8/views/1).

## Setup

UQRoute-TC supports Python 3.10 through 3.13.

```bash
git clone https://github.com/RavindraSSK/uqroute-tc.git
cd uqroute-tc
python -m venv .venv

# Windows Git Bash
source .venv/Scripts/activate

# macOS or Linux
# source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e ".[analysis,client,dev]"
ruff check .
pytest -q
```

## Documentation

- [Project description and tasks](docs/PROJECT_TASKS.md)
- [Evaluation protocol](docs/PROTOCOL.md)
- [Technical progress](docs/PROGRESS.md)
- [Weekly timeline](docs/WEEKLY_TIMELINE.md)
- [Literature evidence matrix](docs/literature/EVIDENCE_MATRIX.md)

## Expected outcome

The final package will include a reproducible routing toolkit, experiment records, failure analysis, capstone report, presentation, and a submission-ready research paper. Submission will follow after the results and claims are verified. Publication acceptance depends on external peer review.
