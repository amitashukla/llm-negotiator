from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


Phase = Literal["setup", "play", "done"]
OfferType = Literal["candidate", "employer"]
ActionType = Literal["propose", "confirm", "cancel", "reset"]
EmployerRule = Literal["nash", "lens"]
UiMode = Literal["blind", "omniscient"]


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


class CurvePoint(BaseModel):
    xH: float
    yH: float


class IndifferenceCurves(BaseModel):
    candidate: list[CurvePoint]
    employer: list[CurvePoint]


class HistoryEntry(BaseModel):
    round: int
    candidate: Offer
    employer: Offer
    alphaHat: float


class GameState(BaseModel):
    alpha: Optional[float] = None
    endowXH: Optional[float] = Field(default=None, description="Candidate initial x (bottom-left origin); p*(W,H) share.")
    endowYH: Optional[float] = Field(default=None, description="Candidate initial y; same p as endowXH for both goods.")
    phase: Phase = "setup"
    round: int = 1
    offers: list[Offer] = Field(default_factory=list)
    pending: Optional[Offer] = None
    msg: str = ""
    posterior: Posterior = Field(default_factory=lambda: Posterior(a=2.0, b=2.0))
    alphaHat: float = 0.5
    agreed: Optional[Offer] = None
    nashEst: Optional[NashEstimate] = None
    trueNash: Optional[NashEstimate] = None
    indifferenceCurves: Optional[IndifferenceCurves] = None
    endowmentIndifferenceCurves: Optional[IndifferenceCurves] = None
    history: list[HistoryEntry] = Field(default_factory=list)
    employerRule: EmployerRule = "nash"
    uiMode: Optional[UiMode] = None


class StartGameRequest(BaseModel):
    alpha: float
    employer_rule: EmployerRule = "nash"
    ui_mode: Optional[UiMode] = None


class ActionRequest(BaseModel):
    type: ActionType
    xH: Optional[float] = None
    yH: Optional[float] = None


class SessionResponse(BaseModel):
    session_id: str
    state: GameState
