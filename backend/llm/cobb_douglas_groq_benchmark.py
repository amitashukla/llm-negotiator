#!/usr/bin/env python3
"""
Cobb-Douglas Exponent Benchmark Runner for Groq-hosted LLMs.

Purpose
-------
Runs a compact microeconomics benchmark against one or more Groq models.
Each model receives several randomized trials. Each trial asks the model to
recover alpha in normalized Cobb-Douglas utility:

    u(x,y) = x^alpha y^(1-alpha)

from observed choices under budget constraints.

Setup
-----
    pip install groq

Then set your API key:

    export GROQ_API_KEY="your_key_here"

Example
-------
    python cobb_douglas_groq_benchmark.py \
        --models llama-3.3-70b-versatile openai/gpt-oss-120b \
        --trials-per-problem 3 \
        --out results

Outputs
-------
    results/results.jsonl
    results/summary.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import time
from dataclasses import dataclass, asdict
from fractions import Fraction
from pathlib import Path
from typing import Any, Optional

from groq import Groq


# -----------------------------
# Benchmark problem definitions
# -----------------------------

@dataclass(frozen=True)
class Problem:
    id: str
    title: str
    prompt: str
    expected_alpha: Optional[Fraction]
    expected_text: str
    notes: str


PROBLEMS: list[Problem] = [
    Problem(
        id="P1",
        title="Basic recovery from two observations",
        prompt="""A consumer has normalized Cobb-Douglas utility u(x,y)=x^alpha y^(1-alpha), with alpha in (0,1).

You observe two choices:

Observation 1: prices are p_x=2, p_y=1, income m=12, chosen bundle is (x,y)=(4,4).
Observation 2: prices are p_x=1, p_y=2, income m=18, chosen bundle is (x,y)=(12,3).

Assuming each observed bundle is an interior utility-maximizing choice, solve for alpha.""",
        expected_alpha=Fraction(2, 3),
        expected_text="2/3",
        notes="Both observations imply x-expenditure share 2/3.",
    ),
    Problem(
        id="P2",
        title="Different relative prices",
        prompt="""A consumer has normalized Cobb-Douglas utility u(x,y)=x^alpha y^(1-alpha), with alpha in (0,1).

You observe two choices:

Observation 1: prices are p_x=3, p_y=2, income m=25, chosen bundle is (x,y)=(5,5).
Observation 2: prices are p_x=4, p_y=1, income m=20, chosen bundle is (x,y)=(3,8).

Assuming each observed bundle is an interior utility-maximizing choice, solve for alpha.""",
        expected_alpha=Fraction(3, 5),
        expected_text="3/5",
        notes="Both observations imply x-expenditure share 3/5.",
    ),
    Problem(
        id="P3",
        title="Recovery from MRS condition",
        prompt="""A consumer has normalized Cobb-Douglas utility u(x,y)=x^alpha y^(1-alpha), with alpha in (0,1).

You observe two choices:

Observation 1: prices are p_x=1, p_y=3, income m=16, chosen bundle is (x,y)=(4,4).
Observation 2: prices are p_x=5, p_y=2, income m=40, chosen bundle is (x,y)=(2,15).

Assuming each observed bundle is an interior utility-maximizing choice, solve for alpha. Your solution should use the marginal rate of substitution or an equivalent first-order condition.""",
        expected_alpha=Fraction(1, 4),
        expected_text="1/4",
        notes="Both observations imply x-expenditure share 1/4.",
    ),
    Problem(
        id="P4",
        title="Per-unit tax",
        prompt="""A consumer has normalized Cobb-Douglas utility u(x,y)=x^alpha y^(1-alpha), with alpha in (0,1).

The posted price of x is 2, but there is a per-unit tax of 1 on x. The price of y is 1. Income is m=21. The observed chosen bundle is (x,y)=(4,9).

Assuming the observed bundle is an interior utility-maximizing choice under the tax-inclusive price, solve for alpha.""",
        expected_alpha=Fraction(4, 7),
        expected_text="4/7",
        notes="Effective p_x is 3, so x-expenditure share is 12/21 = 4/7.",
    ),
    Problem(
        id="P5",
        title="Inconsistent observations",
        prompt="""A consumer has normalized Cobb-Douglas utility u(x,y)=x^alpha y^(1-alpha), with alpha in (0,1).

You observe two choices:

Observation 1: prices are p_x=6, p_y=2, income m=48, chosen bundle is (x,y)=(2,18).
Observation 2: prices are p_x=3, p_y=5, income m=40, chosen bundle is (x,y)=(4,28/5).

Assuming each observed bundle is claimed to be an interior utility-maximizing choice, determine whether there exists a single alpha that rationalizes both observations. If one exists, solve for alpha; if not, say that no such alpha exists.""",
        expected_alpha=None,
        expected_text="NONE",
        notes="First observation implies 1/4; second implies 3/10; inconsistent.",
    ),
]


SYSTEM_PROMPT = """You are being evaluated on graduate microeconomics problem solving.

Return ONLY valid JSON with exactly these keys:
{
  "alpha": "...",
  "reasoning_summary": "..."
}

Rules:
- If a single alpha exists, put it in lowest-term fractional form, e.g. "2/3".
- If no single alpha exists, put "NONE".
- The reasoning_summary may be concise but should mention the key computation.
- Do not use markdown.
"""


# -----------------------------
# Prompt variation
# -----------------------------

def make_trial_prompt(problem: Problem, rng: random.Random, trial_index: int) -> str:
    """Return a slightly varied prompt to reduce memorization artifacts."""
    variants = [
        "Show the essential steps and final answer.",
        "Compute alpha exactly as an integer or reduced fraction.",
        "Check whether the observations are mutually consistent before giving the final answer.",
        "Use the Cobb-Douglas optimal expenditure share condition where appropriate.",
        "Use a first-order condition or equivalent revealed-preference calculation.",
    ]
    suffix = rng.choice(variants)

    # Occasionally put the output requirement in the user prompt too.
    json_reminder = ""
    if trial_index % 2 == 0:
        json_reminder = '\n\nRemember: return only JSON. Use "NONE" if no common alpha exists.'

    return f"{problem.prompt}\n\n{suffix}{json_reminder}"


# -----------------------------
# Model call
# -----------------------------

def call_groq_model(
    client: Groq,
    model: str,
    prompt: str,
    temperature: float,
    max_completion_tokens: int,
    timeout_retries: int,
    pause_seconds: float,
) -> tuple[str, dict[str, Any]]:
    """Call a Groq chat completion with simple retry handling."""
    last_error: Optional[Exception] = None

    for attempt in range(timeout_retries + 1):
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_completion_tokens=max_completion_tokens,
            )

            content = completion.choices[0].message.content or ""
            usage = {}
            if getattr(completion, "usage", None) is not None:
                usage = {
                    "prompt_tokens": getattr(completion.usage, "prompt_tokens", None),
                    "completion_tokens": getattr(completion.usage, "completion_tokens", None),
                    "total_tokens": getattr(completion.usage, "total_tokens", None),
                }
            return content, usage

        except Exception as exc:
            last_error = exc
            if attempt < timeout_retries:
                time.sleep(pause_seconds * (attempt + 1))
            else:
                raise RuntimeError(f"Groq call failed for model={model}: {exc}") from exc

    raise RuntimeError(f"Groq call failed for model={model}: {last_error}")


# -----------------------------
# Grading
# -----------------------------

def extract_json_object(text: str) -> Optional[dict[str, Any]]:
    """Extract the first valid JSON object from a model response."""
    text = text.strip()

    # Direct parse first.
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # Fallback: find a JSON-looking object.
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None

    try:
        obj = json.loads(match.group(0))
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        return None

    return None


def parse_alpha(value: Any) -> Optional[Fraction | str]:
    """
    Parse alpha values from JSON field.

    Returns:
        Fraction for numeric/fractional answers.
        "NONE" for no-solution answers.
        None if unparseable.
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        try:
            return Fraction(value).limit_denominator(10_000)
        except Exception:
            return None

    s = str(value).strip()
    s_upper = s.upper()

    no_solution_markers = {
        "NONE",
        "NO SUCH ALPHA",
        "NO SUCH ALPHA EXISTS",
        "NO SOLUTION",
        "INCONSISTENT",
        "DOES NOT EXIST",
        "N/A",
        "NA",
    }

    if s_upper in no_solution_markers:
        return "NONE"

    # Strip common wrappers.
    s = s.replace("\\boxed{", "").replace("}", "")
    s = s.replace("$", "").replace("\\", "")
    s = s.strip()

    # Convert LaTeX frac if present: frac{2}{3}
    frac_match = re.search(r"frac\s*\{?\s*(-?\d+)\s*\}?\s*\{?\s*(-?\d+)\s*\}?", s)
    if frac_match:
        num = int(frac_match.group(1))
        den = int(frac_match.group(2))
        if den != 0:
            return Fraction(num, den)

    # Plain fraction or integer.
    plain_frac_match = re.search(r"^-?\d+\s*/\s*-?\d+$", s)
    if plain_frac_match:
        num_s, den_s = s.split("/")
        den = int(den_s)
        if den != 0:
            return Fraction(int(num_s), den)

    int_match = re.search(r"^-?\d+$", s)
    if int_match:
        return Fraction(int(s), 1)

    # Decimal.
    decimal_match = re.search(r"^-?\d+\.\d+$", s)
    if decimal_match:
        return Fraction(float(s)).limit_denominator(10_000)

    # Fallback: look for a fraction anywhere in the string.
    embedded = re.search(r"(-?\d+)\s*/\s*(-?\d+)", s)
    if embedded:
        den = int(embedded.group(2))
        if den != 0:
            return Fraction(int(embedded.group(1)), den)

    return None


def grade_response(problem: Problem, raw_response: str) -> dict[str, Any]:
    """
    Grade a response.

    Scoring:
        exact_score = 1 if the final alpha field exactly matches the expected answer.
        json_score = 1 if the response contained parseable JSON with an alpha field.
        total_score = exact_score.

    This deliberately avoids giving credit for lucky partial work unless the final
    answer is correct, because the benchmark is designed to compare model accuracy.
    """
    obj = extract_json_object(raw_response)
    json_score = 1 if isinstance(obj, dict) and "alpha" in obj else 0

    alpha_raw = obj.get("alpha") if isinstance(obj, dict) else None
    parsed = parse_alpha(alpha_raw)

    if problem.expected_alpha is None:
        exact = parsed == "NONE"
        parsed_text = "NONE" if parsed == "NONE" else str(parsed)
    else:
        exact = parsed == problem.expected_alpha
        parsed_text = str(parsed)

    return {
        "json_score": json_score,
        "exact_score": 1 if exact else 0,
        "total_score": 1 if exact else 0,
        "parsed_alpha": parsed_text,
        "expected_alpha": problem.expected_text,
        "parseable": parsed is not None,
    }


# -----------------------------
# Running and summarizing
# -----------------------------

def run_benchmark(args: argparse.Namespace) -> list[dict[str, Any]]:
    rng = random.Random(args.seed)
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []

    trial_records: list[tuple[str, Problem, int]] = []
    for model in args.models:
        for problem in PROBLEMS:
            for trial in range(args.trials_per_problem):
                trial_records.append((model, problem, trial))

    if args.shuffle:
        rng.shuffle(trial_records)

    jsonl_path = out_dir / "results.jsonl"

    with jsonl_path.open("w", encoding="utf-8") as f:
        for i, (model, problem, trial) in enumerate(trial_records, start=1):
            prompt = make_trial_prompt(problem, rng, trial)

            print(
                f"[{i}/{len(trial_records)}] model={model} problem={problem.id} trial={trial + 1}",
                flush=True,
            )

            started = time.time()
            try:
                raw_response, usage = call_groq_model(
                    client=client,
                    model=model,
                    prompt=prompt,
                    temperature=args.temperature,
                    max_completion_tokens=args.max_completion_tokens,
                    timeout_retries=args.retries,
                    pause_seconds=args.pause_seconds,
                )
                error = None
            except Exception as exc:
                raw_response = ""
                usage = {}
                error = str(exc)

            elapsed = time.time() - started

            if error is None:
                grade = grade_response(problem, raw_response)
            else:
                grade = {
                    "json_score": 0,
                    "exact_score": 0,
                    "total_score": 0,
                    "parsed_alpha": None,
                    "expected_alpha": problem.expected_text,
                    "parseable": False,
                }

            record = {
                "model": model,
                "problem_id": problem.id,
                "problem_title": problem.title,
                "trial": trial + 1,
                "expected_alpha": problem.expected_text,
                "score": grade["total_score"],
                "exact_score": grade["exact_score"],
                "json_score": grade["json_score"],
                "parsed_alpha": grade["parsed_alpha"],
                "parseable": grade["parseable"],
                "elapsed_seconds": round(elapsed, 3),
                "usage": usage,
                "error": error,
                "prompt": prompt,
                "raw_response": raw_response,
                "grading_notes": problem.notes,
            }

            results.append(record)
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()

            if args.pause_seconds > 0:
                time.sleep(args.pause_seconds)

    write_summary(results, out_dir / "summary.csv")
    return results


def write_summary(results: list[dict[str, Any]], path: Path) -> None:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    by_model: dict[str, list[dict[str, Any]]] = {}

    for r in results:
        grouped.setdefault((r["model"], r["problem_id"]), []).append(r)
        by_model.setdefault(r["model"], []).append(r)

    rows: list[dict[str, Any]] = []

    for (model, problem_id), recs in sorted(grouped.items()):
        rows.append({
            "model": model,
            "scope": problem_id,
            "trials": len(recs),
            "exact_correct": sum(r["exact_score"] for r in recs),
            "accuracy": sum(r["exact_score"] for r in recs) / len(recs) if recs else 0,
            "json_compliance": sum(r["json_score"] for r in recs) / len(recs) if recs else 0,
            "avg_elapsed_seconds": sum(r["elapsed_seconds"] for r in recs) / len(recs) if recs else 0,
        })

    for model, recs in sorted(by_model.items()):
        rows.append({
            "model": model,
            "scope": "OVERALL",
            "trials": len(recs),
            "exact_correct": sum(r["exact_score"] for r in recs),
            "accuracy": sum(r["exact_score"] for r in recs) / len(recs) if recs else 0,
            "json_compliance": sum(r["json_score"] for r in recs) / len(recs) if recs else 0,
            "avg_elapsed_seconds": sum(r["elapsed_seconds"] for r in recs) / len(recs) if recs else 0,
        })

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "model",
                "scope",
                "trials",
                "exact_correct",
                "accuracy",
                "json_compliance",
                "avg_elapsed_seconds",
            ],
        )
        writer.writeheader()
        for row in rows:
            row = dict(row)
            row["accuracy"] = round(row["accuracy"], 4)
            row["json_compliance"] = round(row["json_compliance"], 4)
            row["avg_elapsed_seconds"] = round(row["avg_elapsed_seconds"], 3)
            writer.writerow(row)


def print_overall_summary(results: list[dict[str, Any]]) -> None:
    by_model: dict[str, list[dict[str, Any]]] = {}
    for r in results:
        by_model.setdefault(r["model"], []).append(r)

    print("\nOverall scores")
    print("--------------")
    for model, recs in sorted(by_model.items()):
        correct = sum(r["exact_score"] for r in recs)
        total = len(recs)
        accuracy = correct / total if total else 0
        json_ok = sum(r["json_score"] for r in recs) / total if total else 0
        print(f"{model}: {correct}/{total} exact = {accuracy:.1%}; JSON compliance = {json_ok:.1%}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Cobb-Douglas exponent recovery benchmark against multiple Groq models."
    )

    parser.add_argument(
        "--models",
        nargs="+",
        required=True,
        help="Groq model IDs, e.g. llama-3.3-70b-versatile openai/gpt-oss-120b",
    )
    parser.add_argument(
        "--trials-per-problem",
        type=int,
        default=3,
        help="Number of randomized trials per problem per model.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature.",
    )
    parser.add_argument(
        "--max-completion-tokens",
        type=int,
        default=700,
        help="Maximum tokens for each model response.",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="results",
        help="Output directory.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20260510,
        help="Random seed for reproducible prompt variation and ordering.",
    )
    parser.add_argument(
        "--shuffle",
        action="store_true",
        help="Shuffle model/problem/trial order.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=2,
        help="Number of retries after a failed API call.",
    )
    parser.add_argument(
        "--pause-seconds",
        type=float,
        default=0.25,
        help="Pause between API calls; also used as retry backoff base.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not os.environ.get("GROQ_API_KEY"):
        raise SystemExit(
            "Missing GROQ_API_KEY. Set it first, e.g. export GROQ_API_KEY='your_key_here'."
        )

    results = run_benchmark(args)
    print_overall_summary(results)
    print(f"\nWrote detailed results to: {Path(args.out) / 'results.jsonl'}")
    print(f"Wrote summary to: {Path(args.out) / 'summary.csv'}")


if __name__ == "__main__":
    main()
