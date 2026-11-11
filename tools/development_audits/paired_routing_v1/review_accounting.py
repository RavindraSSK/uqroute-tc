"""Display existing saved routing accounting; no inference, recomputation or writes."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DEFAULT = REPO / "artifacts/local_development_audits/paired_routing_development_v1"
MODELS = ("qwen15b", "llama3b", "qwen7b")
PANELS = ("official_reference_compliance", "tooleyes_relevance")


def number(value):
    if value is None:
        return "unavailable"
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError("Invalid saved nonnegative accounting value")
    return str(value) if type(value) is int else f"{value:.3f}"


def metric_row(label, result):
    accounting = result["accounting"]
    usage = accounting["usage"]
    correct = result["reference_matches_known"]
    unknown = result["reference_outcomes_unavailable"]
    values = []
    for field in ("prompt_tokens", "completion_tokens", "elapsed_seconds"):
        item = usage[field]
        if item["missing_calls"]:
            if item["total"] is not None:
                raise ValueError("Missing usage must not have a complete total")
            values.append(f"unavailable ({item['missing_calls']} missing)")
        else:
            values.append(number(item["total"]))
    calls_per_match = accounting["model_calls"] / correct if correct and not unknown else None
    seconds = usage["elapsed_seconds"]["total"]
    seconds_per_match = (
        seconds / correct if correct and not unknown and seconds is not None else None
    )
    cells = [
        label,
        f"{correct}/{result['rows']}" + (f"; {unknown} unknown" if unknown else ""),
        number(result["fallback_rows"]),
        number(accounting["model_calls"]),
        number(result["unusable_final_outputs"]),
        *values,
        number(calls_per_match),
        number(seconds_per_match),
    ]
    return "| " + " | ".join(cells) + " |"


def render(summary, baselines, budgets):
    if summary["version"] != "uqroute-paired-routing-development-1.0.0":
        raise ValueError("Unexpected saved paired-analysis version")
    for key in ("held_out_access_enabled", "main_experiment_ready", "routing_threshold_selected"):
        if summary[key] is not False:
            raise ValueError("Expected retrospective development-only outputs")
    lines = [
        "# Saved development routing accounting",
        "",
        "Display of existing saved results; original evidence is not revalidated by this viewer.",
        "Reference compliance and ToolEyes name relevance remain separate.",
        "",
    ]
    for model in MODELS:
        for panel in PANELS:
            scope = "panel/" + panel
            expected = summary["paired_panels"][model][panel]["rows"]
            lines += [
                f"## {model} / {panel}",
                "",
                (
                    "| Policy | Matches | Fallback calls | Total calls | Unusable final | "
                    "Prompt tokens | Completion tokens | Request seconds | Calls/match | "
                    "Request seconds/match |"
                ),
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
            notes = []
            results = [
                (name, result) for name, result in baselines[model][scope]["baselines"].items()
            ]
            for view in budgets[model][scope]:
                label = f"gate cap {view['budget_cap']:.0%}"
                if not view["feasible"]:
                    notes.append(
                        f"{label}: infeasible; minimum forced fallback "
                        f"{view['minimum_fallback_rows']}/{expected}."
                    )
                    continue
                results.append((label, view["gated"]))
            for label, result in results:
                if result["rows"] != expected or result["panel"] != panel:
                    raise ValueError("Saved endpoint denominators differ")
                lines.append(metric_row(label, result))
            lines.append("")
            lines.extend(notes)
            lines.append("")
    lines += [
        "Calls are policy attempt slots, including unsuccessful outputs.",
        "Request seconds sum cached elapsed times; they are not online latency or GPU billing.",
        "Calls/match and seconds/match use reference or relevance matches, not executed success.",
        "Missing totals are unavailable; known partial sums are preserved in baselines.json.",
        "Token counts across differently priced models do not establish monetary savings.",
        "Fixed-cap views are retrospective; no deployment threshold is selected.",
    ]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-dir", type=Path, default=DEFAULT)
    args = parser.parse_args()
    try:
        data = [
            json.loads((args.analysis_dir / name).read_text(encoding="utf-8"))
            for name in ("summary.json", "baselines.json", "budget_views.json")
        ]
        print(render(*data), end="")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise SystemExit("Cannot display saved accounting: " + str(exc)) from None


if __name__ == "__main__":
    main()
