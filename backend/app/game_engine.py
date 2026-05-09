from __future__ import annotations

import math
from typing import Optional

from .models import GameState, HistoryEntry, NashEstimate, Offer, Posterior

W = 10.0
H = 10.0
BETA = 0.6
ROUNDS = 5
DELTA = 0.7
EPSILON = 0.08
ACCEPT_RADIUS = 0.3


def cd_util(x: float, y: float, a: float) -> float:
    if x <= 0 or y <= 0:
        return 0.0
    return (x**a) * (y ** (1 - a))


def ai_util(xH: float, yH: float) -> float:
    return cd_util(W - xH, H - yH, BETA)


def human_util(xH: float, yH: float, a: float) -> float:
    return cd_util(xH, yH, a)


def human_ic_y(xH: float, alpha: float, u: float) -> Optional[float]:
    if xH <= 0 or xH >= W:
        return None
    base = xH**alpha
    if base == 0:
        return None
    return (u / base) ** (1 / (1 - alpha))


def best_ai_on_ic(alpha_hat: float, u_target: float) -> Optional[tuple[float, float]]:
    best_ai_u = -math.inf
    best_x = None
    best_y = None
    for i in range(1, 400):
        xH = (i / 400) * (W - 0.01) + 0.005
        yH = human_ic_y(xH, alpha_hat, u_target)
        if yH is None or yH <= 0 or yH >= H:
            continue
        u = ai_util(xH, yH)
        if u > best_ai_u:
            best_ai_u = u
            best_x = xH
            best_y = yH
    if best_x is None or best_y is None:
        return None
    return best_x, best_y


def update_posterior(prior: Posterior, offers: list[Offer]) -> Posterior:
    a = prior.a
    b = prior.b
    for offer in offers:
        if offer.type != "human":
            continue
        sig = (offer.xH / W) / ((offer.xH / W) + (offer.yH / H))
        a += 3 * sig
        b += 3 * (1 - sig)
    return Posterior(a=a, b=b)


def posterior_mean(post: Posterior) -> float:
    return post.a / (post.a + post.b)


def nash_point(alpha: float) -> NashEstimate:
    best = -math.inf
    bx = 5.0
    by = 5.0
    for i in range(1, 100):
        for j in range(1, 100):
            xH = (i / 100) * (W - 0.1) + 0.05
            yH = (j / 100) * (H - 0.1) + 0.05
            v = human_util(xH, yH, alpha) * ai_util(xH, yH)
            if v > best:
                best = v
                bx = xH
                by = yH
    return NashEstimate(xH=bx, yH=by)


def ai_counteroffer(round_num: int, offers: list[Offer], prior: Posterior) -> tuple[Offer, Posterior, float, NashEstimate]:
    post = update_posterior(prior, offers)
    alpha_hat = posterior_mean(post)
    nb = nash_point(alpha_hat)
    u_nash = human_util(nb.xH, nb.yH, alpha_hat)
    remaining = ROUNDS - round_num
    u_target = u_nash * (1 - EPSILON * (DELTA**remaining))
    result = best_ai_on_ic(alpha_hat, u_target)

    if result is None:
        ai_offer = Offer(xH=nb.xH, yH=nb.yH, type="ai", round=round_num)
    else:
        ai_offer = Offer(xH=result[0], yH=result[1], type="ai", round=round_num)
    return ai_offer, post, alpha_hat, nb


def make_default_state() -> GameState:
    return GameState()


def start_game(alpha: float) -> GameState:
    if alpha <= 0 or alpha >= 1:
        raise ValueError("Alpha must be between 0 and 1 (exclusive).")
    return GameState(
        alpha=alpha,
        phase="play",
        round=1,
        offers=[],
        pending=None,
        msg="Round 1 of 5 - click the box to propose your allocation. Your origin is bottom-left.",
        posterior=Posterior(a=2.0, b=2.0),
        alphaHat=0.5,
        agreed=None,
        nashEst=None,
        history=[],
    )


def _last_offer(offers: list[Offer], offer_type: str) -> Optional[Offer]:
    for offer in reversed(offers):
        if offer.type == offer_type:
            return offer
    return None


def apply_propose(state: GameState, xH: float, yH: float) -> GameState:
    if state.phase != "play":
        return state
    if xH < 0 or xH > W or yH < 0 or yH > H:
        return state
    state.pending = Offer(xH=xH, yH=yH, type="human", round=state.round)
    state.msg = (
        f"Proposing: you ({xH:.2f}, {yH:.2f}), AI ({W - xH:.2f}, {H - yH:.2f}). Confirm?"
    )
    return state


def apply_cancel(state: GameState) -> GameState:
    if state.phase != "play":
        return state
    state.pending = None
    state.msg = f"Round {state.round} - click to propose your allocation."
    return state


def apply_confirm(state: GameState) -> GameState:
    if state.phase != "play" or state.pending is None:
        return state

    human_offer = Offer(xH=state.pending.xH, yH=state.pending.yH, type="human", round=state.round)
    new_offers = [*state.offers, human_offer]
    last_ai_offer = _last_offer(state.offers, "ai")

    if last_ai_offer:
        dist = math.hypot(state.pending.xH - last_ai_offer.xH, state.pending.yH - last_ai_offer.yH)
        if dist < ACCEPT_RADIUS:
            state.agreed = last_ai_offer
            state.phase = "done"
            state.offers = new_offers
            state.pending = None
            state.msg = (
                f"Deal! Final: you ({last_ai_offer.xH:.2f}, {last_ai_offer.yH:.2f}), "
                f"AI ({W - last_ai_offer.xH:.2f}, {H - last_ai_offer.yH:.2f})."
            )
            return state

    if state.round >= ROUNDS:
        state.offers = new_offers
        state.pending = None
        state.phase = "done"
        state.msg = "5 rounds complete with no agreement. Both sides receive 0."
        return state

    ai_offer, new_post, a_hat, nb = ai_counteroffer(state.round, new_offers, Posterior(a=2.0, b=2.0))
    all_offers = [*new_offers, ai_offer]

    state.posterior = new_post
    state.alphaHat = a_hat
    state.nashEst = nb
    state.offers = all_offers
    state.history.append(
        HistoryEntry(round=state.round, human=human_offer, ai=ai_offer, alphaHat=a_hat)
    )
    state.round += 1
    state.pending = None
    state.msg = (
        f"Round {state.round - 1} done. AI inferred a_hat={a_hat:.2f}, "
        f"countered ({ai_offer.xH:.2f}, {ai_offer.yH:.2f}) for you. "
        f"Round {state.round} of 5 - click to offer, or click near the AI's counter to accept."
    )
    return state
