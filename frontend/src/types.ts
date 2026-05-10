export type Phase = "setup" | "play" | "done";
export type OfferType = "candidate" | "employer";
export type EmployerRule = "nash" | "lens";
export type GameMode = "blind" | "omniscient";
export type AppScreen = "opening" | "game" | "reveal";

export interface Offer {
  xH: number;
  yH: number;
  type: OfferType;
  round: number;
}

export interface Posterior {
  a: number;
  b: number;
}

export interface NashEstimate {
  xH: number;
  yH: number;
}

export interface CurvePoint {
  xH: number;
  yH: number;
}

export interface IndifferenceCurves {
  candidate: CurvePoint[];
  employer: CurvePoint[];
}

export interface HistoryEntry {
  round: number;
  candidate: Offer;
  employer: Offer;
  alphaHat: number;
}

export interface GameState {
  alpha: number | null;
  /** Candidate initial allocation (symmetric p on both goods); set when play starts */
  endowXH: number | null;
  endowYH: number | null;
  phase: Phase;
  round: number;
  offers: Offer[];
  pending: Offer | null;
  msg: string;
  posterior: Posterior;
  alphaHat: number;
  agreed: Offer | null;
  nashEst: NashEstimate | null;
  trueNash: NashEstimate | null;
  indifferenceCurves: IndifferenceCurves | null;
  /** True preferences (alpha): ICs through initial endowment; shown when phase is done */
  endowmentIndifferenceCurves: IndifferenceCurves | null;
  history: HistoryEntry[];
  employerRule: EmployerRule;
}

export interface SessionResponse {
  session_id: string;
  state: GameState;
}
