"""Strict BFCL syntax-to-token alignment for meaningful-token uncertainty.

This draft accepts complete Python-style BFCL calls only. Other output formats
require separate audited rules; failures never receive a partial score.
"""

from __future__ import annotations

import ast
import math
import re
from dataclasses import dataclass
from typing import Any

from uqroute_tc.inference.pilot import token_evidence
from uqroute_tc.parsing.canonical import canonical_key

_SIMPLE_STRING = re.compile(rb'''(?:"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')''', re.DOTALL)
_DOTTED_NAME = re.compile(rb"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*")


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


def meaningful_token_score(
    raw_output: str,
    parsed_calls: list[dict[str, Any]],
    chosen_tokens: list[dict[str, Any]],
    finish_reason: str,
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
