import type { GameMode, GameState } from "../types";
import { offerUtilities, ROUNDS } from "../utils/curves";
import EdgeworthChart from "./EdgeworthChart";
import ModeBadge from "./ModeBadge";
import RoundPips from "./RoundPips";
import EmployerBeliefPanel from "./EmployerBeliefPanel";
import OfferHistory from "./OfferHistory";
import Legend from "./Legend";
import ApiWarningBanner from "./ApiWarningBanner";

interface GameScreenProps {
  mode: GameMode;
  gameState: GameState;
  pendingPoint: { xH: number; yH: number } | null;
  actionLoading: boolean;
  apiWarnings: string[];
  onDismissWarning: () => void;
  onChartClick: (x: number, y: number) => void;
}

export default function GameScreen({
  mode,
  gameState,
  pendingPoint,
  actionLoading,
  apiWarnings,
  onDismissWarning,
  onChartClick,
}: GameScreenProps) {
  const isPlayerTurn = gameState.phase === "play" && !actionLoading;
  const offers = gameState.offers ?? [];
  const history = gameState.history ?? [];
  const offersRemaining = ROUNDS - history.length;

  const lastCandidateOffer = offers.filter((o) => o.type === "candidate").slice(-1)[0];
  const lastEmployerOffer = offers.filter((o) => o.type === "employer").slice(-1)[0];

  const alpha = gameState.alpha;
  const lastCandidateVals =
    lastCandidateOffer && alpha != null
      ? offerUtilities(lastCandidateOffer.xH, lastCandidateOffer.yH, alpha)
      : null;
  const lastEmployerVals =
    lastEmployerOffer && alpha != null
      ? offerUtilities(lastEmployerOffer.xH, lastEmployerOffer.yH, alpha)
      : null;

  return (
    <div style={{ padding: "1.25rem 1rem", color: "#1f2937", maxWidth: 1100, margin: "0 auto" }}>
      {/* API warnings */}
      {apiWarnings.length > 0 && (
        <ApiWarningBanner warnings={apiWarnings} onDismiss={onDismissWarning} />
      )}

      {/* Top bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 16,
          marginBottom: "1.25rem",
          flexWrap: "wrap",
        }}
      >
        <div style={{ flex: 1 }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 2px", color: "#111827" }}>
            Edgeworth Box Bargaining
          </h2>
          <p style={{ fontSize: 12, color: "#9ca3af", margin: 0 }}>
            {isPlayerTurn
              ? "Click the chart to place your counteroffer"
              : actionLoading
              ? "Processing…"
              : ""}
          </p>
        </div>
        <RoundPips
          round={gameState.round}
          historyLength={history.length}
          phase={gameState.phase}
        />
        <ModeBadge mode={mode} />
      </div>

      {/* Two-column layout */}
      <div style={{ display: "flex", gap: "1.5rem", alignItems: "flex-start", flexWrap: "wrap" }}>
        {/* Chart (~65%) */}
        <div style={{ flex: "0 0 auto" }}>
          <EdgeworthChart
            mode={mode}
            offers={offers}
            pendingPoint={pendingPoint}
            endowment={{
              xH: gameState.endowXH ?? 5,
              yH: gameState.endowYH ?? 5,
            }}
            alpha={gameState.alpha}
            alphaHat={gameState.alphaHat}
            agreedOffer={gameState.agreed}
            trueNash={gameState.trueNash}
            employerNash={gameState.nashEst}
            isPlayerTurn={isPlayerTurn}
            employerRule={gameState.employerRule}
            onChartClick={onChartClick}
          />
        </div>

        {/* Sidebar (~35%) */}
        <div
          style={{
            flex: 1,
            minWidth: 220,
            display: "flex",
            flexDirection: "column",
            gap: 10,
          }}
        >
          {/* Round status */}
          <div
            style={{
              background: "#fff",
              border: "1px solid #e5e7eb",
              borderLeft: "3px solid #1D9E75",
              borderRadius: 10,
              padding: "0.75rem 1rem",
            }}
          >
            <p style={{ margin: 0, fontSize: 13, fontWeight: 600, color: "#374151" }}>
              Round {gameState.round} of {ROUNDS}
            </p>
            <p style={{ margin: "2px 0 0", fontSize: 12, color: "#6b7280" }}>
              {actionLoading
                ? "Processing…"
                : isPlayerTurn
                ? "Your turn — click the chart"
                : "Awaiting employer response"}
            </p>
          </div>

          {/* Employer belief (Omniscient only) */}
          {mode === "omniscient" && (
            <EmployerBeliefPanel
              posterior={gameState.posterior}
              alphaHat={gameState.alphaHat}
              trueAlpha={gameState.alpha}
              nashGuess={gameState.nashEst}
            />
          )}

          {/* Your utility */}
          {(lastCandidateVals || lastEmployerVals) && (
            <div
              style={{
                background: "#fff",
                border: "1px solid #e5e7eb",
                borderRadius: 10,
                padding: "0.875rem 1rem",
              }}
            >
              <p style={{ margin: "0 0 6px", fontSize: 13, fontWeight: 600, color: "#374151" }}>
                Your utility
              </p>
              {lastCandidateVals && lastCandidateOffer && (
                <p style={{ margin: "0 0 3px", fontSize: 12, color: "#6b7280" }}>
                  At your last offer (C{lastCandidateOffer.round}):{" "}
                  <strong>{lastCandidateVals.candidateU.toFixed(3)}</strong>
                </p>
              )}
              {lastEmployerVals && lastEmployerOffer && (
                <p style={{ margin: 0, fontSize: 12, color: "#6b7280" }}>
                  At employer&apos;s last offer (E{lastEmployerOffer.round}):{" "}
                  <strong>{lastEmployerVals.candidateU.toFixed(3)}</strong>
                </p>
              )}
            </div>
          )}

          {/* Lens acceptance rule hint */}
          {gameState.employerRule === "lens" && (
            <div
              style={{
                background: "#f0fdf4",
                border: "1px solid #bbf7d0",
                borderLeft: "3px solid #1D9E75",
                borderRadius: 10,
                padding: "0.75rem 1rem",
              }}
            >
              <p style={{ margin: "0 0 3px", fontSize: 12, fontWeight: 600, color: "#15803d" }}>
                Employer auto-accepts
              </p>
              <p style={{ margin: 0, fontSize: 11, color: "#166534" }}>
                {mode === "omniscient"
                  ? "Employer will accept any offer within the dashed teal region (their believed feasibility space)."
                  : "Employer will accept your offer if it falls within their believed feasibility space."}
              </p>
            </div>
          )}

          {/* Offer history */}
          <OfferHistory mode={mode} history={history} alpha={gameState.alpha} />

          {/* Legend */}
          <Legend mode={mode} employerRule={gameState.employerRule} />
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          marginTop: "1rem",
          paddingTop: "0.75rem",
          borderTop: "1px solid #f3f4f6",
          display: "flex",
          gap: 16,
          fontSize: 12,
          color: "#9ca3af",
          flexWrap: "wrap",
        }}
      >
        <span>
          {offersRemaining > 0
            ? `${offersRemaining} offer${offersRemaining !== 1 ? "s" : ""} remaining`
            : "Final offer placed"}
        </span>
        {gameState.agreed && (
          <span style={{ color: "#1D9E75", fontWeight: 600 }}>Deal reached!</span>
        )}
      </div>
    </div>
  );
}
