from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from .game_engine import ROUNDS, W, H, BETA, candidate_util, employer_util
from .models import GameState, Offer


def _last_offer(offers: list[Offer], offer_type: str) -> Optional[Offer]:
    for offer in reversed(offers):
        if offer.type == offer_type:
            return offer
    return None


def _build_rounds(state: GameState) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for h in state.history:
        rows.append(
            {
                "round": h.round,
                "candidate_offer": {"x": h.candidate.xH, "y": h.candidate.yH},
                "employer_counter": {"x": h.employer.xH, "y": h.employer.yH},
                "alpha_hat_after_round": h.alphaHat,
            }
        )

    if state.phase != "done":
        return rows

    agreed = state.agreed
    last_c = _last_offer(state.offers, "candidate")
    if last_c is None:
        return rows

    r = last_c.round
    if agreed is not None:
        if rows and rows[-1]["round"] == r:
            return rows
        rows.append(
            {
                "round": r,
                "candidate_offer": {"x": last_c.xH, "y": last_c.yH},
                "employer_counter": {"x": agreed.xH, "y": agreed.yH},
                "alpha_hat_after_round": state.alphaHat,
            }
        )
        return rows

    # Failure: last round may have candidate offer but no employer counter for that round.
    last_e = _last_offer(state.offers, "employer")
    if rows and rows[-1]["round"] == r:
        return rows
    emp: Optional[dict[str, float]] = None
    if last_e is not None and last_e.round == r:
        emp = {"x": last_e.xH, "y": last_e.yH}
    rows.append(
        {
            "round": r,
            "candidate_offer": {"x": last_c.xH, "y": last_c.yH},
            "employer_counter": emp,
            "alpha_hat_after_round": state.alphaHat,
        }
    )
    return rows


def build_completed_game_document(session_id: str, state: GameState) -> dict[str, Any]:
    """Serialize a terminal game state for MongoDB analytics."""
    if state.phase != "done" or state.alpha is None:
        raise ValueError("Game must be finished with a known alpha.")

    now = datetime.now(timezone.utc)
    agreed = state.agreed
    resolution = "agreement" if agreed is not None else "failure"

    final_allocation: Optional[dict[str, float]] = None
    u_c_final = 0.0
    u_e_final = 0.0
    if agreed is not None:
        final_allocation = {"x": agreed.xH, "y": agreed.yH}
        u_c_final = candidate_util(agreed.xH, agreed.yH, state.alpha)
        u_e_final = employer_util(agreed.xH, agreed.yH)

    tn = state.trueNash
    u_c_nash = 0.0
    u_e_nash = 0.0
    product_nash = 0.0
    true_nash_doc: Optional[dict[str, float]] = None
    if tn is not None:
        true_nash_doc = {"x": tn.xH, "y": tn.yH}
        u_c_nash = candidate_util(tn.xH, tn.yH, state.alpha)
        u_e_nash = employer_util(tn.xH, tn.yH)
        product_nash = u_c_nash * u_e_nash

    nb = state.nashEst
    employer_guess: Optional[dict[str, float]] = None
    if nb is not None:
        employer_guess = {"x": nb.xH, "y": nb.yH}

    if resolution == "agreement":
        candidate_utility_ratio = (u_c_final / u_c_nash) if u_c_nash > 0 else 0.0
        denom_p = product_nash
        product_ratio = ((u_c_final * u_e_final) / denom_p) if denom_p > 0 else 0.0
    else:
        candidate_utility_ratio = 0.0
        product_ratio = 0.0

    rounds_completed = state.round if agreed is not None else ROUNDS

    return {
        "schema_version": 1,
        "game_id": str(uuid.uuid4()),
        "session_id": session_id,
        "created_at": now,
        "resolution": resolution,
        "final_allocation": final_allocation,
        "true_nash": true_nash_doc,
        "employer_nash_guess": employer_guess,
        "rounds_completed": rounds_completed,
        "max_rounds": ROUNDS,
        "rounds": _build_rounds(state),
        "utilities": {"candidate": u_c_final, "employer": u_e_final},
        "nash_reference": {
            "candidate_at_true_nash": u_c_nash,
            "employer_at_true_nash": u_e_nash,
            "product_at_true_nash": product_nash,
        },
        "candidate_utility_ratio": candidate_utility_ratio,
        "product_ratio": product_ratio,
        "experiment": {
            "alpha": state.alpha,
            "endowment": {"x": state.endowXH, "y": state.endowYH},
            "engine_constants": {"W": W, "H": H, "BETA": BETA, "ROUNDS": ROUNDS},
        },
    }
