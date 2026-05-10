import { ROUNDS } from "../utils/curves";
import type { Phase } from "../types";

interface RoundPipsProps {
  round: number;
  historyLength: number;
  phase: Phase;
}

export default function RoundPips({ round, historyLength, phase }: RoundPipsProps) {
  return (
    <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
      {Array.from({ length: ROUNDS }, (_, i) => {
        const n = i + 1;
        const isDone = n <= historyLength || (phase === "done" && n <= historyLength);
        const isActive = n === round && phase === "play";
        return (
          <div
            key={n}
            title={`Round ${n}`}
            style={{
              width: 20,
              height: 20,
              borderRadius: "50%",
              background: isDone ? "#1D9E75" : "transparent",
              border: isDone
                ? "2px solid #1D9E75"
                : isActive
                ? "2px solid #1D9E75"
                : "2px solid #d1d5db",
              flexShrink: 0,
            }}
          />
        );
      })}
    </div>
  );
}
