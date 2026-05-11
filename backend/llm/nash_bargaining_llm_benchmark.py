#!/usr/bin/env python3
"""
Run Nash bargaining / Edgeworth-box benchmark problems against multiple Groq-hosted LLMs.

Setup:
    pip install groq
    export GROQ_API_KEY="your_api_key_here"

Example:
    python nash_bargaining_llm_benchmark.py \
        --models llama-3.3-70b-versatile llama-3.1-8b-instant \
        --trials 3 \
        --out-prefix results/nash_bargaining

Outputs:
    <out-prefix>_trials.jsonl
    <out-prefix>_summary.csv

Notes:
    - The scoring is deterministic and answer-key based.
    - The model is asked to return JSON.
    - The parser also tries to recover JSON if the model wraps it in prose or Markdown.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from groq import Groq


SYSTEM_PROMPT = """You are solving graduate microeconomics problems about Nash bargaining in an Edgeworth box.

You must solve carefully and return ONLY valid JSON. Do not include Markdown, LaTeX fences, or prose outside JSON.

Use strings for fractions, e.g. "8/3". Use integers as strings too, e.g. "5".
"""


@dataclass(frozen=True)
class ExpectedField:
    key: str
    expected: Any
    points: float


@dataclass(frozen=True)
class Problem:
    problem_id: str
    title: str
    prompt: str
    expected_fields: List[ExpectedField]


def frac(value: Any) -> Optional[Fraction]:
    """Convert a model value into a Fraction when possible."""
    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return Fraction(value, 1)

    if isinstance(value, float):
        return Fraction(value).limit_denominator(10_000)

    if isinstance(value, str):
        s = value.strip()
        s = s.replace("$", "")
        s = s.replace("\\frac", "frac")
        s = s.replace(" ", "")

        # Parse simple LaTeX-ish fractions: frac{8}{3}
        m = re.fullmatch(r"frac\{(-?\d+)\}\{(-?\d+)\}", s)
        if m:
            return Fraction(int(m.group(1)), int(m.group(2)))

        # Parse ordinary integer or a/b fraction.
        try:
            return Fraction(s)
        except Exception:
            return None

    return None


def normalize_pair(value: Any) -> Optional[Tuple[Fraction, Fraction]]:
    """Convert a pair-like object into a tuple of Fractions."""
    if isinstance(value, dict):
        # Accept {"x": ..., "y": ...}
        if "x" in value and "y" in value:
            x = frac(value["x"])
            y = frac(value["y"])
            if x is not None and y is not None:
                return (x, y)

        # Accept {"x_A": ..., "y_A": ...} or {"x_B": ..., "y_B": ...}
        x_keys = [k for k in value if k.lower().startswith("x")]
        y_keys = [k for k in value if k.lower().startswith("y")]
        if len(x_keys) == 1 and len(y_keys) == 1:
            x = frac(value[x_keys[0]])
            y = frac(value[y_keys[0]])
            if x is not None and y is not None:
                return (x, y)

    if isinstance(value, (list, tuple)) and len(value) == 2:
        x = frac(value[0])
        y = frac(value[1])
        if x is not None and y is not None:
            return (x, y)

    if isinstance(value, str):
        # Accept "(8/3, 8/3)" or "8/3,8/3"
        s = value.strip().strip("()[]")
        parts = [p.strip() for p in s.split(",")]
        if len(parts) == 2:
            x = frac(parts[0])
            y = frac(parts[1])
            if x is not None and y is not None:
                return (x, y)

    return None


def compare_expected(actual: Any, expected: Any) -> bool:
    """Exact comparison, with support for rational numbers and allocation pairs."""
    if isinstance(expected, tuple) and len(expected) == 2:
        return normalize_pair(actual) == expected

    if isinstance(expected, Fraction):
        return frac(actual) == expected

    if isinstance(expected, str):
        return str(actual).strip() == expected

    return actual == expected


def extract_json(text: str) -> Dict[str, Any]:
    """Extract JSON from a model response; raise ValueError if impossible."""
    text = text.strip()

    # Direct JSON.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Markdown code fence.
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fence:
        return json.loads(fence.group(1))

    # First {...} block.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])

    raise ValueError("Could not extract JSON from model response.")


def score_response(problem: Problem, parsed: Dict[str, Any]) -> Tuple[float, float, List[Dict[str, Any]]]:
    """Return earned points, max points, and per-field scoring details."""
    earned = 0.0
    max_points = sum(f.points for f in problem.expected_fields)
    details = []

    for field in problem.expected_fields:
        actual = parsed.get(field.key)
        ok = compare_expected(actual, field.expected)
        if ok:
            earned += field.points

        details.append(
            {
                "key": field.key,
                "expected": stringify_expected(field.expected),
                "actual": actual,
                "points": field.points,
                "earned": field.points if ok else 0.0,
                "correct": ok,
            }
        )

    return earned, max_points, details


def stringify_expected(value: Any) -> Any:
    if isinstance(value, Fraction):
        if value.denominator == 1:
            return str(value.numerator)
        return f"{value.numerator}/{value.denominator}"
    if isinstance(value, tuple):
        return [stringify_expected(v) for v in value]
    return value


def build_answer_schema(problem: Problem) -> str:
    fields = []
    for field in problem.expected_fields:
        if isinstance(field.expected, tuple):
            fields.append(f'"{field.key}": ["x_value", "y_value"]')
        else:
            fields.append(f'"{field.key}": "value"')

    fields_text = ",\n  ".join(fields)
    return "{\n  " + fields_text + "\n}"


def make_user_prompt(problem: Problem) -> str:
    schema = build_answer_schema(problem)
    return f"""{problem.prompt}

Return ONLY valid JSON with exactly these keys:
{schema}

Use strings for all numeric values. For allocations, use a two-item list [x, y].
"""


def call_groq(
    client: Groq,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
    sleep_seconds: float,
) -> str:
    if sleep_seconds > 0:
        time.sleep(sleep_seconds)

    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return completion.choices[0].message.content or ""


def run_trial(
    client: Groq,
    model: str,
    problem: Problem,
    trial_index: int,
    temperature: float,
    max_tokens: int,
    sleep_seconds: float,
) -> Dict[str, Any]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": make_user_prompt(problem)},
    ]

    started = time.time()
    raw = call_groq(
        client=client,
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        sleep_seconds=sleep_seconds,
    )
    latency = time.time() - started

    parse_error = None
    parsed: Dict[str, Any] = {}

    try:
        parsed = extract_json(raw)
    except Exception as exc:
        parse_error = str(exc)

    if parse_error is None:
        earned, max_points, details = score_response(problem, parsed)
    else:
        max_points = sum(f.points for f in problem.expected_fields)
        earned = 0.0
        details = []

    return {
        "model": model,
        "problem_id": problem.problem_id,
        "problem_title": problem.title,
        "trial_index": trial_index,
        "score": earned / max_points if max_points else 0.0,
        "earned_points": earned,
        "max_points": max_points,
        "latency_seconds": latency,
        "parse_error": parse_error,
        "parsed_response": parsed,
        "raw_response": raw,
        "field_scores": details,
    }


def summarize(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for r in results:
        grouped.setdefault(r["model"], []).append(r)

    rows = []
    for model, rs in sorted(grouped.items()):
        total_earned = sum(r["earned_points"] for r in rs)
        total_possible = sum(r["max_points"] for r in rs)
        avg_score = total_earned / total_possible if total_possible else 0.0
        parse_failures = sum(1 for r in rs if r["parse_error"])
        avg_latency = sum(r["latency_seconds"] for r in rs) / len(rs)

        rows.append(
            {
                "model": model,
                "num_trials": len(rs),
                "overall_score": round(avg_score, 4),
                "earned_points": round(total_earned, 4),
                "max_points": round(total_possible, 4),
                "parse_failures": parse_failures,
                "avg_latency_seconds": round(avg_latency, 3),
            }
        )

    return rows


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def get_problems() -> List[Problem]:
    F = Fraction

    return [
        Problem(
            problem_id="P1",
            title="Symmetric Cobb-Douglas",
            prompt=r"""
Problem 1: Symmetric Cobb-Douglas, inefficient endowment.

Total resources: (10,10).
Initial endowment: omega_A=(2,8), omega_B=(8,2).
Utilities: u_A=x_A y_A, u_B=x_B y_B.
Disagreement point is the initial endowment.
Find the Nash bargaining allocation maximizing (u_A-u_A^0)(u_B-u_B^0) subject to feasibility.
""",
            expected_fields=[
                ExpectedField("u_A0", F(16), 1),
                ExpectedField("u_B0", F(16), 1),
                ExpectedField("mrs_A_at_general_bundle", "y_A/x_A", 1),
                ExpectedField("mrs_B_at_general_bundle", "y_B/x_B", 1),
                ExpectedField("contract_curve", "y_A=x_A", 2),
                ExpectedField("A_allocation", (F(5), F(5)), 3),
                ExpectedField("B_allocation", (F(5), F(5)), 3),
            ],
        ),
        Problem(
            problem_id="P2",
            title="Asymmetric Cobb-Douglas",
            prompt=r"""
Problem 2: Asymmetric Cobb-Douglas, zero disagreement utilities.

Total resources: (9,9).
Initial endowment: omega_A=(9,0), omega_B=(0,9).
Utilities: u_A=x_A^2 y_A, u_B=x_B y_B^2.
Disagreement point is the initial endowment.
Find the Nash bargaining allocation maximizing (u_A-u_A^0)(u_B-u_B^0) subject to feasibility.
""",
            expected_fields=[
                ExpectedField("u_A0", F(0), 1),
                ExpectedField("u_B0", F(0), 1),
                ExpectedField("mrs_A_at_general_bundle", "2y_A/x_A", 1),
                ExpectedField("mrs_B_at_general_bundle", "y_B/(2x_B)", 1),
                ExpectedField("A_allocation", (F(6), F(3)), 4),
                ExpectedField("B_allocation", (F(3), F(6)), 4),
                ExpectedField("mrs_at_solution", F(1), 2),
            ],
        ),
        Problem(
            problem_id="P3",
            title="Linear Utilities",
            prompt=r"""
Problem 3: Linear utilities, corner contract allocation.

Total resources: (12,12).
Initial endowment: omega_A=(10,2), omega_B=(2,10).
Utilities: u_A=x_A+2y_A, u_B=2x_B+y_B.
Disagreement point is the initial endowment.
Find the Nash bargaining allocation maximizing (u_A-u_A^0)(u_B-u_B^0) subject to feasibility.
""",
            expected_fields=[
                ExpectedField("u_A0", F(14), 1),
                ExpectedField("u_B0", F(14), 1),
                ExpectedField("mrs_A", F(1, 2), 1),
                ExpectedField("mrs_B", F(2), 1),
                ExpectedField("A_allocation", (F(0), F(12)), 4),
                ExpectedField("B_allocation", (F(12), F(0)), 4),
                ExpectedField("utility_gain_A", F(10), 1),
                ExpectedField("utility_gain_B", F(10), 1),
            ],
        ),
        Problem(
            problem_id="P4",
            title="Quasilinear Utilities",
            prompt=r"""
Problem 4: Quasilinear utilities with quadratic private values.

Total resources: (10,10), where y is the transferable numeraire.
Initial endowment: omega_A=(2,5), omega_B=(8,5).
Utilities: u_A=8x_A-x_A^2+y_A, u_B=12x_B-x_B^2+y_B.
Disagreement point is the initial endowment.
Find the Nash bargaining allocation maximizing (u_A-u_A^0)(u_B-u_B^0) subject to feasibility.
""",
            expected_fields=[
                ExpectedField("u_A0", F(17), 1),
                ExpectedField("u_B0", F(37), 1),
                ExpectedField("efficient_x_A", F(4), 2),
                ExpectedField("efficient_x_B", F(6), 2),
                ExpectedField("total_efficient_utility", F(62), 1),
                ExpectedField("total_disagreement_utility", F(54), 1),
                ExpectedField("surplus_gain", F(8), 1),
                ExpectedField("A_allocation", (F(4), F(5)), 3),
                ExpectedField("B_allocation", (F(6), F(5)), 3),
            ],
        ),
        Problem(
            problem_id="P5",
            title="Cobb-Douglas vs Linear",
            prompt=r"""
Problem 5: Cobb-Douglas versus linear utility.

Total resources: (8,8).
Initial endowment: omega_A=(8,0), omega_B=(0,8).
Utilities: u_A=x_A y_A, u_B=x_B+y_B.
Disagreement point is the initial endowment.
Find the Nash bargaining allocation maximizing (u_A-u_A^0)(u_B-u_B^0) subject to feasibility.
""",
            expected_fields=[
                ExpectedField("u_A0", F(0), 1),
                ExpectedField("u_B0", F(8), 1),
                ExpectedField("A_allocation", (F(8, 3), F(8, 3)), 5),
                ExpectedField("B_allocation", (F(16, 3), F(16, 3)), 5),
                ExpectedField("utility_gain_A", F(64, 9), 2),
                ExpectedField("utility_gain_B", F(8, 3), 2),
            ],
        ),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark Groq-hosted LLMs on Nash bargaining Edgeworth-box problems."
    )
    parser.add_argument(
        "--models",
        nargs="+",
        required=True,
        help="Groq model IDs to test, e.g. llama-3.3-70b-versatile llama-3.1-8b-instant",
    )
    parser.add_argument("--trials", type=int, default=3, help="Trials per model per problem.")
    parser.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature.")
    parser.add_argument("--max-tokens", type=int, default=1600, help="Max output tokens per call.")
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.0,
        help="Optional delay between calls to reduce rate-limit pressure.",
    )
    parser.add_argument(
        "--out-prefix",
        type=str,
        default="nash_bargaining_results",
        help="Output prefix. Writes *_trials.jsonl and *_summary.csv.",
    )
    parser.add_argument(
        "--problem-ids",
        nargs="*",
        default=None,
        help="Optional subset, e.g. --problem-ids P1 P3 P5",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GROQ_API_KEY environment variable.")

    client = Groq(api_key=api_key)
    problems = get_problems()

    if args.problem_ids:
        keep = set(args.problem_ids)
        problems = [p for p in problems if p.problem_id in keep]
        if not problems:
            raise RuntimeError(f"No matching problems for --problem-ids={args.problem_ids}")

    results: List[Dict[str, Any]] = []

    for model in args.models:
        for problem in problems:
            for trial_index in range(1, args.trials + 1):
                print(f"Running model={model} problem={problem.problem_id} trial={trial_index}")
                try:
                    result = run_trial(
                        client=client,
                        model=model,
                        problem=problem,
                        trial_index=trial_index,
                        temperature=args.temperature,
                        max_tokens=args.max_tokens,
                        sleep_seconds=args.sleep_seconds,
                    )
                except Exception as exc:
                    max_points = sum(f.points for f in problem.expected_fields)
                    result = {
                        "model": model,
                        "problem_id": problem.problem_id,
                        "problem_title": problem.title,
                        "trial_index": trial_index,
                        "score": 0.0,
                        "earned_points": 0.0,
                        "max_points": max_points,
                        "latency_seconds": None,
                        "parse_error": f"API_OR_RUNTIME_ERROR: {exc}",
                        "parsed_response": {},
                        "raw_response": "",
                        "field_scores": [],
                    }

                results.append(result)

    out_prefix = Path(args.out_prefix)
    trials_path = out_prefix.with_name(out_prefix.name + "_trials.jsonl")
    summary_path = out_prefix.with_name(out_prefix.name + "_summary.csv")

    write_jsonl(trials_path, results)
    summary_rows = summarize(results)
    write_csv(summary_path, summary_rows)

    print("\nSummary")
    print("=======")
    for row in summary_rows:
        print(
            f"{row['model']}: overall_score={row['overall_score']} "
            f"earned={row['earned_points']}/{row['max_points']} "
            f"parse_failures={row['parse_failures']} "
            f"avg_latency_seconds={row['avg_latency_seconds']}"
        )

    print(f"\nWrote trial-level results to: {trials_path}")
    print(f"Wrote summary results to: {summary_path}")


if __name__ == "__main__":
    main()
