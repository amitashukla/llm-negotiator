import type { GameMode, GameState } from "../types";
import { offerUtilities, ROUNDS } from "../utils/curves";
import EdgeworthChart from "./EdgeworthChart";
import ModeBadge from "./ModeBadge";
import RoundPips from "./RoundPips";
import OfferHistory from "./OfferHistory";
import Legend from "./Legend";

interface RevealScreenProps {
  mode: GameMode;
  gameState: GameState;
  onPlayAgain: () => void;
}

export default function RevealScreen({ mode, gameState, onPlayAgain }: RevealScreenProps) {
  const alpha = gameState.alpha;
  const agreed = gameState.agreed;
  const history = gameState.history ?? [];
  const dealReached = agreed != null;

  const agreedValsCandidate =
    agreed && alpha != null ? offerUtilities(agreed.xH, agreed.yH, alpha) : null;

  return (
    <div style={{ padding: "1.25rem 1rem", color: "#1f2937", maxWidth: 1100, margin: "0 auto" }}>
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
            {dealReached ? "Deal reached!" : "No deal — game over"}
          </h2>
          <p style={{ fontSize: 12, color: "#9ca3af", margin: 0 }}>
            All hidden information is now revealed
          </p>
        </div>
        <RoundPips
          round={ROUNDS + 1}
          historyLength={history.length}
          phase={gameState.phase}
        />
        <ModeBadge mode={mode} />
      </div>

      {/* Two-column layout */}
      <div style={{ display: "flex", gap: "1.5rem", alignItems: "flex-start", flexWrap: "wrap" }}>
        {/* Chart (reveal mode — all layers visible) */}
        <div style={{ flex: "0 0 auto" }}>
          <EdgeworthChart
            mode="reveal"
            offers={gameState.offers ?? []}
            pendingPoint={null}
            endowment={{
              xH: gameState.endowXH ?? 5,
              yH: gameState.endowYH ?? 5,
            }}
            alpha={gameState.alpha}
            alphaHat={gameState.alphaHat}
            agreedOffer={agreed}
            trueNash={gameState.trueNash}
            employerNash={gameState.nashEst}
            isPlayerTurn={false}
            onChartClick={() => undefined}
          />
        </div>

        {/* Sidebar */}
        <div
          style={{
            flex: 1,
            minWidth: 220,
            display: "flex",
            flexDirection: "column",
            gap: 10,
          }}
        >
          {/* Deal summary */}
          <div
            style={{
              background: dealReached ? "#f0fdf4" : "#fff7f7",
              border: `1px solid ${dealReached ? "#bbf7d0" : "#fecaca"}`,
              borderRadius: 10,
              padding: "0.875rem 1rem",
            }}
          >
            <p
              style={{
                margin: "0 0 6px",
                fontSize: 14,
                fontWeight: 700,
                color: dealReached ? "#15803d" : "#b91c1c",
              }}
            >
              {dealReached ? "Deal reached" : "No deal"}
            </p>
            {dealReached && agreed && agreedValsCandidate && (
              <>
                <p style={{ margin: "0 0 3px", fontSize: 12, color: "#6b7280" }}>
                  {agreed.type === "candidate"
                    ? "Employer accepted your offer"
                    : "You accepted the employer's offer"}
                </p>
                <p style={{ margin: "0 0 3px", fontSize: 12, color: "#6b7280" }}>
                  Final allocation: ({agreed.xH.toFixed(2)}, {agreed.yH.toFixed(2)})
                </p>
                <p style={{ margin: "0 0 3px", fontSize: 12, color: "#6b7280" }}>
                  Your utility (U_c): <strong>{agreedValsCandidate.candidateU.toFixed(3)}</strong>
                </p>
                <p style={{ margin: 0, fontSize: 12, color: "#6b7280" }}>
                  Employer utility (U_e): <strong>{agreedValsCandidate.employerU.toFixed(3)}</strong>
                </p>
              </>
            )}
            {!dealReached && (
              <p style={{ margin: 0, fontSize: 12, color: "#6b7280" }}>
                No agreement was reached in {ROUNDS} rounds.
              </p>
            )}
          </div>

          {/* Revealed: Employer's true alpha */}
          <div
            style={{
              background: "#fff",
              border: "1px solid #e5e7eb",
              borderLeft: "3px solid #7F77DD",
              borderRadius: 10,
              padding: "0.875rem 1rem",
            }}
          >
            <p style={{ margin: "0 0 6px", fontSize: 13, fontWeight: 600, color: "#374151" }}>
              Revealed: Employer preferences
            </p>
            <p style={{ margin: "0 0 4px", fontSize: 12, color: "#6b7280" }}>
              Employer alpha (fixed): <strong>0.8</strong>
            </p>
            <p style={{ margin: "0 0 4px", fontSize: 12, color: "#6b7280" }}>
              Your true alpha: <strong style={{ color: "#111827" }}>{alpha != null ? alpha.toFixed(3) : "—"}</strong>
            </p>
            <p style={{ margin: 0, fontSize: 12, color: "#6b7280" }}>
              Employer&apos;s inferred α̂: <strong style={{ color: "#534AB7" }}>{gameState.alphaHat.toFixed(3)}</strong>
            </p>
          </div>

          {/* Nash points */}
          {(gameState.trueNash || gameState.nashEst) && (
            <div
              style={{
                background: "#fff",
                border: "1px solid #e5e7eb",
                borderRadius: 10,
                padding: "0.875rem 1rem",
              }}
            >
              <p style={{ margin: "0 0 6px", fontSize: 13, fontWeight: 600, color: "#374151" }}>
                Nash points
              </p>
              {gameState.trueNash && (
                <p style={{ margin: "0 0 4px", fontSize: 12, color: "#6b7280" }}>
                  True Nash (Nash*): ({gameState.trueNash.xH.toFixed(2)}, {gameState.trueNash.yH.toFixed(2)})
                </p>
              )}
              {gameState.nashEst && (
                <p style={{ margin: 0, fontSize: 12, color: "#6b7280" }}>
                  Employer&apos;s Nash guess (Nasĥ): ({gameState.nashEst.xH.toFixed(2)}, {gameState.nashEst.yH.toFixed(2)})
                </p>
              )}
            </div>
          )}

          {/* Offer history (full) */}
          <OfferHistory mode="reveal" history={history} alpha={gameState.alpha} />

          {/* Legend (reveal mode) */}
          <Legend mode="reveal" />
        </div>
      </div>

      {/* Footer */}
      <div style={{ marginTop: "1.5rem", paddingTop: "1rem", borderTop: "1px solid #f3f4f6" }}>
        <button
          onClick={onPlayAgain}
          style={{
            background: "#111827",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            padding: "10px 24px",
            fontSize: 14,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Play again
        </button>
      </div>
    </div>
  );
}
