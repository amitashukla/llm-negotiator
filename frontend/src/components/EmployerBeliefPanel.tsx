import type { Posterior, NashEstimate } from "../types";

interface EmployerBeliefPanelProps {
  posterior: Posterior;
  alphaHat: number;
  trueAlpha: number | null;
  nashGuess: NashEstimate | null;
}

export default function EmployerBeliefPanel({
  posterior,
  alphaHat,
  trueAlpha,
  nashGuess,
}: EmployerBeliefPanelProps) {
  return (
    <div
      style={{
        background: "#fff",
        border: "1px solid #e5e7eb",
        borderRadius: 10,
        padding: "0.875rem 1rem",
        borderLeft: "3px solid #7F77DD",
      }}
    >
      <p style={{ margin: "0 0 8px", fontSize: 13, fontWeight: 600, color: "#374151" }}>
        Employer&apos;s belief
      </p>
      <p style={{ margin: "0 0 4px", fontSize: 12, color: "#6b7280" }}>
        Posterior: Beta({posterior.a.toFixed(1)}, {posterior.b.toFixed(1)})
      </p>
      <p style={{ margin: "0 0 4px", fontSize: 12, color: "#6b7280" }}>
        Inferred α̂ = <strong style={{ color: "#534AB7" }}>{alphaHat.toFixed(3)}</strong>
      </p>
      <p style={{ margin: "0 0 4px", fontSize: 12, color: "#6b7280" }}>
        True α = <strong style={{ color: "#111827" }}>{trueAlpha != null ? trueAlpha.toFixed(3) : "—"}</strong>
      </p>
      {nashGuess ? (
        <p style={{ margin: 0, fontSize: 12, color: "#6b7280" }}>
          Nash guess: ({nashGuess.xH.toFixed(2)}, {nashGuess.yH.toFixed(2)})
        </p>
      ) : (
        <p style={{ margin: 0, fontSize: 12, color: "#9ca3af" }}>Nash guess: —</p>
      )}
    </div>
  );
}
