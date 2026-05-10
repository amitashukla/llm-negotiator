import type { GameMode, HistoryEntry } from "../types";
import { offerUtilities } from "../utils/curves";

interface OfferHistoryProps {
  mode: GameMode | "reveal";
  history: HistoryEntry[];
  alpha: number | null;
}

export default function OfferHistory({ mode, history, alpha }: OfferHistoryProps) {
  if (history.length === 0) return null;
  const showEmployer = mode === "omniscient" || mode === "reveal";

  return (
    <div
      style={{
        background: "#fff",
        border: "1px solid #e5e7eb",
        borderRadius: 10,
        padding: "0.875rem 1rem",
        maxHeight: 240,
        overflowY: "auto",
      }}
    >
      <p style={{ margin: "0 0 8px", fontSize: 13, fontWeight: 600, color: "#374151" }}>
        Offer history
      </p>
      {history.map((h) => {
        const cVals = alpha != null ? offerUtilities(h.candidate.xH, h.candidate.yH, alpha) : null;
        const eVals = alpha != null ? offerUtilities(h.employer.xH, h.employer.yH, alpha) : null;

        return (
          <div
            key={h.round}
            style={{
              marginBottom: 8,
              paddingBottom: 8,
              borderBottom: "1px solid #f3f4f6",
              fontSize: 12,
              color: "#6b7280",
            }}
          >
            <div style={{ fontWeight: 600, color: "#374151", marginBottom: 2 }}>Round {h.round}</div>
            <div>
              <span style={{ color: "#378ADD", fontWeight: 600 }}>E{h.round}</span>{" "}
              ({h.employer.xH.toFixed(2)}, {h.employer.yH.toFixed(2)}){" "}
              {eVals != null && (
                <>
                  U_c={eVals.candidateU.toFixed(3)}
                  {showEmployer && <> · U_e={eVals.employerU.toFixed(3)}</>}
                </>
              )}
              {alpha == null && "—"}
            </div>
            <div>
              <span style={{ color: "#639922", fontWeight: 600 }}>C{h.round}</span>{" "}
              ({h.candidate.xH.toFixed(2)}, {h.candidate.yH.toFixed(2)}){" "}
              {cVals != null && (
                <>
                  U_c={cVals.candidateU.toFixed(3)}
                  {showEmployer && <> · U_e={cVals.employerU.toFixed(3)}</>}
                </>
              )}
              {alpha == null && "—"}
            </div>
          </div>
        );
      })}
    </div>
  );
}
