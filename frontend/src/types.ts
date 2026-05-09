export type Phase = "setup" | "play" | "done";
export type OfferType = "candidate" | "employer";

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

export interface HistoryEntry {
  round: number;
  candidate: Offer;
  employer: Offer;
  alphaHat: number;
}

export interface GameState {
  alpha: number | null;
  phase: Phase;
  round: number;
  offers: Offer[];
  pending: Offer | null;
  msg: string;
  posterior: Posterior;
  alphaHat: number;
  agreed: Offer | null;
  nashEst: NashEstimate | null;
  history: HistoryEntry[];
}

export interface SessionResponse {
  session_id: string;
  state: GameState;
}
