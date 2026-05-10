import type { GameState } from "../types";

export function validateApiResponse(state: GameState, stage: "start" | "play" | "done"): string[] {
  const missing: string[] = [];

  if (state.posterior == null) missing.push("posterior (employer belief distribution)");
  if (state.alphaHat == null) missing.push("alpha_hat (employer's inferred alpha)");

  if (stage === "play" || stage === "done") {
    if (state.endowXH == null || state.endowYH == null)
      missing.push("endowment coordinates (endowXH / endowYH)");
    if (state.alpha == null) missing.push("true_alpha (candidate's actual alpha)");
    if (state.nashEst == null) missing.push("employer_nash_guess");
  }

  if (stage === "done") {
    if (state.trueNash == null) missing.push("true_nash");
  }

  return missing;
}
