from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


Phase = Literal["setup", "play", "done"]
OfferType = Literal["human", "ai"]
ActionType = Literal["propose", "confirm", "cancel", "reset"]


class Offer(BaseModel):
    xH: float
    yH: float
    type: OfferType
    round: int


class Posterior(BaseModel):
    a: float
    b: float


class NashEstimate(BaseModel):
    xH: float
    yH: float


class HistoryEntry(BaseModel):
    round: int
    human: Offer
    ai: Offer
    alphaHat: float


class GameState(BaseModel):
    alpha: Optional[float] = None
    phase: Phase = "setup"
    round: int = 1
    offers: list[Offer] = Field(default_factory=list)
    pending: Optional[Offer] = None
    msg: str = ""
    posterior: Posterior = Field(default_factory=lambda: Posterior(a=2.0, b=2.0))
    alphaHat: float = 0.5
    agreed: Optional[Offer] = None
    nashEst: Optional[NashEstimate] = None
    history: list[HistoryEntry] = Field(default_factory=list)


class StartGameRequest(BaseModel):
    alpha: float


class ActionRequest(BaseModel):
    type: ActionType
    xH: Optional[float] = None
    yH: Optional[float] = None


class SessionResponse(BaseModel):
    session_id: str
    state: GameState
