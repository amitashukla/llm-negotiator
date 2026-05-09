from __future__ import annotations

import math
import random
from typing import Optional

from .models import CurvePoint, GameState, HistoryEntry, IndifferenceCurves, NashEstimate, Offer, Posterior

W = 10.0
H = 10.0
BETA = 0.8
ROUNDS = 5
DELTA = 0.7
EPSILON = 0.08
ACCEPT_RADIUS = 0.3

ENDOW_P_MEAN = 0.5
ENDOW_P_STDEV = 0.05


def sample_initial_endowment(rng: Optional[random.Random] = None) -> tuple[float, float]:
    """Candidate receives p * (W, H) with p ~ N(mu, sigma), clipped to keep allocations interior."""
    r = rng if rng is not None else random
    p = r.gauss(ENDOW_P_MEAN, ENDOW_P_STDEV)
    eps = 1e-3
    p = min(max(p, eps), 1.0 - eps)
    return p * W, p * H


def cd_util(x: float, y: float, a: float) -> float:
    if x <= 0 or y <= 0:
        return 0.0
    return (x**a) * (y ** (1 - a))


def employer_util(xC: float, yC: float) -> float:
    return cd_util(W - xC, H - yC, BETA)


def candidate_util(xC: float, yC: float, alpha: float) -> float:
    return cd_util(xC, yC, alpha)


def candidate_ic_y(xC: float, alpha: float, utility: float) -> Optional[float]:
    """Indifference curve y(x) for U = x^alpha * y^(1-alpha). Uses logs when alpha ≈ 1 to avoid overflow."""
    if xC <= 0 or xC >= W:
        return None
    if not (0 < alpha < 1) or utility <= 0:
        return None
    denom = 1.0 - alpha
    if denom < 1e-15:
        return None
    log_u = math.log(utility)
    log_x = math.log(xC)
    log_y = (log_u - alpha * log_x) / denom
    if not math.isfinite(log_y):
        return None
    log_hi = math.log(H)
    log_lo = math.log(1e-12)
    if log_y > log_hi or log_y < log_lo:
        return None
    try:
        y = math.exp(log_y)
    except OverflowError:
        return None
    if not math.isfinite(y) or y <= 0:
        return None
    return y


def employer_ic_y(xC: float, utility: float) -> Optional[float]:
    if xC <= 0 or xC >= W:
        return None
    employer_x = W - xC
    base = employer_x**BETA
    if base == 0:
        return None
    employer_y = (utility / base) ** (1 / (1 - BETA))
    return H - employer_y


def build_indifference_curves(xH: float, yH: float, alpha: float) -> IndifferenceCurves:
    candidate_u = candidate_util(xH, yH, alpha)
    employer_u = employer_util(xH, yH)
    candidate_points: list[CurvePoint] = []
    employer_points: list[CurvePoint] = []
    samples = 240

    for i in range(1, samples):
        xC = (i / samples) * (W - 0.02) + 0.01
        y_candidate = candidate_ic_y(xC, alpha, candidate_u)
        if y_candidate is not None and 0 <= y_candidate <= H:
            candidate_points.append(CurvePoint(xH=xC, yH=y_candidate))

        y_employer = employer_ic_y(xC, employer_u)
        if y_employer is not None and 0 <= y_employer <= H:
            employer_points.append(CurvePoint(xH=xC, yH=y_employer))

    return IndifferenceCurves(candidate=candidate_points, employer=employer_points)


def best_employer_on_ic(alpha_hat: float, candidate_u_target: float) -> Optional[tuple[float, float]]:
    best_employer_u = -math.inf
    best_x = None
    best_y = None
    for i in range(1, 400):
        xC = (i / 400) * (W - 0.01) + 0.005
        yC = candidate_ic_y(xC, alpha_hat, candidate_u_target)
        if yC is None or yC <= 0 or yC >= H:
            continue
        utility = employer_util(xC, yC)
        if utility > best_employer_u:
            best_employer_u = utility
            best_x = xC
            best_y = yC
    if best_x is None or best_y is None:
        return None
    return best_x, best_y


def update_posterior(prior: Posterior, offers: list[Offer]) -> Posterior:
    a = prior.a
    b = prior.b
    for offer in offers:
        if offer.type != "candidate":
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
            v = candidate_util(xH, yH, alpha) * employer_util(xH, yH)
            if v > best:
                best = v
                bx = xH
                by = yH
    return NashEstimate(xH=bx, yH=by)


def employer_counteroffer(round_num: int, offers: list[Offer], prior: Posterior) -> tuple[Offer, Posterior, float, NashEstimate]:
    post = update_posterior(prior, offers)
    alpha_hat = posterior_mean(post)
    nb = nash_point(alpha_hat)
    u_nash = candidate_util(nb.xH, nb.yH, alpha_hat)
    remaining = ROUNDS - round_num
    u_target = u_nash * (1 - EPSILON * (DELTA**remaining))
    result = best_employer_on_ic(alpha_hat, u_target)

    if result is None:
        employer_offer = Offer(xH=nb.xH, yH=nb.yH, type="employer", round=round_num)
    else:
        employer_offer = Offer(xH=result[0], yH=result[1], type="employer", round=round_num)
    return employer_offer, post, alpha_hat, nb


def _finalize_done_state(state: GameState) -> None:
    """Recompute employer belief from all candidate offers; Nash guess; true ICs through endowment."""
    post = update_posterior(Posterior(a=2.0, b=2.0), state.offers)
    state.posterior = post
    state.alphaHat = posterior_mean(post)
    if state.alpha is not None:
        state.nashEst = nash_point(state.alphaHat)
        if state.endowXH is not None and state.endowYH is not None:
            state.endowmentIndifferenceCurves = build_indifference_curves(state.endowXH, state.endowYH, state.alpha)
        else:
            state.endowmentIndifferenceCurves = None
    else:
        state.nashEst = None
        state.endowmentIndifferenceCurves = None


def make_default_state() -> GameState:
    return GameState()


def last_employer_offer(state: GameState) -> Optional[Offer]:
    """Most recent employer offer in play, if any."""
    return _last_offer(state.offers, "employer")


def start_game(alpha: float, endowment: Optional[tuple[float, float]] = None) -> GameState:
    if alpha <= 0 or alpha >= 1:
        raise ValueError("Alpha must be between 0 and 1 (exclusive).")
    if endowment is None:
        ex, ey = sample_initial_endowment()
    else:
        ex, ey = endowment
    return GameState(
        alpha=alpha,
        endowXH=ex,
        endowYH=ey,
        phase="play",
        round=1,
        offers=[],
        pending=None,
        msg="Round 1 of 5 - click the box to propose your allocation. Your origin is bottom-left.",
        posterior=Posterior(a=2.0, b=2.0),
        alphaHat=0.5,
        agreed=None,
        nashEst=None,
        trueNash=None,
        indifferenceCurves=None,
        endowmentIndifferenceCurves=None,
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
    state.pending = Offer(xH=xH, yH=yH, type="candidate", round=state.round)
    candidate_u = candidate_util(xH, yH, state.alpha) if state.alpha is not None else 0.0
    employer_u = employer_util(xH, yH)
    state.msg = (
        f"Proposing: Candidate ({xH:.2f}, {yH:.2f}) U = {candidate_u:.3f}, "
        f"Employer ({W - xH:.2f}, {H - yH:.2f}) U = {employer_u:.3f}. Confirm?"
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

    candidate_offer = Offer(xH=state.pending.xH, yH=state.pending.yH, type="candidate", round=state.round)
    new_offers = [*state.offers, candidate_offer]
    last_employer_offer = _last_offer(state.offers, "employer")

    if last_employer_offer:
        dist = math.hypot(state.pending.xH - last_employer_offer.xH, state.pending.yH - last_employer_offer.yH)
        if dist < ACCEPT_RADIUS:
            state.agreed = last_employer_offer
            state.phase = "done"
            state.offers = new_offers
            state.pending = None
            state.trueNash = nash_point(state.alpha) if state.alpha is not None else None
            state.indifferenceCurves = (
                build_indifference_curves(last_employer_offer.xH, last_employer_offer.yH, state.alpha)
                if state.alpha is not None
                else None
            )
            state.msg = (
                f"Deal! Final: Candidate ({last_employer_offer.xH:.2f}, {last_employer_offer.yH:.2f}), "
                f"Employer ({W - last_employer_offer.xH:.2f}, {H - last_employer_offer.yH:.2f})."
            )
            _finalize_done_state(state)
            return state

    if state.round >= ROUNDS:
        state.offers = new_offers
        state.pending = None
        state.phase = "done"
        state.trueNash = nash_point(state.alpha) if state.alpha is not None else None
        state.indifferenceCurves = None
        state.msg = "5 rounds complete with no agreement. Both sides receive 0."
        _finalize_done_state(state)
        return state

    employer_offer, new_post, a_hat, nb = employer_counteroffer(state.round, new_offers, Posterior(a=2.0, b=2.0))
    all_offers = [*new_offers, employer_offer]

    state.posterior = new_post
    state.alphaHat = a_hat
    state.nashEst = nb
    state.offers = all_offers
    state.history.append(
        HistoryEntry(round=state.round, candidate=candidate_offer, employer=employer_offer, alphaHat=a_hat)
    )
    state.round += 1
    state.pending = None
    state.msg = (
        f"Round {state.round - 1} done. Employer inferred a_hat={a_hat:.2f}, "
        f"countered ({employer_offer.xH:.2f}, {employer_offer.yH:.2f}) for Candidate. "
        f"Round {state.round} of 5 - click to offer, or click near the Employer's counter to accept."
    )
    return state
