#!/usr/bin/env python3
"""Batch-run LLM negotiation games: sequential, independent random draws per game.

Each run uses a fresh ``random.Random()`` so alpha and endowment are independent draws.

Examples::

  cd backend && python batch_run_llm_negotiation.py --runs 20
  cd backend && python batch_run_llm_negotiation.py --model=llama-3.3-70b-versatile --runs 10
  cd backend && python batch_run_llm_negotiation.py --model=openai/gpt-oss-20b --model=openai/gpt-oss-120b --runs 5
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_BACKEND_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = _BACKEND_ROOT.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

load_dotenv(_REPO_ROOT / ".env")

from app.mongo_games import MongoGameStore
from run_llm_negotiation import run_single_negotiation


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run multiple Groq negotiation games (--runs per model); independent α/endowment each run.",
    )
    parser.add_argument(
        "--model",
        action="append",
        dest="models",
        metavar="MODEL",
        help="Groq model id (repeat for multiple). Use --model=<id> so slugs with / stay one token. Default: llama-3.3-70b-versatile.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        metavar="N",
        help="Games per model (default: 20).",
    )
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument(
        "--fixed-endowment",
        action="store_true",
        help="Use fixed endowment (5,5) for every game.",
    )
    parser.add_argument(
        "--no-mongo",
        action="store_true",
        help="Do not write to MongoDB (still calls Groq).",
    )
    parser.add_argument(
        "--employer-rule",
        choices=["nash", "lens"],
        default="nash",
        help="Employer counteroffer rule: 'nash' (default) or 'lens' (endowment-lens optimal).",
    )
    args = parser.parse_args()

    models = args.models if args.models else ["llama-3.3-70b-versatile"]
    if args.runs < 1:
        print("--runs must be >= 1", file=sys.stderr)
        sys.exit(2)

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("GROQ_API_KEY is not set (expected in .env at repository root).", file=sys.stderr)
        sys.exit(1)

    store: Optional[MongoGameStore] = None
    if not args.no_mongo:
        store = MongoGameStore()
        store.ping()

    failed = 0
    ok = 0
    try:
        for model in models:
            for i in range(args.runs):
                rng = random.Random()
                label = f"{model} [{i + 1}/{args.runs}]"
                try:
                    doc, session_id, game_id, turns = run_single_negotiation(
                        api_key=api_key,
                        model=model,
                        temperature=args.temperature,
                        fixed_endowment=args.fixed_endowment,
                        rng=rng,
                        recorded_seed=None,
                        employer_rule=args.employer_rule,
                    )
                except (ValueError, RuntimeError) as exc:
                    failed += 1
                    print(f"FAIL {label}: {exc}", file=sys.stderr)
                    continue

                ok += 1
                if store is not None:
                    store.insert_completed_game(doc)
                print(
                    f"OK {label} session_id={session_id} game_id={game_id} "
                    f"resolution={doc['resolution']} turns={turns}"
                )
    finally:
        if store is not None:
            store.close()

    print(f"Done: {ok} succeeded, {failed} failed.", file=sys.stderr)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
