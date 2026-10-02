"""Conservative syntax-to-token alignment for BFCL and ReAct tool calls.

Unsupported outputs never receive a partial meaningful-token score.
"""

from __future__ import annotations

import ast
import json
import math
import re
from dataclasses import dataclass
from typing import Any

from uqroute_tc.inference.pilot import token_evidence
from uqroute_tc.parsing.canonical import canonical_key

_SIMPLE_STRING = re.compile(rb'''(?:"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')''', re.DOTALL)
_DOTTED_NAME = re.compile(rb"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*")
_REACT_ACTION = re.compile(r"^[ \t]*Action(?:[ \t]*Code)?[ \t]*:[ \t]*([^\r\n]+)",
                           re.IGNORECASE | re.MULTILINE)
_REACT_INPUT = re.compile(r"^[ \t]*Action(?:[ \t]*Code)?[ \t]*Input[ \t]*:[ \t]*",
                          re.IGNORECASE | re.MULTILINE)
_JSON_ATOM = re.compile(
    r'"(?:[^"\\]|\\.)*"|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?|\b(?:true|false|null)\b'
)


@dataclass(frozen=True)
class MeaningfulTokenScore:
    mean_token_nll: float
    selected_token_indices: tuple[int, ...]
    boundary_crossing_token_indices: tuple[int, ...]
    tool_name_spans: tuple[tuple[int, int], ...]
    argument_name_spans: tuple[tuple[int, int], ...]
    argument_value_spans: tuple[tuple[int, int], ...]


def _span(node: ast.AST, line_starts: list[int]) -> tuple[int, int]:
    return (line_starts[node.lineno - 1] + node.col_offset,
            line_starts[node.end_lineno - 1] + node.end_col_offset)


def _merge(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if start == end:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def _react_spans(
    raw_output: str, parsed_calls: list[dict[str, Any]]
) -> tuple[list[tuple[int, int]], list[tuple[int, int]], list[tuple[int, int]]]:
    """Accept one complete ReAct Action/Input pair with a JSON object input."""
    actions = list(_REACT_ACTION.finditer(raw_output))
    inputs = list(_REACT_INPUT.finditer(raw_output))
    if len(actions) != 1 or len(inputs) != 1 or actions[0].end() > inputs[0].start():
        raise ValueError("expected one ReAct Action followed by one Action Input")
    action_text = actions[0].group(1)
    if re.fullmatch(r"[A-Za-z_]\w*", action_text.strip()) is None:
        raise ValueError("ReAct action name is not a plain identifier")
    name = action_text.strip()
    name_start = actions[0].start(1) + len(action_text) - len(action_text.lstrip())
    decoder = json.JSONDecoder()
    input_start = inputs[0].end()
    try:
        params, length = decoder.raw_decode(raw_output[input_start:])
    except json.JSONDecodeError as exc:
        raise ValueError("ReAct Action Input is not JSON") from exc
    if not isinstance(params, dict) or raw_output[input_start + length:].strip():
        raise ValueError("ReAct Action Input must be one complete JSON object")
    if canonical_key([{"name": name, "parameters": params}]) != canonical_key(parsed_calls):
        raise ValueError("ReAct call does not match the benchmark parser")

    def byte_span(start: int, end: int) -> tuple[int, int]:
        return (len(raw_output[:start].encode("utf-8")),
                len(raw_output[:end].encode("utf-8")))

    names = [byte_span(name_start, name_start + len(name))]
    arguments: list[tuple[int, int]] = []
    values: list[tuple[int, int]] = []
    input_text = raw_output[input_start:input_start + length]
    for match in _JSON_ATOM.finditer(input_text):
        atom = match.group()
        start, end = input_start + match.start(), input_start + match.end()
        is_key = atom.startswith('"') and re.match(r"\s*:", input_text[match.end():])
        if atom.startswith('"') and len(atom) > 2:
            start += 1
            end -= 1
        (arguments if is_key else values).append(byte_span(start, end))
    if not arguments and params:
        raise ValueError("ReAct JSON argument spans are unavailable")
    return names, arguments, values


def meaningful_token_score(
    raw_output: str,
    parsed_calls: list[dict[str, Any]],
    chosen_tokens: list[dict[str, Any]],
    finish_reason: str,
    benchmark: str = "bfcl_v3",
) -> MeaningfulTokenScore:
    """Match AST name/value byte spans to visible chosen-token log-probabilities.

    A token overlapping a meaningful byte is included in full. Boundary
    crossing indices expose the resulting punctuation contamination.
    """
    if finish_reason == "length":
        raise ValueError("truncated output")
    if not isinstance(raw_output, str) or not raw_output.strip():
        raise ValueError("empty output")
    evidence = token_evidence({"message": {"content": raw_output},
                               "logprobs": {"content": chosen_tokens}})
    if not evidence["valid"]:
        raise ValueError(f"invalid token evidence: {evidence['reason']}")
    if benchmark in {"rotbench", "tooleyes"}:
        names, arguments, values = _react_spans(raw_output, parsed_calls)
        return _score_spans(evidence, chosen_tokens, names, arguments, values)
    if benchmark != "bfcl_v3":
        raise ValueError(f"unsupported benchmark for meaningful-token alignment: {benchmark}")
    raw_bytes = raw_output.encode("utf-8")
    line_starts = [0]
    for line in raw_output.splitlines(keepends=True):
        line_starts.append(line_starts[-1] + len(line.encode("utf-8")))
    try:
        body = ast.parse(raw_output, mode="eval").body
    except SyntaxError as exc:
        raise ValueError("output is not a complete BFCL expression") from exc
    expressions = body.elts if isinstance(body, ast.List) else [body]
    if not expressions or not all(isinstance(expr, ast.Call) for expr in expressions):
        raise ValueError("output is not a BFCL call or list of calls")

    names: list[tuple[int, int]] = []
    arguments: list[tuple[int, int]] = []
    values: list[tuple[int, int]] = []
    ast_calls = []
    for expr in expressions:
        if expr.args or any(kw.arg is None for kw in expr.keywords):
            raise ValueError("positional or expanded arguments are unsupported")
        fn_span = _span(expr.func, line_starts)
        fn_bytes = raw_bytes[fn_span[0]:fn_span[1]]
        fn = fn_bytes.decode("utf-8")
        if not isinstance(expr.func, (ast.Name, ast.Attribute)):
            raise ValueError("tool name must be a plain or dotted name")
        if _DOTTED_NAME.fullmatch(fn_bytes) is None:
            raise ValueError("tool name must be a plain or dotted name")
        names.append(fn_span)
        params = {}
        for kw in expr.keywords:
            if kw.arg in params:
                raise ValueError("duplicate argument name")
            key_start, _ = _span(kw, line_starts)
            key_end = key_start + len(kw.arg.encode("utf-8"))
            if raw_bytes[key_start:key_end] != kw.arg.encode("utf-8"):
                raise ValueError("argument name does not match source bytes")
            arguments.append((key_start, key_end))
            val_start, val_end = _span(kw.value, line_starts)
            try:
                params[kw.arg] = ast.literal_eval(kw.value)
            except (SyntaxError, ValueError, TypeError, MemoryError, RecursionError) as exc:
                raise ValueError("argument is not a literal value") from exc
            source_value = raw_bytes[val_start:val_end]
            if isinstance(params[kw.arg], str):
                if _SIMPLE_STRING.fullmatch(source_value) is None:
                    raise ValueError("unsupported string-literal syntax")
                if len(source_value) > 2:
                    val_start += 1  # exclude opening quote, retain encoded value bytes
                    val_end -= 1  # exclude closing quote
            values.append((val_start, val_end))
        ast_calls.append({"name": fn, "parameters": params})
    if canonical_key(ast_calls) != canonical_key(parsed_calls):
        raise ValueError("AST calls do not match the benchmark parser")

    return _score_spans(evidence, chosen_tokens, names, arguments, values)


def _score_spans(
    evidence: dict[str, Any],
    chosen_tokens: list[dict[str, Any]],
    names: list[tuple[int, int]],
    arguments: list[tuple[int, int]],
    values: list[tuple[int, int]],
) -> MeaningfulTokenScore:
    semantic_spans = _merge(names + arguments + values)
    selected = []
    boundary = []
    visible = (chosen_tokens[:-1] if evidence["excluded_trailing_token"]
               else chosen_tokens)
    for i, ((start, end), token) in enumerate(zip(evidence["visible_token_spans"], visible)):
        covered = sum(max(0, min(end, b) - max(start, a)) for a, b in semantic_spans)
        if covered:
            selected.append(i)
            if covered != end - start:
                boundary.append(i)
    if not selected:
        raise ValueError("no visible tokens overlap tool names or argument content")
    nll = sum(-visible[i]["logprob"] for i in selected) / len(selected)
    if not math.isfinite(nll):
        raise ValueError("nonfinite meaningful-token score")
    return MeaningfulTokenScore(nll, tuple(selected), tuple(boundary),
                                tuple(names), tuple(arguments), tuple(values))
