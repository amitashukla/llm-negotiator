#!/usr/bin/env python3
"""Run one negotiation game via Groq (OpenAI-compatible API) and archive to MongoDB.

Usage (from repo root or backend):

  cd backend && python run_llm_negotiation.py --model=llama-3.3-70b-versatile

Requires GROQ_API_KEY in .env at repository root. Optional MONGODB_URI / MONGODB_DB.

Groq ``model`` slugs for ``--model=…`` (use equals form so values with ``/`` are one
argument; availability changes — see https://console.groq.com/docs/models):

  python run_llm_negotiation.py --model=llama-3.3-70b-versatile
  python run_llm_negotiation.py --model=llama-3.1-8b-instant
  python run_llm_negotiation.py --model=openai/gpt-oss-120b
  python run_llm_negotiation.py --model=openai/gpt-oss-20b
  python run_llm_negotiation.py --model=groq/compound
  python run_llm_negotiation.py --model=groq/compound-mini
  python run_llm_negotiation.py --model=meta-llama/llama-4-scout-17b-16e-instruct
  python run_llm_negotiation.py --model=qwen/qwen3-32b
  python run_llm_negotiation.py --model=openai/gpt-oss-safeguard-20b
  python run_llm_negotiation.py --model=gemma2-9b-it"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import uuid
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_REPO_ROOT / ".env")

_BACKEND_ROOT = Path(__file__).resolve().parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from openai import OpenAI

from app.game_engine import (
    H,
    ROUNDS,
    W,
    apply_confirm,
    apply_propose,
    last_employer_offer,
    sample_initial_endowment,
    start_game,
)
from app.game_record import build_completed_game_document
from app.models import EmployerRule, GameState
from app.mongo_games import MongoGameStore

GROQ_BASE_URL = "https://api.groq.com/openai/v1"

SYSTEM_PROMPT = """You are the Candidate in a bilateral negotiation over two goods (X and Y) between you and an Employer.
- Total quantities: W={W}, H={H}. You choose a split (x, y) for yourself; the Employer receives (W-x, H-y).
- Your utility is Cobb-Douglas: U_c = x^alpha * y^(1-alpha). You know your alpha.
- The Employer uses the same functional form on their bundle with some exponent beta in (0,1) that you do NOT know.
- There are exactly {ROUNDS} rounds. Each round you send one JSON message: either a new proposal or an acceptance of the Employer's latest counter-offer.
- If you accept, your allocation is set to the Employer's last offered (x, y) for you (you cannot modify it).

Respond with a single JSON object only (no markdown fences, no commentary):
- To propose: {{"intent": "propose", "x": <float>, "y": <float>}}
- To accept: {{"intent": "accept"}}

Feasible coordinates: 0 <= x <= W and 0 <= y <= H. On round 1 there is no employer offer yet; you must propose."""


def slug_model_name(model: str) -> str:
    s = model.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:80] if s else "model"


def sample_alpha(rng: random.Random) -> float:
    eps = 1e-3
    a = rng.gauss(0.5, 0.2)
    return min(max(a, eps), 1.0 - eps)


def parse_strict_json_object(content: str) -> dict[str, Any]:
    s = content.strip()
    if s.startswith("```"):
        lines = s.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    try:
        out = json.loads(s)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON from model: {exc}\n---\n{content}\n---") from exc
    if not isinstance(out, dict):
        raise ValueError("Model response must be a JSON object")
    return out


def build_user_message(state: GameState) -> str:
    lines = [
        f"Your alpha = {state.alpha}",
        f"Your initial endowment (reference): ({state.endowXH}, {state.endowYH})",
        f"Current round: {state.round} of {ROUNDS}",
        "",
        "History (your proposal, then employer counter; coordinates are your x,y as Candidate):",
    ]
    for h in state.history:
        lines.append(
            f"  Round {h.round}: you proposed ({h.candidate.xH:.4f}, {h.candidate.yH:.4f}); "
            f"employer countered ({h.employer.xH:.4f}, {h.employer.yH:.4f})."
        )
    if not state.history:
        lines.append("  (none yet — this is your first move.)")

    emp = last_employer_offer(state)
    lines.append("")
    if emp is None:
        lines.append("There is no employer counter yet. You must respond with intent \"propose\".")
    else:
        lines.append(
            f"Employer's latest counter (your coordinates): ({emp.xH:.4f}, {emp.yH:.4f}). "
            'Respond with intent \"accept\" to take it, or \"propose\" with new x,y.'
        )
    return "\n".join(lines)


def run_turn(
    client: OpenAI,
    model: str,
    temperature: float,
    state: GameState,
    messages: list[dict[str, str]],
) -> dict[str, Any]:
    messages = [*messages, {"role": "user", "content": build_user_message(state)}]
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    choice = completion.choices[0].message.content
    if not choice:
        raise ValueError("Empty completion from Groq")
    parsed = parse_strict_json_object(choice)
    assistant_msg = {"role": "assistant", "content": choice.strip()}
    return {"parsed": parsed, "messages": [*messages, assistant_msg]}


def apply_llm_action(state: GameState, parsed: dict[str, Any]) -> GameState:
    intent = parsed.get("intent")
    if intent not in ("propose", "accept"):
        raise ValueError(f'intent must be "propose" or "accept", got {intent!r}')

    emp = last_employer_offer(state)

    if intent == "accept":
        if emp is None:
            raise ValueError('Cannot use intent "accept" before any employer counter exists')
        state = apply_propose(state, emp.xH, emp.yH)
        state = apply_confirm(state)
        return state

    if parsed.get("x") is None or parsed.get("y") is None:
        raise ValueError('intent "propose" requires numeric "x" and "y"')
    x = float(parsed["x"])
    y = float(parsed["y"])
    if not (0 <= x <= W and 0 <= y <= H):
        raise ValueError(f"Coordinates out of bounds: ({x}, {y}) must lie in [0,{W}] x [0,{H}]")

    state = apply_propose(state, x, y)
    if state.pending is None:
        raise ValueError("apply_propose rejected coordinates (unexpected)")
    state = apply_confirm(state)
    return state


def run_single_negotiation(
    *,
    api_key: str,
    model: str,
    temperature: float,
    fixed_endowment: bool,
    rng: random.Random,
    recorded_seed: Optional[int] = None,
    employer_rule: EmployerRule = "nash",
) -> tuple[dict[str, Any], str, str, int]:
    """Play one game via Groq and build the MongoDB document (does not insert).

    Use a fresh ``random.Random()`` per call in batch mode for independent α and endowment draws.
    """
    alpha = sample_alpha(rng)
    endowment: tuple[float, float] = (
        (5.0, 5.0) if fixed_endowment else sample_initial_endowment(rng)
    )

    state = start_game(alpha, endowment=endowment, employer_rule=employer_rule)
    session_id = str(uuid.uuid4())
    slug = slug_model_name(model)
    game_id = f"{slug}_{uuid.uuid4()}"

    client = OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)

    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT.format(W=W, H=H, ROUNDS=ROUNDS)},
    ]

    turn = 0
    while state.phase == "play":
        turn += 1
        if turn > 40:
            raise RuntimeError("Exceeded maximum turns without terminal state.")
        result = run_turn(client, model, temperature, state, messages)
        messages = result["messages"]
        state = apply_llm_action(state, result["parsed"])

    llm_run: dict[str, Any] = {
        "provider": "groq",
        "model": model,
        "model_slug": slug,
        "temperature": temperature,
        "turns": turn,
    }
    if recorded_seed is not None:
        llm_run["seed"] = recorded_seed

    doc = build_completed_game_document(
        session_id,
        state,
        game_id=game_id,
        llm_run=llm_run,
    )
    return doc, session_id, game_id, turn


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LLM negotiation via Groq and save to MongoDB.")
    parser.add_argument(
        "--model",
        default="llama-3.3-70b-versatile",
        help="Groq model id (e.g. --model=openai/gpt-oss-120b; use = so slugs with / parse as one arg)",
    )
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument(
        "--fixed-endowment",
        action="store_true",
        help="Use fixed endowment (5,5) instead of sampling like the web game.",
    )
    parser.add_argument("--seed", type=int, default=None, help="RNG seed for alpha and optional sampling.")
    parser.add_argument(
        "--no-mongo",
        action="store_true",
        help="Simulate only: do not write to MongoDB.",
    )
    parser.add_argument(
        "--employer-rule",
        choices=["nash", "lens"],
        default="nash",
        help="Employer counteroffer rule: 'nash' (default) or 'lens' (endowment-lens optimal).",
    )
    args = parser.parse_args()

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("GROQ_API_KEY is not set (expected in .env at repository root).", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(args.seed) if args.seed is not None else random.Random()

    try:
        doc, session_id, game_id, _turns = run_single_negotiation(
            api_key=api_key,
            model=args.model,
            temperature=args.temperature,
            fixed_endowment=args.fixed_endowment,
            rng=rng,
            recorded_seed=args.seed,
            employer_rule=args.employer_rule,
        )
    except (ValueError, RuntimeError) as exc:
        print(f"Hard fail: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.no_mongo:
        print(json.dumps(doc, default=str, indent=2))
        print(f"session_id={session_id} game_id={game_id}", file=sys.stderr)
        return

    store = MongoGameStore()
    try:
        store.insert_completed_game(doc)
        store.ping()
    finally:
        store.close()

    print(f"Saved session_id={session_id} game_id={game_id} resolution={doc['resolution']}")


if __name__ == "__main__":
    main()
